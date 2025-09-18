import os, random, logging
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FlexSendMessage

# --- إعداد ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

app = Flask(__name__)

game_active = False
assigned = {}

# 100 منصب جاد + مضحك
JOBS = [
    "👑 سلطان العصور","🚜 فلاح المملكة","🐒 مروض القرود","🧙 ساحر الليل","🕵️ محقق سري",
    "🛡️ حارس القلعة","🎭 ممثل القصر","🍯 صانع العسل","🐔 مربي الدجاج","🏹 صياد الغزلان",
    "🌋 مراقب البراكين","🏰 مهندس القلاع","⚔️ قائد الجيوش","🔮 قارئ النجوم","🐪 دليل القوافل",
    "🎨 رسام الأساطير","📚 حكيم الزمان","🥷 نينجا الظلال","💡 مخترع العجائب","🕯️ حافظ الأسرار",
    "🥁 ضارب الطبول","🍇 مزارع الكروم","🐕 مروض الذئاب","🏆 بطل الحلبة","🍵 صانع الشاي",
    "🎨 خطاط الملك","🌹 مزارع الورود","🌊 غواص الأعماق","🦅 صائد النسور","🛠️ حداد المملكة",
    "🎤 منشد القوافل","💼 مستشار الملك","🐼 راعي الباندا","🏇 فارس الميدان","🔑 حارس الخزائن",
    "🥶 حارس الجليد","🔥 جامع الحطب","🍿 بائع الفشار","🎣 صياد الأسماك","🕊️ مربي الحمام",
    "🌴 حارس الواحة","🎯 رامٍ بارع","🧗 متسلق الجبال","⚓ ربان البحار","🥋 مدرب القتال",
    "🎬 مخرج الأساطير","💃 راقص السيف","🧛 صائد مصاصي الدماء","🧚 جامع الأساطير",
    "🦊 حارس الغابة","🥨 خباز القرية","🍀 حارس الحظ","🥸 محقق الألغاز","🪂 قافز السماء",
    "🎩 ساحر القبعة","🐳 راعي الحيتان","🦁 مروض الأسود","🥕 مزارع الجزر","🐝 حارس النحل",
    "🏜️ حارس الصحراء","🕰️ مسافر الزمن","🎢 مهندس الألعاب","🦉 مراقب البوم","🍉 بائع البطيخ",
    "🎿 متزلج الثلوج","🧴 صانع العطور","🎷 عازف الساكس","🐢 مربي السلاحف","🍂 جامع الأعشاب",
    "🏖️ منقذ الشاطئ","⚙️ مخترع الآلات","🎇 مطلق الألعاب النارية","🌻 بستاني الملك",
    "🍎 جالب التفاح","🧊 صانع الجليد","🪄 خبير الحيل","🦜 مربي الببغاوات","🎺 عازف البوق",
    "🪕 عازف البانجو","🚴 سائق الدراجة","🛶 قبطان النهر","🌌 مستكشف المجرات","📜 مؤرخ البلاط",
    "🧵 خياط القصر","🎼 عازف الناي","🚂 سائق القطار","🧭 مكتشف الأراضي","🌌 راصد النجوم",
    "⚡ مهندس الطاقة","🥗 طاهٍ نباتي","🚴 راكب الرياح","💎 تاجر الجواهر","🚀 رائد الفضاء",
    "🥳 منظم الاحتفالات","🪖 جندي الحدود","🎹 عازف القيثارة","💤 حارس الأحلام","🍗 مشوي الدواجن"
]

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

    # تشغيل وإيقاف (أوامر الأدمن كما تحب)
    if text.lower() == ".g":
        game_active = True
        assigned.clear()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🎮 تم تشغيل لعبة المناصب!"))
        return
    if text.lower() == ".go":
        game_active = False
        assigned.clear()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⛔ تم إيقاف اللعبة."))
        return

    if text == "منصب":
        if not game_active:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ اللعبة غير مفعّلة."))
            return

        if user_id in assigned:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="😂 عطيتك منصب سابقًا!"))
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

        # Flex Bubble جميل مع صورة دائرية ولمعة
        flex_content = {
          "type": "bubble",
          "size": "mega",
          "body": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#000000",
            "contents": [
              {
                "type": "box",
                "layout": "vertical",
                "contents": [
                  {
                    "type": "image",
                    "url": pic,
                    "aspectMode": "cover",
                    "size": "240px",
                    "aspectRatio": "1:1",
                    "borderWidth": "4px",
                    "borderColor": "#FFD700",
                    "cornerRadius": "150px"   # صورة دائرية
                  }
                ],
                "justifyContent": "center",
                "alignItems": "center",
                "backgroundColor": "#000000"
              },
              {
                "type": "text",
                "text": name,
                "weight": "bold",
                "size": "xl",
                "align": "center",
                "color": "#FFD700",
                "margin": "md"
              },
              {
                "type": "text",
                "text": job,
                "wrap": True,
                "align": "center",
                "color": "#FF69B4",
                "weight": "bold",
                "margin": "sm"
              }
            ]
          },
          "styles": {
            "body": {
              "backgroundColor": "#000000",
              "separator": True,
              "separatorColor": "#FFD700"
            }
          }
        }

        message = FlexSendMessage(alt_text="🎲 منصبك!", contents=flex_content)
        line_bot_api.reply_message(event.reply_token, message)

if __name__ == "__main__":
    app.run(port=8000)
