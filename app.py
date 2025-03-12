from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests

# إنشاء تطبيق Flask
app = Flask(__name__)

# معلومات تسجيل الدخول إلى LINE
EMAIL = "choaib03dz@gmail.com"
PASSWORD = "123chl!321"

# معلومات LINE Messaging API
CHANNEL_ACCESS_TOKEN = "OGuV9/KT+JED14YLuEYZuyhi+BCCZfTSpRUD+OQzp3HXMQpvob/UteHHf10JOeNMz5sRMtXPH0/bNDdVtXfjno1tZGqIsJ4whziPkw4CO5VECZT56SaaFsRrvHI5wBPFNs6iFJIcfHSptnKZNcsnmgdB04t89/1O/w1cDnyilFU="
OWNER_USER_ID = "Ua673da6876bab906ce8734e94e59502a"  # ID الخاص بالمشرف (المالك)

# تعريف المسار الرئيسي
@app.route('/')
def home():
    return "Hello, World!"

# وظيفة للحصول على قائمة المستخدمين المتصلين
def get_online_users():
    # إعداد الخيارات لتشغيل المتصفح في وضع headless
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # تشغيل المتصفح بدون واجهة رسومية
    chrome_options.add_argument("--no-sandbox")  # ضروري للأمان في البيئات المشتركة
    chrome_options.add_argument("--disable-dev-shm-usage")  # حل مشكلة ذاكرة التخزين المؤقت
    chrome_options.add_argument("--disable-gpu")  # تعطيل GPU (ضروري في بعض البيئات)

    # تهيئة المتصفح
    driver = webdriver.Chrome(options=chrome_options)

    try:
        # الانتقال إلى صفحة تسجيل الدخول في LINE
        driver.get("https://line.me/ti/p/your-group-link")

        # الانتظار حتى يتم تحميل حقول البريد الإلكتروني وكلمة المرور
        wait = WebDriverWait(driver, 20)  # انتظار لمدة 20 ثانية كحد أقصى
        email_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
        password_input = driver.find_element(By.NAME, "password")

        # إدخال البريد الإلكتروني وكلمة المرور
        email_input.send_keys(EMAIL)
        password_input.send_keys(PASSWORD)

        # النقر على زر تسجيل الدخول
        login_button = driver.find_element(By.CLASS_NAME, "login-button")
        login_button.click()

        # الانتظار حتى يتم تحميل قائمة المستخدمين المتصلين
        online_users = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "online-user-class")))
        online_users_list = [user.text for user in online_users]

    except Exception as e:
        print(f"حدث خطأ: {e}")
        online_users_list = ["لا يمكن جلب قائمة المستخدمين المتصلين بسبب خطأ."]

    finally:
        # إغلاق المتصفح
        driver.quit()

    return online_users_list

# إرسال رسالة عبر LINE Messaging API
def send_message(user_id, message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "to": user_id,
        "messages": [
            {
                "type": "text",
                "text": message
            }
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    print(response.status_code)

# استقبال الرسائل من LINE
@app.route('/callback', methods=['POST'])
def callback():
    # الحصول على البيانات من الطلب
    body = request.json
    events = body.get("events", [])

    for event in events:
        # التحقق من أن الحدث هو رسالة نصية
        if event["type"] == "message" and event["message"]["type"] == "text":
            user_id = event["source"]["userId"]
            message_text = event["message"]["text"]

            # التحقق من أن المرسل هو المالك وأن الرسالة هي ".r"
            if user_id == OWNER_USER_ID and message_text.strip() == ".r":
                # جلب قائمة المستخدمين المتصلين
                online_users_list = get_online_users()

                # إرسال القائمة إلى المالك
                send_message(user_id, "المستخدمون المتصلون:\n" + "\n".join(online_users_list))

    return jsonify({"status": "success"}), 200

# تشغيل التطبيق (اختياري، فقط للاستخدام المحلي)
if __name__ == '__main__':
    app.run()