import os
import sqlite3
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import TextMessage, MessageEvent, JoinEvent, LeaveEvent
import logging
import time

# إعداد تسجيل الأخطاء
logging.basicConfig(level=logging.DEBUG)

# استبدل هذه القيم بقيمك الخاصة
LINE_CHANNEL_ACCESS_TOKEN = 'OGuV9/KT+JED14YLuEYZuyhi+BCCZfTSpRUD+OQzp3HXMQpvob/UteHHf10JOeNMz5sRMtXPH0/bNDdVtXfjno1tZGqIsJ4whziPkw4CO5VECZT56SaaFsRrvHI5wBPFNs6iFJIcfHSptnKZNcsnmgdB04t89/1O/w1cDnyilFU='
LINE_CHANNEL_SECRET = '7d0ad0324f874c8574f15058646fa067'
OWNER_USER_ID = 'Ua673da6876bab906ce8734e94e59502a'

# تهيئة LINE Bot API
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# مسار قاعدة البيانات
DB_PATH = '/data/lurk.db' if os.getenv('RENDER') else 'lurk.db'

# حالة التتبع (Lurk)
LURK_MODE = False
LURK_SESSION_ID = 'lurk_session'

# تهيئة قاعدة البيانات
def init_db():
    try:
        db_dir = os.path.dirname(DB_PATH)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)  # إنشاء المجلد إذا لم يكن موجودًا

        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS lurk_messages
                         (message_id TEXT PRIMARY KEY, text TEXT, timestamp INTEGER)''')
            c.execute('''CREATE TABLE IF NOT EXISTS lurk_readers
                         (message_id TEXT, user_id TEXT, timestamp INTEGER, PRIMARY KEY (message_id, user_id))''')
            c.execute('''CREATE TABLE IF NOT EXISTS logs
                         (log_id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT, timestamp INTEGER)''')
            c.execute('''CREATE TABLE IF NOT EXISTS members
                         (user_id TEXT PRIMARY KEY, name TEXT, group_id TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS banned_users
                         (user_id TEXT PRIMARY KEY, reason TEXT, timestamp INTEGER)''')
            c.execute('''CREATE TABLE IF NOT EXISTS users
                         (id TEXT PRIMARY KEY, username TEXT, last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            conn.commit()
            logging.info("Database tables created successfully.")
    except Exception as e:
        logging.error(f"Critical error in init_db: {e}")

# دالة لإضافة مستخدم إلى الجدول users
def add_user_to_db(user_id, username):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)", (user_id, username))
            conn.commit()
            logging.info(f"User {username} added to the database.")
    except sqlite3.OperationalError as e:
        logging.error(f"Database Error in add_user_to_db: {e}")

# دالة لتحديث وقت النشاط
def update_user_activity(user_id):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
            conn.commit()
            logging.info(f"User {user_id} activity updated.")
    except sqlite3.OperationalError as e:
        logging.error(f"Database Error in update_user_activity: {e}")

# دالة لاسترجاع بيانات المستخدم
def get_user(user_id):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            return c.fetchone()
    except sqlite3.OperationalError as e:
        logging.error(f"Database Error in get_user: {e}")
        return None

# دالة لإضافة قارئ إلى قاعدة البيانات
def add_reader(user_id):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO lurk_readers (message_id, user_id, timestamp) VALUES (?, ?, ?)",
                      (LURK_SESSION_ID, user_id, int(time.time())))
            conn.commit()
    except sqlite3.OperationalError as e:
        logging.error(f"Database Error in add_reader: {e}")

# دالة لعرض قائمة القراء
def show_readers(event):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT user_id FROM lurk_readers WHERE message_id = ?", (LURK_SESSION_ID,))
            readers = c.fetchall()

            if readers:
                reader_ids = [reader[0] for reader in readers]
                message = f"الأعضاء النشطاء: {', '.join(reader_ids)}"
            else:
                message = "لا يوجد أعضاء نشطاء حتى الآن."

            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text=message)
            )
            log_event("Readers list requested")
    except sqlite3.OperationalError as e:
        logging.error(f"Database Error in show_readers: {e}")
        line_bot_api.reply_message(
            event.reply_token,
            TextMessage(text="حدث خطأ أثناء عرض قائمة القراء.")
        )

# دالة لتسجيل الأحداث
def log_event(event):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO logs (event, timestamp) VALUES (?, ?)",
                      (event, int(time.time())))
            conn.commit()
    except sqlite3.OperationalError as e:
        logging.error(f"Database Error in log_event: {e}")

# دالة للتعامل مع الأوامر
def handle_command(event):
    global LURK_MODE

    message_text = event.message.text.lower()
    user_id = event.source.user_id
    group_id = event.source.group_id if hasattr(event.source, 'group_id') else None

    if user_id != OWNER_USER_ID and not message_text.startswith('!'):
        return

    if user_id == OWNER_USER_ID:
        if message_text == '.u':
            LURK_MODE = True
            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text="تم تفعيل وضع التتبع.")
            )
            log_event("Lurk Mode Activated")
            return

        if message_text == '.o':
            LURK_MODE = False
            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text="تم إيقاف وضع التتبع.")
            )
            log_event("Lurk Mode Deactivated")
            return

        if message_text == '.p':
            show_readers(event)
            return

        if message_text == 'id g':
            if group_id:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextMessage(text=f"معرف المجموعة: {group_id}"))
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextMessage(text="هذا الأمر يعمل فقط في المجموعات."))
            return

        if message_text == 'id a':
            if group_id:
                try:
                    members = line_bot_api.get_group_member_ids(group_id)
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextMessage(text=f"معرفات الأعضاء: {', '.join(members)}"))
                except LineBotApiError as e:
                    logging.error(f"LineBotApiError occurred: {e}")
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextMessage(text="حدث خطأ أثناء جلب معرفات الأعضاء."))
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextMessage(text="هذا الأمر يعمل فقط في المجموعات."))
            return

        # أمر جديد: عرض معلومات المستخدم
        if message_text == '!myinfo':
            user_data = get_user(user_id)
            if user_data:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextMessage(text=f"معلوماتك:\nID: {user_data[0]}\nالاسم: {user_data[1]}\nآخر نشاط: {user_data[2]}"))
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextMessage(text="لم يتم العثور على معلوماتك."))
            return

    if LURK_MODE and user_id != OWNER_USER_ID:
        add_reader(user_id)

# إعداد التطبيق
app = Flask(__name__)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    events = request.json.get('events', [])
    if not events:
        logging.warning("No events found in the request.")
        return 'OK'

    delivery_context = events[0].get('deliveryContext', {})
    if delivery_context.get('isRedelivery', False):
        logging.info("Ignoring redelivered event.")
        return 'OK'

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    try:
        user_id = event.source.user_id
        username = line_bot_api.get_profile(user_id).display_name

        # إضافة المستخدم إلى قاعدة البيانات إذا لم يكن موجودًا
        add_user_to_db(user_id, username)

        # تحديث وقت النشاط
        update_user_activity(user_id)

        # التعامل مع الأوامر
        handle_command(event)

    except LineBotApiError as e:
        logging.error(f"LineBotApiError occurred: {e}")
    except Exception as e:
        logging.error(f"Unexpected error occurred: {e}")

@handler.add(JoinEvent)
def handle_join(event):
    try:
        group_id = event.source.group_id
        user_id = event.source.user_id
        log_event(f"User {user_id} joined group {group_id}")
    except Exception as e:
        logging.error(f"Error handling join event: {e}")

@handler.add(LeaveEvent)
def handle_leave(event):
    try:
        group_id = event.source.group_id
        user_id = event.source.user_id
        log_event(f"User {user_id} left group {group_id}")
    except Exception as e:
        logging.error(f"Error handling leave event: {e}")

if __name__ == "__main__":
    init_db()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))