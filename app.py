from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    ImageSendMessage, StickerSendMessage,
    MemberJoinedEvent, MemberLeftEvent
)
import os
import time
from datetime import datetime

app = Flask(__name__)

# قراءة المتغيرات البيئية
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
BOT_IDS = ["BOT_FAKE_1", "BOT_FAKE_2", "BOT_FAKE_3"]

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
    
    if txt.startswith(".") and event.source.user_id == OWNER_USER_ID:
        commands = {
            ".lurk on": lambda: set_lurking(True, event.reply_token),
            ".lurk off": lambda: set_lurking(False, event.reply_token),
            ".wr": lambda: show_readers(event.reply_token),
            ".break rules": lambda: toggle_break_rules(event.reply_token),
            ".help": lambda: send_help(event.reply_token),
            ".sticker": lambda: send_sticker(event.reply_token),
            ".image": lambda: send_image(event.reply_token)
        }
        commands.get(txt, lambda: None)()

    if lurking and event.source.type == "group":
        track_readers(event)

@handler.add(MemberLeftEvent)
def handle_member_left(event):
    left_user_id = event.left.members[0].user_id
    if left_user_id in BOT_IDS:
        reinvite_bot(event.source.group_id, left_user_id)

@handler.add(MemberJoinedEvent)
def handle_member_joined(event):
    joined_user_id = event.joined.members[0].user_id
    if joined_user_id != OWNER_USER_ID:
        notify_owner(f"⚠️ New member joined the group: {joined_user_id}")

def set_lurking(state, reply_token):
    global lurking, seen_users
    lurking = state
    seen_users = [] if state else []
    line_bot_api.reply_message(reply_token, TextSendMessage(text=f"Lurking is now {'ON' if state else 'OFF'}"))

def show_readers(reply_token):
    if not seen_users:
        line_bot_api.reply_message(reply_token, TextSendMessage(text="No users have read the message yet."))
    else:
        readers_message = "\n".join(
            [f"👤 {u['name']} (ID: {u['user_id']})\n   📱 Read at: {datetime.fromtimestamp(u['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}" for u in seen_users]
        )
        line_bot_api.reply_message(reply_token, TextSendMessage(text=f"👥 Readers:\n\n{readers_message}"))

def toggle_break_rules(reply_token):
    global break_rules
    break_rules = not break_rules
    line_bot_api.reply_message(reply_token, TextSendMessage(text="⚠️ Rules are now broken!" if break_rules else "Rules restored."))

def send_help(reply_token):
    help_message = """Available commands:
- .lurk on / off: Toggle lurking mode.
- .wr: Show readers.
- .break rules: Toggle break rules mode.
- .sticker: Send a random sticker.
- .image: Send an image."""
    line_bot_api.reply_message(reply_token, TextSendMessage(text=help_message))

def send_sticker(reply_token):
    sticker_message = StickerSendMessage(package_id='11537', sticker_id='52002734')
    line_bot_api.reply_message(reply_token, sticker_message)

def send_image(reply_token):
    image_message = ImageSendMessage(
        original_content_url='https://example.com/image.jpg',
        preview_image_url='https://example.com/image_preview.jpg'
    )
    line_bot_api.reply_message(reply_token, image_message)

def track_readers(event):
    global seen_users
    user_id = event.source.user_id
    group_id = event.source.group_id
    try:
        profile = line_bot_api.get_group_member_profile(group_id, user_id)
        user_name = profile.display_name
    except:
        user_name = f"User-{user_id}"
    if not any(u['user_id'] == user_id for u in seen_users):
        seen_users.append({'name': user_name, 'user_id': user_id, 'timestamp': time.time()})

def reinvite_bot(group_id, bot_id):
    try:
        line_bot_api.invite_into_group(group_id, [bot_id])
        line_bot_api.push_message(group_id, TextSendMessage(text=f"Bot {bot_id} has been re-invited."))
    except Exception as e:
        print(f"Error re-inviting bot {bot_id}: {e}")

def notify_owner(message):
    line_bot_api.push_message(OWNER_USER_ID, TextSendMessage(text=message))

@app.route("/")
def index():
    return "Hello, this is a LINE bot."

if __name__ == "__main__":
    app.run(port=8000)
