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
    TemplateSendMessage, ButtonsTemplate, MessageAction
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

        # رسالة ترحيب بالعضو الجديد
        try:
            line_bot_api.push_message(group_id, TextSendMessage(f"👋 مرحباً {name} في المجموعة!"))
        except LineBotApiError:
            pass

        # سجل التتبع لو مفعّل
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

    # أوامر البوت
    if not is_admin(group_id, user_id):
        return  # فقط الأدمن يتفاعل مع الأوامر

    # ===== أوامر البوت =====
    if text.startswith(".help"):
        help_text = (
            "أوامر البوت:\n"
            ".lurk on  - تفعيل التتبع\n"
            ".lurk off - إيقاف التتبع\n"
            ".lurk list - عرض المتصلين\n"
            ".sal - تفعيل تذكير الصلاة على النبي كل ساعة\n"
            ".war - بدء استفتاء الحرب\n"
            ".war r - عرض النتائج\n"
            ".war s - إيقاف الاستفتاء\n"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(help_text))

    elif text == ".lurk on":
        group_data[group_id]["lurking"] = True
        group_data[group_id]["lurkers"] = []
        save_data()
        line_bot_api.reply_message(event.reply_token, TextSendMessage("✅ تم تفعيل التتبع."))

    elif text == ".lurk off":
        group_data[group_id]["lurking"] = False
        save_data()
        line_bot_api.reply_message(event.reply_token, TextSendMessage("⛔ تم إيقاف التتبع."))

    elif text == ".lurk list":
        lurkers = group_data[group_id]["lurkers"]
        if lurkers:
            list_text = "👀 المتصلون:\n" + "\n".join([f"- {l['name']} ({l['time']})" for l in lurkers])
        else:
            list_text = "📭 لا يوجد متصلون مسجلون."
        line_bot_api.reply_message(event.reply_token, TextSendMessage(list_text))

    # ===== تذكير الصلاة على النبي =====
    elif text == ".sal":
        group_data[group_id]["sal_active"] = True
        save_data()
        line_bot_api.reply_message(event.reply_token, TextSendMessage("🕌 تذكير الصلاة على النبي مفعل كل ساعة لهذه المجموعة."))

    # ===== استفتاء الحرب =====
    elif text == ".war":
        group_data[group_id]["war_active"] = True
        group_data[group_id]["war_participants"] = []
        group_data[group_id]["war_muslims"] = []
        save_data()
        send_war_card(group_id)

    elif text == ".war s":
        group_data[group_id]["war_active"] = False
        save_data()
        line_bot_api.reply_message(event.reply_token, TextSendMessage("⛔ تم إيقاف الاستفتاء."))

    elif text == ".war r":
        send_war_results(group_id, event.reply_token)

# ==== دوال الاستفتاء ====
def send_war_card(group_id):
    if not group_data[group_id]["war_active"]:
        return
    buttons = TemplateSendMessage(
        alt_text="⚔️ استفتاء الحرب",
        template=ButtonsTemplate(
            title="⚔️ استفتاء الحرب",
            text="اضغط على الزر لتسجيل اختيارك:",
            actions=[
                MessageAction(label="⚔️ مشارك بالحرب", text="war join"),
                MessageAction(label="🏰 يتم تسليم قلعتي", text="war muslmun")
            ]
        )
    )
    try:
        line_bot_api.push_message(group_id, buttons)
    except LineBotApiError:
        pass

def send_war_results(group_id, reply_token=None):
    members = group_data[group_id]["members"]
    participants = group_data[group_id]["war_participants"]
    muslims = group_data[group_id]["war_muslims"]
    # المتخاذلون
    traitors = [name for uid, name in members.items() if name not in participants and name not in muslims]
    text = f"⚔️ استفتاء الحرب (مباشر)\n\n"
    text += f"🗡️ المشاركون ({len(participants)}):\n" + "\n".join([f"{i+1}. {n}" for i, n in enumerate(participants)]) + "\n\n"
    text += f"🏰 المسلمون ({len(muslims)}):\n" + "\n".join([f"{i+1}. {n}" for i, n in enumerate(muslims)]) + "\n\n"
    text += f"🐍 المتخاذلون الذين لم يكتبوا أسماءهم ({len(traitors)}):\n" + "\n".join([f"{i+1}. {n}" for i, n in enumerate(traitors)]) if traitors else "يرجى المشاركة بالنموذج"
    if reply_token:
        line_bot_api.reply_message(reply_token, TextSendMessage(text))
    else:
        try:
            line_bot_api.push_message(group_id, TextSendMessage(text))
        except LineBotApiError:
            pass

# ==== الرد على اختيار الاستفتاء ====
@handler.add(MessageEvent)
def handle_war_choice(event):
    group_id = event.source.group_id
    user_id = event.source.user_id
    if not is_admin(group_id, user_id) and not group_data[group_id]["war_active"]:
        return
    text = (event.message.text or "").strip()
    name = safe_get_profile(group_id, user_id)

    if text == "war join":
        if name not in group_data[group_id]["war_participants"]:
            group_data[group_id]["war_participants"].append(name)
        # إزالة من المسلمين لو موجود
        if name in group_data[group_id]["war_muslims"]:
            group_data[group_id]["war_muslims"].remove(name)
        save_data()
        send_war_results(group_id)
        send_war_card(group_id)

    elif text == "war muslmun":
        if name not in group_data[group_id]["war_muslims"]:
            group_data[group_id]["war_muslims"].append(name)
        # إزالة من المشاركين لو موجود
        if name in group_data[group_id]["war_participants"]:
            group_data[group_id]["war_participants"].remove(name)
        save_data()
        send_war_results(group_id)
        send_war_card(group_id)

# ==== تذكير الصلاة على النبي كل ساعة ====
def reminder_loop():
    while True:
        time.sleep(3600)  # كل ساعة
        for gid, data in group_data.items():
            if data.get("sal_active"):
                try:
                    line_bot_api.push_message(gid, TextSendMessage("🌸 صلوا على رسول الله ﷺ 🌸"))
                except:
                    pass

threading.Thread(target=reminder_loop, daemon=True).start()

# ==== Runner ====
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
