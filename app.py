# -*- coding: utf-8 -*-
import os, random
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, FlexSendMessage, TextSendMessage,
    FollowEvent, MemberJoinedEvent, MemberLeftEvent
)
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

app = Flask(__name__)

# ===== متغيرات البيئة =====
CHANNEL_ACCESS_TOKEN = os.environ.get("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET       = os.environ.get("CHANNEL_SECRET")
ADMIN_USER_ID        = os.environ.get("ADMIN_USER_ID")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler      = WebhookHandler(CHANNEL_SECRET)

# ===== قائمة المناصب المضحكة =====
ROLES = [
    "👑 زعيم المطبخ", "🌾 مزارع البطاطس", "🍳 طباخ فطير الصبح", "🐒 مدير القرود",
    "🕊️ مربي الحمام الزاجل", "🪄 ساحر التلفاز", "⚔️ قائد السجاد الطائر", "🧩 محلل الألغاز المزدحمة",
    "🚀 حارس الفضاء الخارجي", "🎨 رسام الوجوه الغريبة", "💎 حارس الخواتم المصنوعة في الصين", "🥁 عازف الطبول الصراخية",
    "🌋 مراقب البراكين النائمة", "🐴 فارس السرج البلاستيكي", "🥳 منظم أعياد الميلاد المتعبة", "🧙 ساحر الظلال المتدلية",
    "🍞 خباز الكعك المتفجر", "🐘 مروض الفيلة الصغيرة", "🕰️ حارس الزمن المكسور", "📖 راوي القصص المللقة",
    "🥷 نينجا الظلال الملونة", "💡 مخترع المصباح الغازي", "🎯 بطل النبال المفقود", "🧼 صانع الصابون العطري",
    "🎻 عازف الكمان المكسور", "🌌 عالم النجوم المغمورة", "🍯 صانع العسل الحامض", "🧵 خياط الستائر",
    "🚒 مطفئ الحرائق المبلل", "🎭 ممثل البلاط المتقاعد", "🪆 جامع الدمى المكسورة", "🐝 مربي النحل العاطل",
    "🍹 خبير العصائر المجمدة", "🎩 سيد الألغاز المربكة", "🪖 جندي الحدود النائمة", "🐀 صائد الجرذان الأنيق",
    "🎮 لاعب محترف في النوم", "🥩 قصاب القصر المتخلف", "🧃 موزع العصير المغلق", "📦 مدير المخازن الفارغة",
    "🍵 صانع الشاي البارد", "🎷 عازف الساكسفون الصارخ", "🕵️ جاسوس الملك المتنكر", "🧙‍♀️ عراف المملكة المخطئ",
    "🌠 ملتقط النجوم المتساقطة", "🛡️ حارس القصر المتهدم", "🥨 صانع المعجنات المجمدة", "💃 راقص البلاط المتعب",
    "🪓 قاطع الأشجار الميتة", "🎳 بطل البولينج المفقود", "🎤 مغني الساحة المجهول", "📜 كاتب الأسرار المكشوفة",
    "🏆 حامل الجوائز المزيفة", "🍗 مشوي الدواجن الفاسدة", " genie المصباح المكسور", "🎺 منشد البلاط الصاخب",
    "🥘 طباخ الملكة المتسلطة", "🌊 ساحر الماء الملوث", "🔥 ساحر النار المطفأة", "❄️ ساحر الثلج الذائب",
    "⚡ ساحر البرق المتقطع", "🚨 ناقوس الخطر الكاذب", "🧩 صانع الألغاز الغامضة", "🏇 فارس الصيد المفقود",
    "🚲 ساعي البريد البطيء", "🪔 حافظ النور المطفأ", "🕺 راقص القصر المتعب", "🔮 قارئ الطالع الغامض",
    "🪙 صانع العملات المزيفة", "🐎 راعي الخيول المتقاعد", "🧯 مسؤول الأمن النائم", "⚖️ قاضي المحكمة المتهورة",
    "🎣 صياد السمك الجاف", "🧹 منظف القصر المتسول", "📚 أمين المكتبة المفقودة", "🐉 حارس التنانين الوهمية",
    "💤 حارس الأحلام المكسورة", "🥶 منظف الثلج المذاب", "🩺 طبيب القصر المتقاعد", "🍀 زارع الحظ المفقود",
    "🤡 مهرج البلاط المتعب", "💰 أمين الخزانة الفارغة", "🌾 مزارع المملكة المهجورة", "🪤 صائد الوحوش الورقية",
    "🚪 حارس البوابة المغلقة", "🗝️ حارس الأسرار المكشوفة", "💡 عالم الاختراعات الفاشلة", "🎨 مزخرف الجدران المتهالكة",
    "📯 ناقوس الإنذار الكاذب", "🧊 ساحر الجليد الذائب", "🐪 سائق الإبل البطيء", "🍬 صانع الحلوى المُرّة",
    "🧙 ساحر المملكة المتقاعد", "🎹 عازف القيثارة المكسورة", "🛶 ملاح البحيرة الجافة", "🧩 مبدع الألغاز الغريبة",
    "🥛 موزع الحليب المُرّ", "🍹 محترف العصائر المُرّة", "📖 قارئ الحكايات النائمة", "🎟️ منظم العروض الملغاة",
    "🐑 خروف النساء", "👑 زير النساء", "😴 النعسان", "🤥 الكذاب",
    "🤪 ملك السخف", "🥔 سلطان البطاطس", "🎭 ممثل الدراما", "📱 خبير التيك توك",
    "🍕 رئيس جلسة البيتزا", "🎮 سيد بلاي ستيشن", "😴 نايم على الدوام", "🍫 موزع الشوكولاتة المُرّة",
    "🎭 ممثل التراجيديا", "🧻 خبير ورق التواليت", "🎯 خبير الإخفاقات", "👑 ملك التاج المكسور",
    "🎭 ممثل الكوميديا البائسة", "🧼 ملك الصابون الفارغ", "👑 زعيم السبات", "🎭 ممثل الفيلم الوهمي",
    "😴 سلطان النعاس", "🤥 سيد الأكاذيب", "👑 ملك الكسل", "🎭 ممثل المأساة الفاشلة",
    "🎭 ممثل الفرح المفقود", "👑 زعيم الضحكة المتعبة", "🎭 ممثل الحزن المبالغ فيه", "👑 ملك التفاهة",
    "🎭 ممثل الغضب المفقود", "👑 زعيم البكاء المبالغ فيه", "🎭 ممثل الخوف المتخيل", "👑 ملك الغباء الراقي",
    "🎭 ممثل الحب المفقود", "👑 زعيم العشق المتعب", "🎭 ممثل الحقد المفقود", "👑 ملك الكراهية المبالغ فيها",
    "🎭 ممثل الغيرة المتخيلة", "👑 زعيم الحسد المفقود", "🎭 ممثل الكآبة المبالغ فيها", "👑 ملك الفرح المفقود"
]

game_active = False
user_roles = {}  # تخزين مناصب المستخدمين
known_groups = set()  # ✅ تخزين معرفات المجموعات اللي دخلها البوت

# ===== متغيرات لعبة القرعة =====
raffle_active = {}      # group_id -> bool
raffle_participants = {}  # group_id -> set of user_ids
raffle_names = {}         # user_id -> display_name

# ===== متغيرات لعبة الجائزة السرية =====
secret_game_active = {}      # group_id -> bool
secret_participants = {}     # group_id -> list of names
donors_list = [
    "أحمد", "سارة", "الكايد", "فاطمة", "قير عادي", "نورا", "قلق", "منى", "ليلى", "عمر",
    "مريم", "بدر", "الدشاش", "اقشر", "نور", "رانيا", "أمينة", "رائد الحارثي", "داوود", "ياسر"
]
prizes_list = [
    "نعله منقطعه", "عفريته", "سروال ابو كرسي", "شم سري", "نير",
    "موز", "بوسه مقدمه من معطاب", "حليب كامل الدسم ", "كراع دجاجه", "رحلة سياحية إلى قريح",
    "كراتين", "شنطة تيلي تابيز", "جهاز نوكيا", "برج خليفه", "عصير طماط",
    "رمح طويل", "حقيبة سفر", "ساعة ذكية", "تريلة بلور ", "تريلة موارد  "
]

# ===== متغيرات مراقبة الدخول =====
lurking_active = {}  # group_id -> bool
lurkers_list = {}    # group_id -> list of names

# ============= دالة بطاقة المناصب (معدلة - صورة دائرية بتلميع وإطار ذهبي) =============
def send_role_card(reply_token, name, profile_pic, role):
    bg_url = "https://i.imgur.com/SAqlVNr.gif"  # ✅ تم حذف المسافة

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
                        "opacity": "0.6"
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
                                "borderColor": "#FFD700",
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
                    {
                        "type": "image",
                        "url": "https://i.imgur.com/SAqlVNr.gif",  # ✅ حذف المسافة
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
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
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

# ============= دالة بطاقة تسجيل القرعة (معدلة - زر أسود) =============
def send_raffle_card(reply_token, group_id):
    flex = FlexSendMessage(
        alt_text="🎯 سجّل في القرعة!",
        contents={
            "type": "bubble",
            "size": "kilo",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "image",
                        "url": "https://i.imgur.com/SAqlVNr.gif",  # ✅ حذف المسافة
                        "size": "full",
                        "aspectMode": "cover",
                        "position": "absolute",
                        "offsetTop": "0px",
                        "offsetBottom": "0px",
                        "offsetStart": "0px",
                        "offsetEnd": "0px",
                        "flex": 1,
                        "opacity": "0.5"
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
                                "type": "text",
                                "text": "🎯 القرعة الحين مفتوحة!",
                                "weight": "bold",
                                "size": "lg",
                                "align": "center",
                                "color": "#FFFFFF",
                                "margin": "xxl"
                            },
                            {
                                "type": "text",
                                "text": "اضغط الزر تحت عشان تسجل اسمك",
                                "size": "md",
                                "align": "center",
                                "color": "#FFFFE0",
                                "margin": "md",
                                "wrap": True
                            },
                            {
                                "type": "button",
                                "action": {
                                    "type": "message",
                                    "label": "✅ سجّلني!",
                                    "text": "سجلني"
                                },
                                "style": "primary",
                                "color": "#000000",  # ✅ لون أسود الآن
                                "margin": "xl"
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

# ============= دالة إرسال تذكير الصلاة على النبي ﷺ =============
def send_prayer_reminder():
    if not known_groups:
        print("لا توجد مجموعات مسجلة لإرسال التذكير.")
        return

    message = TextSendMessage(text="📿 اللهم صلِّ على محمد 🌹\nاللهم صلِّ وسلم وبارك على نبينا محمد ﷺ")

    for group_id in known_groups:
        try:
            line_bot_api.push_message(group_id, message)
            print(f"تم إرسال تذكير الصلاة على النبي إلى المجموعة: {group_id}")
        except Exception as e:
            print(f"فشل إرسال التذكير إلى {group_id}: {e}")

# ============= إعداد الجدولة =============
scheduler = BackgroundScheduler()
scheduler.add_job(func=send_prayer_reminder, trigger="interval", hours=1)
scheduler.start()

# إيقاف الجدولة عند إغلاق التطبيق
atexit.register(lambda: scheduler.shutdown())

# ============= معالجة دخول البوت للمجموعة =============
@handler.add(FollowEvent)
def handle_follow(event):
    source = event.source
    if hasattr(source, 'group_id') and source.group_id:
        known_groups.add(source.group_id)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="شكرًا على الإضافة 🎉👑")
        )

# ============= معالجة دخول عضو جديد =============
@handler.add(MemberJoinedEvent)
def handle_member_joined(event):
    source = event.source
    if hasattr(source, 'group_id') and source.group_id:
        group_id = source.group_id
        # ✅ تحقق: هل المراقبة مفعلة في هذه المجموعة؟
        if not lurking_active.get(group_id, False):
            return

        for member in event.joined.members:
            try:
                profile = line_bot_api.get_profile(member.user_id)
                name = profile.display_name
            except:
                name = "عضو جديد"

            # ✅ أضف إلى قائمة المراقبين
            if group_id not in lurkers_list:
                lurkers_list[group_id] = []
            if name not in lurkers_list[group_id]:
                lurkers_list[group_id].append(name)

            # ✅ رسالة درامية
            message = f"🚨 {name} متصل الآن! \n✨ انتبهوا، هذي المجموعة صارت أخطر! \n👑 من يجرؤ يتحدى؟"

            line_bot_api.push_message(
                group_id,
                TextSendMessage(text=message)
            )

# ============= معالجة خروج عضو =============
@handler.add(MemberLeftEvent)
def handle_member_left(event):
    for member in event.left.members:
        try:
            profile = line_bot_api.get_profile(member.user_id)
            name = profile.display_name
        except:
            name = "عضو"
        # ✅ إرسال وداع في نفس المجموعة
        line_bot_api.push_message(
            event.source.group_id,
            TextSendMessage(text=f"وداعًا {name} 😢👑")
        )

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
    global game_active, raffle_active, raffle_participants, raffle_names
    global secret_game_active, secret_participants
    text = event.message.text.strip()
    uid  = event.source.user_id
    source = event.source

    # ✅ تسجيل المجموعة إذا كانت جديدة
    if hasattr(source, 'group_id') and source.group_id:
        group_id = source.group_id
        known_groups.add(group_id)
    else:
        group_id = None

    # ✅ يرد فقط على 3 عبارات بالضبط — لا أكثر ولا أقل
    EXACT_TRIGGERS = {"عاشور", "بو جواد", "@ـــ ⁵⁶⁰"}

    if text in EXACT_TRIGGERS:
        try:
            profile = line_bot_api.get_profile(uid)
            mentioner_name = profile.display_name
            mentioner_pic = profile.picture_url or "https://i.imgur.com/SAqlVNr.gif"  # ✅ حذف المسافة
        except:
            mentioner_name, mentioner_pic = "عضو مجهول", "https://i.imgur.com/SAqlVNr.gif"  # ✅ حذف المسافة
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
        user_roles.clear()
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text="⏹️ تم إيقاف لعبة المناصب وتجديدها!"))
        return

    # 🚪 أمر مغادرة المجموعة — فقط للأدمن
    if text.lower() == ".leave" and uid == ADMIN_USER_ID:
        if group_id:
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="وداعًا 👋👑"))
            line_bot_api.leave_group(group_id)
            return
        else:
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="❌ هذا الأمر فقط للمجموعات."))
            return

    # 🎯 لعبة القرعة - بدء التسجيل (Admin فقط)
    if text.lower() == ".r" and group_id and uid == ADMIN_USER_ID:
        raffle_active[group_id] = True
        raffle_participants[group_id] = set()
        send_raffle_card(event.reply_token, group_id)
        return

    # 📋 لعبة القرعة - عرض القائمة
    if text.lower() == ".rr" and group_id:
        participants = raffle_participants.get(group_id, set())
        if not participants:
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text=".FileNotFoundException: الملف غير موجود 😏"))
            return
        names = [raffle_names.get(uid, "عضو مجهول") for uid in participants]
        message = "📋 قائمة المسجلين:\n" + "\n".join(f"• {name}" for name in names)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message))
        return

    # 🎁 لعبة القرعة - اختيار فائز
    if text.lower() == ".rs" and group_id:
        participants = raffle_participants.get(group_id, set())
        if not participants:
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text=".FileNotFoundException: الملف غير موجود 😏"))
            return
        winner_id = random.choice(list(participants))
        winner_name = raffle_names.get(winner_id, "الفائز المجهول")
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text=f"🎉🎉🎉\nالفائز هو: {winner_name} 🏆👑\nمبروك!"))
        # ✅ إعادة ضبط اللعبة لهذه المجموعة فقط
        raffle_active.pop(group_id, None)
        raffle_participants.pop(group_id, None)
        return

    # ✅ تسجيل في القرعة — مع تحسينات
    if text == "سجلني" and group_id:
        # ✅ التحقق: هل اللعبة مفعلة في هذه المجموعة؟
        if not raffle_active.get(group_id, False):
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="❌ التسجيل مغلق حاليًا. انتظر الجولة القادمة!"))
            return

        # ✅ التحقق: هل العضو مسجل مسبقًا؟
        if uid in raffle_participants.get(group_id, set()):
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="✅ أنت مسجل مسبقًا! ما يلزم تسجيل مرتين 😊"))
            return

        # ✅ تسجيل العضو
        try:
            profile = line_bot_api.get_profile(uid)
            name = profile.display_name
        except:
            name = "عضو مجهول"

        raffle_participants.setdefault(group_id, set()).add(uid)
        raffle_names[uid] = name
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text=f"✅ تم تسجيلك: {name} 🎯"))

        # ✅ إشعار لطيف بعد 3 تسجيلات
        if len(raffle_participants[group_id]) % 3 == 0 and len(raffle_participants[group_id]) > 0:
            line_bot_api.push_message(group_id,
                TextSendMessage(text=f"🎯 {len(raffle_participants[group_id])} شخص سجلوا حتى الآن! من يجرؤ ينافس؟"))

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
                pic  = profile.picture_url or "https://i.imgur.com/SAqlVNr.gif"  # ✅ حذف المسافة
            except:
                name, pic = "عضو مجهول", "https://i.imgur.com/SAqlVNr.gif"  # ✅ حذف المسافة
            role = random.choice(ROLES)
            user_roles[uid] = role
            send_role_card(event.reply_token, name, pic, role)
            return

    # ====================== لعبة الجائزة السرية ======================

    # 🎁 بدء لعبة الجائزة السرية (Admin فقط)
    if text.lower() == ".sg" and group_id and uid == ADMIN_USER_ID:
        secret_game_active[group_id] = True
        secret_participants[group_id] = []
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text="🎁 بدأت لعبة الجائزة السرية! اكتب `.sr` لتسجيل اسمك."))
        return

    # 📝 تسجيل في الجائزة السرية
    if text.lower() == ".sr" and group_id:
        if not secret_game_active.get(group_id, False):
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="❌ اللعبة مغلقة حاليًا."))
            return

        try:
            profile = line_bot_api.get_profile(uid)
            name = profile.display_name
        except:
            name = "عضو مجهول"

        if name in secret_participants.get(group_id, []):
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="✅ أنت مسجل مسبقًا!"))
            return

        secret_participants[group_id].append(name)
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text=f"✅ تم تسجيلك: {name} 🎁"))
        return

    # 📋 عرض المشاركين في الجائزة السرية
    if text.lower() == ".srr" and group_id:
        participants = secret_participants.get(group_id, [])
        if not participants:
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text=".FileNotFoundException: الملف غير موجود 😏"))
            return
        message = "📋 المشاركين:\n" + "\n".join(f"• {name}" for name in participants)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message))
        return

    # 🏆 اختيار الفائز في الجائزة السرية
    if text.lower() == ".ss" and group_id:
        participants = secret_participants.get(group_id, [])
        if not participants:
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text=".FileNotFoundException: الملف غير موجود 😏"))
            return

        winner = random.choice(participants)
        prize = random.choice(prizes_list)
        donor = random.choice(donors_list)

        message = f"🎉 مبروك يا {winner}! لقد فزت بـ {prize} مقدمة من {donor} 🎁👑"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message))

        # إعادة ضبط اللعبة
        secret_game_active.pop(group_id, None)
        secret_participants.pop(group_id, None)
        return

    # ====================== مراقبة الدخول ======================

    # ✅ تفعيل المراقبة (Admin فقط)
    if text.lower() == ".l" and group_id and uid == ADMIN_USER_ID:
        lurking_active[group_id] = True
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text="✅ بدأت مراقبة دخول الأعضاء!"))
        return

    # ✅ إيقاف المراقبة (Admin فقط)
    if text.lower() == ".sl" and group_id and uid == ADMIN_USER_ID:
        lurking_active[group_id] = False
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text="❌ توقفت مراقبة دخول الأعضاء."))
        return

    # ✅ عرض قائمة المراقبين
    if text.lower() == ".lurkers" and group_id:
        lurkers = lurkers_list.get(group_id, [])
        if not lurkers:
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="❌ مافيه أحد مسجل!"))
            return
        message = "🕵️‍♂️ Lurkers:\n" + "\n".join(f"{i+1}. {name}" for i, name in enumerate(lurkers))
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text=message))
        return

# ============= نقطة التشغيل =============
if __name__ == "__main__":
    app.run(port=5000, host="0.0.0.0")
