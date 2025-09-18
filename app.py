# -*- coding: utf-8 -*-
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import random

app = Flask(__name__)

# ضع توكناتك كما هي في متغيرات البيئة
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ====== قائمة المناصب (أكثر من 100) ======
JOBS = [
    "👑 ملك المملكة","🕌 سلطان الصحراء","⚔️ قائد الحرس","🛡️ حارس القصر",
    "🎺 منشد البلاط","🥘 طباخ القصر","🐪 سائق الإبل","🧹 منظف الإسطبل",
    "🤡 مهرّج البلاط","🎤 مغنّي الساحة","📜 كاتب الأسرار","💰 أمين الخزانة",
    "🏹 رامٍ محترف","🐉 مروّض التنانين","⚒️ حدّاد القلعة","🥶 منظف الثلج",
    "🚪 حارس البوابة","📯 ناقوس الإنذار","🩺 طبيب القصر","🧙 ساحر المملكة",
    "🕵️ جاسوس الملك","🧛 مصاص دماء سري","🏴‍☠️ قرصان متمرّد","🍷 ساقي النبيذ",
    "🛶 ملاح البحيرة","🏇 فارس الصيد","🎭 ممثل الحكايات","🦹 شرير القصة",
    "🧞 جني المصباح","🐀 صائد الجرذان","🥳 منظم الاحتفالات","🪓 قاطع الأشجار",
    "🎣 صياد السمك","🦅 صقار الصقور","🍯 صانع العسل","🧵 خياط القصر",
    "🧼 صانع الصابون","💡 مخترع غريب","🪆 صانع الدمى","🔮 قارئ الطالع",
    "🪖 جندي الحدود","🚨 ناقوس الخطر","🐎 راعي الخيول","🧩 محلل الألغاز",
    "⚖️ قاضي المحكمة","👩‍🍳 طباخ الملكة","🚒 مطفئ الحرائق","🧯 مسؤول الأمن",
    "🎯 لاعب النبال","🎮 لاعب محترف","🎹 عازف القيثارة","🥁 عازف الطبول",
    "🎷 عازف الساكسفون","💃 راقص البلاط","🕺 راقص القصر","🍀 زارع الحظ",
    "🪔 حافظ النور","🌋 مراقب البراكين","❄️ ساحر الثلج","🔥 ساحر النار",
    "💨 ساحر الرياح","🌊 ساحر الماء","⚡ ساحر البرق","🌌 عالم النجوم",
    "🪙 صانع العملات","🕰️ حارس الزمن","🧙‍♀️ عرّاف القصر","📦 مدير المخازن",
    "🚲 ساعي البريد","🏰 مهندس القلعة","🗝️ حارس الأسرار","💎 حارس المجوهرات",
    "🥷 نينجا الظلال","🪤 صائد الوحوش","🧃 موزع العصير","🍗 مشوي الدواجن",
    "🍞 خباز القصر","🥨 صانع المعجنات","🍬 صانع الحلوى","🍵 صانع الشاي",
    "🥛 موزع الحليب","🥩 قصاب القصر","🍹 خبير العصائر","🎨 رسام اللوحات",
    "🖌️ مزخرف الجدران","🧩 صانع الألغاز","📖 راوي القصص","📚 أمين المكتبة",
    "🕊️ مربي الحمام","🐝 مربي النحل","🐴 مروض الخيول","🐘 مروض الفيلة",
    "🐒 مروض القردة","🐉 حارس التنانين","🪆 جامع الدمى","🎳 بطل البولينج",
    "🏆 حامل الجوائز","🚀 حارس الفضاء","🌠 ملتقط النجوم","💤 حارس الأحلام"
]

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
    text = event.message.text.strip()

    # أمر من الأدمن لتشغيل اللعبة
    if text.lower() == ".g":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="🎮 تم تفعيل لعبة المناصب! اكتب: منصب")
        )

    # أي عضو يكتب: منصب
    elif text == "منصب":
        try:
            profile = line_bot_api.get_profile(event.source.user_id)
            name = profile.display_name
        except:
            name = "العضو"
        job = random.choice(JOBS)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"🎲 {name} منصبه العشوائي: {job}")
        )

if __name__ == "__main__":
    app.run(port=5000)
        
