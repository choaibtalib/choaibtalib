from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage, PostbackEvent, TemplateSendMessage, ButtonsTemplate, PostbackAction
from linebot.exceptions import LineBotApiError
import os

app = Flask(__name__)

# استخدم نفس التوكن والايدي والبيانات السابقة
line_bot_api = LineBotApi(os.environ['LINE_CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['LINE_CHANNEL_SECRET'])
GROUP_ID = os.environ['GROUP_ID']  # الأيدي القديمة

# حالة الاستفتاء
war_poll_active = False
participants = []
castle_surrender = []

# إرسال بطاقة الاستفتاء
def send_war_poll():
    global war_poll_active
    if not war_poll_active:
        return
    buttons = TemplateSendMessage(
        alt_text="استفتاء الحرب",
        template=ButtonsTemplate(
            title="⚔️ استفتاء الحرب",
            text="اختر خيارك:",
            actions=[
                PostbackAction(label="مشارك بالحرب ⚔️", data="join"),
                PostbackAction(label="أسلم قلعتي 🏰", data="surrender")
            ]
        )
    )
    line_bot_api.push_message(GROUP_ID, buttons)

# تحديث القوائم
def update_war_lists(user_id, choice):
    global participants, castle_surrender
    if choice == "join":
        if user_id in castle_surrender:
            castle_surrender.remove(user_id)
        if user_id not in participants:
            participants.append(user_id)
    elif choice == "surrender":
        if user_id in participants:
            participants.remove(user_id)
        if user_id not in castle_surrender:
            castle_surrender.append(user_id)
    send_war_results()

# إرسال النتائج مباشرة
def send_war_results():
    text = "⚔️ استفتاء الحرب (مباشر)\n\n"
    text += "🗡️ المشاركون ({}):\n".format(len(participants))
    for i, user in enumerate(participants, 1):
        text += f"{i}- {user}\n"
    text += "\n🏰 المسلمون ({}):\n".format(len(castle_surrender))
    for i, user in enumerate(castle_surrender, 1):
        text += f"{i}- {user}\n"
    # المتخاذلون
    text += "\n🐍 المتخاذلون الذين لم يكتبوا اسماءهم:\n"
    # هنا ضع جميع الأعضاء بالقروب الذين لم يشاركوا
    all_members = []  # ضع جميع الأعضاء الفعليين
    non_participants = [m for m in all_members if m not in participants and m not in castle_surrender]
    for i, user in enumerate(non_participants, 1):
        text += f"{i}- {user}\n"
    line_bot_api.push_message(GROUP_ID, TextSendMessage(text=text))
    send_war_poll()  # إعادة إرسال البطاقة

# أوامر الرسائل
@handler.add(MessageEvent, message=TextMessage)
def on_message(event):
    global war_poll_active, participants, castle_surrender
    msg = event.message.text.lower()
    user_id = event.source.user_id

    if event.source.user_id != os.environ['ADMIN_ID']:  # للأدمن فقط
        return

    if msg == ".war":
        war_poll_active = True
        participants = []
        castle_surrender = []
        send_war_poll()
    elif msg == ".war s":
        war_poll_active = False
        participants = []
        castle_surrender = []
        line_bot_api.push_message(GROUP_ID, TextSendMessage(text="⚔️ تم إيقاف الاستفتاء وإعادة التصفير"))
    elif msg == ".war r":
        send_war_results()

# التعامل مع الضغط على الخيارات
@handler.add(PostbackEvent)
def on_postback(event):
    user_id = event.source.user_id
    choice = event.postback.data
    update_war_lists(user_id, choice)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except LineBotApiError as e:
        print(e)
    return 'OK'

if __name__ == "__main__":
    app.run()
    
