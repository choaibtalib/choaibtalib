from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import TextMessage, TextSendMessage

app = Flask(__name__)

# إعداد الـ Channel Secret و الـ Access Token
line_bot_api = LineBotApi('OGuV9/KT+JED14YLuEYZuyhi+BCCZfTSpRUD+OQzp3HXMQpvob/UteHHf10JOeNMz5sRMtXPH0/bNDdVtXfjno1tZGqIsJ4whziPkw4CO5VECZT56SaaFsRrvHI5wBPFNs6iFJIcfHSptnKZNcsnmgdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('7d0ad0324f874c8574f15058646fa067')

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.default()
def default(event):
    # استجابة لكل رسالة
    if isinstance(event.message, TextMessage):
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='مرحباً! كيف يمكنني مساعدتك؟'))

if __name__ == "__main__":
    app.run()