import os
import json
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    PostbackEvent, TemplateSendMessage, ButtonsTemplate, PostbackAction
)

# --- متغيرات البيئة ---
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")
ADMIN_USER_ID = os.getenv("USER_ID")  # أدمن رئيسي

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET or not ADMIN_USER_ID:
    raise Exception("يرجى ضبط متغيرات البيئة CHANNEL_ACCESS_TOKEN و CHANNEL_SECRET و USER_ID")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# --- بيانات المجموعات ---
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
            "members": {},
            "war": {
                "active": False,
                "participants": [],
                "castle_holders": []
            }
        }
        save_data()

def is_admin(group_id, user_id):
    return user_id in group_data[group_id]["admins"]

def safe_get_profile(group_id, user_id):
    try:
        profile = line_bot_api.get_group_member_profile(group_id, user_id)
        return profile.display_name
    except:
        return "مجهول"

# ==== نظام التتبع الأقصى (Lurkers) ====
if "lurkers" not in group_data.get("global", {}):
    group_data.setdefault("global", {})["lurkers"] = {}

def mark_lurker(group_id, user_id):
    lurkers = group_data.setdefault("global", {}).setdefault("lurkers", {})
    group_lurk = lurkers.setdefault(group_id, {"readers": [], "last_msg_id": None})
    if user_id not in group_lurk["readers"]:
        group_lurk["readers"].append(user_id)
    save_data()

def reset_lurkers(group_id):
    lurkers = group_data.setdefault("global", {}).setdefault("lurkers", {})
    lurkers[group_id] = {"readers": [], "last_msg_id": None}
    save_data()

def show_lurkers(group_id, reply_token):
    lurkers = group_data.get("global", {}).get("lurkers", {})
    readers = lurkers.get(group_id, {}).get("readers", [])
    members = group_data[group_id]["members"].keys()
    laggards = [uid for uid in members if uid not in readers]

    if laggards:
        msg = "👀 المتخاذلون:\n" + "\n".join([f"- {safe_get_profile(group_id,uid)}" for uid in laggards])
    else:
        msg = "🔥 لا يوجد متخاذلين، الكل متابع!"
    line_bot_api.reply_message(reply_token, TextSendMessage(msg))

# ==== استفتاء الحرب ====
def send_war_poll(reply_token):
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
    line_bot_api.reply_message(reply_token, buttons)

def send_war_results(group_id, reply_token=None, include_laggards=False):
    war = group_data[group_id]["war"]
    members = list(group_data[group_id]["members"].keys())
    participants = [safe_get_profile(group_id, uid) for uid in war["participants"]]
    castles = [safe_get_profile(group_id, uid) for uid in war["castle_holders"]]
    laggards = [uid for uid in members if uid not in war["participants"] and uid not in war["castle_holders"]]

    msg = f"⚔️ استفتاء الحرب\n\n"
    msg += f"🗡️ المشاركون ({len(participants)}):\n" + ("\n".join([f"{i+1}. {p}" for i, p in enumerate(participants)]) or "لا يوجد") + "\n\n"
    msg += f"🏰 المسلمون ({len(castles)}):\n" + ("\n".join([f"{i+1}. {p}" for i, p in enumerate(castles)]) or "لا يوجد") + "\n\n"

    if include_laggards:
        if laggards:
            msg += "🐍 المتخاذلون:\n" + "\n".join([f"- {safe_get_profile(group_id, uid)}" for uid in laggards])
        else:
            msg += "👑🔥 لا يوجد متخاذلين."

    if reply_token:
        line_bot_api.reply_message(reply_token, TextSendMessage(msg))
    else:
        line_bot_api.push_message(group_id, TextSendMessage(msg))

# ==== التعامل مع الرسائل ====
@handler.add(MessageEvent, message=TextMessage)
def on_message(event):
    if not hasattr(event.source, "group_id"):
        return

    group_id = event.source.group_id
    user_id = event.source.user_id
    text = (event.message.text or "").strip()
    init_group(group_id)
    group_data[group_id]["members"][user_id] = safe_get_profile(group_id, user_id)

    # تسجيل القراءة لكل عضو
    mark_lurker(group_id, user_id)
    save_data()

    # أوامر الأدمن
    if is_admin(group_id, user_id):
        if text.lower() == ".lurkers":
            show_lurkers(group_id, event.reply_token)
        elif text.lower() == ".lurkers reset":
            reset_lurkers(group_id)
            line_bot_api.reply_message(event.reply_token, TextSendMessage("♻️ تم إعادة تعيين المتتبعين."))

        # أوامر الحرب
        elif text == ".war":
            group_data[group_id]["war"]["active"] = True
            group_data[group_id]["war"]["participants"] = []
            group_data[group_id]["war"]["castle_holders"] = []
            save_data()
            send_war_poll(event.reply_token)
        elif text == ".war r":
            send_war_results(group_id, event.reply_token)
        elif text == ".war rl":
            send_war_results(group_id, event.reply_token, include_laggards=True)
        elif text == ".war s":
            group_data[group_id]["war"]["active"] = False
            group_data[group_id]["war"]["participants"] = []
            group_data[group_id]["war"]["castle_holders"] = []
            save_data()
            line_bot_api.reply_message(event.reply_token, TextSendMessage("⛔ تم إيقاف الاستفتاء وإفراغ القوائم."))

# ==== التعامل مع الاختيارات ====
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
    line_bot_api.reply_message(event.reply_token, TextSendMessage(f"✅ تم تسجيل اختيارك {name}"))

# ==== تشغيل السيرفر ====
app = Flask(__name__)

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
