import os
import sqlite3
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import TextMessage, MessageEvent
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
DB_PATH = 'C:\\data\\lurk.db' if os.getenv('RENDER') else 'lurk.db'

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
            conn.commit()
            logging.info("Database tables created successfully.")
    except Exception as e:
        logging.error(f"Critical error in init_db: {e}")

# باقي الكود...