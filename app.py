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
    ButtonsTemplate, TemplateSendMessage, PostbackAction, PostbackEvent
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

war_data = {}  # استفتاء الحرب لكل مجموعة

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
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dm_admin(f"🔔 عضو جديد دخل المجموعة!\n👤 الاسم: {name}\n👥 المجموعة: {group_name}\n🕒 الوقت: {ts}")
        if group_data[group_id]["lurking"]:
            add_lurker(group_id, uid, name)
    save_data()
    # ترحيب بالعضو
    for member in event.joined.members:
        uid = member.user_id
        name = safe_get_profile(group_id, uid)
        try:
            line_bot_api.push_message(group_id, TextSendMessage(f"👋 مرحباً {name}!"))
        except LineBotApiError:
            pass

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

# ==== الصلاة على النبي كل ساعة أو عند الأمر .sal ====
def reminder_loop():
    while True:
        time.sleep(3600)  # كل ساعة
        try:
            for gid in group_data.keys():
                if group_data[gid].get("sal_enabled", False):
                    line_bot_api.push_message(gid, TextSendMessage("🌸 صلوا على رسول الله ﷺ 🌸"))
        except:
            pass

threading.Thread(target=reminder_loop, daemon=True).start()

# ==== أوامر البوت واستفتاء الحرب ====
def war_buttons():
    return TemplateSendMessage(
        alt_text="⚔️ استفتاء الحرب",
        template=ButtonsTemplate(
            title="⚔️🔥 استفتاء الحرب!",
            text="اضغط على الأزرار للتفاعل:\n🔴 للقتال   🔵 لتسليم القلعة",
            actions=[
                PostbackAction(label="🔴 أنا مشارك", data="war_participate"),
                PostbackAction(label="🔵 أسلم قلعتِي", data="war_muslim")
            ]
        )
    )

def send_war_card(group_id, text):
    line_bot_api.push_message(group_id, [
        TextSendMessage(text),
        war_buttons()
    ])

def start_war(group_id):
    war_data[group_id] = {
        "active": True,
        "participants": [],
        "muslims": [],
        "lurkers": list(group_data[group_id]["members"].keys())
    }
    send_war_card(group_id, "⚔️ استفتاء الحرب بدأ! اضغط على الأزرار للتفاعل.")

def stop_war(group_id):
    if group_id in war_data:
        war_data[group_id]["active"] = False

def show_war_results(group_id):
    if group_id not in war_data:
        return TextSendMessage("❌ لم يبدأ استفتاء الحرب بعد.")
    data = war_data[group_id]
    participants = [safe_get_profile(group_id, uid) for uid in data["participants"]]
    muslims = [safe_get_profile(group_id, uid) for uid in data["muslims"]]
    lurkers = [safe_get_profile(group_id, uid) for uid in data["lurkers"]
               if uid not in data["participants"] + data["muslims"]]
    result_text = (
        f"⚔️ استفتاء الحرب (مباشر)\n\n"
        f"🗡️ المشاركون ({len(participants)}):\n" + "\n".join(f"{i+1}- {n}" for i,n in enumerate(participants)) + "\n\n"
        f"🏰 المسلمون ({len(muslims)}):\n" + "\n".join(f"{i+1}- {n}" for i,n in enumerate(muslims)) + "\n\n"
        f"🐍 المتخاذلون الذين لم يكتبوا أسماءهم ({len(lurkers)}):\n" + "\n".join(f"{i+1}- {n}" for i,n in enumerate(lurkers))
    )
    return TextSendMessage(result_text)

@handler.add(PostbackEvent)
def handle_war_postback(event):
    group_id = event.source.group_id
    user_id = event.source.user_id
    data = event.postback.data

    if group_id not in war_data or not war_data[group_id]["active"]:
        return

    # إزالة العضو من كل القوائم أولًا
    for lst in ["participants", "muslims"]:
        if user_id in war_data[group_id][lst]:
            war_data[group_id][lst].remove(user_id)

    if data == "war_participate":
        war_data[group_id]["participants"].append(user_id)
    elif data == "war_muslim":
        war_data[group_id]["muslims"].append(user_id)

    # إرسال النتائج المباشرة
    line_bot_api.push_message(group_id, show_war_results(group_id))
    # إعادة إرسال البطاقة للاستفتاء
    send_war_card(group_id, "⚔️ استفتاء الحرب مستمر! اضغط على الأزرار للتفاعل.")

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

    # ===== أوامر الادمن فقط =====
    if not is_admin(group_id, user_id):
        return

    if text.startswith(".help"):
        help_text = (
            "أوامر البوت:\n"
            ".lurk on/off/list - التتبع\n"
            ".clear - مسح المتصلين\n"
            ".all - منشن للجميع\n"
            ".war - بدء استفتاء الحرب\n"
            ".war s - إيقاف الاستفتاء\n"
            ".war r - عرض النتائج\n"
            ".sal - تفعيل الصلاة على النبي في هذه المجموعة\n"
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
    elif text == ".clear":
        group_data[group_id]["lurkers"] = []
        save_data()
        line_bot_api.reply_message(event.reply_token, TextSendMessage("🗑️ تم مسح قائمة المتصلين."))
    elif text == ".all":
        members = list(group_data[group_id]["members"].values())
        mention_text = " ".join(members) if members else "❌ لا يوجد أعضاء."
        line_bot_api.reply_message(event.reply_token, TextSendMessage(f"📢 منشن للجميع:\n{mention_text}"))
    elif text == ".sal":
        group_data[group_id]["sal_enabled"] = True
        save_data()
        line_bot_api.reply_message(event.reply_token, TextSendMessage("✅ تم تفعيل الصلاة على النبي ﷺ لهذه المجموعة."))
    elif text == ".war":
        start_war(group_id)
    elif text == ".war s":
        stop_war(group_id)
        line_bot_api.reply_message(event.reply_token, TextSendMessage("⛔ تم إيقاف استفتاء الحرب."))
    elif text == ".war r":
        line_bot_api.reply_message(event.reply_token, show_war_results(group_id))

# ==== Runner ====
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
        
