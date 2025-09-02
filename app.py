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
            "poll": {"active": False, "participants": [], "muslims": []}
        }
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

def is_admin(group_id, user_id):
    init_group(group_id)
    return user_id in group_data[group_id]["admins"]

def add_lurker(group_id, user_id, name):
    init_group(group_id)
    lurkers = group_data[group_id]["lurkers"]
    if not any(l['id'] == user_id for l in lurkers):
        lurkers.append({"id": user_id, "name": name, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        save_data()

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
        dm_admin(f"🔔 عضو جديد دخل المجموعة!\n👤 {name}\n👥 {group_name}\n🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
        poll = group_data[group_id]["poll"]
        poll["participants"] = [x for x in poll["participants"] if x != uid]
        poll["muslims"] = [x for x in poll["muslims"] if x != uid]
    save_data()

# ==== الرسائل ====
@handler.add(MessageEvent, message=TextMessage)
def on_message(event):
    group_id = event.source.group_id
    user_id = event.source.user_id
    text = (event.message.text or "").strip()
    init_group(group_id)

    # سجل التفاعل لو التتبع مفعل
    if group_data[group_id]["lurking"]:
        name = safe_get_profile(group_id, user_id)
        add_lurker(group_id, user_id, name)

    # الرد على منشن الأدمن
    if f"@{ADMIN_USER_ID}" in text or f"<@{ADMIN_USER_ID}>" in text:
        sender_name = safe_get_profile(group_id, user_id)
        dm_admin(f"👑 {sender_name}، أنت مشغول الآن. يمكنك ترك رسالة له بالخاص.")

    # ==== أوامر الأدمن ====
    if text.startswith(".help"):
        help_text = (
            "أوامر البوت:\n"
            ".lurk on/off/list - تتبع الأعضاء\n"
            ".poll start - بدء استفتاء الحرب\n"
            ".poll stop - إيقاف الاستفتاء\n"
            ".poll results - عرض النتائج\n"
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
            dm_admin(f"✅ تم تفعيل التتبع في: {safe_get_group_name(group_id)}")
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage("❌ ليس لديك صلاحية."))

    elif text == ".lurk off":
        if is_admin(group_id, user_id):
            group_data[group_id]["lurking"] = False
            save_data()
            line_bot_api.reply_message(event.reply_token, TextSendMessage("⛔ تم إيقاف التتبع."))
            dm_admin(f"⛔ تم إيقاف التتبع في: {safe_get_group_name(group_id)}")
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

    # ==== أوامر الاستفتاء ====
    elif text == ".poll start":
        if is_admin(group_id, user_id):
            group_data[group_id]["poll"]["active"] = True
            group_data[group_id]["poll"]["participants"] = []
            group_data[group_id]["poll"]["muslims"] = []
            buttons = TemplateSendMessage(
                alt_text="استفتاء الحرب",
                template=ButtonsTemplate(
                    title="🏹 حرب القلاع",
                    text="اختر: هل تشارك بالحرب أم تسلم قلعك؟",
                    actions=[
                        PostbackAction(label="أشارك بالحرب", data="join_war"),
                        PostbackAction(label="أسلم قلعي", data="give_castle")
                    ]
                )
            )
            line_bot_api.reply_message(event.reply_token, buttons)
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage("❌ ليس لديك صلاحية."))

    elif text == ".poll stop":
        if is_admin(group_id, user_id):
            group_data[group_id]["poll"]["active"] = False
            save_data()
            line_bot_api.reply_message(event.reply_token, TextSendMessage("⛔ تم إيقاف الاستفتاء."))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage("❌ ليس لديك صلاحية."))

    elif text == ".poll results":
        if is_admin(group_id, user_id):
            poll = group_data[group_id]["poll"]
            members = list(group_data[group_id]["members"].values())
            participants_names = [safe_get_profile(group_id, uid) for uid in poll["participants"]]
            muslim_names = [safe_get_profile(group_id, uid) for uid in poll["muslims"]]
            all_uids = set(group_data[group_id]["members"].keys())
            non_participants_uids = all_uids - set(poll["participants"]) - set(poll["muslims"])
            non_participants_names = [group_data[group_id]["members"][uid] for uid in non_participants_uids]

            res_text = (
                f"📊 نتائج الاستفتاء:\n"
                f"👊 المشاركون: {', '.join(participants_names) if participants_names else 'لا أحد'}\n"
                f"🏰 المسلمون: {', '.join(muslim_names) if muslim_names else 'لا أحد'}\n"
                f"⚠️ المتخاذلون: {', '.join(non_participants_names) if non_participants_names else 'لا أحد'}"
            )
            line_bot_api.reply_message(event.reply_token, TextSendMessage(res_text))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage("❌ ليس لديك صلاحية."))

# ==== Postback (الضغط على أزرار الاستفتاء) ====
@handler.add(PostbackEvent)
def on_postback(event):
    group_id = event.source.group_id
    user_id = event.source.user_id
    data = event.postback.data
    init_group(group_id)
    poll = group_data[group_id]["poll"]

    if not poll["active"]:
        line_bot_api.reply_message(event.reply_token, TextSendMessage("⛔ الاستفتاء مغلق حالياً."))
        return

    if data == "join_war":
        if user_id not in poll["participants"]:
            poll["participants"].append(user_id)
        if user_id in poll["muslims"]:
            poll["muslims"].remove(user_id)
        save_data()
        line_bot_api.reply_message(event.reply_token, TextSendMessage("✅ تم تسجيلك كمشارك في الحرب."))

    elif data == "give_castle":
        if user_id not in poll["muslims"]:
            poll["muslims"].append(user_id)
        if user_id in poll["participants"]:
            poll["participants"].remove(user_id)
        save_data()
        line_bot_api.reply_message(event.reply_token, TextSendMessage("✅ تم تسجيلك لمن يسلم قلعه."))

# ==== تذكير الصلاة على النبي كل ساعة ====
def reminder_loop():
    while True:
        time.sleep(3600)  # ساعة
        try:
            dm_admin("🌸 صلوا على رسول الله ﷺ 🌸")
        except:
            pass

threading.Thread(target=reminder_loop, daemon=True).start()

# ==== Runner ====
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
        
