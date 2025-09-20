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
user_roles = {}  # تخزين مناصب المستخدمين

# ============= دالة بطاقة المناصب (كما هي - احترافية) =============
def send_role_card(reply_token, name, profile_pic, role):
    bg_url = "https://i.imgur.com/U5lzq0F.jpeg"

    flex = FlexSendMessage(
        alt_text="🎉 بطاقتك الرسمية!",
        contents={
            "type": "bubble",
            "size": "kilo",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
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
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
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
                            {
                                "type": "text",
                                "text": name,
                                "weight": "bold",
                                "size": "lg",
                                "align": "center",
                                "color": "#FFFFFF",
                                "margin": "md",
                                "wrap": True
                            },
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "contents": [
                                    {"type": "filler"},
                                    {
                                        "type": "box",
                                        "layout": "vertical",
                                        "contents": [],
                                        "width": "60%",
                                        "height": "2px",
                                        "backgroundColor": "#FFD700",
                                        "cornerRadius": "1px"
                                    },
                                    {"type": "filler"}
                                ],
                                "margin": "lg"
                            },
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
                            {
                                "type": "text",
                                "text": "👑560👑",
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

# ============= دالة بطاقة المنشن (نارية 🔥 - مصححة وخالية من الأخطاء) =============
def send_admin_mention_card(reply_token, mentioner_name, mentioner_pic):
    flex = FlexSendMessage(
        alt_text="✨ تم منشن الادمن!",
        contents={
            "type": "bubble",
            "size": "kilo",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    # الخلفية المتدرجة الزاهية
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [],
                        "position": "absolute",
                        "background": {
                            "type": "linearGradient",
                            "angle": "45deg",
                            "startColor": "#FF3366",
                            "endColor": "#3366FF",
                            "centerColor": "#FFCC33"
                        },
                        "cornerRadius": "32px",
                        "offsetTop": "0px",
                        "offsetBottom": "0px",
                        "offsetStart": "0px",
                        "offsetEnd": "0px",
                        "flex": 1
                    },
                    # الإطار النيون المتوهج (طبقتين)
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [],
                        "position": "absolute",
                        "cornerRadius": "32px",
                        "borderWidth": "4px",
                        "borderColor": "#FFFFFF",
                        "offsetTop": "4px",
                        "offsetBottom": "4px",
                        "offsetStart": "4px",
                        "offsetEnd": "4px"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [],
                        "position": "absolute",
                        "cornerRadius": "30px",
                        "borderWidth": "2px",
                        "borderColor": "#FF00FF",
                        "offsetTop": "6px",
                        "offsetBottom": "6px",
                        "offsetStart": "6px",
                        "offsetEnd": "6px"
                    },
                    # المحتوى الداخلي
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            # صورة العضو بإطار مضيء
                            {
                                "type": "image",
                                "url": mentioner_pic,
                                "size": "xl",
                                "aspectMode": "cover",
                                "aspectRatio": "1:1",
                                "cornerRadius": "100px",
                                "align": "center",
                                "margin": "xxl",
                                "offsetTop": "30px",
                                "style": "solid"
                            },
                            # دائرة توهج خلف الصورة — ✅ تم التصحيح هنا (بدون calc)
                            {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [],
                                "width": "120px",
                                "height": "120px",
                                "cornerRadius": "100px",
                                "borderWidth": "4px",
                                "borderColor": "#FFFFFF44",
                                "position": "absolute",
                                "offsetTop": "80px",
                                "offsetStart": "50%",
                                "marginStart": "-60px"
                            },
                            # اسم العضو — متوهج
                            {
                                "type": "text",
                                "text": mentioner_name,
                                "weight": "bold",
                                "size": "lg",
                                "align": "center",
                                "color": "#FFFFFF",
                                "margin": "lg",
                                "wrap": True,
                                "style": "normal",
                                "decoration": "none",
                                "offsetTop": "10px"
                            },
                            # خط فاصل ملون
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "contents": [
                                    {"type": "filler"},
                                    {
                                        "type": "box",
                                        "layout": "vertical",
                                        "contents": [],
                                        "width": "50%",
                                        "height": "4px",
                                        "background": {
                                            "type": "linearGradient",
                                            "angle": "90deg",
                                            "startColor": "#FF00CC",
                                            "endColor": "#33FFFF"
                                        },
                                        "cornerRadius": "2px"
                                    },
                                    {"type": "filler"}
                                ],
                                "margin": "lg"
                            },
                            # رسالة "مشغول يا حلو"
                            {
                                "type": "text",
                                "text": "مشغول يا حلو 💌",
                                "weight": "bold",
                                "size": "xl",
                                "align": "center",
                                "color": "#FFFFFF",
                                "margin": "md",
                                "wrap": True,
                                "style": "normal",
                                "decoration": "none",
                                "offsetTop": "5px"
                            },
                            # رسالة ثانوية
                            {
                                "type": "text",
                                "text": "✨ اترك له رسالة ويرد عليك قريب ✨",
                                "size": "sm",
                                "align": "center",
                                "color": "#FFFF99",
                                "margin": "none",
                                "wrap": True
                            },
                            # الشعار
                            {
                                "type": "text",
                                "text": "👑560👑",
                                "size": "xs",
                                "align": "center",
                                "color": "#FFFFFFDD",
                                "margin": "xxl"
                            }
                        ],
                        "position": "relative",
                        "paddingAll": "20px",
                        "justifyContent": "center",
                        "alignItems": "center"
                    }
                ],
                "paddingAll": "0px"
            }
        }
    )
    line_bot_api.reply_message(reply_token, flex)

# ============= نقطة الـ Webhook =============
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# ============= معالجة الرسائل =============
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global game_active
    text = event.message.text.strip()
    uid  = event.source.user_id

    # ✅ الحل الخارق: قائمة أسماء ثابتة — تضمن ظهور البطاقة دائمًا
    ADMIN_ALIASES = [
        "@ـــ ⁵⁶⁰",
        "عاشور",
        "بو جواد",
        "560",
        "@560",
        "عــاشــور",
        "بو_جواد",
        "ع",
        "جواد",
        "بو",
        "⁵⁶⁰",
        "5 6 0",
        "@ 560",
        "@ عاشور",
        "@ بو جواد",
        "بو جواد 560",
        "عشور",
        "الجواد",
        "ملك 560"
    ]

    # تنظيف النص: إزالة المسافات + lowercase
    text_clean = ''.join(text.split()).lower()

    for alias in ADMIN_ALIASES:
        alias_clean = ''.join(alias.split()).lower()
        if alias_clean in text_clean:
            try:
                profile = line_bot_api.get_profile(uid)  # uid = مين اللي كتب
                mentioner_name = profile.display_name
                mentioner_pic = profile.picture_url or "https://i.imgur.com/U5lzq0F.jpeg"
            except:
                mentioner_name, mentioner_pic = "عضو مجهول", "https://i.imgur.com/U5lzq0F.jpeg"
            send_admin_mention_card(event.reply_token, mentioner_name, mentioner_pic)
            return

    # الأوامر الأخرى — بدون أي تغيير
    if text.lower() == ".g" and uid == ADMIN_USER_ID:
        game_active = True
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text="🎮 تم تشغيل لعبة المناصب للجميع!"))
        return

    if text.lower() == ".stop" and uid == ADMIN_USER_ID:
        game_active = False
        user_roles.clear()  # تجديد المناصب
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text="⏹️ تم إيقاف لعبة المناصب وتجديدها!"))
        return

    if text.lower() == ".u" and uid == ADMIN_USER_ID:
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text="🧹 تم تنظيف الدردشة!"))
        return

    if game_active and text == "منصب":
        if uid in user_roles:
            previous_role = user_roles[uid]
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text=f"لك تم إعطاؤك منصبك: {previous_role}"))
            return
        else:
            try:
                profile = line_bot_api.get_profile(uid)
                name = profile.display_name
                pic  = profile.picture_url or "https://i.imgur.com/U5lzq0F.jpeg"
            except:
                name, pic = "عضو مجهول", "https://i.imgur.com/U5lzq0F.jpeg"
            role = random.choice(ROLES)
            user_roles[uid] = role
            send_role_card(event.reply_token, name, pic, role)
            return

# ============= نقطة التشغيل =============
if __name__ == "__main__":
    app.run(port=5000, host="0.0.0.0")
