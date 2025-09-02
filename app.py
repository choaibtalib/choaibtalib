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
    JoinEvent, MemberJoinedEvent, MemberLeftEvent,
    PostbackEvent
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
            "members": {},
            "sal_active": False,
            "war_active": False,
            "war_participants": [],
            "war_muslims": [],
            "war_non": []
        }
        save_data()

def is_admin(group_id, user_id):
    init_group(group_id)
    return user_id in group_data[group_id]["admins"]

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

        # رسالة الترحيب
        try:
            line_bot_api.push_message(group_id, TextSendMessage(f"🌸 أهلاً وسهلاً {name}!"))
        except LineBotApiError:
            pass

        # تسجيل العضو في قائمة التتبع إذا مفعل
        if group_data[group_id]["lurking"]:
            add_lurker(group_id, uid, name)

        # إشعار الأدمن
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dm_admin(f"🔔 عضو جديد دخل المجموعة!\n👤 {name}\n👥 {group_name}\n🕒 {ts}")

    save_data()

@handler.add(MemberLeftEvent)
def on_member_left(event):
    group_id = event.source.group_id
    init_group(group_id)
    for member in event.left.members:
        uid = member.user_id
        name = group_data[group_id]["members"].pop(uid, "مستخدم")
        try:
            line_bot_api.push_message(group_id, TextSendMessage(f"👋 مع السلامة {name}!"))
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

    # ===== أوامر البوت =====
    if text.startswith(".help"):
        help_text = (
            "أوامر البوت:\n"
            ".lurk on  - تفعيل التتبع\n"
            ".lurk off - إيقاف التتبع\n"
            ".lurk list - عرض المتصلين\n"
            ".sal - تفعيل الصلاة على النبي كل ساعة في المجموعة\n"
            ".war - بدء استفتاء الحرب\n"
            ".war r - عرض النتائج\n"
            ".war s - إيقاف الاستفتاء\n"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(help_text))
        return

    # ===== التتبع =====
    elif text == ".lurk on" and is_admin(group_id, user_id):
        group_data[group_id]["lurking"] = True
        group_data[group_id]["lurkers"] = []
        save_data()
        line_bot_api.reply_message(event.reply_token, TextSendMessage("✅ تم تفعيل التتبع."))
    elif text == ".lurk off" and is_admin(group_id, user_id):
        group_data[group_id]["lurking"] = False
        save_data()
        line_bot_api.reply_message(event.reply_token, TextSendMessage("⛔ تم إيقاف التتبع."))
    elif text == ".lurk list" and is_admin(group_id, user_id):
        lurkers = group_data[group_id]["lurkers"]
        if lurkers:
            list_text = "👀 المتصلون:\n" + "\n".join([f"- {l['name']} ({l['time']})" for l in lurkers])
        else:
            list_text = "📭 لا يوجد متصلون مسجلون."
        line_bot_api.reply_message(event.reply_token, TextSendMessage(list_text))

    # ===== الصلاة على النبي =====
    elif text == ".sal" and is_admin(group_id, user_id):
        group_data[group_id]["sal_active"] = True
        save_data()
        line_bot_api.reply_message(event.reply_token, TextSendMessage("🌸 تم تفعيل تذكير الصلاة على النبي ﷺ كل ساعة في هذه المجموعة."))

    # ===== استفتاء الحرب =====
    elif text == ".war" and is_admin(group_id, user_id):
        group_data[group_id]["war_active"] = True
        group_data[group_id]["war_participants"] = []
        group_data[group_id]["war_muslims"] = []
        group_data[group_id]["war_non"] = []
        save_data()
        line_bot_api.reply_message(event.reply_token, TextSendMessage("⚔️ استفتاء الحرب بدأ! اضغط على الأزرار للتفاعل."))

    elif text == ".war r" and is_admin(group_id, user_id):
        war_text = format_war_results(group_id)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(war_text))

    elif text == ".war s" and is_admin(group_id, user_id):
        group_data[group_id]["war_active"] = False
        group_data[group_id]["war_participants"] = []
        group_data[group_id]["war_muslims"] = []
        group_data[group_id]["war_non"] = []
        save_data()
        line_bot_api.reply_message(event.reply_token, TextSendMessage("⛔ تم إيقاف الاستفتاء وإعادة القوائم للصفر."))

# ==== تذكير الصلاة على النبي كل ساعة للمجموعات المفعلة ====
def sal_loop():
    while True:
        time.sleep(3600)  # كل ساعة
        for gid, gdata in group_data.items():
            if gdata.get("sal_active"):
                try:
                    line_bot_api.push_message(gid, TextSendMessage("🌸 صلوا على رسول الله ﷺ 🌸"))
                except:
                    pass

threading.Thread(target=sal_loop, daemon=True).start()

# ==== مساعد استفتاء الحرب ====
def format_war_results(group_id):
    gdata = group_data[group_id]
    participants = gdata.get("war_participants", [])
    muslims = gdata.get("war_muslims", [])
    non_participating = gdata.get("war_non", [])
    text = "⚔️ استفتاء الحرب (مباشر)\n\n"
    text += f"🗡️ المشاركون ({len(participants)}):\n"
    text += "\n".join([f"{i+1}. {p}" for i, p in enumerate(participants)]) + "\n\n"
    text += f"🏰 المسلمون ({len(muslims)}):\n"
    text += "\n".join([f"{i+1}. {m}" for i, m in enumerate(muslims)]) + "\n\n"
    text += f"🐍 المتخاذلون الذين لم يكتبوا أسماءهم ({len(non_participating)}):\n"
    text += "\n".join([f"{i+1}. {n}" for i, n in enumerate(non_participating)])
    return text

# ==== Runner ====
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
