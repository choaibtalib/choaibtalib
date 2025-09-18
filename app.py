# -*- coding: utf-8 -*-
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, FlexSendMessage, TextSendMessage
)
import os, random, re

app = Flask(__name__)

# ===== متغيرات البيئة =====
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")
ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ===== قائمة المناصب =====
JOBS = [
    "👑 سلطان العصور", "🌾 فلاح المملكة", "🍳 طباخ القصر", "🐒 مروض القرود",
    "🕊️ مربي الحمام", "🪄 ساحر الرياح", "⚔️ قائد الحرس", "🧩 محلل الألغاز",
    "🚀 حارس الفضاء", "🎨 رسام اللوحات", "💎 حارس المجوهرات", "🥁 عازف الطبول",
    "🌋 مراقب البراكين", "🐴 فارس الساحة", "🥳 منظم الاحتفالات", "🧙 ساحر الظلال",
    "🍞 خباز القصر", "🐘 مروض الفيلة", "🕰️ حارس الزمن", "📖 راوي الأساطير",
    "🥷 نينجا الظلال", "💡 مخترع القلعة", "🎯 بطل النبال", "🧼 صانع الصابون",
    "🎻 عازف الكمان", "🌌 عالم النجوم", "🍯 صانع العسل", "🧵 خياط المملكة",
    "🚒 مطفئ الحرائق", "🎭 ممثل البلاط", "🪆 جامع الدمى", "🐝 مربي النحل",
    "🍹 خبير العصائر", "🎩 سيد الألغاز", "🪖 جندي الحدود", "🐀 صائد الجرذان",
    "🎮 لاعب محترف", "🥩 قصاب القصر", "🧃 موزع العصير", "📦 مدير المخازن",
    "🍵 صانع الشاي", "🎷 عازف الساكسفون", "🕵️ جاسوس الملك", "🧙‍♀️ عراف المملكة",
    "🌠 ملتقط النجوم", "🛡️ حارس القصر", "🥨 صانع المعجنات", "💃 راقص البلاط",
    "🪓 قاطع الأشجار", "🎳 بطل البولينج", "🎤 مغني الساحة", "📜 كاتب الأسرار",
    "🏆 حامل الجوائز", "🍗 مشوي الدواجن", "🧞 جني المصباح", "🎺 منشد البلاط",
    "🥘 طباخ الملكة", "🌊 ساحر الماء", "🔥 ساحر النار", "❄️ ساحر الثلج",
    "⚡ ساحر البرق", "🚨 ناقوس الخطر", "🧩 صانع الألغاز", "🏇 فارس الصيد",
    "🚲 ساعي البريد", "🪔 حافظ النور", "🕺 راقص القصر", "🔮 قارئ الطالع",
    "🪙 صانع العملات", "🐎 راعي الخيول", "🧯 مسؤول الأمن", "⚖️ قاضي المحكمة",
    "🎣 صياد السمك", "🧹 منظف القصر", "📚 أمين المكتبة", "🐉 حارس التنانين",
    "💤 حارس الأحلام", "🥶 منظف الثلج", "🩺 طبيب القصر", "🍀 زارع الحظ",
    "🤡 مهرج البلاط", "💰 أمين الخزانة", "🌾 مزارع المملكة", "🪤 صائد الوحوش",
    "🚪 حارس البوابة", "🗝️ حارس الأسرار", "💡 عالم الاختراعات", "🎨 مزخرف الجدران",
    "📯 ناقوس الإنذار", "🧊 ساحر الجليد", "🐪 سائق الإبل", "🍬 صانع الحلوى",
    "🧙 ساحر المملكة", "🎹 عازف القيثارة", "🛶 ملاح البحيرة", "🧩 مبدع الألغاز",
    "🥛 موزع الحليب", "🍹 محترف العصائر", "📖 قارئ الحكايات", "🎟️ منظم العروض",
    # مناصب إضافية مضحكة جدًا
    "🐔 راعي الدجاج", "🪱 مروض الديدان", "🪰 صياد الذباب", "🧄 ملك الثوم",
    "🍉 مقسم البطيخ", "🥕 مراقب الجزر", "🐸 ناطق الضفادع", "🦆 همس البط",
    "🧻 حارس المناديل", "🥒 مخلل القصر", "🍟 فنان البطاطس", "🍕 عاشق البيتزا",
    "🪣 جامع الأمطار", "🪴 خبير الصبار", "🦄 راعي أحادي القرن", "🐳 مدرب الحيتان",
    "🐙 همس الأخطبوط", "🦍 مروض الغوريلا", "🐌 متسابق الحلزون", "🦖 حارس الديناصورات",
    "🌭 صانع النقانق", "🍩 ملك الدونات", "🧊 بائع الثلج", "🍫 ساحر الشوكولاتة",
    "🫧 صانع الفقاعات", "🎢 مشغل الملاهي", "🎠 مدير الكاروسيل", "🚽 حارس المرحاض",
    "🧦 منسق الجوارب", "🪳 مقاتل الصراصير", "🍿 بائع الفشار", "🥤 مخلط العصائر",
    "🧀 أمير الجبن", "🥨 عاشق البريتزل", "🍜 ملك النودلز", "🍱 ساموراي السوشي"
]

# ===== دالة إنشاء بطاقة =====
def make_job_card(name, profile_pic, job):
    bg_url = "https://i.imgur.com/H7c5hit.jpg"
    return FlexSendMessage(
        alt_text="بطاقة المنصب",
        contents={
            "type": "bubble",
            "size": "giga",
            "hero": {
                "type": "image",
                "url": bg_url,
                "size": "full",
                "aspectRatio": "9:16",
                "aspectMode": "cover"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "image",
                        "url": profile_pic,
                        "size": "xxl",
                        "aspectMode": "cover",
                        "aspectRatio": "1:1",
                        "backgroundColor": "#FFFFFF",
                        "cornerRadius": "150px",
                        "borderColor": "#FFD700",
                        "borderWidth": "6px",
                        "align": "center",
                        "gravity": "center"
                    },
                    {
                        "type": "text",
                        "text": name,
                        "weight": "bold",
                        "size": "xxl",
                        "align": "center",
                        "color": "#FFFFFF",
                        "margin": "lg"
                    },
                    {
                        "type": "text",
                        "text": job,
                        "weight": "bold",
                        "size": "xxl",
                        "align": "center",
                        "color": "#FFD700",
                        "margin": "sm"
                    }
                ],
                "backgroundColor": "#00000099",
                "cornerRadius": "20px",
                "paddingAll": "20px"
            }
        }
    )

# ===== حالة اللعبة =====
game_active = False
assigned = {}  # user_id -> job

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
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

    # تشغيل اللعبة (أدمن فقط)
    if text.lower() == ".g":
        if event.source.user_id != ADMIN_USER_ID:
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="❌ هذا الأمر للمشرف فقط"))
            return
        game_active = True
        assigned = {}
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text="🎮 تم تفعيل لعبة المناصب!"))
        return

    # إيقاف اللعبة (أدمن فقط)
    if text.lower() == ".go":
        if event.source.user_id != ADMIN_USER_ID:
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="❌ هذا الأمر للمشرف فقط"))
            return
        game_active = False
        assigned = {}
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text="⛔ تم إيقاف اللعبة"))
        return

    # حذف رسائل البوت (أدمن فقط)
    if text.lower() == ".u":
        if event.source.user_id != ADMIN_USER_ID:
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="❌ هذا الأمر للمشرف فقط"))
            return
        # ملاحظة: تحتاج آلية حفظ IDs للرسائل إذا أردت حذفها فعليًا
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text="🗑️ (تطبيق حذف الرسائل هنا)"))
        return

    # إعطاء منصب
    if text == "منصب":
        if not game_active:
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="⚠️ اللعبة غير مفعّلة حالياً"))
            return

        user_id = event.source.user_id
        if user_id in assigned:
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="🤣 لديك منصب بالفعل!"))
            return

        try:
            profile = line_bot_api.get_profile(user_id)
            name = profile.display_name
            profile_pic = profile.picture_url or "https://via.placeholder.com/240"
        except:
            name = "عضو مجهول"
            profile_pic = "https://via.placeholder.com/240"

        job = random.choice(JOBS)
        assigned[user_id] = job
        msg = make_job_card(name, profile_pic, job)
        line_bot_api.reply_message(event.reply_token, msg)
        return

    # منشن للأدمن
    if ADMIN_USER_ID and re.search(r"@.+", text):
        # إذا تم ذكر الأدمن في النص
        if event.source.user_id != ADMIN_USER_ID and ADMIN_USER_ID in text:
            try:
                profile = line_bot_api.get_profile(event.source.user_id)
                name = profile.display_name
                pic = profile.picture_url or "https://via.placeholder.com/240"
            except:
                name = "عضو مجهول"
                pic = "https://via.placeholder.com/240"
            greet = make_job_card(name, pic, f"مرحباً يا {name}! 👋 الأدمن مشغول حالياً.")
            line_bot_api.reply_message(event.reply_token, greet)
            return

if __name__ == "__main__":
    app.run(port=5000)
    
