import os
import sqlite3
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
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
    
    # إنشاء جدول الأعضاء
    c.execute('''CREATE TABLE IF NOT EXISTS members 
                 (mid TEXT PRIMARY KEY, name TEXT, last_seen INTEGER, status TEXT)''')
    
    # إنشاء جدول الرسائل
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

# عرض القراء
def show_readers(event):
    """عرض الأشخاص الذين قرأوا آخر رسالة"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # الحصول على آخر رسالة
    cursor.execute("SELECT msg_id, read_count FROM messages ORDER BY timestamp DESC LIMIT 1")
    last_message = cursor.fetchone()

    if not last_message:
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="لا توجد رسائل سابقة.")
            )
        except LineBotApiError as e:
            logging.error(f"خطأ في الرد على الرسالة: {e}")
        return

    last_msg_id, read_count = last_message

    # الحصول على القراء المحتملين
    cursor.execute("SELECT name FROM members WHERE status = 'possible_reader' LIMIT ?", (read_count,))
    readers = cursor.fetchall()

    if not readers:
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="لم يتم العثور على قراء لهذه الرسالة.")
            )
        except LineBotApiError as e:
            logging.error(f"خطأ في الرد على الرسالة: {e}")
    else:
        readers_list = "\n".join([reader[0] for reader in readers])
        reply_text = f"عدد القراء: {read_count}\nأسماء القراء:\n{readers_list}"
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply_text)
            )
        except LineBotApiError as e:
            logging.error(f"خطأ في الرد على الرسالة: {e}")

# معالجة الأوامر النصية
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """معالجة الرسائل النصية القادمة"""
    user_message = event.message.text.strip()
    logging.info(f"تم استقبال رسالة: {user_message}")

    try:
        if user_message == ".r":
            show_readers(event)
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"لقد قلت: {user_message}")
            )
    except LineBotApiError as e:
        logging.error(f"خطأ في الرد على الرسالة: {e}")

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

@app.route("/", methods=['GET'])
def home():
    """الصفحة الرئيسية"""
    return "Welcome to the LINE Bot service!"

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