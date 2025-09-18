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
ADMIN_USER_ID        = os.environ.get("ADMIN_USER_ID")
USER_ID              = os.environ.get("USER_ID")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler      = WebhookHandler(CHANNEL_SECRET)

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

game_active = False

def send_role_card(reply_token, name, profile_pic, role):
    bg_url = "https://i.imgur.com/U5lzq0F.jpeg"  # خلفية البطاقة (بدون مسافة زائدة)

    flex = FlexSendMessage(
        alt_text="🎉 بطاقتك الرسمية في البلاط الملكي!",
        contents={
            "type": "bubble",
            "size": "kilo",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    # الخلفية المزخرفة بإطار ذهبي
                    {
                        "type": "image",
                        "url": bg_url,
                        "size": "full",
                        "aspectRatio": "9:16",
                        "aspectMode": "cover",
                        "position": "absolute",
                        "offsetTop": "0px",
                        "offsetBottom": "0px",
                        "offsetStart": "0px",
                        "offsetEnd": "0px",
                        "flex": 1
                    },
                    # إطار البطاقة الخارجي (مزخرف)
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [],
                        "position": "absolute",
                        "cornerRadius": "32px",
                        "borderWidth": "6px",
                        "borderColor": "#FFD700",
                        "offsetTop": "8px",
                        "offsetBottom": "8px",
                        "offsetStart": "8px",
                        "offsetEnd": "8px",
                        "flex": 1,
                        "paddingAll": "0px"
                    },
                    # ظل داخلي للبطاقة
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [],
                        "position": "absolute",
                        "cornerRadius": "28px",
                        "backgroundColor": "#00000055",
                        "offsetTop": "12px",
                        "offsetBottom": "12px",
                        "offsetStart": "12px",
                        "offsetEnd": "12px",
                        "flex": 1
                    },
                    # المحتوى الداخلي (الصورة + الاسم + المنصب)
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            # صورة العضو
                            {
                                "type": "image",
                                "url": profile_pic,
                                "size": "xl",
                                "aspectMode": "cover",
                                "aspectRatio": "1:1",
                                "cornerRadius": "100px",
                                "align": "center",
                                "margin": "xxl",
                                "offsetTop": "40px"
                            },
                            # اسم العضو
                            {
                                "type": "text",
                                "text": name,
                                "weight": "bold",
                                "size": "lg",
                                "align": "center",
                                "color": "#FFFFFF",
                                "margin": "md",
                                "wrap": True,
                                "style": "normal",
                                "decoration": "none"
                            },
                            # خط فاصل
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "contents": [
                                    {
                                        "type": "filler"
                                    },
                                    {
                                        "type": "box",
                                        "layout": "vertical",
                                        "contents": [],
                                        "width": "60%",
                                        "height": "2px",
                                        "backgroundColor": "#FFD700",
                                        "cornerRadius": "1px"
                                    },
                                    {
                                        "type": "filler"
                                    }
                                ],
                                "margin": "lg"
                            },
                            # منصب العضو
                            {
                                "type": "text",
                                "text": role,
                                "weight": "bold",
                                "size": "lg",
                                "align": "center",
                                "color": "#FFD700",
                                "margin": "sm",
                                "wrap": True,
                                "style": "italic",
                                "decoration": "underline"
                            },
                            # شعار ملكي أسفل البطاقة
                            {
                                "type": "text",
                                "text": "👑 البلاط الملكي 🏰",
                                "size": "xs",
                                "align": "center",
                                "color": "#FFFFFFCC",
                                "margin": "xl"
                            }
                        ],
                        "position": "relative",
                        "paddingAll": "20px",
                        "justifyContent": "center",
                        "alignItems": "center"
                    }
                ],
                "paddingAll": "0px",
                "backgroundColor": "#00000000"
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
            TextSendMessage(text="🗑️ أمر الحذف (يمكن تعديله)."))
        return

    if game_active and text == "منصب":
        try:
            profile = line_bot_api.get_profile(uid)
            name  = profile.display_name
            pic   = profile.picture_url or "https://i.imgur.com/U5lzq0F.jpeg"
        except:
            name, pic = "عضو مجهول", "https://i.imgur.com/U5lzq0F.jpeg"
        role = random.choice(ROLES)
        send_role_card(event.reply_token, name, pic, role)

if __name__ == "__main__":
    app.run(port=5000, host="0.0.0.0")
