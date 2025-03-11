from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    MemberJoinedEvent, MemberLeftEvent
)
import os
import time
from datetime import datetime

app = Flask(__name__)

# قراءة المتغيرات البيئية
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
OWNER_USER_ID = "Ua673da6876bab906ce8734e94e59502a"

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

lurking = False
seen_users = []

def get_user_name(group_id, user_id):
    try:
        profile = line_bot_api.get_group_member_profile(group_id, user_id)
        return profile.display_name
    except:
        return f"User-{user_id}"  # اسم افتراضي في حال فشل جلب الاسم

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except Exception as e:
        print(f'Error: {e}')
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global lurking, seen_users
    txt = event.message.text.strip()
    user_id = event.source.user_id
    group_id = event.source.group_id if event.source.type == "group" else None
    
    if txt.startswith(".") and user_id == OWNER_USER_ID:
        if txt == ".lurk on":
            lurking = True
            seen_users = []
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Lurking mode activated!"))
        elif txt == ".lurk off":
            lurking = False
            seen_users = []
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Lurking mode deactivated!"))
        elif txt == ".r":
            if not seen_users:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="No users have read the message yet."))
            else:
                readers_message = "👥 Users who read the message:\n" + "\n".join([f"- {u['name']}" for u in seen_users])
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=readers_message))
    
    if lurking and group_id:
        user_name = get_user_name(group_id, user_id)
        if not any(user['user_id'] == user_id for user in seen_users):
            seen_users.append({'name': user_name, 'user_id': user_id, 'timestamp': time.time()})

if __name__ == "__main__":
    app.run(port=8000)
