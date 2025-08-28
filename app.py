import os
import json
import time
import threading
import logging
from datetime import datetime, timedelta
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    JoinEvent, MemberJoinedEvent, MemberLeftEvent
)

# ======================= إعدادات عامة =======================
app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")
ADMIN_USER_ID = os.getenv("USER_ID")  # معرف الأدمن الرئيسي (مالك البوت)

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET or not ADMIN_USER_ID:
    raise Exception("يرجى ضبط متغيرات البيئة CHANNEL_ACCESS_TOKEN و CHANNEL_SECRET و USER_ID")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# ======================= التسجيل (Logs) =======================
logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("bot")

# ======================= التخزين =======================
DATA_FILE = "group_data.json"

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        group_data = json.load(f)
else:
    group_data = {}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(group_data, f, ensure_ascii=False, indent=2)

def init_group(group_id):
    if group_id not in group_data:
        group_data[group_id] = {
            "admins": [ADMIN_USER_ID],  # قائمة الأدمنز
            "lurking": False,           # وضع التتبع
            "lurkers": [],              # قائمة المتفاعلين (سجل)
            "members": {},              # user_id -> display_name
            "owner_name": None,         # يتم التقاطه تلقائيًا من أول رسالة يكتبها الأدمن داخل المجموعة
            "notified_active": [],      # من تم تبليغ الأدمن أنهم متواجدون (لتجنب التكرار)
            "reminder": True,           # تذكير "صلّوا على رسول الله ﷺ" كل 4 ساعات
            "last_reminder": None       # آخر وقت تم فيه الإرسال
        }
        save_data()

# ======================= أدوات مساعدة =======================
def push_with_retry(to, message, tries=3, delay=1.5):
    """محاولة الإرسال مع إعادة المحاولة في حال الفشل."""
    for i in range(tries):
        try:
            line_bot_api.push_message(to, message)
            return True
        except LineBotApiError as e:
            log.warning(f"push retry {i+1}/{tries} failed: {e}")
            time.sleep(delay)
    return False

def dm_admin(text):
    """إرسال خاص للإدمن مع معالجة الأخطاء."""
    ok = push_with_retry(ADMIN_USER_ID, TextSendMessage(text))
    if not ok:
        log.error("فشل إرسال DM للإدمن.")
    return ok

def safe_get_profile(group_id, user_id):
    try:
        p = line_bot_api.get_group_member_profile(group_id, user_id)
        return p.display_name
    except LineBotApiError:
        return "مستخدم"

def safe_get_group_name(group_id):
    try:
        summary = line_bot_api.get_group_summary(group_id)
        return summary.group_name
    except LineBotApiError:
        return f"Group-{group_id[-6:]}"

def add_lurker(group_id, user_id, name):
    init_group(group_id)
    lurkers = group_data[group_id]["lurkers"]
    if not any(l['id'] == user_id for l in lurkers):
        lurkers.append({
            "id": user_id,
            "name": name,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        save_data()

def is_admin(group_id, user_id):
    init_group(group_id)
    return user_id in group_data[group_id]["admins"]

def add_admin(group_id, user_id):
    init_group(group_id)
    if user_id not in group_data[group_id]["admins"]:
        group_data[group_id]["admins"].append(user_id)
        save_data()

def remove_admin(group_id, user_id):
    init_group(group_id)
    if user_id in group_data[group_id]["admins"]:
        group_data[group_id]["admins"].remove(user_id)
        save_data()

# ======================= مضاد السبام للأوامر =======================
# structure: rate_limit[(group_id, user_id)] = [timestamps...]
rate_limit = {}

def allow_command(group_id, user_id, max_cmd=3, window_sec=60):
    key = (group_id, user_id)
    now = time.time()
    lst = rate_limit.get(key, [])
    lst = [t for t in lst if now - t < window_sec]
    if len(lst) >= max_cmd:
        rate_limit[key] = lst
        return False
    lst.append(now)
    rate_limit[key] = lst
    return True

# ======================= جدولة التذكير كل 4 ساعات =======================
def reminder_worker():
    while True:
        try:
            now = datetime.now()
            for gid, g in list(group_data.items()):
                try:
                    if not g.get("reminder", True):
                        continue
                    last = g.get("last_reminder")
                    if last:
                        last_dt = datetime.fromisoformat(last)
                    else:
                        last_dt = now - timedelta(hours=5)  # لإرسال أولي سريع إن مر وقت طويل
                    if (now - last_dt) >= timedelta(hours=4):
                        txt = "💚 صلّوا على رسول الله ﷺ"
                        ok = push_with_retry(gid, TextSendMessage(txt))
                        if ok:
                            group_data[gid]["last_reminder"] = now.isoformat()
                            save_data()
                except Exception as e:
                    log.error(f"reminder_worker error for group {gid}: {e}")
        except Exception as e:
            log.error(f"reminder loop error: {e}")
        time.sleep(60)  # فحص كل دقيقة

# تشغيل الثريد في الخلفية
threading.Thread(target=reminder_worker, daemon=True).start()

# ======================= Webhook =======================
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    if not signature:
        abort(400)
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

# ======================= الأحداث =======================
@handler.add(JoinEvent)
def on_join(event):
    group_id = event.source.group_id
    init_group(group_id)
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage("مرحباً! البوت جاهز.\nاستخدم .help لمشاهدة الأوامر.")
    )
    log.info(f"Joined group: {group_id}")

@handler.add(MemberJoinedEvent)
def on_member_joined(event):
    group_id = event.source.group_id
    init_group(group_id)
    group_name = safe_get_group_name(group_id)

    for member in event.joined.members:
        uid = member.user_id
        name = safe_get_profile(group_id, uid)
        group_data[group_id]["members"][uid] = name

        # تتبع أقوى: عند التفعيل أرسل DM فوري للأدمن عند الدخول
        if group_data[group_id]["lurking"]:
            add_lurker(group_id, uid, name)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            msg = f"🔔 دخول عضو جديد\n👤 الاسم: {name}\n👥 المجموعة: {group_name}\n🕒 الوقت: {ts}"
            dm_admin(msg)

    save_data()

@handler.add(MemberLeftEvent)
def on_member_left(event):
    group_id = event.source.group_id
    init_group(group_id)
    for member in event.left.members:
        uid = member.user_id
        name = group_data[group_id]["members"].pop(uid, "مستخدم")
        try:
            line_bot_api.push_message(group_id, TextSendMessage(f"👋 وداعاً {name}!"))
        except LineBotApiError:
            pass
        # نظّف من lurkers و notified_active
        group_data[group_id]["lurkers"] = [l for l in group_data[group_id]["lurkers"] if l["id"] != uid]
        group_data[group_id]["notified_active"] = [x for x in group_data[group_id]["notified_active"] if x != uid]
    save_data()

@handler.add(MessageEvent, message=TextMessage)
def on_message(event):
    group_id = event.source.group_id
    user_id  = event.source.user_id
    text = (event.message.text or "").strip()

    init_group(group_id)

    # التقط اسم المالك تلقائيًا من أول رسالة يكتبها الأدمن داخل المجموعة
    if user_id == ADMIN_USER_ID and not group_data[group_id].get("owner_name"):
        owner_name = safe_get_profile(group_id, user_id)
        group_data[group_id]["owner_name"] = owner_name
        save_data()

    # إذا التتبع مفعل: سجل أول تفاعل وبلّغ الأدمن "صار متواجد الآن" مرة واحدة لكل عضو
    if group_data[group_id]["lurking"]:
        name = safe_get_profile(group_id, user_id)
        add_lurker(group_id, user_id, name)

        if user_id not in group_data[group_id]["notified_active"]:
            group_data[group_id]["notified_active"].append(user_id)
            save_data()
            group_name = safe_get_group_name(group_id)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            dm_admin(f"🟢 عضو صار متواجد الآن\n👤 {name}\n👥 {group_name}\n🕒 {ts}")

    # ===== الأوامر =====
    if text.startswith("."):
        # مضاد السبام
        if not allow_command(group_id, user_id):
            try:
                line_bot_api.reply_message(event.reply_token, TextSendMessage("⛔ تم إيقاف السبام مؤقتًا."))
            except LineBotApiError:
                pass
            return

    if text.startswith(".help"):
        help_text = (
            "أوامر البوت:\n"
            ".lurk on  - تفعيل التتبع + DM للأدمن عند دخول/تواجد أي عضو\n"
            ".lurk off - إيقاف التتبع\n"
            ".lurk list - عرض المتصلين\n"
            ".gadmin @user - تعيين أدمن\n"
            ".radmin @user - إزالة أدمن\n"
            ".kick @user - طرد عضو (للأدمن فقط)\n"
            ".all - منشن للجميع\n"
            ".clear - مسح قائمة المتصلين\n"
            ".reminder on/off - تفعيل/إيقاف تذكير (كل 4 ساعات)\n"
            ".ping - اختبار استجابة البوت\n"
            ".stats - إحصائيات سريعة\n"
            ".resetnotify - مسح قائمة (تم تبليغ أنهم متواجدون)\n"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(help_text))
        return

    if text == ".lurk on":
        if is_admin(group_id, user_id):
            group_data[group_id]["lurking"] = True
            group_data[group_id]["lurkers"] = []
            group_data[group_id]["notified_active"] = []
            save_data()
            line_bot_api.reply_message(event.reply_token, TextSendMessage("✅ تم تفعيل التتبع."))
            group_name = safe_get_group_name(group_id)
            dm_admin(f"✅ تم تفعيل التتبع في المجموعة: {group_name}\nسيصلك إشعار بالخاص عند دخول أو تواجد أي عضو.")
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage("❌."))

    elif text == ".lurk off":
        if is_admin(group_id, user_id):
            group_data[group_id]["lurking"] = False
            save_data()
            line_bot_api.reply_message(event.reply_token, TextSendMessage("⛔ تم إيقاف التتبع."))
            group_name = safe_get_group_name(group_id)
            dm_admin(f"⛔ تم إيقاف التتبع في المجموعة: {group_name}.")
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage("❌."))

    elif text == ".lurk list":
        lurkers = group_data[group_id]["lurkers"]
        if lurkers:
            list_text = "👀 المتصلون:\n" + "\n".join([f"- {l['name']} ({l['time']})" for l in lurkers])
        else:
            list_text = "📭 لا يوجد متصلون مسجلون."
        line_bot_api.reply_message(event.reply_token, TextSendMessage(list_text))

    elif text == ".clear":
        if is_admin(group_id, user_id):
            group_data[group_id]["lurkers"] = []
            group_data[group_id]["notified_active"] = []
            save_data()
            line_bot_api.reply_message(event.reply_token, TextSendMessage("🗑️ تم مسح قائمة المتصلين والإشعارات."))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage("❌."))

    elif text.startswith(".gadmin"):
        if is_admin(group_id, user_id):
            if "@" in text:
                target_name = text.split("@", 1)[1].strip()
                try:
                    target_id = None
                    for uid, name in group_data[group_id]["members"].items():
                        if target_name in name:
                            target_id = uid
                            break
                    if target_id:
                        add_admin(group_id, target_id)
                        line_bot_api.reply_message(event.reply_token, TextSendMessage(f"✅ تم تعيين {target_name} كأدمن."))
                    else:
                        line_bot_api.reply_message(event.reply_token, TextSendMessage("❌ المستخدم غير موجود في المجموعة."))
                except Exception as e:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(f"❌ خطأ: {str(e)}"))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage("❌ الرجاء استخدام @username بعد الأمر."))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage("❌ فقط الأدمن يمكنه تعيين أدمن جديد."))

    elif text.startswith(".radmin"):
        if is_admin(group_id, user_id):
            if "@" in text:
                target_name = text.split("@", 1)[1].strip()
                try:
                    target_id = None
                    for uid, name in group_data[group_id]["members"].items():
                        if target_name in name:
                            target_id = uid
                            break
                    if target_id:
                        remove_admin(group_id, target_id)
                        line_bot_api.reply_message(event.reply_token, TextSendMessage(f"✅ تم إزالة {target_name} من الأدمن."))
                    else:
                        line_bot_api.reply_message(event.reply_token, TextSendMessage("❌ المستخدم غير موجود في المجموعة."))
                except Exception as e:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(f"❌ خطأ: {str(e)}"))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage("❌ الرجاء استخدام @username بعد الأمر."))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage("❌ فقط الأدمن يمكنه إزالة الأدمن."))

    elif text.startswith(".kick"):
        if is_admin(group_id, user_id):
            if "@" in text:
                target_name = text.split("@", 1)[1].strip()
                try:
                    target_id = None
                    for uid, name in group_data[group_id]["members"].items():
                        if target_name in name:
                            target_id = uid
                            break
                    if target_id:
                        line_bot_api.kickout_from_group(group_id, target_id)
                        line_bot_api.reply_message(event.reply_token, TextSendMessage(f"✅ تم طرد {target_name} من المجموعة."))
                    else:
                        line_bot_api.reply_message(event.reply_token, TextSendMessage("❌ المستخدم غير موجود في المجموعة."))
                except Exception as e:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(f"❌ خطأ: {str(e)}"))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage("❌ الرجاء استخدام @username بعد الأمر."))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage("❌ فقط الأدمن يمكنه طرد الأعضاء."))

    elif text == ".all":
        members = list(group_data[group_id]["members"].values())
        if members:
            mention_text = " ".join(members)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(f"📢 منشن للجميع:\n{mention_text}"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage("❌ لا يوجد أعضاء في المجموعة."))

    elif text == ".ping":
        t0 = time.time()
        try:
            line_bot_api.reply_message(event.reply_token, TextSendMessage("pong"))
        except LineBotApiError:
            pass
        ms = int((time.time() - t0) * 1000)
        dm_admin(f"🏓 ping: ~{ms}ms")

    elif text == ".stats":
        g = group_data[group_id]
        stats = (
            f"📊 إحصائيات المجموعة:\n"
            f"- أعضاء مُسجّلون: {len(g['members'])}\n"
            f"- متصلون (سجل): {len(g['lurkers'])}\n"
            f"- تذكير 4 ساعات: {'مفعل' if g.get('reminder', True) else 'متوقف'}\n"
            f"- اسم المالك: {g.get('owner_name') or 'غير محدد بعد'}"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(stats))

    elif text == ".resetnotify":
        if is_admin(group_id, user_id):
            group_data[group_id]["notified_active"] = []
            save_data()
            line_bot_api.reply_message(event.reply_token, TextSendMessage("✅ تم مسح قائمة الإشعارات (notified_active)."))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage("❌."))

    elif text == ".reminder on":
        if is_admin(group_id, user_id):
            group_data[group_id]["reminder"] = True
            save_data()
            line_bot_api.reply_message(event.reply_token, TextSendMessage("✅ تم تفعيل التذكير كل 4 ساعات."))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage("❌."))

    elif text == ".reminder off":
        if is_admin(group_id, user_id):
            group_data[group_id]["reminder"] = False
            save_data()
            line_bot_api.reply_message(event.reply_token, TextSendMessage("⛔ تم إيقاف التذكير."))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage("❌."))

    else:
        # ===== رد المنشن لاسم المالك =====
        owner_name = group_data[group_id].get("owner_name")
        if owner_name and owner_name in text:
            try:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(f"👑 {owner_name} مشغول الآن، يمكنك ترك رسالة له في الخاص 📩")
                )
            except LineBotApiError:
                pass

# ======================= Runner =======================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
        
