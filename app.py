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
            "sal_active": False,
            "war": {
                "active": False,
                "participants": [],
                "castle_holders": []
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
    for member in event.joined.members:
        uid = member.user_id
        name = safe_get_profile(group_id, uid)
        group_data[group_id]["members"][uid] = name
        line_bot_api.push_message(group_id, TextSendMessage(f"مرحباً {name}! 👋"))
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dm_admin(f"🔔 عضو جديد دخل المجموعة: {name} في {safe_get_group_name(group_id)} | الوقت: {ts}")
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
            line_bot_api.push_message(group_id, TextSendMessage(f"مع السلامة {name} 👋"))
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

    # أوامر الأدمن
    if is_admin(group_id, user_id):
        if text.startswith(".help"):
            help_text = (
                "أوامر البوت:\n"
                ".lurk on/off - تفعيل/إيقاف التتبع\n"
                ".lurk list - عرض المتصلين\n"
                ".sal - تفعيل تذكير الصلاة على النبي\n"
                ".war - بدء استفتاء الحرب\n"
                ".war r - عرض نتائج الحرب\n"
                ".war s - إيقاف الاستفتاء\n"
            )
            line_bot_api.reply_message(event.reply_token, TextSendMessage(help_text))
            return

        elif text == ".lurk on":
            group_data[group_id]["lurking"] = True
            group_data[group_id]["lurkers"] = []
            save_data()
            line_bot_api.reply_message(event.reply_token, TextSendMessage("✅ تم تفعيل التتبع."))
            return

        elif text == ".lurk off":
            group_data[group_id]["lurking"] = False
            save_data()
            line_bot_api.reply_message(event.reply_token, TextSendMessage("⛔ تم إيقاف التتبع."))
            return

        elif text == ".lurk list":
            lurkers = group_data[group_id]["lurkers"]
            if lurkers:
                list_text = "👀 المتصلون:\n" + "\n".join([f"- {l['name']} ({l['time']})" for l in lurkers])
            else:
                list_text = "📭 لا يوجد متصلون مسجلون."
            line_bot_api.reply_message(event.reply_token, TextSendMessage(list_text))
            return

        elif text == ".sal":
            group_data[group_id]["sal_active"] = True
            save_data()
            line_bot_api.reply_message(event.reply_token, TextSendMessage("🕋 سيتم تذكير الصلاة على النبي كل ساعة 🌸"))
            return

        # ==== استفتاء الحرب ====
        elif text == ".war":
            group_data[group_id]["war"]["active"] = True
            group_data[group_id]["war"]["participants"] = []
            group_data[group_id]["war"]["castle_holders"] = []
            save_data()
            send_war_poll(group_id)
            return

        elif text == ".war r":
            send_war_results(group_id)
            return

        elif text == ".war s":
            group_data[group_id]["war"]["active"] = False
            group_data[group_id]["war"]["participants"] = []
            group_data[group_id]["war"]["castle_holders"] = []
            save_data()
            line_bot_api.reply_message(event.reply_token, TextSendMessage("⛔ تم إيقاف الاستفتاء وإفراغ القوائم."))
            return

# ==== الاستفتاء ====
def send_war_poll(group_id):
    buttons = TemplateSendMessage(
        alt_text="⚔️ استفتاء الحرب",
        template=ButtonsTemplate(
            title="⚔️ استفتاء الحرب",
            text="اختر خيارك:",
            actions=[
                PostbackAction(label="⚔️ مشاركة بالحرب", data="war_join"),
                PostbackAction(label="🏰 أسلم قلعتي", data="war_castle")
            ]
        )
    )
    line_bot_api.push_message(group_id, buttons)

def send_war_results(group_id):
    war = group_data[group_id]["war"]
    members = list(group_data[group_id]["members"].values())
    participants = [safe_get_profile(group_id, uid) for uid in war["participants"]]
    castles = [safe_get_profile(group_id, uid) for uid in war["castle_holders"]]
    # المتخاذلين
    laggards = [m for m in members if m not in participants and m not in castles]

    msg = f"⚔️ استفتاء الحرب (مباشر)\n\n"
    msg += f"🗡️ المشاركون ({len(participants)}):\n" + "\n".join([f"{i+1}. {p}" for i, p in enumerate(participants)]) + "\n\n"
    msg += f"🏰 المسلمون ({len(castles)}):\n" + "\n".join([f"{i+1}. {p}" for i, p in enumerate(castles)]) + "\n\n"
    msg += f"🐍 المتخاذلون ({len(laggards)}):\n" + "\n".join([f"{i+1}. {p}" for i, p in enumerate(laggards)])
    line_bot_api.push_message(group_id, TextSendMessage(msg))
    if war["active"]:
        send_war_poll(group_id)  # إعادة إرسال البطاقة لتفاعل أعضاء آخرين

# ==== الرد على Postback ====
from linebot.models import PostbackEvent

@handler.add(PostbackEvent)
def on_postback(event):
    group_id = event.source.group_id
    user_id = event.source.user_id
    data = event.postback.data
    name = safe_get_profile(group_id, user_id)
    war = group_data[group_id]["war"]
    if not war["active"]:
        line_bot_api.reply_message(event.reply_token, TextSendMessage("❌ الاستفتاء متوقف."))
        return

    if data == "war_join":
        if user_id not in war["participants"]:
            war["participants"].append(user_id)
        if user_id in war["castle_holders"]:
            war["castle_holders"].remove(user_id)
    elif data == "war_castle":
        if user_id not in war["castle_holders"]:
            war["castle_holders"].append(user_id)
        if user_id in war["participants"]:
            war["participants"].remove(user_id)

    save_data()
    send_war_results(group_id)
    line_bot_api.reply_message(event.reply_token, TextSendMessage(f"تم تسجيل اختيارك {name} ✅"))

# ==== تذكير الصلاة على النبي ﷺ كل ساعة ====
def reminder_loop():
    while True:
        time.sleep(3600)  # كل ساعة
        for gid, gdata in group_data.items():
            if gdata.get("sal_active"):
                try:
                    line_bot_api.push_message(gid, TextSendMessage("🌸 صلوا على رسول الله ﷺ 🌸"))
                except:
                    pass

threading.Thread(target=reminder_loop, daemon=True).start()

# ==== Runner ====
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
