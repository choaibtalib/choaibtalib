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
    PostbackEvent, TemplateSendMessage, ButtonsTemplate, PostbackAction
)

app = Flask(__name__)

# ==== المتغيرات ====
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")
ADMIN_USER_ID = os.getenv("USER_ID")

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET or not ADMIN_USER_ID:
    raise Exception("❌ يرجى ضبط متغيرات البيئة: CHANNEL_ACCESS_TOKEN و CHANNEL_SECRET و USER_ID")

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
            "war_votes": {},
        }
        save_data()

def is_admin(group_id, user_id):
    init_group(group_id)
    return user_id in group_data[group_id]["admins"]

def safe_get_profile(group_id, user_id):
    try:
        p = line_bot_api.get_group_member_profile(group_id, user_id)
        return p.display_name
    except:
        return "مستخدم"

# ==== التذكير بالصلاة على النبي ﷺ ====
sal_groups = set()

def sal_loop():
    while True:
        time.sleep(3600)  # كل ساعة
        for gid in list(sal_groups):
            try:
                line_bot_api.push_message(
                    gid,
                    TextSendMessage("🌹✨ صلّوا على الحبيب المصطفى ﷺ 🌹✨")
                )
            except:
                pass

threading.Thread(target=sal_loop, daemon=True).start()

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

# ==== عرض نتائج الاستفتاء ====
def format_war_results(group_id):
    votes = group_data[group_id]["war_votes"]
    members = group_data[group_id]["members"]

    joiners = [safe_get_profile(group_id, uid) for uid, v in votes.items() if v == "join"]
    muslims = [safe_get_profile(group_id, uid) for uid, v in votes.items() if v == "muslimun"]

    # المتخاذلون (من لم يصوتوا)
    traitors = [name for uid, name in members.items() if uid not in votes]

    txt = "📊 نتائج استفتاء الحرب (مباشر) 📊\n\n"

    if joiners:
        txt += "⚔️ **المشاركون ({}):**\n".format(len(joiners))
        for i, n in enumerate(joiners, 1):
            txt += f"  {i}. {n}\n"
    else:
        txt += "⚔️ **لا يوجد مشاركون حتى الآن.**\n"

    if muslims:
        txt += "\n🏰 **المسلمون ({}):**\n".format(len(muslims))
        for i, n in enumerate(muslims, 1):
            txt += f"  {i}. {n}\n"
    else:
        txt += "\n🏰 **لا يوجد مسلمون حتى الآن.**\n"

    if traitors:
        txt += "\n🐍 **المتخاذلون الذين لم يكتبوا أسماءهم ({}):**\n".format(len(traitors))
        for i, n in enumerate(traitors, 1):
            txt += f"  {i}. {n}\n"
    else:
        txt += "\n🐍 **لا يوجد متخاذلون حتى الآن.**\n"

    return txt.strip()

# ==== بطاقة الاستفتاء الديناميكية (مع عدد المشاركين) ====
def war_card(group_id):
    votes = group_data[group_id]["war_votes"]
    members_count = len(group_data[group_id]["members"])
    voted_count = len(votes)
    title = f"⚔️ استفتاء الحرب [{voted_count}/{members_count}]"

    return TemplateSendMessage(
        alt_text="⚔️ استفتاء الحرب",
        template=ButtonsTemplate(
            title=title,
            text="اختر أحد الخيارين:",
            actions=[
                PostbackAction(label="⚔️ مشارك بالحرب", data="war:join"),
                PostbackAction(label="🏰 يتم تسليم قلعتي", data="war:muslimun"),
            ]
        )
    )

# ==== إرسال تحديث الاستفتاء (البطاقة + النتيجة) ====
def send_war_update(group_id):
    """إرسال بطاقة الاستفتاء والنتيجة فوراً"""
    try:
        line_bot_api.push_message(group_id, war_card(group_id))
        result_text = format_war_results(group_id)
        line_bot_api.push_message(group_id, TextSendMessage(result_text))
    except Exception as e:
        print(f"Error sending war update: {e}")

# ==== Events ====
@handler.add(JoinEvent)
def on_join(event):
    group_id = event.source.group_id
    init_group(group_id)
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage("🤖 مرحباً! البوت جاهز.\nاستخدم .help لمشاهدة الأوامر.")
    )

@handler.add(MemberJoinedEvent)
def on_member_joined(event):
    group_id = event.source.group_id
    init_group(group_id)

    for member in event.joined.members:
        uid = member.user_id
        name = safe_get_profile(group_id, uid)
        group_data[group_id]["members"][uid] = name
        line_bot_api.push_message(
            group_id,
            TextSendMessage(f"🎉 أهلاً وسهلاً {name}! نورت المجموعة 🌹")
        )
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
        except:
            pass
    save_data()

# ==== Postback ====
@handler.add(PostbackEvent)
def handle_postback(event):
    group_id = event.source.group_id
    init_group(group_id)
    user_id = event.source.user_id
    data = event.postback.data

    if not group_data[group_id]["war_active"]:
        return

    if data == "war:join":
        group_data[group_id]["war_votes"][user_id] = "join"
    elif data == "war:muslimun":
        group_data[group_id]["war_votes"][user_id] = "muslimun"

    save_data()

    # تحديث: إرسال البطاقة والنتيجة من جديد
    send_war_update(group_id)

# ==== الرسائل ====
@handler.add(MessageEvent, message=TextMessage)
def on_message(event):
    if event.source.type != "group":
        return  # تجاهل الرسائل الفردية

    group_id = event.source.group_id
    init_group(group_id)
    user_id = event.source.user_id
    text = (event.message.text or "").strip()

    # أوامر التذكير بالصلاة
    if text == ".sal" and user_id == ADMIN_USER_ID:
        sal_groups.add(group_id)
        line_bot_api.reply_message(event.reply_token, TextSendMessage("✅ سيتم التذكير بالصلاة على النبي ﷺ كل ساعة."))
        return
    elif text == ".unsal" and user_id == ADMIN_USER_ID:
        sal_groups.discard(group_id)
        line_bot_api.reply_message(event.reply_token, TextSendMessage("❌ تم إلغاء التذكير في هذه المجموعة."))
        return

    # أوامر الحرب
    if text == ".war" and is_admin(group_id, user_id):
        group_data[group_id]["war_active"] = True
        group_data[group_id]["war_votes"] = {}
        save_data()
        send_war_update(group_id)
        return

    elif text == ".war s" and is_admin(group_id, user_id):
        group_data[group_id]["war_active"] = False
        save_data()
        line_bot_api.reply_message(event.reply_token, TextSendMessage("⛔ تم إيقاف الاستفتاء."))
        return

    elif text == ".war r" and is_admin(group_id, user_id):
        send_war_update(group_id)
        return

# ==== Runner ====
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
