import os
import sqlite3
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from flask import Flask, request, jsonify
import time
import logging
import threading
from datetime import datetime

# إعداد السجل (Logging)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_log.log'),  # حفظ السجل في ملف
        logging.StreamHandler()  # عرض السجل في الطرفية
    ]
)

# قراءة المتغيرات البيئية أو استخدام قيم افتراضية
CHANNEL_ACCESS_TOKEN = 'OGuV9/KT+JED14YLuEYZuyhi+BCCZfTSpRUD+OQzp3HXMQpvob/UteHHf10JOeNMz5sRMtXPH0/bNDdVtXfjno1tZGqIsJ4whziPkw4CO5VECZT56SaaFsRrvHI5wBPFNs6iFJIcfHSptnKZNcsnmgdB04t89/1O/w1cDnyilFU='
CHANNEL_SECRET = '7d0ad0324f874c8574f15058646fa067'
DB_NAME = 'group_data.db'

# التحقق من وجود المتغيرات البيئية
if not all([CHANNEL_ACCESS_TOKEN, CHANNEL_SECRET]):
    logging.error("لم يتم العثور على جميع المتغيرات البيئية المطلوبة.")
    exit(1)

# الاتصال بـ LINE باستخدام Channel Access Token وChannel Secret
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

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

# إرسال رسالة اختبار
def send_test_message(group_id, conn, cursor):
    """إرسال رسالة لتتبع القراء وحفظها"""
    message = f"رسالة اختبار - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    try:
        msg = line_bot_api.push_message(group_id, TextSendMessage(text=message))
        msg_id = msg.message_id
        cursor.execute("INSERT INTO messages (msg_id, content, read_count, timestamp) VALUES (?, ?, ?, ?)",
                      (msg_id, message, 0, int(time.time())))
        conn.commit()
        logging.info(f"تم إرسال الرسالة: {message} (ID: {msg_id})")
        return msg_id
    except Exception as e:
        logging.error(f"خطأ في إرسال الرسالة: {e}")
        return None

# تتبع عدد القراء وتحديث قاعدة البيانات
def track_readers(group_id, msg_id, conn, cursor):
    """تتبع عدد القراء باستخدام Linepy (محدود)"""
    last_read_count = 0
    while True:
        try:
            group = line_bot_api.get_group_summary(group_id)
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
            cursor.execute("UPDATE members SET status = 'possible_reader' WHERE mid = ?", (mid,))
        conn.commit()

# إعداد Flask لتلقي طلبات الويبهووك
app = Flask(__name__)

@app.route("/callback", methods=['POST'])
def callback():
    """معالجة طلبات الويبهووك من LINE"""
    body = request.get_data(as_text=True)
    signature = request.headers['X-Line-Signature']
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logging.error("خطأ في التوقيع: التوقيع غير صالح.")
        return jsonify({"status": "error", "message": "Invalid signature"}), 400
    except Exception as e:
        logging.error(f"خطأ في معالجة الويبهووك: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
    return jsonify({"status": "success"}), 200

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """معالجة الرسائل النصية القادمة"""
    user_message = event.message.text
    logging.info(f"تم استقبال رسالة: {user_message}")
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"لقد قلت: {user_message}")
    )

# تشغيل البوت في خيط منفصل
def run_bot():
    """تشغيل البوت الرئيسي"""
    conn, cursor = setup_database()
    
    # بدء تشغيل Flask
    app.run(host="0.0.0.0", port=int(os.getenv('PORT', 5000)))

# البرنامج الرئيسي
if __name__ == "__main__":
    logging.info("بدء تشغيل البوت...")
    run_bot()