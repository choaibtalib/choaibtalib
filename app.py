from flask import Flask, request, abort
import os
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, PostbackEvent, PostbackAction, TemplateSendMessage, ButtonsTemplate

app = Flask(__name__)

# استخدام متغيرات البيئة كما هي عندك
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")
ADMIN_USER_ID = os.getenv("USER_ID")  # الأدمن الرئيسي

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET or not ADMIN_USER_ID:
    raise Exception("يرجى ضبط متغيرات البيئة CHANNEL_ACCESS_TOKEN و CHANNEL_SECRET و USER_ID")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# القوائم لكل خيار
shared_list = []
not_shared_list = []

# دالة لإرسال الاستفتاء
def send_poll():
    buttons = TemplateSendMessage(
        alt_text='استفتاء المشاركة',
        template=ButtonsTemplate(
            title='حرب المجد',
            text='اختر خيارك:',
            actions=[
                PostbackAction(label='شارك', data='share'),
                PostbackAction(label='لا تسلم القلعة', data='not_share')
            ]
        )
    )
    line_bot_api.push_message(ADMIN_USER_ID, buttons)  # إرسال للأدمن أو مجموعة محددة

# دالة لتحديث القائمة
def update_list(user_name, choice):
    global shared_list, not_shared_list
    if choice == 'share':
        if user_name in shared_list:
            return "لقد اخترت هذا الخيار مسبقًا!"
        if user_name in not_shared_list:
            not_shared_list.remove(user_name)
        shared_list.append(user_name)
    elif choice == 'not_share':
        if user_name in not_shared_list:
            return "لقد اخترت هذا الخيار مسبقًا!"
        if user_name in shared_list:
            shared_list.remove(user_name)
        not_shared_list.append(user_name)
    return None

# عرض القوائم الحالية
def get_list_message():
    msg = "🔹 المشاركون:\n"
    if shared_list:
        msg += "\n".join(shared_list)
    else:
        msg += "لا أحد بعد."
    msg += "\n\n🔹 الذين لم يسلموا القلعة:\n"
    if not_shared_list:
        msg += "\n".join(not_shared_list)
    else:
        msg += "لا أحد بعد."
    return msg

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def on_message(event):
    text = event.message.text.lower()
    if text == 'استفتاء':
        send_poll()
    elif text == 'القائمة':
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=get_list_message()))

@handler.add(PostbackEvent)
def on_postback(event):
    user_name = event.source.user_id  # أو يمكن تعديل ليستخدم displayName
    choice = event.postback.data
    error = update_list(user_name, choice)
    if error:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=error))
    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=get_list_message()))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
    
