import os, json, logging, random
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage,
    TextSendMessage, FlexSendMessage
)

# --- إعدادات التسجيل ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- متغيرات البيئة ---
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")
ADMIN_USER_ID = os.getenv("USER_ID")

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    raise Exception("يرجى ضبط متغيرات البيئة CHANNEL_ACCESS_TOKEN و CHANNEL_SECRET")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# --- بيانات اللعبة ---
game_active = False
assigned = {}

# 100 منصب عشوائي (خليط جاد + مضحك + منطقية)
JOBS = [
    "👑 سلطان العصور", "🚜 فلاح المملكة", "🌾 مزارع القمح", "🍳 طباخ القصر",
    "🐒 مروض القرود", "🧞‍♂️ جالب الحظ", "🎭 ممثل القصر", "🕵️ محقق سري",
    "🛡️ حارس القلعة", "🎨 رسام الأساطير", "🧩 صانع الألغاز", "🧙‍♂️ ساحر الليل",
    "🌋 مراقب البراكين", "🏰 مهندس القلاع", "⚔️ قائد الجيوش", "🚀 رائد الفضاء",
    "🔮 قارئ النجوم", "🐔 مربي الدجاج", "🏹 صياد الغزلان", "🍯 صانع العسل",
    "💎 تاجر الجواهر", "🧵 خياط القصر", "🎼 عازف الناي", "🚂 سائق القطار",
    "🧭 مكتشف الأراضي", "🐪 دليل القوافل", "🛶 قبطان النهر", "🌌 مستكشف المجرات",
    "📚 حكيم الزمان", "🥷 نينجا الظلال", "⚡ مهندس الطاقة", "💡 مخترع العجائب",
    "🕯️ حافظ الأسرار", "🥁 ضارب الطبول", "🍇 مزارع الكروم", "🏄 راكب الأمواج",
    "🐕 مروض الذئاب", "🦂 صائد العقارب", "🏆 بطل الحلبة", "🍵 صانع الشاي",
    "🎨 خطاط الملك", "🌹 مزارع الورود", "🌙 حارس الليل", "🌊 غواص الأعماق",
    "🦅 صائد النسور", "🛠️ حداد المملكة", "🎤 منشد القوافل", "🚨 منقذ الأرواح",
    "💼 مستشار الملك", "🥗 طاهٍ نباتي", "🐼 راعي الباندا", "🚴 راكب الرياح",
    "🏇 فارس الميدان", "📜 مؤرخ البلاط", "🔑 حارس الخزائن", "🥶 حارس الجليد",
    "🔥 جامع الحطب", "🍿 بائع الفشار", "🎣 صياد الأسماك", "🕊️ مربي الحمام",
    "🌴 حارس الواحة", "🎯 رامٍ بارع", "🧗 متسلق الجبال", "⚓ ربان البحار",
    "🥋 مدرب القتال", "🎬 مخرج الأساطير", "💃 راقص السيف", "🧛 صائد مصاصي الدماء",
    "🧚‍♂️ جامع الأساطير", "🦊 حارس الغابة", "🥨 خباز القرية", "🍀 حارس الحظ",
    "🥸 محقق الألغاز", "🪂 قافز السماء", "🎩 ساحر القبعة", "🐳 راعي الحيتان",
    "🛶 مجدف النهر", "🦁 مروض الأسود", "🥕 مزارع الجزر", "🐝 حارس النحل",
    "🏜️ حارس الصحراء", "🕰️ مسافر الزمن", "🎢 مهندس الألعاب", "🛻 سائق العربة",
    "🦉 مراقب البوم", "🥁 قارع الطبول", "🍉 بائع البطيخ", "🎿 متزلج الثلوج",
    "🧴 صانع العطور", "🎷 عازف الساكس", "🐢 مربي السلاحف", "🍂 جامع الأعشاب",
    "🏖️ منقذ الشاطئ", "⚙️ مخترع الآلات", "🎇 مطلق الألعاب النارية",
    "🌻 بستاني الملك", "🍎 جالب التفاح", "🧊 صانع الجليد", "🪄 خبير الحيل",
    "🦜 مربي الببغاوات", "🎺 عازف البوق", "🪕 عازف البانجو", "🚴‍♂️ سائق الدراجة"
]

# --- تطبيق Flask ---
app = Flask(__name__)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global game_active, assigned
    text = event.message.text.strip()
    user_id = event.source.user_id

    # أوامر الأدمن فقط
    if text.lower() == ".g":
        if user_id == ADMIN_USER_ID:
            game_active = True
            assigned.clear()
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="✅ تم تشغيل لعبة المناصب! اكتبوا: منصب")
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="⚠️ هذا الأمر مخصص للأدمن فقط.")
            )
        return

    if text.lower() == ".go":
        if user_id == ADMIN_USER_ID:
            game_active = False
            assigned.clear()
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="⛔ تم إيقاف اللعبة.")
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="⚠️ هذا الأمر مخصص للأدمن فقط.")
            )
        return

    # طلب منصب
    if text == "منصب":
        if not game_active:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="🎮 اللعبة غير مفعلة حالياً.")
            )
            return

        if user_id in assigned:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="😄 عطيتك منصب من قبل!")
            )
            return

        try:
            profile = line_bot_api.get_profile(user_id)
            name = profile.display_name
            pic = profile.picture_url or "https://via.placeholder.com/300"
        except:
            name = "مشارك"
            pic = "https://via.placeholder.com/300"

        job = random.choice(JOBS)
        assigned[user_id] = {"name": name, "job": job, "pic": pic}

        flex_content = {
          "type": "bubble",
          "size": "mega",
          "hero": {
            "type": "image",
            "url": pic,
            "size": "full",
            "aspectRatio": "1:1",
            "aspectMode": "cover",
            "backgroundColor": "#FFD700"
          },
          "body": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#fff0f5",
            "contents": [
              {
                "type": "text",
                "text": name,
                "weight": "bold",
                "size": "xl",
                "align": "center",
                "color": "#FF1493"
              },
              {
                "type": "text",
                "text": f"منصبه العشوائي: {job}",
                "wrap": True,
                "align": "center",
                "color": "#8A2BE2",
                "margin": "md"
              }
            ]
          },
          "styles": {
            "body": { "backgroundColor": "#ffe4e1" },
            "hero": { "backgroundColor": "#FFD700" }
          }
        }

        message = FlexSendMessage(
            alt_text="🎲 منصبك العشوائي!", contents=flex_content
        )
        line_bot_api.reply_message(event.reply_token, message)

if __name__ == "__main__":
    app.run(port=8000)
        
