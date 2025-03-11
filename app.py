from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    ImageSendMessage, StickerSendMessage,
    MemberJoinedEvent, MemberLeftEvent
)
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

# قائمة البوتات الوهمية
BOT_IDS = ["CR7", "BOT_FAKE_2", "BOT_FAKE_3"]  # معرفات وهمية للبوتات

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

    # تسجيل مصدر الرسالة
    print(f"Message received from user_id: {event.source.user_id}, type: {event.source.type}")

    txt = event.message.text.strip()

    # أوامر خاصة بالمالك فقط
    if txt.startswith("."):
        if event.source.user_id != OWNER_USER_ID:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="You are not authorized to use this command."))
            return

    # معالجة الأوامر
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
            names_list = "\n".join(seen_users)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"Users who read the message:\n{names_list}"))
    elif txt == ".break rules":
        break_rules = not break_rules
        if break_rules:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ Rules are now broken! Proceed with caution. You are fully responsible for any consequences. ⚠️"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Rules are restored. Normal operation resumed."))
    elif txt == ".help":
        help_message = """Available commands:
- .lurk on: Enable lurking mode.
- .lurk off: Disable lurking mode.
- .wr: Show users who read the message.
- .break rules: Toggle breaking rules mode.
- .sticker: Send a random sticker.
- .image: Send an image."""
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=help_message))
    elif txt == ".sticker":
        # إرسال ملصق عشوائي
        sticker_message = StickerSendMessage(
            package_id='11537',
            sticker_id='52002734'
        )
        line_bot_api.reply_message(event.reply_token, sticker_message)
    elif txt == ".image":
        # إرسال صورة
        image_message = ImageSendMessage(
            original_content_url='https://example.com/image.jpg',
            preview_image_url='https://example.com/image_preview.jpg'
        )
        line_bot_api.reply_message(event.reply_token, image_message)

    # منع المنشن
    if "@everyone" in txt:
        group_id = event.source.group_id
        line_bot_api.push_message(group_id, TextSendMessage(text="⚠️ Warning: Someone mentioned everyone in the group!"))

    # معالجة رسائل المجموعة
    if lurking and event.source.type == "group":
        group_id = event.source.group_id
        user_id = event.source.user_id

        try:
            # الحصول على اسم المستخدم من المجموعة
            profile = line_bot_api.get_group_member_profile(group_id, user_id)
            user_name = profile.display_name
        except Exception as e:
            print(f"Error fetching profile for user_id {user_id}: {e}")
            user_name = "Unknown User"

        # إضافة الاسم إلى القائمة إذا لم يكن موجودًا بالفعل
        if user_name not in seen_users:
            seen_users.append(user_name)

@handler.add(MemberLeftEvent)
def handle_member_left(event):
    # التحقق مما إذا كان العضو الذي غادر هو أحد البوتات الوهمية
    left_user_id = event.left.members[0].user_id
    if left_user_id in BOT_IDS:
        group_id = event.source.group_id
        try:
            line_bot_api.invite_into_group(group_id, [left_user_id])
            line_bot_api.push_message(group_id, TextSendMessage(text=f"Bot {left_user_id} has been re-invited to the group."))
        except Exception as e:
            print(f"Error re-inviting bot {left_user_id}: {e}")

@handler.add(MemberJoinedEvent)
def handle_member_joined(event):
    # التحقق مما إذا كان العضو الجديد هو أحد البوتات الوهمية
    joined_user_id = event.joined.members[0].user_id
    if joined_user_id in BOT_IDS:
        group_id = event.source.group_id
        line_bot_api.push_message(group_id, TextSendMessage(text=f"Bot {joined_user_id} has joined the group."))

    # إشعار المالك عند انضمام أعضاء جدد
    if joined_user_id != OWNER_USER_ID:
        line_bot_api.push_message(OWNER_USER_ID, TextSendMessage(text=f"⚠️ New member joined the group: {joined_user_id}"))

@app.route("/")
def index():
    return "Hello, this is a LINE bot."

if __name__ == "__main__":
    app.run(port=8000)