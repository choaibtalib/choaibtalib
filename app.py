import os
import json
from flask import Flask, request, abort
from datetime import datetime
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, JoinEvent

# تحميل المتغيرات من البيئة
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")
ADMIN_USER_ID = os.getenv("USER_ID")  # أو ADMIN_USER_ID حسب إعدادك

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET or not ADMIN_USER_ID:
    raise Exception("خطأ: يرجى ضبط CHANNEL_ACCESS_TOKEN و CHANNEL_SECRET و USER_ID في متغيرات البيئة.")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

app = Flask(__name__)

DATA_FILE = "lurk_data.json"

# تحميل بيانات الـ Lurk أو تهيئتها
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        lurk_data = json.load(f)
else:
    lurk_data = {}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(lurk_data, f, ensure_ascii=False, indent=2)

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    if signature is None:
        app.logger.error("Missing X-Line-Signature")
        abort(400)

    body = request.get_data()  # استلم البايتس كما هي

    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature error")
        abort(400)

    return "OK"

@handler.add(JoinEvent)
def handle_join(event):
    group_id = event.source.group_id
    lurk_data.setdefault(group_id, {"tracking": False, "readers": []})
    save_data()
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="👋 مرحبًا! أرسل `.lurk on` لتفعيل تتبع القراء، و `.lurk off` لإيقافه.")
    )

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip().lower()
    source = event.source

    if not hasattr(source, "group_id"):
        return  # تجاهل الرسائل غير من مجموعة

    group_id = source.group_id

    if group_id not in lurk_data:
        lurk_data[group_id] = {"tracking": False, "readers": []}

    if text == ".lurk on":
        lurk_data[group_id]["tracking"] = True
        lurk_data[group_id]["readers"] = []
        save_data()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ تم تفعيل نظام التتبع (Lurk)."))

    elif text == ".lurk off":
        lurk_data[group_id]["tracking"] = False
        save_data()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⛔ تم إيقاف نظام التتبع (Lurk)."))

    elif text == ".lurk list":
        readers = lurk_data[group_id]["readers"]
        if not readers:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📭 لا يوجد قراء مسجلين حالياً."))
        else:
            list_text = "\n".join(f"- {r['name']}" for r in readers)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"👀 قائمة القراء:\n{list_text}"))

    elif text == ".lurk clear":
        lurk_data[group_id]["readers"] = []
        save_data()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🗑 تم مسح قائمة القراء."))

    elif text == ".lurk status":
        status = "مفعل ✅" if lurk_data[group_id]["tracking"] else "معطل ⛔"
        count = len(lurk_data[group_id]["readers"])
        line_bot_api.reply_message(event.reply_token, TextSendMessage(
            text=f"📊 حالة نظام التتبع: {status}\n👀 عدد القراء المسجلين: {count}"
        ))

    else:
        if lurk_data[group_id]["tracking"]:
            user_id = source.user_id
            if not any(r["id"] == user_id for r in lurk_data[group_id]["readers"]):
                try:
                    profile = line_bot_api.get_group_member_profile(group_id, user_id)
                    display_name = profile.display_name
                except Exception:
                    display_name = "مستخدم مجهول"
                lurk_data[group_id]["readers"].append({
                    "id": user_id,
                    "name": display_name,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                save_data()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
