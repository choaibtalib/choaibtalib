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
    FlexSendMessage, BubbleContainer, BoxComponent, TextComponent,
    ButtonComponent, PostbackAction, PostbackEvent
)

app = Flask(__name__)

# ==== المتغيرات ====
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")
ADMIN_USER_ID = os.getenv("USER_ID")

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET or not ADMIN_USER_ID:
    raise Exception("❌ يرجى ضبط متغيرات البيئة")

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
            "warriors": [],
            "castle_surrender": [],
            "war_message_id": None  # لتحديث الاستفتاء مباشرة
        }
        save_data()

def is_admin(group_id, user_id):
    init_group(group_id)
    return user_id in group_data[group_id]["admins"]

def add_lurker(group_id, user_id, name):
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
    except:
        pass

# ==== FlexMessage Poll ====
def build_war_poll(group_id):
    warriors = group_data[group_id]["warriors"]
    castles = group_data[group_id]["castle_surrender"]

    warriors_text = "\n".join([f"- {n}" for n in warriors]) or "لا يوجد"
    castles_text = "\n".join([f"- {n}" for n in castles]) or "لا يوجد"

    bubble = BubbleContainer(
        body=BoxComponent(
            layout="vertical",
            contents=[
                TextComponent(text="⚔️ استفتاء الحرب", weight="bold", size="xl", align="center"),
                TextComponent(text=f"🗡️ المشاركون: {len(warriors)}", margin="md"),
                TextComponent(text=warriors_text, size="sm", wrap=True, color="#d32f2f"),
                TextComponent(text=f"🏰 المسلمون: {len(castles)}", margin="md"),
                TextComponent(text=castles_text, size="sm", wrap=True, color="#1976d2"),
                BoxComponent(
                    layout="vertical",
                    margin="lg",
                    contents=[
                        ButtonComponent(style="primary", color="#d32f2f", action=PostbackAction(label="🗡️ أشارك", data="warrior")),
                        ButtonComponent(style="secondary", color="#1976d2", action=PostbackAction(label="🏰 أسلم قلعتني", data="surrender"))
                    ]
                )
            ]
        )
    )
    return FlexSendMessage(alt_text="⚔️ استفتاء الحرب", contents=bubble)

# ==== Webhook ====
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    if not signature: abort(400)
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
        line_bot_api.push_message(group_id, TextSendMessage(f"🎉 أهلًا {name} في {group_name}! نورت ✨"))
        dm_admin(f"🔔 عضو جديد: {name} دخل {group_name}")
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
        line_bot_api.push_message(group_id, TextSendMessage(f"👋 مع السلامة {name}, نتمنى لك التوفيق 🌸"))
        group_data[group_id]["lurkers"] = [l for l in group_data[group_id]["lurkers"] if l["id"] != uid]
    save_data()

# ==== Postback ====
@handler.add(PostbackEvent)
def on_postback(event):
    group_id = event.source.group_id
    user_id = event.source.user_id
    data = event.postback.data
    name = safe_get_profile(group_id, user_id)
    init_group(group_id)

    if data == "warrior":
        if name not in group_data[group_id]["warriors"]:
            group_data[group_id]["warriors"].append(name)
            save_data()
    elif data == "surrender":
        if name not in group_data[group_id]["castle_surrender"]:
            group_data[group_id]["castle_surrender"].append(name)
            save_data()

    # تحديث الرسالة بالنتائج الجديدة
    poll = build_war_poll(group_id)
    line_bot_api.push_message(group_id, poll)

# ==== Messages ====
@handler.add(MessageEvent, message=TextMessage)
def on_message(event):
    group_id = event.source.group_id
    user_id = event.source.user_id
    text = (event.message.text or "").strip()
    init_group(group_id)

    if group_data[group_id]["lurking"]:
        name = safe_get_profile(group_id, user_id)
        add_lurker(group_id, user_id, name)

    # منشن الأدمن
    if f"@{ADMIN_USER_ID}" in text or f"<@{ADMIN_USER_ID}>" in text:
        sender_name = safe_get_profile(group_id, user_id)
        line_bot_api.push_message(group_id, TextSendMessage(f"📩 {sender_name}، الأدمن مشغول. اترك له رسالة بالخاص."))
        return

    if not is_admin(group_id, user_id):
        return

    if text == ".help":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(
            "أوامر البوت:\n"
            ".lurk on/off - تشغيل أو إيقاف التتبع\n"
            ".lurk list - عرض المتصلين\n"
            ".clear - مسح المتصلين\n"
            ".all - منشن للجميع\n"
            ".war - استفتاء الحرب\n"
        ))

    elif text == ".lurk on":
        group_data[group_id]["lurking"] = True
        group_data[group_id]["lurkers"] = []
        save_data()
        line_bot_api.reply_message(event.reply_token, TextSendMessage("✅ التتبع شغال"))

    elif text == ".lurk off":
        group_data[group_id]["lurking"] = False
        save_data()
        line_bot_api.reply_message(event.reply_token, TextSendMessage("⛔ التتبع توقف"))

    elif text == ".lurk list":
        lurkers = group_data[group_id]["lurkers"]
        if lurkers:
            msg = "👀 المتصلون:\n" + "\n".join([f"- {l['name']} ({l['time']})" for l in lurkers])
        else:
            msg = "📭 لا يوجد متصلون."
        line_bot_api.reply_message(event.reply_token, TextSendMessage(msg))

    elif text == ".clear":
        group_data[group_id]["lurkers"] = []
        save_data()
        line_bot_api.reply_message(event.reply_token, TextSendMessage("🗑️ تم مسح المتصلين."))

    elif text == ".all":
        members = list(group_data[group_id]["members"].values())
        mention_text = " ".join(members) if members else "❌ لا يوجد أعضاء"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(f"📢 {mention_text}"))

    elif text == ".war":
        poll = build_war_poll(group_id)
        line_bot_api.reply_message(event.reply_token, poll)

# ==== تذكير بالصلاة على النبي ﷺ ====
def reminder_loop():
    while True:
        time.sleep(3600)
        dm_admin("🌸 صلوا على رسول الله ﷺ 🌸")

threading.Thread(target=reminder_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
