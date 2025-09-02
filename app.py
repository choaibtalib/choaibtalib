import os
import json
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    JoinEvent, MemberJoinedEvent, MemberLeftEvent,
    TemplateSendMessage, ButtonsTemplate, MessageTemplateAction
)

app = Flask(__name__)

# ===== إعداد المتغيرات (اضبـطهم في البيئة) =====
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")
ADMIN_USER_ID = os.getenv("USER_ID")  # أدمن رئيسي (صاحب البوت)

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET or not ADMIN_USER_ID:
    raise Exception("يرجى ضبط متغيرات البيئة CHANNEL_ACCESS_TOKEN و CHANNEL_SECRET و USER_ID")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# ===== التخزين =====
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
            "admins": [ADMIN_USER_ID],
            "lurking": False,
            "lurkers": [],
            "members": {},            # user_id -> display_name
            "war_active": False,
            "warriors_ids": [],       # user ids of participants
            "surrender_ids": [],      # user ids of surrendered
            "reminder": True,         # تذكير الصلوات للمجموعة
            "last_reminder": None
        }
        save_data()

# ===== أدوات مساعدة =====
def push_with_retry(to, message, tries=3, delay=1.5):
    for i in range(tries):
        try:
            line_bot_api.push_message(to, message)
            return True
        except LineBotApiError as e:
            print(f"[push retry {i+1}/{tries}] error: {e}")
            time.sleep(delay)
    return False

def dm_admin(text):
    # ترسل إشعار خاص للأدمن (مع إعادة المحاولة)
    return push_with_retry(ADMIN_USER_ID, TextSendMessage(text))

def is_admin(group_id, user_id):
    init_group(group_id)
    # فقط الأدمن الأساسي يسمح لجميع الأوامر
    return user_id == ADMIN_USER_ID

def add_member(group_id, user_id, name):
    init_group(group_id)
    group_data[group_id]["members"][user_id] = name
    save_data()

def add_lurker(group_id, user_id, name):
    init_group(group_id)
    lurkers = group_data[group_id]["lurkers"]
    if not any(l['id'] == user_id for l in lurkers):
        lurkers.append({"id": user_id, "name": name, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        save_data()

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

def id_list_to_names(group_id, id_list):
    names = []
    members = group_data[group_id].get("members", {})
    for uid in id_list:
        name = members.get(uid)
        if not name:
            # حاول استرجاع الاسم وتحديث السجل
            try:
                name = safe_get_profile(group_id, uid)
            except:
                name = "مستخدم"
            members[uid] = name
        names.append(name)
    # حفظ تحديثات الأسماء إن طُلِب
    group_data[group_id]["members"] = members
    save_data()
    return names

# ===== استفتاء الحرب: نرسل ملخص كامل ثم أزرار التصويت =====
def send_war_status(group_id):
    init_group(group_id)
    warriors_ids = group_data[group_id].get("warriors_ids", [])
    surrender_ids = group_data[group_id].get("surrender_ids", [])
    all_member_ids = list(group_data[group_id].get("members", {}).keys())

    warriors_names = id_list_to_names(group_id, warriors_ids)
    surrender_names = id_list_to_names(group_id, surrender_ids)
    non_participants_ids = [uid for uid in all_member_ids if uid not in set(warriors_ids) and uid not in set(surrender_ids)]
    non_participants_names = id_list_to_names(group_id, non_participants_ids)

    full_msg = (
        "⚔️ استفتاء الحرب (مباشر)\n\n"
        f"🗡️ المشاركون ({len(warriors_names)}):\n" + ("\n".join(warriors_names) if warriors_names else "لا أحد") + "\n\n"
        f"🏰 المسلمون ({len(surrender_names)}):\n" + ("\n".join(surrender_names) if surrender_names else "لا أحد") + "\n\n"
        f"🐍 المتخاذلون الذين لم يكتبوا أسماءهم ({len(non_participants_names)}):\n" + ("\n".join(non_participants_names) if non_participants_names else "لا أحد")
    )

    # نرسل الرسالة الكاملة (ليراها الجميع) ثم نرسل أزرار التصويت
    push_with_retry(group_id, TextSendMessage(full_msg))

    buttons = TemplateSendMessage(
        alt_text="استفتاء الحرب — اضغط لمشاركة موقفك",
        template=ButtonsTemplate(
            title="⚔️ اختر موقفك",
            text="اضغط أحد الخيارين:",
            actions=[
                MessageTemplateAction(label="🗡️ أشارك في الحرب", text="مشارك في الحرب"),
                MessageTemplateAction(label="🏰 أسلم قلعتني", text="أسلم قلعة")
            ]
        )
    )
    push_with_retry(group_id, buttons)

# ===== Webhook =====
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

# ===== أحداث الانضمام/المغادرة =====
@handler.add(JoinEvent)
def on_join(event):
    group_id = event.source.group_id
    init_group(group_id)
    line_bot_api.reply_message(event.reply_token, TextSendMessage("مرحباً! البوت جاهز.\nاستخدم .help لمشاهدة الأوامر."))

@handler.add(MemberJoinedEvent)
def on_member_joined(event):
    group_id = event.source.group_id
    init_group(group_id)
    group_name = safe_get_group_name(group_id)
    for member in event.joined.members:
        uid = member.user_id
        name = safe_get_profile(group_id, uid)
        add_member(group_id, uid, name)
        try:
            push_with_retry(group_id, TextSendMessage(f"🎉 أهلًا وسهلًا {name} في {group_name}!"))
        except:
            pass
    save_data()

@handler.add(MemberLeftEvent)
def on_member_left(event):
    group_id = event.source.group_id
    init_group(group_id)
    for member in event.left.members:
        uid = member.user_id
        name = group_data[group_id]["members"].pop(uid, "مستخدم")
        try:
            push_with_retry(group_id, TextSendMessage(f"👋 مع السلامة {name}! نتمنى لك التوفيق 🌸"))
        except:
            pass
        # تنظيف من القوائم
        group_data[group_id]["lurkers"] = [l for l in group_data[group_id]["lurkers"] if l["id"] != uid]
        if uid in group_data[group_id]["warriors_ids"]:
            group_data[group_id]["warriors_ids"].remove(uid)
        if uid in group_data[group_id]["surrender_ids"]:
            group_data[group_id]["surrender_ids"].remove(uid)
    save_data()

# ===== استقبال الرسائل (التصويت + أوامر الأدمن) =====
@handler.add(MessageEvent, message=TextMessage)
def on_message(event):
    group_id = event.source.group_id
    user_id = event.source.user_id
    text = (event.message.text or "").strip()
    init_group(group_id)

    # حدّث سجل الأعضاء دائماً عند أي رسالة (يحافظ على قائمة الأعضاء محدثة)
    try:
        display_name = safe_get_profile(group_id, user_id)
        add_member(group_id, user_id, display_name)
    except:
        display_name = group_data[group_id]["members"].get(user_id, "مستخدم")

    # تسجيل تفاعل في حالة التتبع مفعل
    if group_data[group_id].get("lurking"):
        add_lurker(group_id, user_id, display_name)

    # إذا الرسالة هي زر تصويت (يأتي كنص)، اسمح لأي عضو بالتصويت طالما الاستفتاء مفعّل
    if group_data[group_id].get("war_active"):
        if text == "مشارك في الحرب":
            # إذا كان في قائمة التسليم، اشيله، ثم اضيفه لقائمة المحاربين
            if user_id in group_data[group_id]["surrender_ids"]:
                group_data[group_id]["surrender_ids"].remove(user_id)
            if user_id not in group_data[group_id]["warriors_ids"]:
                group_data[group_id]["warriors_ids"].append(user_id)
            save_data()
            send_war_status(group_id)
            return

        if text == "أسلم قلعة" or text == "أسلم قلعة":
            # إذا كان في قائمة المحاربين، اشيله، ثم اضيفه لقائمة التسليم
            if user_id in group_data[group_id]["warriors_ids"]:
                group_data[group_id]["warriors_ids"].remove(user_id)
            if user_id not in group_data[group_id]["surrender_ids"]:
                group_data[group_id]["surrender_ids"].append(user_id)
            save_data()
            send_war_status(group_id)
            return

    # رد تلقائي على من ينشُد الأدمن (منشن الأدمن)
    if f"@{ADMIN_USER_ID}" in text or f"<@{ADMIN_USER_ID}>" in text:
        sender_name = display_name
        push_with_retry(group_id, TextSendMessage(f"📩 {sender_name}، صاحب المجموعة مشغول الآن. يمكنك ترك رسالة له بالخاص."))
        return

    # ===== الأوامر: للأدمن فقط =====
    if not is_admin(group_id, user_id):
        return

    if text == ".help":
        help_text = (
            "أوامر البوت (للأدمن فقط):\n"
            ".war - بدء استفتاء حرب جديد\n"
            ".war stop - إيقاف الاستفتاء\n"
            ".war result - عرض النتائج الحالية\n"
            ".lurk on/off - تفعيل/إيقاف التتبع\n"
            ".lurk list - عرض المتصلين\n"
            ".clear - مسح المتصلين\n"
            ".all - منشن للأعضاء\n"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(help_text))
        return

    if text == ".war" or text == ".war start":
        # بدء استفتاء جديد => فرّغ القوائم وفعل الاستفتاء
        group_data[group_id]["war_active"] = True
        group_data[group_id]["warriors_ids"] = []
        group_data[group_id]["surrender_ids"] = []
        save_data()
        send_war_status(group_id)
        return

    if text == ".war stop":
        group_data[group_id]["war_active"] = False
        save_data()
        line_bot_api.reply_message(event.reply_token, TextSendMessage("⛔ تم إيقاف الاستفتاء."))
        return

    if text == ".war result":
        # إرسال النتائج الحالية (بما فيها المتخاذلون)
        send_war_status(group_id)
        return

    if text in [".lurk on", ".lurk  on"]:
        group_data[group_id]["lurking"] = True
        group_data[group_id]["lurkers"] = []
        save_data()
        line_bot_api.reply_message(event.reply_token, TextSendMessage("✅ تم تفعيل التتبع."))
        return

    if text in [".lurk off", ".lurk  off"]:
        group_data[group_id]["lurking"] = False
        save_data()
        line_bot_api.reply_message(event.reply_token, TextSendMessage("⛔ تم إيقاف التتبع."))
        return

    if text == ".lurk list":
        lurkers = group_data[group_id]["lurkers"]
        if lurkers:
            list_text = "👀 المتصلون:\n" + "\n".join([f"- {l['name']} ({l['time']})" for l in lurkers])
        else:
            list_text = "📭 لا يوجد متصلون."
        line_bot_api.reply_message(event.reply_token, TextSendMessage(list_text))
        return

    if text == ".clear":
        group_data[group_id]["lurkers"] = []
        save_data()
        line_bot_api.reply_message(event.reply_token, TextSendMessage("🗑️ تم مسح قائمة المتصلين."))
        return

    if text == ".all":
        # منشن للأعضاء المسجلين في members
        members = list(group_data[group_id]["members"].values())
        mention_text = " ".join(members) if members else "❌ لا يوجد أعضاء."
        line_bot_api.reply_message(event.reply_token, TextSendMessage(f"📢 {mention_text}"))
        return

# ===== تذكير الصلاة على النبي ﷺ (كل ساعة) =====
def reminder_loop():
    while True:
        now = datetime.now()
        for gid, g in list(group_data.items()):
            try:
                if not g.get("reminder", True):
                    continue
                last = g.get("last_reminder")
                if last:
                    last_dt = datetime.fromisoformat(last)
                else:
                    # إذا لم يُحدَّد سابقًا، اجعل آخر تذكير قبل ساعة ونصف حتى لا يرسل فور التشغيل
                    last_dt = now - timedelta(hours=1, minutes=30)
                if (now - last_dt) >= timedelta(hours=1):
                    txt = "🌸 صلّوا على رسول الله ﷺ 🌸"
                    ok = push_with_retry(gid, TextSendMessage(txt))
                    if ok:
                        group_data[gid]["last_reminder"] = now.isoformat()
                        save_data()
            except Exception as e:
                print(f"[reminder error] group {gid}: {e}")
        # أرسل إشعار مختصر للأدمن بأن التذكيرات أرسلت (لمرة واحدة في كل دورة كاملة)
        try:
            dm_admin("✅ تذكير الصلاة تم إرساله للمجموعات المفعّلة.")
        except:
            pass
        time.sleep(3600)  # فاصل ساعة

# تشغيل ثريد التذكير
threading.Thread(target=reminder_loop, daemon=True).start()

# ===== Runner =====
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
                
