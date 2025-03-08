import os
import sqlite3

# مسار قاعدة البيانات
DB_PATH = '/data/lurk.db' if os.getenv('RENDER') else 'lurk.db'

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

# استدعاء الدالة لتهيئة قاعدة البيانات
init_db()