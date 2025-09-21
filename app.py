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

# ============= دالة بطاقة المناصب (معدلة - صورة دائرية بتلميع وإطار ذهبي) =============
def send_role_card(reply_token, name, profile_pic, role):
    bg_url = "https://i.imgur.com/SAqlVNr.gif"  # ✅ خلفية متحركة الآن

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
                        "flex": 1,
                        "opacity": "0.6"  # ✅ شفافية للخلفية المتحركة
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
                            # ✅ صورة العضو مع إطار أصفر وتلميع
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
                                        "align": "center"
                                    }
                                ],
                                "cornerRadius": "100px",
                                "borderWidth": "4px",
                                "borderColor": "#FFD700",  # ذهبي
                                "align": "center",
                                "margin": "xxl",
                                "offsetTop": "40px",
                                "paddingAll": "2px",
                                "background": {
                                    "type": "linearGradient",
                                    "angle": "45deg",
                                    "startColor": "#FFFFFF00",
                                    "endColor": "#FFFF0033"
                                }
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

# ============= دالة بطاقة المنشن (معدلة - صورة بتلميع + إيموجيات ملكية) =============
def send_admin_mention_card(reply_token, mentioner_name, mentioner_pic):
    flex = FlexSendMessage(
        alt_text="✨ عاشور مشغول الحين!",
        contents={
            "type": "bubble",
            "size": "kilo",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    # الخلفية المتحركة
                    {
                        "type": "image",
                        "url": "https://i.imgur.com/SAqlVNr.gif",
                        "size": "full",
                        "aspectMode": "cover",
                        "position": "absolute",
                        "offsetTop": "0px",
                        "offsetBottom": "0px",
                        "offsetStart": "0px",
                        "offsetEnd": "0px",
                        "flex": 1,
                        "aspectRatio": "9:16",
                        "opacity": "0.5"
                    },
                    # إطار براق
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [],
                        "borderWidth": "4px",
                        "borderColor": "#FFFFFF",
                        "cornerRadius": "32px",
                        "position": "absolute",
                        "offsetTop": "4px",
                        "offsetBottom": "4px",
                        "offsetStart": "4px",
                        "offsetEnd": "4px"
                    },
                    # المحتوى الرئيسي
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            # ✅ صورة العضو مع إطار أصفر وتلميع
                            {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {
                                        "type": "image",
                                        "url": mentioner_pic,
                                        "size": "xl",
                                        "aspectMode": "cover",
                                        "aspectRatio": "1:1",
                                        "cornerRadius": "100px",
                                        "align": "center"
                                    }
                                ],
                                "cornerRadius": "100px",
                                "borderWidth": "4px",
                                "borderColor": "#FFD700",
                                "align": "center",
                                "margin": "xxl",
                                "paddingAll": "2px",
                                "background": {
                                    "type": "linearGradient",
                                    "angle": "135deg",
                                    "startColor": "#FFFFFF22",
                                    "endColor": "#FFFF0044"
                                }
                            },
                            {
                                "type": "text",
                                "text": mentioner_name,
                                "weight": "bold",
                                "size": "lg",
                                "align": "center",
                                "color": "#FFFFFF",
                                "margin": "md",
                                "wrap": True,
                                "style": "normal"
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
                                        "width": "40%",
                                        "height": "3px",
                                        "background": {
                                            "type": "linearGradient",
                                            "angle": "90deg",
                                            "startColor": "#FF6B6B",
                                            "endColor": "#4ECDC4"
                                        },
                                        "cornerRadius": "2px"
                                    },
                                    {"type": "filler"}
                                ],
                                "margin": "lg"
                            },
                            {
                                "type": "text",
                                "text": "يا حلو عاشور مشغول الحين 💌",
                                "weight": "bold",
                                "size": "md",
                                "align": "center",
                                "color": "#FFFFFF",
                                "margin": "sm",
                                "wrap": True
                            },
                            {
                                "type": "text",
                                "text": "يمكنك ترك رسالة له بالخاص ✨",
                                "size": "sm",
                                "align": "center",
                                "color": "#FFFFE0",
                                "margin": "none",
                                "wrap": True
                            },
                            # ✅ إيموجيات ملكية جديدة
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "contents": [
                                    {"type": "text", "text": "👑", "size": "sm", "gravity": "center"},
                                    {"type": "text", "text": "⚡", "size": "sm", "gravity": "center"},
                                    {"type": "text", "text": "🎖️", "size": "sm", "gravity": "center"},
                                    {"type": "text", "text": "🎯", "size": "sm", "gravity": "center"},
                                    {"type": "text", "text": "🏆", "size": "sm", "gravity": "center"}
                                ],
                                "justifyContent": "center",
                                "margin": "lg"
                            },
                            {
                                "type": "text",
                                "text": "👑560👑",
                                "size": "xs",
                                "align": "center",
                                "color": "#FFFFFFDD",
                                "margin": "xl"
                            }
                        ],
                        "position": "relative",
                        "paddingAll": "24px",
                        "justifyContent": "center",
                        "alignItems": "center",
                        "backgroundColor": "#00000000"
                    }
                ],
                "paddingAll": "0px",
                "backgroundColor": "#00000000"
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

    # ✅ يرد فقط على 3 عبارات بالضبط — لا أكثر ولا أقل
    EXACT_TRIGGERS = {"عاشور", "بو جواد", "@ـــ ⁵⁶⁰"}

    if text in EXACT_TRIGGERS:
        try:
            profile = line_bot_api.get_profile(uid)  # uid = مين اللي كتب
            mentioner_name = profile.display_name
            mentioner_pic = profile.picture_url or "https://i.imgur.com/SAqlVNr.gif"
        except:
            mentioner_name, mentioner_pic = "عضو مجهول", "https://i.imgur.com/SAqlVNr.gif"
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

    # 🎲 لعبة زهر اللّقمة
    if text.lower() in [".roll", ".زَر"]:
        dice_result = random.randint(1, 6)
        dice_emojis = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
        dice_gif_map = {
            1: "https://i.imgur.com/8VZLXQh.gif",
            2: "https://i.imgur.com/3WQYp5f.gif",
            3: "https://i.imgur.com/9JmR7kN.gif",
            4: "https://i.imgur.com/4Kk0RzX.gif",
            5: "https://i.imgur.com/7ZQp1dE.gif",
            6: "https://i.imgur.com/6W0R2fO.gif"
        }
        gif_url = dice_gif_map.get(dice_result, "https://i.imgur.com/8VZLXQh.gif")

        try:
            profile = line_bot_api.get_profile(uid)
            name = profile.display_name
        except:
            name = "عضو مجهول"

        flex = FlexSendMessage(
            alt_text=f"🎲 {name} رمى الزهر!",
            contents={
                "type": "bubble",
                "size": "kilo",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "image",
                            "url": "https://i.imgur.com/SAqlVNr.gif",
                            "size": "full",
                            "aspectMode": "cover",
                            "position": "absolute",
                            "offsetTop": "0px",
                            "offsetBottom": "0px",
                            "offsetStart": "0px",
                            "offsetEnd": "0px",
                            "flex": 1,
                            "opacity": "0.4"
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [],
                            "borderWidth": "4px",
                            "borderColor": "#FFFFFF",
                            "cornerRadius": "32px",
                            "position": "absolute",
                            "offsetTop": "8px",
                            "offsetBottom": "8px",
                            "offsetStart": "8px",
                            "offsetEnd": "8px"
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "image",
                                    "url": gif_url,
                                    "size": "3xl",
                                    "aspectMode": "fit",
                                    "align": "center",
                                    "margin": "xxl"
                                },
                                {
                                    "type": "text",
                                    "text": f"🎲 {name}",
                                    "weight": "bold",
                                    "size": "lg",
                                    "align": "center",
                                    "color": "#FFFFFF",
                                    "margin": "md"
                                },
                                {
                                    "type": "text",
                                    "text": f"رماها وطلع له: {dice_result}",
                                    "weight": "bold",
                                    "size": "xl",
                                    "align": "center",
                                    "color": "#FFD700",
                                    "margin": "none"
                                },
                                {
                                    "type": "text",
                                    "text": dice_emojis[dice_result - 1],
                                    "size": "4xl",
                                    "align": "center",
                                    "color": "#FFFFFF",
                                    "margin": "sm"
                                },
                                {
                                    "type": "text",
                                    "text": "👑560👑",
                                    "size": "xs",
                                    "align": "center",
                                    "color": "#FFFFFFDD",
                                    "margin": "xl"
                                }
                            ],
                            "position": "relative",
                            "paddingAll": "24px",
                            "justifyContent": "center",
                            "alignItems": "center",
                            "backgroundColor": "#00000000"
                        }
                    ],
                    "paddingAll": "0px",
                    "backgroundColor": "#00000000"
                }
            }
        )
        line_bot_api.reply_message(event.reply_token, flex)
        return

    # 🤪 لعبة "مين يمثل؟!" - مهام تمثيلية مضحكة
    if text.lower() in [".مثل", ".ادا", ".act"]:
        tasks = [
            "ادّعي إنك جوالك خطفه جن وبيكلمك بالليل!",
            "صرخ في الشات: 'يا جماعة أنا بقرة!' 🐄",
            "تظاهر إنك أمير وتطلب من الخادم يجيب لك القمر! 🌙",
            "اقرأ آخر رسالة أرسلتها بصوت عالي جدًا وكأنك مذيع نشرة أخبار! 📢",
            "تظاهر أنك روبوت وتكلم بجملة واحدة فقط: 'بيب بوب أنا لا أفهم المشاعر' 🤖",
            "اسأل بوت آخر في الجروب: 'متى نتزوج؟' 💍",
            "تظاهر أنك في مزاد وبيع آخر شيء أكلته! 🍕",
            "ادّعي إنك شيخ قبيلة وتعاقب اللي ما يحب الكبسة! 🍚",
            "تظاهر أنك مذيع طقس: 'درجة الحرارة 500 تحت الصفر... والناس تسبح!' 🌡️",
            "قول للشخص اللي فوقك في الشات: 'أنا جيت أخطفك عروسة!' 👰",
            "تظاهر أنك محقق وتسأل الجميع: 'مين اللي أكل آخر قطعة شكولاتة؟!' 🍫",
            "ادّعي إنك مخترع وقدم اختراعك الجديد: 'المنديل الطائر'! 🧻✈️",
            "تظاهر أنك في برنامج مسابقات وصرخ: 'أعطوني الجووووائز!' 🎁",
            "ادّعي إنك طبيب وشخصيتك مريض — وداويه بـ'خل وليمون'! 🍋",
            "تظاهر أنك ساحر وحاول تحول أقرب واحد لك إلى ضفدعة! 🐸",
            "ادّعي إنك ملك وطلب من الجميع يصفق لك 10 ثواني! 👏",
            "تظاهر أنك في مطعم فاخر واطلب 'برجر من سحاب'! ☁️🍔",
            "ادّعي إنك نينجا واكتب: 'هاااااااي ياه!' ثم اهرب! 🥷",
            "تظاهر أنك في مقابلة عمل وأول سؤالك: 'شو رأيك في الموز؟' 🍌",
            "ادّعي إنك مذيع رياضي وعلق على مباراة... بين قطتين! 🐱⚽"
        ]

        selected_task = random.choice(tasks)

        try:
            profile = line_bot_api.get_profile(uid)
            name = profile.display_name
        except:
            name = "عضو مجهول"

        flex = FlexSendMessage(
            alt_text=f"🎭 {name} — دورك تتمثّل!",
            contents={
                "type": "bubble",
                "size": "kilo",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "image",
                            "url": "https://i.imgur.com/SAqlVNr.gif",
                            "size": "full",
                            "aspectMode": "cover",
                            "position": "absolute",
                            "offsetTop": "0px",
                            "offsetBottom": "0px",
                            "offsetStart": "0px",
                            "offsetEnd": "0px",
                            "flex": 1,
                            "opacity": "0.4"
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [],
                            "borderWidth": "4px",
                            "borderColor": "#FFFFFF",
                            "cornerRadius": "32px",
                            "position": "absolute",
                            "offsetTop": "8px",
                            "offsetBottom": "8px",
                            "offsetStart": "8px",
                            "offsetEnd": "8px"
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "image",
                                    "url": "https://i.imgur.com/6W0R2fO.gif",
                                    "size": "3xl",
                                    "aspectMode": "fit",
                                    "align": "center",
                                    "margin": "xxl"
                                },
                                {
                                    "type": "text",
                                    "text": f"🎭 {name}",
                                    "weight": "bold",
                                    "size": "lg",
                                    "align": "center",
                                    "color": "#FFFFFF",
                                    "margin": "md"
                                },
                                {
                                    "type": "text",
                                    "text": "دورك تتمثّل!",
                                    "weight": "bold",
                                    "size": "xl",
                                    "align": "center",
                                    "color": "#FF69B4",  # وردي — للضحك والعبث
                                    "margin": "none"
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
                                            "backgroundColor": "#FF69B4",
                                            "cornerRadius": "1px"
                                        },
                                        {"type": "filler"}
                                    ],
                                    "margin": "lg"
                                },
                                {
                                    "type": "text",
                                    "text": selected_task,
                                    "weight": "bold",
                                    "size": "md",
                                    "align": "center",
                                    "color": "#FFFFFF",
                                    "margin": "md",
                                    "wrap": True,
                                    "style": "normal"
                                },
                                {
                                    "type": "text",
                                    "text": "⏰ عندك دقيقة... يلا بينا! 😜",
                                    "size": "sm",
                                    "align": "center",
                                    "color": "#FFFFE0",
                                    "margin": "sm",
                                    "wrap": True
                                },
                                {
                                    "type": "text",
                                    "text": "👑560👑",
                                    "size": "xs",
                                    "align": "center",
                                    "color": "#FFFFFFDD",
                                    "margin": "xl"
                                }
                            ],
                            "position": "relative",
                            "paddingAll": "24px",
                            "justifyContent": "center",
                            "alignItems": "center",
                            "backgroundColor": "#00000000"
                        }
                    ],
                    "paddingAll": "0px",
                    "backgroundColor": "#00000000"
                }
            }
        )
        line_bot_api.reply_message(event.reply_token, flex)
        return

    # 🚪 أمر مغادرة المجموعة — فقط للأدمن
    if text.lower() == ".leave" and uid == ADMIN_USER_ID:
        source = event.source
        if hasattr(source, 'group_id') and source.group_id:
            # رسالة وداع جميلة
            farewell_message = (
                "😢 تم طردي من المجموعة بأمر الأدمن!\n"
                "لكن لا تنسوني... أنا بوت 560، وعدكم إني أرجع إذا دعوتموني! 💌👑\n"
                "وداعًا... إلى لقاء قريب! 👋✨"
            )
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=farewell_message))
            # غادر المجموعة
            line_bot_api.leave_group(source.group_id)
            return
        elif hasattr(source, 'room_id') and source.room_id:
            # لو في روم (نادر)
            farewell_message = "👋 وداعًا من هذه الدردشة! لا تنسوني!"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=farewell_message))
            line_bot_api.leave_room(source.room_id)
            return
        else:
            # لو في الخاص — ما ينفع يغادر
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="❌ هذا الأمر فقط للمجموعات أو الرومات."))
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
                pic  = profile.picture_url or "https://i.imgur.com/SAqlVNr.gif"
            except:
                name, pic = "عضو مجهول", "https://i.imgur.com/SAqlVNr.gif"
            role = random.choice(ROLES)
            user_roles[uid] = role
            send_role_card(event.reply_token, name, pic, role)
            return

# ============= نقطة التشغيل =============
if __name__ == "__main__":
    app.run(port=5000, host="0.0.0.0")
