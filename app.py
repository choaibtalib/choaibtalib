from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os

app = Flask(__name__)

# قراءة المتغيرات البيئية
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')

# التحقق من وجود القيم
if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    raise ValueError("Please set LINE_CHANNEL_ACCESS_TOKEN and LINE_CHANNEL_SECRET in your environment variables.")

# استخدام القيم
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# حالات البوت
lurking = False
seen_users = []
break_rules = False  # حالة كسر القواعد

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except Exception as e:
        print(f'Error: {e}')
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global lurking, seen_users, break_rules

    txt = event.message.text.strip()

    if txt == ".lurk on":
        lurking = True
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Lurking is now ON."))
    elif txt == ".lurk off":
        lurking = False
        seen_users = []
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Lurking is now OFF."))
    elif txt == ".break rules":
        break_rules = not break_rules  # تبديل حالة كسر القواعد
        if break_rules:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ Rules are now broken! Proceed with caution. You are fully responsible for any consequences. ⚠️"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Rules are restored. Normal operation resumed."))
    else:
        if lurking:
            seen_users.append(event.source.user_id)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"User {event.source.user_id} has read the message."))

        if break_rules:
            # تنفيذ أفعال خاصة عند كسر القواعد
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ This action is executed under 'Break Rules' mode. You are responsible for any consequences. ⚠️"))

@app.route("/")
def index():
    return "Hello, this is a LINE bot."

if __name__ == "__main__":
    app.run(port=8000)