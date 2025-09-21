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
known_groups = set()  # ✅ تخزين معرفات المجموعات اللي دخلها البوت

# ===== متغيرات لعبة القرعة =====
raffle_active = False
raffle_participants = {}  # group_id -> set of user_ids
raffle_names = {}         # user_id -> display_name

# ============= دالة بطاقة المناصب (معدلة - صورة دائرية بتلميع وإطار ذهبي) =============
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
    line_bot_api.reply_message(reply_token, flex)

# ============= دالة بطاقة تسجيل القرعة =============
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
                                "color": "#FFD700",
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
    for member in event.joined.members:
        try:
            profile = line_bot_api.get_profile(member.user_id)
            name = profile.display_name
        except:
            name = "عضو جديد"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"مرحبًا {name} 🎊👑")
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

    # 🎯 لعبة القرعة - بدء التسجيل
    if text.lower() == ".r" and group_id:
        raffle_active = True
        raffle_participants[group_id] = set()
        send_raffle_card(event.reply_token, group_id)
        return

    # 📋 لعبة القرعة - عرض القائمة
    if text.lower() == ".rr" and group_id:
        participants = raffle_participants.get(group_id, set())
        if not participants:
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="📭 مافيه أحد مسجل!"))
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
                TextSendMessage(text="📭 مافيه أحد مسجل!"))
            return
        winner_id = random.choice(list(participants))
        winner_name = raffle_names.get(winner_id, "الفائز المجهول")
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text=f"🎉🎉🎉\nالفائز هو: {winner_name} 🏆👑\nمبروك!"))
        # ✅ إعادة ضبط اللعبة
        raffle_active = False
        raffle_participants.pop(group_id, None)
        return

    # ✅ تسجيل في القرعة
    if text == "سجلني" and raffle_active and group_id:
        try:
            profile = line_bot_api.get_profile(uid)
            name = profile.display_name
        except:
            name = "عضو مجهول"
        raffle_participants.setdefault(group_id, set()).add(uid)
        raffle_names[uid] = name
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text=f"✅ تم تسجيلك: {name}"))
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
