import sqlite3
from linepy import *
import time
import logging
import threading
import os
from datetime import datetime

# إعداد السجل (Logging) لتتبع العمليات بتفصيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_log.log'),  # حفظ السجل في ملف
        logging.StreamHandler()  # عرض السجل في الطرفية
    ]
)

# المتغيرات العامة (قابلة للتعديل)
GROUP_ID = 'YOUR_GROUP_ID'  # استبدل بمعرف المجموعة
EMAIL = 'your_email@example.com'  # بريدك في LINE
PASSWORD = 'your_password'  # كلمة المرور
DB_NAME = 'group_data.db'  # اسم قاعدة البيانات

# الاتصال بـ LINE
def connect_to_line():
    """الاتصال بحساب LINE باستخدام Linepy"""
    try:
        line = LINE(EMAIL, PASSWORD)
        logging.info(f"تم الاتصال بنجاح، اسم المستخدم: {line.profile.displayName}")
        return line
    except Exception as e:
        logging.error(f"فشل الاتصال بـ LINE: {e}")
        return None

# إعداد قاعدة البيانات
def setup_database():
    """إنشاء جداول لتخزين الأعضاء والرسائل"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS members 
                 (mid TEXT PRIMARY KEY, name TEXT, last_seen INTEGER, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages 
                 (msg_id TEXT PRIMARY KEY, content TEXT, read_count INTEGER, timestamp INTEGER)''')
    conn.commit()
    logging.info("تم إعداد قاعدة البيانات بنجاح")
    return conn, c

# جلب وتخزين أعضاء المجموعة
def fetch_and_store_members(line, group_id, conn, cursor):
    """جلب بيانات الأعضاء وحفظها في قاعدة البيانات"""
    try:
        group = line.getGroup(group_id)
        members = group.members
        for member in members:
            cursor.execute("INSERT OR REPLACE INTO members (mid, name, last_seen, status) VALUES (?, ?, ?, ?)",
                          (member.mid, member.displayName, int(time.time()), "unknown"))
        conn.commit()
        logging.info(f"تم حفظ {len(members)} عضو في قاعدة البيانات")
    except Exception as e:
        logging.error(f"خطأ في جلب الأعضاء: {e}")

# إرسال رسالة اختبار
def send_test_message(line, group_id, conn, cursor):
    """إرسال رسالة لتتبع القراء وحفظها"""
    message = f"رسالة اختبار - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    try:
        msg = line.sendMessage(group_id, message)
        msg_id = msg.id
        cursor.execute("INSERT INTO messages (msg_id, content, read_count, timestamp) VALUES (?, ?, ?, ?)",
                      (msg_id, message, 0, int(time.time())))
        conn.commit()
        logging.info(f"تم إرسال الرسالة: {message} (ID: {msg_id})")
        return msg_id
    except Exception as e:
        logging.error(f"خطأ في إرسال الرسالة: {e}")
        return None

# تتبع عدد القراء وتحديث قاعدة البيانات
def track_readers(line, group_id, msg_id, conn, cursor):
    """تتبع عدد القراء باستخدام Linepy (محدود)"""
    last_read_count = 0
    while True:
        try:
            group = line.getGroup(group_id)
            # ملاحظة: هذه دالة افتراضية، تحقق من Linepy إذا كانت متاحة
            read_count = getattr(group, 'getReadCount', lambda x: 0)(msg_id)  # إذا لم تكن موجودة، يرجع 0
            if read_count != last_read_count:
                cursor.execute("UPDATE messages SET read_count = ? WHERE msg_id = ?", (read_count, msg_id))
                conn.commit()
                logging.info(f"تغير عدد القراء إلى: {read_count} في {datetime.now()}")
                last_read_count = read_count
                infer_readers(conn, cursor, read_count)
            time.sleep(5)  # فحص كل 5 ثوانٍ
        except Exception as e:
            logging.error(f"خطأ في تتبع القراء: {e}")
            break

# استنتاج القراء الصامتين
def infer_readers(conn, cursor, read_count):
    """محاولة استنتاج من قرأ بناءً على البيانات المتاحة"""
    cursor.execute("SELECT mid, name FROM members WHERE status = 'unknown' LIMIT ?", (read_count,))
    possible_readers = cursor.fetchall()
    if possible_readers:
        logging.info("القراء المحتملون (استنتاج):")
        for mid, name in possible_readers:
            logging.info(f"- {name} (MID: {mid})")
            # تحديث الحالة إلى 'قارئ محتمل'
            cursor.execute("UPDATE members SET status = 'possible_reader' WHERE mid = ?", (mid,))
        conn.commit()

# تعليمات Wireshark (يدوية)
def wireshark_instructions():
    """تعليمات لاستخدام Wireshark مع البوت"""
    instructions = """
    تعليمات Wireshark لتحليل القراء الصامتين:
    1. شغل Wireshark واختر واجهة الشبكة (مثل Wi-Fi).
    2. ضع فلتر مثل: `ip.dst == line.me || ip.dst == api.line.me`.
    3. افتح LINE على هاتفك (نفس الشبكة) وأرسل رسالة للمجموعة.
    4. راقب الحزم عندما يتغير عدد القراء في السجل (bot_log.log).
    5. ابحث عن أنماط (مثل حزم HTTPS متكررة تحمل أيديات أو طلبات تحديث).
    6. قارن توقيت الحزم مع تغييرات عدد القراء لتحديد القراء الصامتين.
    ملاحظة: البيانات مشفرة، لكن التوقيت والعدد قد يعطيان استنتاجات.
    """
    print(instructions)
    logging.info("تم عرض تعليمات Wireshark")

# تشغيل البوت في خيط منفصل
def run_bot():
    """تشغيل البوت الرئيسي"""
    line = connect_to_line()
    if not line:
        return
    
    conn, cursor = setup_database()
    fetch_and_store_members(line, GROUP_ID, conn, cursor)
    msg_id = send_test_message(line, GROUP_ID, conn, cursor)
    
    if msg_id:
        # تشغيل تتبع القراء في خيط منفصل
        tracker_thread = threading.Thread(target=track_readers, args=(line, GROUP_ID, msg_id, conn, cursor))
        tracker_thread.daemon = True
        tracker_thread.start()
        logging.info("بدأ تتبع القراء في الخلفية")
    
    # عرض تعليمات Wireshark
    wireshark_instructions()
    
    # إبقاء البرنامج شغالًا
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("تم إيقاف البوت")
        conn.close()

# البرنامج الرئيسي
if __name__ == "__main__":
    logging.info("بدء تشغيل البوت...")
    run_bot()