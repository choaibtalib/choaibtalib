import os
import json
from datetime import datetime
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    JoinEvent, MemberJoinedEvent, MemberLeftEvent
)

app = Flask(__name__)

# ==== متغيرات البيئة ====
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")
ADMIN_USER_ID = os.getenv("USER_ID")  # معرف الادمن الرئيسي

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET or not ADMIN_USER_ID:
    raise Exception("يرجى ضبط متغيرات البيئة CHANNEL_ACCESS_TOKEN و CHANNEL_SECRET و USER_ID")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# ==== التخزين ====
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
            "lurkers": [],              # من تفاعلوا
            "members": {}               # user_id -> display_name
        }
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

# ==== مساعدات ====
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

def dm_admin(text):
    """إرسال خاص للإدمن مع معالجة الأخطاء."""
    try:
        line_bot_api.push_message(ADMIN_USER_ID, TextSendMessage(text))
        return True
    except LineBotApiError:
        return False

# ==== Webhook ====
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

# ==== Events ====
@handler.add(JoinEvent)
def on_join(event):
    group_id = event.source.group_id
    init_group(group_id)
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage("مرحباً! البوت جاهز.\nاستخدم .help لمشاهدة الأوامر.")
    )

@handler.add(MemberJoinedEvent)
def on_member_joined(event):
    group_id = event.source.group_id
    init_group(group_id)
    group_name = safe_get_group_name(group_id)

    for member in event.joined.members:
        uid = member.user_id
        name = safe_get_profile(group_id, uid)
        group_data[group_id]["members"][uid] = name

        # إذا وضع التتبع مفعّل: أضف للمتصلين وابعث اسم الداخل للإدمن "بالخاص"
        if group_data[group_id]["lurking"]:
            add_lurker(group_id, uid, name)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            msg = f"🔔 دخول عضو جديد\n👤 الاسم: {name}\n👥 المجموعة: {group_name}\n🕒 الوقت: {ts}"
            sent = dm_admin(msg)
            if not sent:
                # تنبيه خفيف داخل المجموعة إذا تعذر الخاص
                try:
                    line_bot_api.push_message(group_id, TextSendMessage("⚠️ تعذّر إرسال إشعار الدخول للإدمن بالخاص."))
                except LineBotApiError:
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
            line_bot_api.push_message(group_id, TextSendMessage(f"👋 وداعاً {name}!"))
        except LineBotApiError:
            pass
        # نظّف من lurkers
        group_data[group_id]["lurkers"] = [l for l in group_data[group_id]["lurkers"] if l["id"] != uid]
    save_data()

@handler.add(MessageEvent, message=TextMessage)
def on_message(event):
    # ملاحظة: المتطلب الأساسي هو إشعار الانضمام. بقية الأوامر كما كانت.
    group_id = event.source.group_id
    user_id = event.source.user_id
    text = (event.message.text or "").strip()

    init_group(group_id)

    # سجّل تفاعل العضو إذا التتبع مفعّل
    if group_data[group_id]["lurking"]:
        name = safe_get_profile(group_id, user_id)
        add_lurker(group_id, user_id, name)

    # ===== الأوامر =====
    if text.startswith(".help"):
        help_text = (
            "أوامر البوت:\n"
            ".lurk on  - تفعيل تتبع المتصلين + إشعار الإدمن بالخاص عند دخول أي عضو\n"
            ".lurk off - إيقاف التتبع\n"
            ".lurk list - عرض المتصلين\n"
            ".gadmin @user - تعيين أدمن\n"
            ".radmin @user - إزالة أدمن\n"
            ".kick @user - طرد عضو (للأدمن فقط)\n"
            ".all - منشن للجميع\n"
            ".clear - مسح قائمة المتصلين\n"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(help_text))
        return

    if text == ".lurk on":
        if is_admin(group_id, user_id):
            group_data[group_id]["lurking"] = True
            group_data[group_id]["lurkers"] = []
            save_data()
            line_bot_api.reply_message(event.reply_token, TextSendMessage("✅ تم تفعيل التتبع."))
            # أرسل تأكيدًا للإدمن بالخاص
            group_name = safe_get_group_name(group_id)
            dm_admin(f"✅ تم تفعيل التتبع في المجموعة: {group_name}\nسيصلك إشعار خاص عند دخول أي عضو جديد.")
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
            save_data()
            line_bot_api.reply_message(event.reply_token, TextSendMessage("🗑️ تم مسح قائمة المتصلين."))
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

    else:
        # لا شيء
        pass

# ==== Runner ====
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
