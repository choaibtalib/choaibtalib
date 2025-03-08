from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import *
import threading
import time
import random
import os

app = Flask(__name__)

# =====================================
# === إعدادات البوت الرئيسي (الحماية) ===
# =====================================
MAIN_BOT_TOKEN = 'OGuV9/KT+JED14YLuEYZuyhi+BCCZfTSpRUD+OQzp3HXMQpvob/UteHHf10JOeNMz5sRMtXPH0/bNDdVtXfjno1tZGqIsJ4whziPkw4CO5VECZT56SaaFsRrvHI5wBPFNs6iFJIcfHSptnKZNcsnmgdB04t89/1O/w1cDnyilFU='
MAIN_BOT_SECRET = '7d0ad0324f874c8574f15058646fa067'
# =====================================
# === إعدادات أخرى ===
# =====================================
TARGET_GROUP_ID = 'GROUP_ID_HERE'  # المجموعة المستهدفة
BANNED_WORDS = ["سبام", "هاكر", " scam"]  # كلمات ممنوعة
BANNED_LINKS = ["http://", "https://"]  # روابط ممنوعة

# =====================================
# === تهيئة البوت ===
# =====================================
line_bot_api = LineBotApi(MAIN_BOT_TOKEN)
handler = WebhookHandler(MAIN_BOT_SECRET)

# =====================================
# === التعامل مع الأحداث ===
# =====================================
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    handler.handle(body, signature)
    return 'OK'

# =====================================
# === أوامر البوت ===
# =====================================
@handler.add(MessageEvent, message=TextMessage)
def handle_commands(event):
    message_text = event.message.text
    group_id = event.source.group_id

    # أمر الهجوم اليدوي (!attack)
    if message_text == "!attack":
        if is_admin(event.source.user_id):  # تحقق من صلاحية المشرف
            threading.Thread(target=start_flood, args=(group_id,)).start()
            line_bot_api.reply_message(event.reply_token, TextSendMessage("🚀 الهجوم بدأ!"))

    # كشف الروابط والكلمات الممنوعة
    if any(word in message_text for word in BANNED_WORDS) or any(link in message_text for link in BANNED_LINKS):
        user_id = event.source.user_id
        line_bot_api.kickout_from_group(group_id, user_id)
        line_bot_api.push_message(group_id, TextSendMessage("❌ تم طرد العضو بسبب نشاط مشبوه!"))

# =====================================
# === إذا طُرد البوت (تفعيل الإغراق) ===
# =====================================
@handler.add(UnfollowEvent)
def handle_unfollow(event):
    print("البوت طُرد! جارٍ تفعيل بوتات الحرب...")
    threading.Thread(target=start_flood, args=(TARGET_GROUP_ID,)).start()

# =====================================
# === دالة الإغراق (بوتات الحرب) ===
# =====================================
def start_flood(group_id):
    while True:
        for token in FAKE_BOT_TOKENS:
            try:
                fake_bot = LineBotApi(token)
                # إرسال رسالة عشوائية من قائمة محددة
                message = random.choice(["هذا النص سيُرسل بشكل جنوني!", "🔥🔥🔥", "الحماية فشلت!"])
                fake_bot.push_message(group_id, TextSendMessage(message))
                time.sleep(random.uniform(0.1, 0.3))  # تأخير عشوائي
            except Exception as e:
                print(f"خطأ في البوت {token}: {e}")

# =====================================
# === التحقق من صلاحية المشرف ===
# =====================================
def is_admin(user_id):
    # أضف هنا قائمة بالمشرفين المسموح لهم باستخدام !attack
    admins = ["ADMIN_USER_ID_1", "ADMIN_USER_ID_2"]
    return user_id in admins

if __name__ == "__main__":
    app.run(port=5000)