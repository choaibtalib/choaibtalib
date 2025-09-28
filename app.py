# -*- coding: utf-8 -*-
import os
import random
import traceback
from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import (
    MessageEvent, TextMessage, FlexSendMessage, TextSendMessage,
    FollowEvent, MemberJoinedEvent, MemberLeftEvent
)
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import ConflictingIdError
import atexit
import logging
from datetime import datetime
import pytz

# ----------- تهيئة السجل -----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ----------- تطبيق Flask -----------
app = Flask(__name__)

# ===== متغيرات البيئة (لم يتم تغيير أسماء المتغيرات) =====
CHANNEL_ACCESS_TOKEN = os.environ.get("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET       = os.environ.get("CHANNEL_SECRET")
ADMIN_USER_ID        = os.environ.get("ADMIN_USER_ID")

# اختياري: رمز سري لمسار تشغيل التذكير عن طريق HTTP (لو حبيت تضيف للـRender cron)
# إذا لم تقم بتعيين INTERNAL_TRIGGER_TOKEN فالمسار سيفتح بدون مصادقة.
INTERNAL_TRIGGER_TOKEN = os.environ.get("INTERNAL_TRIGGER_TOKEN")

# اختر المنطقة الزمنية المناسبة (افتراضي Africa/Algiers كما طلبت في إعداداتك)
SCHEDULER_TIMEZONE = os.environ.get("SCHEDULER_TIMEZONE", "Africa/Algiers")

# تحقق من متغيرات هامة
if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    logger.warning("تحذير: CHANNEL_ACCESS_TOKEN أو CHANNEL_SECRET غير معرّفة - تأكد من إعداد متغيرات البيئة.")

# ===== تهيئة LINE SDK =====
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler      = WebhookHandler(CHANNEL_SECRET)

# ===== قائمة المناصب المضحكة (لم أغيرها) =====
ROLES = [
    "👑 زعيم المطبخ", "🌾 مزارع البطاطس", "🍳 طباخ فطير الصبح", "🐒 مدير القرود",
    "🍳 اكل الوجبات الشره ", "🪄 ساحر التلفاز", "⚔️ قائد السجاد الطائر", "🧩 محلل الألغاز المزدحمة",
    "🚀 حارس الفضاء الخارجي", "🎨 رسام الوجوه الغريبة", "💎 حارس الخواتم المصنوعة في الصين", "🥁 عازف الطبول الصراخية",
    "🌋 مراقب البراكين النائمة", "🐴 فارس السرج البلاستيكي", "🥳 منظم أعياد الميلاد المتعبة", "🧙 ساحر الظلال المتدلية",
    "🍞 خباز الكعك المتفجر", "🐘 مروض الفيلة الصغيرة", "🕰️ حارس الزمن المكسور", "📖 راوي القصص المللقة",
    "🥷 نينجا الظلال الملونة", "💡 مخترع المصباح الغازي", "🎯 بطل النبال المفقود", "🧼 صانع الصابون العطري",
    " violin عازف الكمان المكسور", "🌌 عالم النجوم المغمورة", "🍯 صانع العسل الحامض", "🧵 خياط الستائر",
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
    "🎭 ممثل الغضب المفقود", "👑 زعيم البكاء المبالغ فيه", "🎭 ممثل الغباء المستغبى", "👑 ملك الغباء الراقي",
    "🎭 ممثل الحب المفقود", "👑 زعيم العشق المتعب", "🎭 ممثل الحقد المفقود", "👑 ملك الكراهية المبالغ فيها",
    "🎭 ممثل الغيرة المتخيلة", "👑 زعيم الحسد المفقود", "🎭 ممثل الكآبة المبالغ فيها", "👑 ملك الفرح المفقود"
]

# ===== متغيرات حالة البوت في الذاكرة (كما في كودك) =====
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
    "فازلين", "سارة", "الامريكي", "حنين", "رونالدو", "نورا", "أريام", "منى", "ليلى", "عمر الكرد",
    "مريم", "قلق", "مهجد", "معطاب", "نور", "رانيا", "نينجا", "ابو ليلى لي أكلها الذئب", "الخديوي", "قطام", "عود" ,"هبايب", "الاسطوره", "عاشور", "دندان"
]
prizes_list = [
    "سيارة ورديه للحلوات", "رحلة إلى الغابة مع التماسيح", "جهاز آيفون الترا22", "جهاز لابتوب من تايلند", "بطاطس المراعي",
    "جهاز تابلت", "مساج ", "كأس ذهبي", "ساعة فاخرة", "ثلاثيني",
    "كرسي طويل", "حقيبة من جاد الكوالا", "عندو كهربائي ", "رحلة إلى بيت جدة ليلى", "مقص فاخر",
    "برج الاسد", "علبه فازلين للبشره", "سروال قصير", "خوخه ", "كيكه  "
]

# ----------- دوال المساعدة الخاصة بالـFlex (لم أغيّر التصميم) -----------
def send_role_card(reply_token, name, profile_pic, role):
    bg_url = "https://i.imgur.com/SAqlVNr.gif"

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
    try:
        line_bot_api.reply_message(reply_token, flex)
    except LineBotApiError as e:
        logger.error("Failed to send role card: %s", e)
        logger.debug(traceback.format_exc())

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
    try:
        line_bot_api.reply_message(reply_token, flex)
    except LineBotApiError as e:
        logger.error("Failed to send admin mention card: %s", e)
        logger.debug(traceback.format_exc())

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
                        "url": "https://i.imgur.com/SAqlVNr.gif",
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
                                "color": "#000000",
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
    try:
        line_bot_api.reply_message(reply_token, flex)
    except LineBotApiError as e:
        logger.error("Failed to send raffle card: %s", e)
        logger.debug(traceback.format_exc())

# ============= دالة إرسال تذكير الصلاة على النبي ﷺ ============
def send_prayer_reminder():
    """ترسل رسالة تذكير إلى كل المجموعات في known_groups.
       يُنادى عليها داخليًا من الجدولة أو من مسار HTTP /run_prayer_reminder
    """
    if not known_groups:
        logger.info("لا توجد مجموعات مسجلة لإرسال التذكير. (known_groups فارغة)")
        # كخيار بديل: لو أردت إرسال broadcast عندما لا توجد مجموعات:
        # try:
        #     line_bot_api.broadcast(TextSendMessage(text="📿 ..."))
        # except Exception as e:
        #     logger.error("Broadcast failed: %s", e)
        return {"status": "no_groups"}

    text = "📿 اللهم صلِّ على محمد 🌹\nاللهم صلِّ وسلم وبارك على نبينا محمد ﷺ\n\n⏰ تذكير من بوت المجموعة"
    message = TextSendMessage(text=text)

    results = {"sent": [], "failed": []}
    for group_id in list(known_groups):
        try:
            line_bot_api.push_message(group_id, message)
            logger.info("تم إرسال تذكير الصلاة على النبي إلى المجموعة: %s", group_id)
            results["sent"].append(group_id)
        except LineBotApiError as e:
            logger.error("فشل إرسال التذكير إلى %s : %s", group_id, e)
            logger.debug(traceback.format_exc())
            results["failed"].append({"group_id": group_id, "error": str(e)})
        except Exception as e:
            logger.error("خطأ غير متوقع عند إرسال التذكير إلى %s : %s", group_id, e)
            logger.debug(traceback.format_exc())
            results["failed"].append({"group_id": group_id, "error": str(e)})

    return results

# ============= إعداد الجدولة باستخدام APScheduler ============
scheduler = BackgroundScheduler(timezone=SCHEDULER_TIMEZONE)

def start_scheduler():
    try:
        # نجرب إضافة مهمة واحدة بمعرف ثابت لتجنب إضافة مكررة
        scheduler.add_job(send_prayer_reminder, 'interval', hours=1, id="prayer_reminder_hourly", replace_existing=True)
        scheduler.start()
        logger.info("Scheduler started (timezone=%s).", SCHEDULER_TIMEZONE)
    except ConflictingIdError:
        logger.warning("Job with same id already exists.")
    except Exception as e:
        logger.error("Failed to start scheduler: %s", e)
        logger.debug(traceback.format_exc())

# تأكد من إيقاف scheduler عند انتهاء التطبيق
atexit.register(lambda: scheduler.shutdown(wait=False))

# محاولة تشغيل الـ scheduler عند تحميل الموديل (لن يعمل إن نام السيرفر — لذلك أضفنا مسار HTTP للـcron)
try:
    start_scheduler()
except Exception as e:
    logger.error("Error starting scheduler on import: %s", e)

# ============= معالجة دخول البوت للمجموعة ============
@handler.add(FollowEvent)
def handle_follow(event):
    source = event.source
    # عند إضافته كمستخدم أو كمجموعة
    try:
        if hasattr(source, 'group_id') and source.group_id:
            known_groups.add(source.group_id)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="شكرًا على الإضافة 🎉👑"))
    except Exception as e:
        logger.error("handle_follow error: %s", e)
        logger.debug(traceback.format_exc())

# ============= معالجة دخول عضو جديد ============
@handler.add(MemberJoinedEvent)
def handle_member_joined(event):
    for member in event.joined.members:
        try:
            profile = line_bot_api.get_profile(member.user_id)
            name = profile.display_name
        except Exception:
            name = "عضو جديد"
        try:
            line_bot_api.push_message(event.source.group_id, TextSendMessage(text=f"مرحبًا {name} 🎊👑"))
            # تأكد من تسجيل الـ group id
            if hasattr(event.source, 'group_id') and event.source.group_id:
                known_groups.add(event.source.group_id)
        except Exception as e:
            logger.error("Error sending welcome message: %s", e)
            logger.debug(traceback.format_exc())

# ============= معالجة خروج عضو ============
@handler.add(MemberLeftEvent)
def handle_member_left(event):
    for member in event.left.members:
        try:
            profile = line_bot_api.get_profile(member.user_id)
            name = profile.display_name
        except Exception:
            name = "عضو"
        try:
            line_bot_api.push_message(event.source.group_id, TextSendMessage(text=f"وداعًا {name} 😢👑"))
        except Exception as e:
            logger.error("Error sending left message: %s", e)
            logger.debug(traceback.format_exc())

# ============= Webhook نقطة النهاية من LINE ============
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    logger.info("Request body: %s", body[:500])
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.warning("Invalid signature.")
        abort(400)
    except Exception as e:
        logger.error("Error handling webhook: %s", e)
        logger.debug(traceback.format_exc())
        # لا نعيد 500 لأن LINE يتوقع 200/400 بشكل نموذجي
        abort(500)
    return 'OK'

# ============= نقطة تشغيل التذكير عبر HTTP (لإستدعاء Cron خارجي مثل Render Cron Jobs) ============
@app.route("/run_prayer_reminder", methods=['GET', 'POST'])
def http_run_prayer_reminder():
    # حماية اختيارية:
    token = request.headers.get("X-Internal-Token") or request.args.get("token")
    if INTERNAL_TRIGGER_TOKEN:
        if not token or token != INTERNAL_TRIGGER_TOKEN:
            logger.warning("Unauthorized attempt to trigger reminder via HTTP.")
            return jsonify({"error": "Unauthorized"}), 401

    logger.info("HTTP trigger received for prayer reminder (by %s)", request.remote_addr)
    result = send_prayer_reminder()
    return jsonify({"status": "ok", "result": result})

# ============= معالجة الرسائل ============
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
            mentioner_pic = profile.picture_url or "https://i.imgur.com/SAqlVNr.gif"
        except Exception:
            mentioner_name, mentioner_pic = "عضو مجهول", "https://i.imgur.com/SAqlVNr.gif"
        send_admin_mention_card(event.reply_token, mentioner_name, mentioner_pic)
        return

    # الأوامر الأخرى — بدون أي تغيير لكن مع بعض الحماية/تحسينات الأخطاء
    try:
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

        if text.lower() == ".leave" and uid == ADMIN_USER_ID:
            if group_id:
                line_bot_api.reply_message(event.reply_token,
                    TextSendMessage(text="وداعًا 👋👑"))
                line_bot_api.leave_group(group_id)
                # إزالة من known_groups عند مغادرة البوت
                known_groups.discard(group_id)
                return
            else:
                line_bot_api.reply_message(event.reply_token,
                    TextSendMessage(text="❌ هذا الأمر فقط للمجموعات."))
                return

        if text.lower() == ".r" and group_id and uid == ADMIN_USER_ID:
            raffle_active[group_id] = True
            raffle_participants[group_id] = set()
            send_raffle_card(event.reply_token, group_id)
            # تأكد من تسجيل المجموعه
            known_groups.add(group_id)
            return

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
            raffle_active.pop(group_id, None)
            raffle_participants.pop(group_id, None)
            return

        if text == "سجلني" and group_id:
            if not raffle_active.get(group_id, False):
                line_bot_api.reply_message(event.reply_token,
                    TextSendMessage(text="❌ التسجيل مغلق حاليًا. انتظر الجولة القادمة!"))
                return

            if uid in raffle_participants.get(group_id, set()):
                line_bot_api.reply_message(event.reply_token,
                    TextSendMessage(text="✅ أنت مسجل مسبقًا! ما يلزم تسجيل مرتين 😊"))
                return

            try:
                profile = line_bot_api.get_profile(uid)
                name = profile.display_name
            except Exception:
                name = "عضو مجهول"

            raffle_participants.setdefault(group_id, set()).add(uid)
            raffle_names[uid] = name
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text=f"✅ تم تسجيلك: {name} 🎯"))

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
                    pic  = profile.picture_url or "https://i.imgur.com/SAqlVNr.gif"
                except Exception:
                    name, pic = "عضو مجهول", "https://i.imgur.com/SAqlVNr.gif"
                role = random.choice(ROLES)
                user_roles[uid] = role
                send_role_card(event.reply_token, name, pic, role)
                return

        # ===== لعبة الجائزة السرية =====
        if text.lower() == ".sg" and group_id and uid == ADMIN_USER_ID:
            secret_game_active[group_id] = True
            secret_participants[group_id] = []
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="🎁 بدأت لعبة الجائزة السرية! اكتب `.sr` لتسجيل اسمك."))
            return

        if text.lower() == ".sr" and group_id:
            if not secret_game_active.get(group_id, False):
                line_bot_api.reply_message(event.reply_token,
                    TextSendMessage(text="❌ اللعبة مغلقة حاليًا."))
                return

            try:
                profile = line_bot_api.get_profile(uid)
                name = profile.display_name
            except Exception:
                name = "عضو مجهول"

            if name in secret_participants.get(group_id, []):
                line_bot_api.reply_message(event.reply_token,
                    TextSendMessage(text="✅ أنت مسجل مسبقًا!"))
                return

            secret_participants[group_id].append(name)
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text=f"✅ تم تسجيلك: {name} 🎁"))
            return

        if text.lower() == ".srr" and group_id:
            participants = secret_participants.get(group_id, [])
            if not participants:
                line_bot_api.reply_message(event.reply_token,
                    TextSendMessage(text=".FileNotFoundException: الملف غير موجود 😏"))
                return
            message = "📋 المشاركين:\n" + "\n".join(f"• {name}" for name in participants)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message))
            return

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

            secret_game_active.pop(group_id, None)
            secret_participants.pop(group_id, None)
            return

    except LineBotApiError as e:
        logger.error("LINE API error in message handler: %s", e)
        logger.debug(traceback.format_exc())
        try:
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="حدث خطأ في تنفيذ الأمر. الرجاء المحاولة لاحقًا."))
        except Exception:
            pass
    except Exception as e:
        logger.error("Unexpected error in message handler: %s", e)
        logger.debug(traceback.format_exc())
        try:
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="خطأ غير متوقع. تواصل مع الأدمن."))
        except Exception:
            pass

# ============= نقطة التشغيل المحلية (مفيدة للتشغيل المباشر) ============
if __name__ == "__main__":
    # تشغيل التطبيق محلياً باستخدام Flask (مناسب للاختبار)
    port = int(os.environ.get("PORT", 5000))
    logger.info("Starting Flask app on 0.0.0.0:%s", port)
    # scheduler قد تم تشغيله عند الاستيراد، لكن إن لم يكن قيد التشغيل نحاول تشغيله مرة أخرى
    if not scheduler.running:
        try:
            start_scheduler()
        except Exception as e:
            logger.error("Error starting scheduler at __main__: %s", e)
    app.run(host="0.0.0.0", port=port)
