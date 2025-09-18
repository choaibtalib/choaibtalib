import os
import random
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, FlexSendMessage,
    TextSendMessage
)

app = Flask(__name__)

# ===== متغيرات البيئة =====
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET       = os.getenv("CHANNEL_SECRET")
ADMIN_ID             = os.getenv("ADMIN_ID")
ADMIN_USER_ID        = os.getenv("ADMIN_USER_ID")
USER_ID              = os.getenv("USER_ID")

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    raise ValueError("⚠️ تأكد من ضبط CHANNEL_ACCESS_TOKEN و CHANNEL_SECRET في متغيرات البيئة.")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler      = WebhookHandler(CHANNEL_SECRET)

# ===== حالة اللعبة =====
game_active = False

# ===== قائمة المناصب (أكثر من 140) =====
ROLES = [
    "👑 سلطان العصور", "🌾 فلاح المملكة", "🍳 الطباخ الملكي", "🐔 راعي الدجاج",
    "🦍 مروض القرود", "🎭 ممثل الظلال", "🚀 رائد فضاء القصر", "🕵️‍♂️ محقق الأسرار",
    "🛡️ حارس البوابة", "🎨 رسام الأساطير", "⚡ ساحر العواصف", "🐉 مروض التنين",
    "🧩 مخطط المكائد", "🥷 نينجا الليل", "🍯 صانع العسل", "🕊️ رسول السلام",
    "🔥 مشعل الحروب", "🎧 منسق موسيقى القصر", "🐪 دليل الصحراء",
    "🏹 رامٍ أسطوري", "🚜 مزارع الأحلام", "💎 جامع الجواهر", "🧙‍♀️ عراف النجوم",
    "📜 كاتب التاريخ", "🎯 قناص القلوب", "🎩 ساحر القبعة", "🐢 حامي السلاحف",
    "🦈 صياد القروش", "🏝️ حاكم الجزر", "🪂 قافز المغامرات", "🛶 ملاح البحار",
    "🍵 صانع الشاي", "🍿 بائع الفشار", "🍩 ملك الدونات", "🥩 مشويّ اللحوم",
    "⚙️ مهندس العجائب", "📡 مراقب الأقمار", "🪐 زائر المجرات",
    # … يمكنك إضافة المزيد بسهولة
]

# ===== مرسل بطاقة المنصب =====
def send_role_card(reply_token, user_name, user_pic, role):
    flex_message = {
      "type": "bubble",
      "size": "mega",
      "hero": {
        "type": "image",
        "url": "https://i.imgur.com/H7c5hit.jpg",  # خلفية البطاقة
        "size": "full",
        "aspectRatio": "20:13",
        "aspectMode": "cover"
      },
      "body": {
        "type": "box",
        "layout": "vertical",
        "contents": [
          {
            "type": "image",
            "url": user_pic,
            "size": "xl",
            "aspectMode": "cover",
            "aspectRatio": "1:1",
            "gravity": "center",
            "style": "circle"
          },
          {
            "type": "text",
            "text": user_name,
            "weight": "bold",
            "size": "xl",
            "align": "center",
            "color": "#FFFFFF",
            "margin": "md"
          },
          {
            "type": "text",
            "text": role,
            "weight": "bold",
            "size": "xxl",
            "align": "center",
            "color": "#FFD700",
            "margin": "lg"
          }
        ],
        "backgroundColor": "#00000099",
        "paddingAll": "20px"
      },
      "styles": {
        "body": {
          "backgroundColor": "#000000"
        }
      }
    }
    line_bot_api.reply_message(reply_token, FlexSendMessage(alt_text="🎲 منصبك العشوائي", contents=flex_message))

# ===== Webhook =====
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

# ===== منطق الرسائل =====
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global game_active
    text = event.message.text.strip()
    uid  = event.source.user_id

    # تشغيل اللعبة
    if text.lower() == ".g" and uid == ADMIN_USER_ID:
        game_active = True
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text="🎮 تم تشغيل لعبة المناصب!"))
        return

    # إيقاف اللعبة
    if text.lower() == ".stop" and uid == ADMIN_USER_ID:
        game_active = False
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text="⏹️ تم إيقاف لعبة المناصب."))
        return

    # أمر الحذف (مثال)
    if text.lower() == ".u" and uid == ADMIN_USER_ID:
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text="🗑️ تم تنفيذ أمر الحذف (تخصيص حسب احتياجك)"))
        return

    # كلمة منصب لأي عضو
    if game_active and "منصب" in text:
        profile = line_bot_api.get_profile(uid)
        user_name = profile.display_name
        user_pic  = profile.picture_url or "https://i.imgur.com/H7c5hit.jpg"
        role = random.choice(ROLES)
        send_role_card(event.reply_token, user_name, user_pic, role)
        return

    # رد افتراضي
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="💡 اكتب .g لتشغيل اللعبة (أمر للأدمن) أو اكتب 'منصب' للعب إذا كانت مفعلة.")
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    
