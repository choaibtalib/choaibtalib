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
BOT_IDS = {}  # سيتم تخزين البوتات الوهمية هنا (المفتاح: اسم البوت، القيمة: معرف البوت الوهمي)

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
    global lurking, seen_users, break_rules, BOT_IDS

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
    elif txt.startswith(".addbot"):
        # إضافة بوت وهمي
        bot_name = txt.split(" ", 1)[1].strip() if len(txt.split()) > 1 else None
        if not bot_name:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Usage: .addbot <bot_name>"))
            return

        fake_bot_id = f"FAKE_BOT_{len(BOT_IDS) + 1}"  # إنشاء معرف وهمي
        BOT_IDS[bot_name] = fake_bot_id
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"Bot '{bot_name}' added with ID: {fake_bot_id}"))
    elif txt.startswith(".bots"):
        # عرض قائمة البوتات الوهمية
        if not BOT_IDS:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="No fake bots added yet."))
        else:
            bots_list = "\n".join([f"{name}: {id}" for name, id in BOT_IDS.items()])
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"Fake bots list:\n{bots_list}"))
    elif txt.startswith(".task"):
        # توزيع مهمة على بوت وهمي
        parts = txt.split(" ", 2)
        if len(parts) < 3:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Usage: .task <bot_name> <message>"))
            return

        bot_name = parts[1]
        task_message = parts[2]

        if bot_name not in BOT_IDS:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"Bot '{bot_name}' not found."))
            return

        fake_bot_id = BOT_IDS[bot_name]
        group_id = event.source.group_id

        # إرسال رسالة من البوت الوهمي
        try:
            line_bot_api.push_message(group_id, TextSendMessage(text=f"[{bot_name}] says: {task_message}"))
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"Task assigned to bot '{bot_name}'."))
        except Exception as e:
            print(f"Error assigning task to bot {bot_name}: {e}")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"Failed to assign task to bot '{bot_name}'."))

    # منع المنشن
    if "@All" in txt:
        group_id = event.source.group_id
        user_id = event.source.user_id

        # إشعار بمحاولة كتابة @All
        line_bot_api.push_message(group_id, TextSendMessage(text="⚠️ Warning: Someone tried to mention everyone in the group!"))

        # طرد العضو الذي كتب @All
        try:
            line_bot_api.kick_out_from_group(group_id, user_id)
            line_bot_api.push_message(group_id, TextSendMessage(text="⚠️ The member has been kicked for mentioning everyone."))
        except Exception as e:
            print(f"Error kicking user {user_id}: {e}")
            line_bot_api.push_message(group_id, TextSendMessage(text="⚠️ Failed to kick the member. Ensure the bot has admin privileges."))

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
            # إذا لم يتمكن من الحصول على الاسم، استخدم النص الكامل للرسالة كاسم
            user_name = event.message.text.split()[0] if event.message.text else "Unknown User"

        # إضافة الاسم إلى القائمة إذا لم يكن موجودًا بالفعل
        if user_name not in seen_users:
            seen_users.append(user_name)

@handler.add(MemberLeftEvent)
def handle_member_left(event):
    # التحقق مما إذا كان العضو الذي غادر هو أحد البوتات الوهمية
    left_user_id = event.left.members[0].user_id
    if left_user_id in BOT_IDS.values():
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
    if joined_user_id in BOT_IDS.values():
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