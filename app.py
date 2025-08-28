import os
import json
import threading
import time
from datetime import datetime
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    JoinEvent, MemberJoinedEvent, MemberLeftEvent
)

app = Flask(__name__)

# ==== المتغيرات ====
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")
ADMIN_USER_ID = os.getenv("USER_ID")  # أدمن رئيسي

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
            "admins": [ADMIN_USER_ID],
            "lurking": False,
            "lurkers": [],
            "members": {}
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
        lurkers.append({"id": user_id, "name": name, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
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

        # 📩 إشعار دائم للخاص عند دخول أي عضو (حتى لو لم يرسل رسالة)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = (
            f"🔔 عضو جديد دخل المجموعة!\n"
            f"👤 الاسم: {name}\n"
            f"👥 المجموعة: {group_name}\n"
            f"🕒 الوقت: {ts}"
        )
        dm_admin(msg)

        # 🔹 تسجيل العضو في قائمة المتصلين إذا التتبع مفعل فقط
        if group_data[group_id]["lurking"]:
            add_lurker(group_id, uid, name)

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
        group_data[group_id]["lurkers"] = [l for l in group_data[group_id]["lurkers"] if l["id"] != uid]
    save_data()

# ==== الرسائل ====
@handler.add(MessageEvent, message=TextMessage)
def on_message(event):
    group_id = event.source.group_id
    user_id = event.source.user_id
    text = (event.message.text or "").strip()

    init_group(group_id)

    # سجل التفاعل لو التتبع مفعّل
    if group_data[group_id]["lurking"]:
        name = safe_get_profile(group_id, user_id)
        add_lurker(group_id, user_id, name)

    # ===== الرد على منشن الأدمن الرئيسي =====
    if f"@{ADMIN_USER_ID}" in text or f"<@{ADMIN_USER_ID}>" in text:
        sender_name = safe_get_profile(group_id, user_id)
        admin_name = safe_get_profile(group_id, ADMIN_USER_ID)
        try:
            dm_admin(f"يا {sender_name}، {admin_name} مشغول الآن 🌸")
        except LineBotApiError:
            pass

    # ===== أوامر البوت =====
    if text.startswith(".help"):
        help_text = (
            "أوامر البوت:\n"
            ".lurk on  - تفعيل التتبع\n"
            ".lurk off - إيقاف التتبع\n"
            ".lurk list - عرض المتصلين\n"
            ".gadmin @user - تعيين أدمن\n"
            ".radmin @user - إزالة أدمن\n"
            ".kick @user - طرد عضو\n"
            ".all - منشن للجميع\n"
            ".clear - مسح المتصلين\n"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(help_text))
        return

    elif text == ".lurk on":
        if is_admin(group_id, user_id):
            group_data[group_id]["lurking"] = True
            group_data[group_id]["lurkers"] = []
            save_data()
            line_bot_api.reply_message(event.reply_token, TextSendMessage("✅ تم تفعيل التتبع."))
            group_name = safe_get_group_name(group_id)
            dm_admin(f"✅ تم تفعيل التتبع في: {group_name}\nسيصلك إشعار عند تفاعل أي عضو.")
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage("❌ ليس لديك صلاحية."))

    elif text == ".lurk off":
        if is_admin(group_id, user_id):
            group_data[group_id]["lurking"] = False
            save_data()
            line_bot_api.reply_message(event.reply_token, TextSendMessage("⛔ تم إيقاف التتبع."))
            group_name = safe_get_group_name(group_id)
            dm_admin(f"⛔ تم إيقاف التتبع في: {group_name}.")
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage("❌ ليس لديك صلاحية."))

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
            line_bot_api.reply_message(event.reply_token, TextSendMessage("❌ ليس لديك صلاحية."))

    elif text == ".all":
        members = list(group_data[group_id]["members"].values())
        if members:
            mention_text = " ".join(members)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(f"📢 منشن للجميع:\n{mention_text}"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage("❌ لا يوجد أعضاء."))

# ==== تذكير الصلاة على النبي ﷺ كل 4 ساعات ====
def reminder_loop():
    while True:
        time.sleep(14400)  # 4 ساعات
        try:
            dm_admin("🌸 صلوا على رسول الله ﷺ 🌸")
        except:
            pass

threading.Thread(target=reminder_loop, daemon=True).start()

# ==== Runner ====
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
