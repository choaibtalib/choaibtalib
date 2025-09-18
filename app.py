# -*- coding: utf-8 -*-
import os, random
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, FlexSendMessage, TextSendMessage

app = Flask(__name__)

# ===== متغيرات البيئة =====
CHANNEL_ACCESS_TOKEN = os.environ.get("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET       = os.environ.get("CHANNEL_SECRET")
ADMIN_USER_ID        = os.environ.get("ADMIN_USER_ID")  # معرّف الأدمن
USER_ID              = os.environ.get("USER_ID")        # (اختياري إذا أردت)

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    raise RuntimeError("يجب ضبط CHANNEL_ACCESS_TOKEN و CHANNEL_SECRET في متغيرات البيئة")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# ===== قائمة المناصب =====
ROLES = [
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
    "🥛 موزع الحليب", "🍹 محترف العصائر", "📖 قارئ الحكايات", "🎟️ منظم العروض"
]

# ===== إعداد اللعبة =====
game_active = False

def send_role_card(reply_token, name, profile_pic, role):
    """إرسال بطاقة المنصب بتصميم Flex Message"""
    bg_url = "https://i.imgur.com/U5lzq0F.jpeg"  # الخلفية الجديدة
    flex = FlexSendMessage(
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
                        "text": role,
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
    line_bot_api.reply_message(reply_token, flex)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global game_active
    text = event.message.text.strip()
    uid  = event.source.user_id

    # === أوامر الأدمن ===
    if text.lower() == ".g" and uid == ADMIN_USER_ID:
        game_active = True
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text="🎮 تم تشغيل لعبة المناصب للجميع!"))
        return

    if text.lower() == ".stop" and uid == ADMIN_USER_ID:
        game_active = False
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text="⏹️ تم إيقاف لعبة المناصب."))
        return

    if text.lower() == ".u" and uid == ADMIN_USER_ID:
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text="🗑️ أمر الحذف (خصصه لاحقًا)."))
        return

    # === لعبة المناصب للجميع ===
    if game_active and text == "منصب":
        try:
            profile = line_bot_api.get_profile(uid)
            name  = profile.display_name
            pic   = profile.picture_url or "https://i.imgur.com/U5lzq0F.jpeg"
        except:
            name, pic = "عضو مجهول", "https://i.imgur.com/U5lzq0F.jpeg"

        role = random.choice(ROLES)
        send_role_card(event.reply_token, name, pic, role)
        return

if __name__ == "__main__":
    app.run(port=5000, host="0.0.0.0")
    
