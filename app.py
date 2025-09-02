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
    TemplateSendMessage, ButtonsTemplate, PostbackAction
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
            "war_active": False,
            "war_participants": [],
            "war_muslims": []
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

        # رسالة ترحيب
        try:
            line_bot_api.push_message(group_id, TextSendMessage(f"👋 مرحباً {name}!"))
        except LineBotApiError:
            pass

        # سجل التفاعل لو التتبع مفعل
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
        if uid in group_data[group_id]["war_participants"]:
            group_data[group_id]["war_participants"].remove(uid)
        if uid in group_data[group_id]["war_muslims"]:
            group_data[group_id]["war_muslims"].remove(uid)
    save_data()

# ==== وظائف الاستفتاء ====
def send_war_card(group_id):
    buttons_template = ButtonsTemplate(
        title="⚔️ استفتاء الحرب",
        text="اختر خيارك:",
        actions=[
            PostbackAction(label="مشارك بالحرب ⚔️", data="war_join"),
            PostbackAction(label="أسلم قلعتي 🏰", data="war_muslim")
        ]
    )
    template_message = TemplateSendMessage(
        alt_text="استفتاء الحرب", template=buttons_template
    )
    try:
        line_bot_api.push_message(group_id, template_message)
    except LineBotApiError:
        pass

def send_war_results(group_id):
    participants = [safe_get_profile(group_id, uid) for uid in group_data[group_id]["war_participants"]]
    muslims = [safe_get_profile(group_id, uid) for uid in group_data[group_id]["war_muslims"]]
    members_all = list(group_data[group_id]["members"].values())
    non_participants = [name for name in members_all if name not in participants and name not in muslims]

    result_text = f"⚔️ استفتاء الحرب (مباشر)\n\n"
    result_text += f"🗡️ المشاركون ({len(participants)}):\n"
    for i, name in enumerate(participants, start=1):
        result_text += f"{i}. {name}\n"

    result_text += f"\n🏰 المسلمون ({len(muslims)}):\n"
    for i, name in enumerate(muslims, start=1):
        result_text += f"{i}. {name}\n"

    result_text += f"\n🐍 المتخاذلون الذين لم يكتبوا أسماءهم ({len(non_participants)}):\n"
    for i, name in enumerate(non_participants, start=1):
        result_text += f"{i}. {name}\n"

    try:
        line_bot_api.push_message(group_id, TextSendMessage(result_text))
    except LineBotApiError:
        pass

# ==== تذكير الصلاة على النبي كل ساعة ====
def reminder_loop():
    while True:
        time.sleep(3600)  # كل ساعة
        for group_id in group_data:
            try:
                line_bot_api.push_message(group_id, TextSendMessage("🌸 صلوا على رسول الله ﷺ 🌸"))
            except:
                continue

threading.Thread(target=reminder_loop, daemon=True).start()

# ==== Runner ====
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
                       
