# -*- coding: utf-8 -*-
import os, random, json, time
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

# ===== مسارات ملفات حفظ البيانات =====
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

def load_json(filename, default):
    try:
        with open(os.path.join(DATA_DIR, filename), 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default

def save_json(filename, obj):
    with open(os.path.join(DATA_DIR, filename), 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False)

# ===== قائمة المناصب المضحكة =====
ROLES = [
    "👑 زعيم المطبخ", "🌾 مزارع البطاطس", "🍳 طباخ فطير الصبح", "🐒 مدير القرود",
    "🕊️ مربي الحمام الزاجل", "🪄 ساحر التلفاز", "⚔️ قائد السجاد الطائر", "🧩 محلل الألغاز المزدحمة",
    "🚀 حارس الفضاء الخارجي", "🎨 رسام الوجوه الغريبة", "💎 حارس الخواتم المصنوعة في الصين", "🥁 عازف الطبول الصراخة",
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
    "🚪 حارس البوابة المغلقة", "🗝️ حارس الأسرار المكشوفة", "💡 عالم الاختراعات الفاشلة", "🎨 مزخرف الجدران المتهاوية",
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

donors_list = [
    "معطاب", "ليلى", "الكايد", "اريام", "قير عادي", "نورا", "قلق", "منى", "هنوف", "الامريكي",
    "مريم", "فازلين", "الدشاش", "اقشر", "نور", "رانيا", "أمينة", "قطام", "مهجد", "الخديوي"
]
prizes_list = [
    "نعله منقطعه", "عفريته", "سروال ابو كرسي", "شم سري", "نير",
    "موز", "بوسه مقدمه من معطاب", "حليب كامل الدسم ", "كراع دجاجه", "رحلة سياحية إلى قريح",
    "كراتين", "شنطة تيلي تابيز", "خوخه ", "برج خليفه", "عصير طماط",
    "رمح طويل", "هدية سرية حسب لي يعطيها ", "اطلب انت يا الفايز ", "تريلة بلور ", "تريلة موارد  "
]

# ========== تحميل بيانات الألعاب عند البدء ==========
game_active         = load_json("game_active.json", False)
user_roles          = load_json("user_roles.json", {})
known_groups        = set(load_json("known_groups.json", []))
raffle_active       = load_json("raffle_active.json", {})
raffle_participants = load_json("raffle_participants.json", {})
raffle_names        = load_json("raffle_names.json", {})
secret_game_active  = load_json("secret_game_active.json", {})
secret_participants = load_json("secret_participants.json", {})
lurking_active      = load_json("lurking_active.json", {})
lurkers_list        = load_json("lurkers_list.json", {})
war_active          = load_json("war_active.json", {})
war_participants    = load_json("war_participants.json", {})
war_absentees       = load_json("war_absentees.json", {})
war_names           = load_json("war_names.json", {})

# ===== حماية من السبام =====
last_register_time = {}

def anti_spam(uid, cooldown=10):
    now = time.time()
    last = last_register_time.get(uid, 0)
    if now - last < cooldown:
        return False
    last_register_time[uid] = now
    return True

def persist_all():
    save_json("game_active.json", game_active)
    save_json("user_roles.json", user_roles)
    save_json("known_groups.json", list(known_groups))
    save_json("raffle_active.json", raffle_active)
    save_json("raffle_participants.json", raffle_participants)
    save_json("raffle_names.json", raffle_names)
    save_json("secret_game_active.json", secret_game_active)
    save_json("secret_participants.json", secret_participants)
    save_json("lurking_active.json", lurking_active)
    save_json("lurkers_list.json", lurkers_list)
    save_json("war_active.json", war_active)
    save_json("war_participants.json", war_participants)
    save_json("war_absentees.json", war_absentees)
    save_json("war_names.json", war_names)

# ============= دوال الرسائل والبطاقات نفس الكود الأصلي =============

# ... ضع هنا جميع دوال البطاقات من النسخة السابقة كما هي بدون تغيير ...

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
atexit.register(lambda: scheduler.shutdown())

# ============= معالجة دخول البوت للمجموعة =============
@handler.add(FollowEvent)
def handle_follow(event):
    source = event.source
    if hasattr(source, 'group_id') and source.group_id:
        known_groups.add(source.group_id)
        persist_all()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="شكرًا على الإضافة 🎉👑")
        )

@handler.add(MemberJoinedEvent)
def handle_member_joined(event):
    source = event.source
    if hasattr(source, 'group_id') and source.group_id:
        group_id = source.group_id
        if not lurking_active.get(group_id, False):
            return
        for member in event.joined.members:
            try:
                profile = line_bot_api.get_profile(member.user_id)
                name = profile.display_name
            except:
                name = "عضو جديد"
            if group_id not in lurkers_list:
                lurkers_list[group_id] = []
            if name not in lurkers_list[group_id]:
                lurkers_list[group_id].append(name)
            persist_all()
            message = f"🚨 {name} متصل الآن! \n✨ انتبهوا، هذي المجموعة صارت أخطر! \n👑 من يجرؤ يتحدى؟"
            line_bot_api.push_message(group_id, TextSendMessage(text=message))

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
    global secret_game_active, secret_participants
    text = event.message.text.strip()
    uid  = event.source.user_id
    source = event.source

    if hasattr(source, 'group_id') and source.group_id:
        group_id = source.group_id
        known_groups.add(group_id)
        persist_all()
    else:
        group_id = None

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

    # ========== أوامر إدارية إضافية ==========
    if text.lower().startswith(".welcome ") and uid == ADMIN_USER_ID:
        custom_msg = text[9:].strip()
        save_json("welcome_message.json", custom_msg)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ تم تغيير رسالة الترحيب!"))
        return

    if text.lower() == ".g" and uid == ADMIN_USER_ID:
        game_active = True
        persist_all()
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text="🎮 تم تشغيل لعبة المناصب للجميع!"))
        return

    if text.lower() == ".stop" and uid == ADMIN_USER_ID:
        game_active = False
        user_roles.clear()
        persist_all()
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text="⏹️ تم إيقاف لعبة المناصب وتجديدها!"))
        return

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

    if text.lower() == ".r" and group_id and uid == ADMIN_USER_ID:
        raffle_active[group_id] = True
        raffle_participants[group_id] = set()
        persist_all()
        send_raffle_card(event.reply_token, group_id)
        return

    if text.lower() == ".rr" and group_id:
        participants = raffle_participants.get(group_id, set())
        if not participants:
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="❌ لا يوجد أي شخص مسجل في القرعة!"))
            return
        names = [raffle_names.get(uid, "عضو مجهول") for uid in participants]
        message = "📋 قائمة المسجلين:\n" + "\n".join(f"• {name}" for name in names)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message))
        return

    if text.lower() == ".rs" and group_id:
        participants = raffle_participants.get(group_id, set())
        if not participants:
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="❌ لا يوجد أي شخص مسجل في القرعة!"))
            return
        winner_id = random.choice(list(participants))
        winner_name = raffle_names.get(winner_id, "الفائز المجهول")
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text=f"🎉🎉🎉\nالفائز هو: {winner_name} 🏆👑\nمبروك!"))
        raffle_active.pop(group_id, None)
        raffle_participants.pop(group_id, None)
        persist_all()
        return

    if text == "سجلني" and group_id:
        if not raffle_active.get(group_id, False):
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="❌ التسجيل مغلق حاليًا. انتظر الجولة القادمة!"))
            return
        if not anti_spam(uid):
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="⏳ يرجى الانتظار قليلاً قبل التسجيل مرة أخرى!"))
            return
        if uid in raffle_participants.get(group_id, set()):
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="✅ أنت مسجل مسبقًا! ما يلزم تسجيل مرتين 😊"))
            return
        try:
            profile = line_bot_api.get_profile(uid)
            name = profile.display_name
        except:
            name = "عضو مجهول"
        raffle_participants.setdefault(group_id, set()).add(uid)
        raffle_names[uid] = name
        persist_all()
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
                TextSendMessage(text=f"تم إعطاؤك منصبك من قبل: {previous_role}"))
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
            persist_all()
            send_role_card(event.reply_token, name, pic, role)
            return

    # ====================== لعبة الجائزة السرية ======================
    if text.lower() == ".sg" and group_id and uid == ADMIN_USER_ID:
        secret_game_active[group_id] = True
        secret_participants[group_id] = []
        persist_all()
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text="🎁 بدأت لعبة الجائزة السرية! اكتب `.sr` لتسجيل اسمك."))
        return

    if text.lower() == ".sr" and group_id:
        if not secret_game_active.get(group_id, False):
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="❌ اللعبة مغلقة حاليًا."))
            return
        if not anti_spam(uid):
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="⏳ يرجى الانتظار قليلاً قبل التسجيل مرة أخرى!"))
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
        persist_all()
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text=f"✅ تم تسجيلك: {name} 🎁"))
        return

    if text.lower() == ".srr" and group_id:
        participants = secret_participants.get(group_id, [])
        if not participants:
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="❌ لا يوجد أي شخص مسجل في الجائزة السرية!"))
            return
        message = "📋 المشاركين:\n" + "\n".join(f"• {name}" for name in participants)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message))
        return

    if text.lower() == ".ss" and group_id:
        participants = secret_participants.get(group_id, [])
        if not participants:
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="❌ لا يوجد أي شخص مسجل في الجائزة السرية!"))
            return
        winner = random.choice(participants)
        prize = random.choice(prizes_list)
        donor = random.choice(donors_list)
        message = f"🎉 مبروك يا {winner}! لقد فزت بـ {prize} مقدمة من {donor} 🎁👑"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message))
        secret_game_active.pop(group_id, None)
        secret_participants.pop(group_id, None)
        persist_all()
        return

    # ====================== مراقبة الدخول ======================
    if text.lower() == ".l" and group_id and uid == ADMIN_USER_ID:
        lurking_active[group_id] = True
        persist_all()
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text="✅ بدأت مراقبة دخول الأعضاء!"))
        return

    if text.lower() == ".sl" and group_id and uid == ADMIN_USER_ID:
        lurking_active[group_id] = False
        persist_all()
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text="❌ توقفت مراقبة دخول الأعضاء."))
        return

    if text.lower() == ".lurkers" and group_id:
        lurkers = lurkers_list.get(group_id, [])
        if not lurkers:
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="❌ لا يوجد أي شخص متابع!"))
            return
        message = "🕵️‍♂️ Lurkers:\n" + "\n".join(f"{i+1}. {name}" for i, name in enumerate(lurkers))
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text=message))
        return

    # ====================== لعبة "تحضير الحرب" ======================
    if text.lower() == ".war" and group_id and uid == ADMIN_USER_ID:
        war_active[group_id] = True
        if group_id not in war_participants:
            war_participants[group_id] = set()
        if group_id not in war_absentees:
            war_absentees[group_id] = set()
        persist_all()
        send_war_card(event.reply_token, group_id)
        return

    if text.lower() == ".war r" and group_id:
        participants = war_participants.get(group_id, set())
        absentees = war_absentees.get(group_id, set())
        msg = "⚔️ تحضير الحرب:\n\n"
        if participants:
            names_part = [war_names.get(u, "مجهول") for u in participants]
            msg += "المشاركين بالحرب ⚔️:\n"
            msg += "\n".join(f"{i+1}- {name}" for i, name in enumerate(names_part))
        else:
            msg += "المشاركين بالحرب ⚔️:\n(لا أحد حتى الآن)"
        msg += "\n\n"
        if absentees:
            names_abs = [war_names.get(u, "مجهول") for u in absentees]
            msg += "الغير مشاركين ويعتذرون عن الحرب (سلمو قلاعهم) 🏰:\n"
            msg += "\n".join(f"{i+1}- {name}" for i, name in enumerate(names_abs))
        else:
            msg += "الغير مشاركين ويعتذرون عن الحرب (سلمو قلاعهم) 🏰:\n(لا أحد حتى الآن)"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
        return

    if text.lower() == ".war s" and group_id and uid == ADMIN_USER_ID:
        war_active[group_id] = False
        war_participants.pop(group_id, None)
        war_absentees.pop(group_id, None)
        persist_all()
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text="🛑 تم إيقاف لعبة الحرب وتجديدها!"))
        return

    if text == "war_join" and group_id:
        if not war_active.get(group_id, False):
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="❌ التسجيل في الحرب مغلق حاليًا."))
            return
        try:
            profile = line_bot_api.get_profile(uid)
            name = profile.display_name
        except:
            name = "عضو مجهول"
        war_names[uid] = name
        if group_id in war_absentees and uid in war_absentees[group_id]:
            war_absentees[group_id].remove(uid)
        war_participants.setdefault(group_id, set()).add(uid)
        persist_all()
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text=f"🛡️ تم تسجيلك كـ **مشارك في الحرب**: {name}!"))
        return

    if text == "war_absent" and group_id:
        if not war_active.get(group_id, False):
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="❌ التسجيل في الحرب مغلق حاليًا."))
            return
        try:
            profile = line_bot_api.get_profile(uid)
            name = profile.display_name
        except:
            name = "عضو مجهول"
        war_names[uid] = name
        if group_id in war_participants and uid in war_participants[group_id]:
            war_participants[group_id].remove(uid)
        war_absentees.setdefault(group_id, set()).add(uid)
        persist_all()
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text=f"🏰 تم تسجيلك كـ **معتذر عن الحرب**: {name}. سلمت قلعتك!"))
        return

if __name__ == "__main__":
    app.run(port=5000, host="0.0.0.0")
