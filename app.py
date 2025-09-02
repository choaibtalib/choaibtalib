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
    PostbackEvent, TemplateSendMessage, ButtonsTemplate, MessageAction
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
            "sal_enabled": False,
            "war": {
                "active": False,
                "participants": [],
                "muslims": [],
                "message_id": None
            }
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

        # الترحيب بالعضو
        try:
            line_bot_api.push_message(group_id, TextSendMessage(f"👋 مرحباً بك يا {name}!"))
        except LineBotApiError:
            pass

        # تسجيل التتبع لو مفعل
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
            line_bot_api.push_message(group_id, TextSendMessage(f"👋 مع السلامة {name}!"))
        except LineBotApiError:
            pass
        group_data[group_id]["lurkers"] = [l for l in group_data[group_id]["lurkers"] if l["id"] != uid]
        # إزالة من الاستفتاء
        war = group_data[group_id]["war"]
        if uid in war["participants"]:
            war["participants"].remove(uid)
        if uid in war["muslims"]:
            war["muslims"].remove(uid)
    save_data()

# ==== رسائل واستفتاءات ====
def create_war_card(group_id):
    war = group_data[group_id]["war"]
    participants = war["participants"]
    muslims = war["muslims"]
    # حساب المتخاذلين
    members_in_group = list(group_data[group_id]["members"].values())
    all_uids = list(group_data[group_id]["members"].keys())
    participants_names = [safe_get_profile(group_id, uid) for uid in participants]
    muslim_names = [safe_get_profile(group_id, uid) for uid in muslims]
    non_participants_names = [safe_get_profile(group_id, uid) for uid in all_uids if uid not in participants]
    participants_text = "\n".join([f"{i+1}. {n}" for i, n in enumerate(participants_names)]) or "لا أحد"
    muslim_text = "\n".join([f"{i+1}. {n}" for i, n in enumerate(muslim_names)]) or "لا أحد"
    non_participants_text = "\n".join([f"{i+1}. {n}" for i, n in enumerate(non_participants_names)]) or "لا أحد"

    text = (
        f"⚔️ استفتاء الحرب (مباشر)\n\n"
        f"🗡️ المشاركون ({len(participants)}):\n{participants_text}\n\n"
        f"🏰 المسلمون ({len(muslims)}):\n{muslim_text}\n\n"
        f"🐍 المتخاذلون الذين لم يكتبوا أسماءهم ({len(non_participants_names)}):\n{non_participants_text}"
    )

    buttons_template = ButtonsTemplate(
        title="استفتاء الحرب",
        text="اضغط على زر اختيارك:",
        actions=[
            MessageAction(label="🗡️ أشارك", text=".war join"),
            MessageAction(label="🏰 أسلم قلعتي", text=".war muslim")
        ]
    )
    return TemplateSendMessage(alt_text="استفتاء الحرب", template=buttons_template), text

@handler.add(MessageEvent, message=TextMessage)
def on_message(event):
    group_id = event.source.group_id
    user_id = event.source.user_id
    text = (event.message.text or "").strip()
    init_group(group_id)

    # التتبع
    if group_data[group_id]["lurking"]:
        name = safe_get_profile(group_id, user_id)
        add_lurker(group_id, user_id, name)

    # أوامر البوت
    if text.startswith(".help"):
        help_text = (
            "أوامر البوت:\n"
            ".lurk on/off/list  - التتبع\n"
            ".sal              - تذكير الصلاة على النبي\n"
            ".war              - بدء استفتاء الحرب\n"
            ".war s            - إيقاف الاستفتاء\n"
            ".war r            - عرض النتائج\n"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(help_text))
        return

    # تذكير الصلاة على النبي
    if text == ".sal" and is_admin(group_id, user_id):
        try:
            line_bot_api.push_message(group_id, TextSendMessage("🌸 صلوا على رسول الله ﷺ 🌸"))
        except:
            pass
        return

    # ====== استفتاء الحرب ======
    war = group_data[group_id]["war"]

    if text == ".war" and is_admin(group_id, user_id):
        war["active"] = True
        war["participants"] = []
        war["muslims"] = []
        msg_card, msg_text = create_war_card(group_id)
        m = line_bot_api.reply_message(event.reply_token, [TextSendMessage(text=msg_text), msg_card])
        if hasattr(m, "message_id"):
            war["message_id"] = m.message_id
        save_data()
        return

    elif text == ".war s" and is_admin(group_id, user_id):
        war["active"] = False
        war["participants"] = []
        war["muslims"] = []
        save_data()
        line_bot_api.reply_message(event.reply_token, TextSendMessage("⛔ تم إيقاف الاستفتاء وإعادة التهيئة."))
        return

    elif text == ".war r" and is_admin(group_id, user_id):
        msg_card, msg_text = create_war_card(group_id)
        line_bot_api.reply_message(event.reply_token, [TextSendMessage(text=msg_text), msg_card])
        return

    # مشاركة الأعضاء
    if war["active"]:
        if text == ".war join":
            if user_id not in war["participants"]:
                war["participants"].append(user_id)
            if user_id in war["muslims"]:
                war["muslims"].remove(user_id)
            save_data()
        elif text == ".war muslim":
            if user_id not in war["muslims"]:
                war["muslims"].append(user_id)
            if user_id not in war["participants"]:
                war["participants"].append(user_id)
            save_data()
        # إعادة إرسال البطاقة مع النتائج
        msg_card, msg_text = create_war_card(group_id)
        line_bot_api.push_message(group_id, [TextSendMessage(text=msg_text), msg_card])
        return

# ==== تذكير الصلاة على النبي كل ساعة ====
def reminder_loop():
    while True:
        time.sleep(3600)  # كل ساعة
        for group_id, data in group_data.items():
            if data.get("sal_enabled", True):
                try:
                    line_bot_api.push_message(group_id, TextSendMessage("🌸 صلوا على رسول الله ﷺ 🌸"))
                except:
                    pass

threading.Thread(target=reminder_loop, daemon=True).start()

# ==== Runner ====
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
            
