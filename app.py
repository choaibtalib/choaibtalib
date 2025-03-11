from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    StickerSendMessage, ImageSendMessage,
    MemberJoinedEvent, MemberLeftEvent
)
import os
import time
from datetime import datetime

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')

if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    raise ValueError("Please set LINE_CHANNEL_ACCESS_TOKEN and LINE_CHANNEL_SECRET in your environment variables.")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

OWNER_USER_ID = "Ua673da6876bab906ce8734e94e59502a"
lurking = False
seen_users = []
break_rules = False

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
    global lurking, seen_users, break_rules

    txt = event.message.text.strip()
    user_id = event.source.user_id
    group_id = event.source.group_id if event.source.type == "group" else None

    if txt.startswith(".") and user_id == OWNER_USER_ID:
        if txt == ".lurk on":
            lurking = True
            seen_users.clear()
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Lurking mode activated."))
        elif txt == ".lurk off":
            lurking = False
            seen_users.clear()
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Lurking mode deactivated. Data cleared."))
        elif txt == ".wr":
            if not seen_users:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="No users have read the message yet."))
            else:
                reader_list = []
                for user in seen_users:
                    timestamp_str = datetime.fromtimestamp(user['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                    reader_list.append(f"👤 {user['name']} ({user['user_id']})\n📅 Read at: {timestamp_str}")
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="👥 Readers:\n\n" + "\n\n".join(reader_list)))
        elif txt == ".kick" and group_id:
            if len(seen_users) > 0:
                for user in seen_users:
                    try:
                        line_bot_api.kick_out_from_group(group_id, user['user_id'])
                        line_bot_api.push_message(group_id, TextSendMessage(text=f"🚨 {user['name']} has been removed."))
                    except Exception as e:
                        print(f"Error kicking user {user['user_id']}: {e}")
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="No users to kick."))

    if lurking and group_id:
        try:
            profile = line_bot_api.get_group_member_profile(group_id, user_id)
            user_name = profile.display_name
        except Exception as e:
            user_name = f"User-{user_id}"
            print(f"Error fetching profile: {e}")
        
        if not any(user['user_id'] == user_id for user in seen_users):
            seen_users.append({
                'name': user_name,
                'user_id': user_id,
                'timestamp': time.time()
            })

@app.route("/")
def index():
    return "LINE bot is running."

if __name__ == "__main__":
    app.run(port=8000)