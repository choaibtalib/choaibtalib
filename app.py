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

# معرف المالك (يستطيع إرسال الأوامر فقط)
OWNER_USER_ID = "Ua673da6876bab906ce8734e94e59502a"

# حالات البوت
lurking = False
seen_users = []  # قائمة لتخزين أسماء المستخدمين الذين قرأوا الرسالة
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

    # التحقق من أن الأمر يأتي من المالك فقط
    if event.source.user_id != OWNER_USER_ID:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="You are not authorized to use this command."))
        return

    txt = event.message.text.strip()

    if txt == ".lurk on":
        lurking = True
        seen_users = []  # تفريغ القائمة عند تفعيل وضع التتبع
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Lurking is now ON."))
    elif txt == ".lurk off":
        lurking = False
        seen_users = []  # حذف جميع الأسماء عند إيقاف وضع التتبع
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Lurking is now OFF. Data cleared."))
    elif txt == ".wr":
        if not seen_users:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="No users have read the message yet."))
        else:
            # إرسال قائمة الأسماء
            names_list = "\n".join(seen_users)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"Users who read the message:\n{names_list}"))
    elif txt == ".break rules":
        break_rules = not break_rules  # تبديل حالة كسر القواعد
        if break_rules:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ Rules are now broken! Proceed with caution. You are fully responsible for any consequences. ⚠️"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Rules are restored. Normal operation resumed."))

# معالجة رسائل المجموعة
@handler.add(MessageEvent, message=TextMessage)
def handle_group_message(event):
    global lurking, seen_users

    if lurking and event.source.type == "group":
        group_id = event.source.group_id
        user_id = event.source.user_id

        try:
            # الحصول على اسم المستخدم من المجموعة
            profile = line_bot_api.get_group_member_profile(group_id, user_id)
            user_name = profile.display_name
        except Exception as e:
            user_name = "Unknown User"  # في حالة فشل استخراج الاسم

        # إضافة الاسم إلى القائمة إذا لم يكن موجودًا بالفعل
        if user_name not in seen_users:
            seen_users.append(user_name)

@app.route("/")
def index():
    return "Hello, this is a LINE bot."

if __name__ == "__main__":
    app.run(port=8000)