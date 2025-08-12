import os
import json
from flask import Flask, request, abort
from datetime import datetime
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, JoinEvent

# إعدادات البوت
CHANNEL_ACCESS_TOKEN = os.getenv("9Db/dSzqq+hazXQT2KK2tt8cmmqu6BJA67/4CxIT9oouKN8p+0I9YIvTl1gb4kna4CXxFfMuGNVDxI219vpUqkk/P3ZWvasHpBJsTcqbzjebP3Hjn/+rc0oqBFZwV3TZcwfIjsPgRH2u4AZMd1OpTwdB04t89/1O/w1cDnyilFU=", "ضع_التوكن_هنا")
CHANNEL_SECRET = os.getenv("38f49345e7d8306354bcd54691e9a991", "ضع_السيكرت_هنا")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

DATA_FILE = "lurk_data.json"
app = Flask(__name__)

# تحميل بيانات Lurk من ملف JSON أو إنشاؤها إذا غير موجود
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
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(JoinEvent)
def handle_join(event):
    group_id = event.source.group_id
    lurk_data.setdefault(group_id, {"tracking": False, "readers": []})
    save_data()
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="👋 مرحبًا! أرسل `.lurk on` لتفعيل تتبع القراء.")
    )

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip().lower()
    source = event.source

    if hasattr(source, "group_id"):
        group_id = source.group_id
    else:
        # إذا الرسالة ليست من مجموعة تجاهلها أو أرسل رسالة مناسبة
        return

    if group_id not in lurk_data:
        lurk_data[group_id] = {"tracking": False, "readers": []}

    if text == ".lurk on":
        lurk_data[group_id]["tracking"] = True
        lurk_data[group_id]["readers"] = []
        save_data()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ تم تفعيل الـ Lurk."))

    elif text == ".lurk off":
        lurk_data[group_id]["tracking"] = False
        save_data()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⛔ تم إيقاف الـ Lurk."))

    elif text == ".status":
        status = "مفعل ✅" if lurk_data[group_id]["tracking"] else "متوقف ⛔"
        count = len(lurk_data[group_id]["readers"])
        line_bot_api.reply_message(event.reply_token, TextSendMessage(
            text=f"📊 حالة Lurk: {status}\n👀 عدد القراء: {count}"
        ))

    elif text == ".clear":
        lurk_data[group_id]["readers"] = []
        save_data()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🗑 تم مسح قائمة القراء."))

    elif text == ".list":
        readers = lurk_data[group_id]["readers"]
        if not readers:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📭 لا يوجد قراء بعد."))
        else:
            reader_list = "\n".join([f"{r['name']} ({r['id']})" for r in readers])
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"👀 قائمة القراء:\n{reader_list}"))

# تابع لتحديث قائمة القراء عند استقبال رسالة جديدة
@handler.add(MessageEvent, message=TextMessage)
def track_readers(event):
    # فقط إذا التتبع مفعل نسجل الكاتب كقارئ
    source = event.source
    if hasattr(source, "group_id"):
        group_id = source.group_id
        user_id = source.user_id
        if lurk_data.get(group_id, {}).get("tracking"):
            # جلب اسم المستخدم
            try:
                profile = line_bot_api.get_group_member_profile(group_id, user_id)
                name = profile.display_name
            except Exception:
                name = "مستخدم مجهول"
            # إضافة القارئ إذا غير موجود
            if not any(r["id"] == user_id for r in lurk_data[group_id]["readers"]):
                lurk_data[group_id]["readers"].append({
                    "id": user_id,
                    "name": name,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                save_data()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
