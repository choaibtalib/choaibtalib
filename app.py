from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests

# معلومات تسجيل الدخول إلى LINE
EMAIL = "choaib03dz@gmail.com"
PASSWORD = "123chl!321"

# معلومات LINE Messaging API
CHANNEL_ACCESS_TOKEN = "OGuV9/KT+JED14YLuEYZuyhi+BCCZfTSpRUD+OQzp3HXMQpvob/UteHHf10JOeNMz5sRMtXPH0/bNDdVtXfjno1tZGqIsJ4whziPkw4CO5VECZT56SaaFsRrvHI5wBPFNs6iFJIcfHSptnKZNcsnmgdB04t89/1O/w1cDnyilFU="
USER_ID = "Ua673da6876bab906ce8734e94e59502a"

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

# إرسال القائمة إلى المستخدم عبر LINE Messaging API
def send_online_users_list(user_id, online_users_list):
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
                "text": "المستخدمون المتصلون:\n" + "\n".join(online_users_list)
            }
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    print(response.status_code)

# إرسال قائمة المستخدمين المتصلين
send_online_users_list(USER_ID, online_users_list)