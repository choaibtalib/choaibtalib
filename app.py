import os
import sqlite3
import logging
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FollowEvent, UnfollowEvent, JoinEvent, LeaveEvent

# تهيئة السجلات (Logging)
logging.basicConfig(level=logging.INFO)

# مسارات ومفاتيح API
LINE_CHANNEL_ACCESS_TOKEN = 'OGuV9/KT+JED14YLuEYZuyhi+BCCZfTSpRUD+OQzp3HXMQpvob/UteHHf10JOeNMz5sRMtXPH0/bNDdVtXfjno1tZGqIsJ4whziPkw4CO5VECZT56SaaFsRrvHI5wBPFNs6iFJIcfHSptnKZNcsnmgdB04t89/1O/w1cDnyilFU='
LINE_CHANNEL_SECRET = '7d0ad0324f874c8574f15058646fa067'

# معرف المالك (يمكن فقط للمالك إرسال الأوامر)
OWNER_USER_ID = 'Ua673da6876bab906ce8734e94e59502a'

# مسار قاعدة البيانات
DB_PATH = r'C:\Data\lurk.db' if os.getenv('RENDER') else r'C:\Data\your_bot_project\lurk.db'

# طباعة المسار للتأكد منه
print(f"مسار قاعدة البيانات: {DB_PATH}")

# إنشاء المجلد إذا لم يكن موجودًا
db_dir = os.path.dirname(DB_PATH)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)
    print(f"تم إنشاء المجلد: {db_dir}")

# تهيئة قاعدة البيانات
def init_db():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS lurk_messages
                         (message_id TEXT PRIMARY KEY, text TEXT, timestamp INTEGER)''')
            c.execute('''CREATE TABLE IF NOT EXISTS lurk_readers
                         (message_id TEXT, user_id TEXT, timestamp INTEGER, PRIMARY KEY (message_id, user_id))''')
            c.execute('''CREATE TABLE IF NOT EXISTS logs
                         (log_id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT, timestamp INTEGER)''')
            c.execute('''CREATE TABLE IF NOT EXISTS group_members
                         (group_id TEXT, user_id TEXT, username TEXT, UNIQUE(group_id, user_id))''')
            c.execute('''CREATE TABLE IF NOT EXISTS tracking_status
                         (status TEXT)''')
            # إعداد حالة التتبع الافتراضية
            c.execute('INSERT OR IGNORE INTO tracking_status (status) VALUES (?)', ('off',))
            conn.commit()
            logging.info("Database tables created successfully.")
    except Exception as e:
        logging.error(f"Critical error in init_db: {e}")

# استدعاء الدالة لتهيئة قاعدة البيانات
init_db()

# تهيئة Flask app
app = Flask(__name__)

# تهيئة Line Bot API
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# دالة لإضافة رسالة جديدة إلى قاعدة البيانات
def add_message_to_db(message_id, text, timestamp):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('INSERT OR IGNORE INTO lurk_messages (message_id, text, timestamp) VALUES (?, ?, ?)',
                      (message_id, text, timestamp))
            conn.commit()
            logging.info(f"Message added to DB: {message_id}")
    except Exception as e:
        logging.error(f"Database Error in add_message_to_db: {e}")

# دالة لتحديث نشاط المستخدم في قاعدة البيانات
def update_user_activity(user_id, message_id, timestamp):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('INSERT OR IGNORE INTO lurk_readers (message_id, user_id, timestamp) VALUES (?, ?, ?)',
                      (message_id, user_id, timestamp))
            conn.commit()
            logging.info(f"User activity updated: {user_id}")
    except Exception as e:
        logging.error(f"Database Error in update_user_activity: {e}")

# دالة لإضافة تسجيل جديد إلى سجل الأحداث
def log_event(event, timestamp):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('INSERT INTO logs (event, timestamp) VALUES (?, ?)', (event, timestamp))
            conn.commit()
            logging.info(f"Event logged: {event}")
    except Exception as e:
        logging.error(f"Database Error in log_event: {e}")

# دالة لتشغيل أو إيقاف التتبع
def toggle_tracking(status):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('UPDATE tracking_status SET status = ?', (status,))
            conn.commit()
            logging.info(f"Tracking status updated to: {status}")
    except Exception as e:
        logging.error(f"Database Error in toggle_tracking: {e}")

# دالة للحصول على حالة التتبع
def get_tracking_status():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('SELECT status FROM tracking_status')
            result = c.fetchone()
            return result[0] if result else 'off'
    except Exception as e:
        logging.error(f"Database Error in get_tracking_status: {e}")
        return 'off'

# دالة لتخزين أعضاء المجموعة
def store_group_members(group_id):
    try:
        members = line_bot_api.get_group_members_summary(group_id)
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            for member in members.user_ids:
                profile = line_bot_api.get_group_member_profile(group_id, member)
                c.execute('INSERT OR IGNORE INTO group_members (group_id, user_id, username) VALUES (?, ?, ?)',
                          (group_id, member, profile.display_name))
            conn.commit()
            logging.info(f"Stored members for group: {group_id}")
    except Exception as e:
        logging.error(f"Error storing group members: {e}")

# نقطة النهاية لـ Webhook
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    logging.info(f"Request body: {body}")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logging.error("Invalid signature. Please check your channel access token/secret.")
        abort(400)

    return 'OK'

# معالجة الرسائل الواردة
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    message_id = event.message.id
    text = event.message.text
    timestamp = event.timestamp

    # إضافة الرسالة إلى قاعدة البيانات
    add_message_to_db(message_id, text, timestamp)

    # تحديث نشاط المستخدم
    update_user_activity(user_id, message_id, timestamp)

    # تسجيل الحدث
    log_event(f"User {user_id} sent message: {text}", timestamp)

    try:
        # التحقق مما إذا كان المستخدم هو المالك
        if user_id == OWNER_USER_ID:
            if text.startswith('.'):
                command = text[1:].strip()
                if command == 'p':
                    # عرض المستخدمين الذين قرؤوا الرسالة
                    with sqlite3.connect(DB_PATH) as conn:
                        c = conn.cursor()
                        c.execute('SELECT DISTINCT user_id FROM lurk_readers WHERE message_id = ?', (message_id,))
                        readers = c.fetchall()
                        if readers:
                            reader_list = "\n".join([reader[0] for reader in readers])
                            line_bot_api.reply_message(
                                event.reply_token,
                                TextSendMessage(text=f"Users who read the message:\n{reader_list}")
                            )
                        else:
                            line_bot_api.reply_message(
                                event.reply_token,
                                TextSendMessage(text="No users have read this message yet.")
                            )
                elif command == 'o':
                    # إيقاف التتبع
                    toggle_tracking('off')
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text="Tracking turned off.")
                    )
                elif command == 'u':
                    # تشغيل التتبع
                    toggle_tracking('on')
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text="Tracking turned on.")
                    )
                elif command.startswith('id g'):
                    # الحصول على ID المجموعة
                    group_id = event.source.group_id if hasattr(event.source, 'group_id') else None
                    if group_id:
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text=f"Group ID: {group_id}")
                        )
                    else:
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text="This command can only be used in a group.")
                        )
                elif command.startswith('id a'):
                    # تخزين أعضاء المجموعة
                    group_id = event.source.group_id if hasattr(event.source, 'group_id') else None
                    if group_id:
                        store_group_members(group_id)
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text="Group members stored successfully.")
                        )
                    else:
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text="This command can only be used in a group.")
                        )
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"Thank you for your message: {text}")
                )
        else:
            # المستخدم غير المالك لا يمكنه إرسال أوامر
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="You are not authorized to send commands.")
            )
    except Exception as e:
        logging.error(f"Error in handling message: {e}")

# تشغيل التطبيق
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))