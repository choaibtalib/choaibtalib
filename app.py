from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import requests

# معلومات تسجيل الدخول إلى LINE
EMAIL = "choaib03dz@gmail.com"
PASSWORD = "123chl!321"

# معلومات LINE Messaging API
CHANNEL_ACCESS_TOKEN = "OGuV9/KT+JED14YLuEYZuyhi+BCCZfTSpRUD+OQzp3HXMQpvob/UteHHf10JOeNMz5sRMtXPH0/bNDdVtXfjno1tZGqIsJ4whziPkw4CO5VECZT56SaaFsRrvHI5wBPFNs6iFJIcfHSptnKZNcsnmgdB04t89/1O/w1cDnyilFU="
USER_ID = "Ua673da6876bab906ce8734e94e59502a"

# تهيئة المتصفح
driver = webdriver.Chrome()

# الانتقال إلى صفحة تسجيل الدخول في LINE
driver.get("https://line.me/ti/p/your-group-link")

# الانتظار حتى يتم تحميل الصفحة
time.sleep(10)

# تسجيل الدخول
email_input = driver.find_element(By.NAME, "email")
email_input.send_keys(EMAIL)

password_input = driver.find_element(By.NAME, "password")
password_input.send_keys(PASSWORD)

login_button = driver.find_element(By.CLASS_NAME, "login-button")
login_button.click()

# الانتظار حتى يتم تحميل المجموعة
time.sleep(10)

# جلب قائمة الأعضاء المتصلين (هذا مثال فقط، قد تحتاج إلى تعديله)
online_users = driver.find_elements(By.CLASS_NAME, "online-user-class")  # قم بتعديل الكلاس حسب واجهة LINE
online_users_list = [user.text for user in online_users]

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