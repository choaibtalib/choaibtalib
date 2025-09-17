import os
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    PostbackEvent, TemplateSendMessage, ButtonsTemplate, 
    PostbackAction, ConfirmTemplate, MessageAction
)

# --- إعدادات التسجيل ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- متغيرات البيئة ---
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")
ADMIN_USER_ID = os.getenv("USER_ID")  # أدمن رئيسي

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    raise Exception("يرجى ضبط متغيرات البيئة CHANNEL_ACCESS_TOKEN و CHANNEL_SECRET")
if not ADMIN_USER_ID:
    logger.warning("USER_ID غير مضبوط، بعض الميزات الإدارية قد لا تعمل")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# --- بيانات المجموعات ---
DATA_FILE = "group_data.json"

def load_data():
    """تحميل البيانات من الملف"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"خطأ في تحميل البيانات: {e}")
            return {}
    return {}

def save_data(data):
    """حفظ البيانات إلى الملف"""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        logger.error(f"خطأ في حفظ البيانات: {e}")

# تحميل البيانات عند البدء
group_data = load_data()

def init_group(group_id):
    """تهيئة بيانات المجموعة إذا لم تكن موجودة"""
    if group_id not in group_data:
        group_data[group_id] = {
            "admins": [ADMIN_USER_ID] if ADMIN_USER_ID else [],
            "members": {},
            "war": {
                "active": False,
                "participants": [],
                "castle_holders": [],
                "start_time": None
            },
            "settings": {
                "auto_reset_lurkers": False,
                "war_timeout_hours": 24
            },
            "created_at": datetime.now().isoformat()
        }
        save_data(group_data)

def is_admin(group_id, user_id):
    """التحقق إذا كان المستخدم أدمن في المجموعة"""
    return user_id in group_data.get(group_id, {}).get("admins", [])

def safe_get_profile(group_id, user_id):
    """الحصول على معلومات العضو بشكل آمن"""
    try:
        profile = line_bot_api.get_group_member_profile(group_id, user_id)
        return profile.display_name
    except Exception as e:
        logger.error(f"خطأ في الحصول على الملف الشخصي: {e}")
        return "مجهول"

def get_user_status(group_id, user_id):
    """الحصول على حالة المستخدم في نظام الحرب"""
    war = group_data[group_id]["war"]
    if user_id in war["participants"]:
        return "مشارك"
    elif user_id in war["castle_holders"]:
        return "مسلم القلعة"
    else:
        return "غير مشارك"

# ==== نظام التتبع الأقصى (Lurkers) المحسن ====
def init_lurkers_system():
    """تهيئة نظام التتبع إذا لم يكن موجودًا"""
    if "global" not in group_data:
        group_data["global"] = {}
    if "lurkers" not in group_data["global"]:
        group_data["global"]["lurkers"] = {}

def mark_lurker(group_id, user_id):
    """تسجيل متتبع جديد"""
    init_lurkers_system()
    lurkers = group_data["global"]["lurkers"]
    group_lurk = lurkers.setdefault(group_id, {
        "readers": [], 
        "last_msg_id": None,
        "last_reset": datetime.now().isoformat()
    })
    if user_id not in group_lurk["readers"]:
        group_lurk["readers"].append(user_id)
    save_data(group_data)

def reset_lurkers(group_id):
    """إعادة تعيين المتتبعين"""
    init_lurkers_system()
    group_data["global"]["lurkers"][group_id] = {
        "readers": [], 
        "last_msg_id": None,
        "last_reset": datetime.now().isoformat()
    }
    save_data(group_data)

def auto_reset_lurkers_if_needed(group_id):
    """إعادة تعيين المتتبعين تلقائيًا إذا انقضى وقت معين"""
    init_lurkers_system()
    lurkers = group_data["global"]["lurkers"]
    
    if group_id not in lurkers:
        return False
        
    last_reset_str = lurkers[group_id].get("last_reset")
    if not last_reset_str:
        return False
        
    try:
        last_reset = datetime.fromisoformat(last_reset_str)
        # إعادة التعيين بعد 24 ساعة
        if datetime.now() - last_reset > timedelta(hours=24):
            reset_lurkers(group_id)
            return True
    except ValueError:
        logger.error("خطأ في تنسيق وقت إعادة التعيين")
    
    return False

def show_lurkers(group_id, reply_token):
    """عرض المتخاذلين"""
    init_lurkers_system()
    lurkers = group_data["global"]["lurkers"]
    readers = lurkers.get(group_id, {}).get("readers", [])
    members = group_data[group_id]["members"].keys()
    laggards = [uid for uid in members if uid not in readers]

    if laggards:
        msg = "👀 المتخاذلون:\n" + "\n".join([f"- {safe_get_profile(group_id,uid)}" for uid in laggards])
    else:
        msg = "🔥 لا يوجد متخاذلين، الكل متابع!"
    line_bot_api.reply_message(reply_token, TextSendMessage(text=msg))

# ==== نظام الحرب المحسن ====
def is_war_expired(group_id):
    """التحقق إذا انتهت مدة الحرب"""
    war = group_data[group_id]["war"]
    if not war["start_time"]:
        return False
        
    try:
        start_time = datetime.fromisoformat(war["start_time"])
        timeout_hours = group_data[group_id]["settings"]["war_timeout_hours"]
        return datetime.now() - start_time > timedelta(hours=timeout_hours)
    except ValueError:
        logger.error("خطأ في تنسيق وقت الحرب")
        return False

def send_war_poll(group_id, reply_token):
    """إرسال استفتاء الحرب"""
    if is_war_expired(group_id):
        line_bot_api.reply_message(
            reply_token, 
            TextSendMessage(text="⏰ انتهت مدة الاستفتاء السابق. يرجى بدء استفتاء جديد.")
        )
        return
        
    buttons = TemplateSendMessage(
        alt_text="⚔️ استفتاء الحرب",
        template=ButtonsTemplate(
            title="⚔️ استفتاء الحرب",
            text="اختر خيارك:",
            actions=[
                PostbackAction(label="⚔️ مشاركة بالحرب", data="war_join"),
                PostbackAction(label="🏰 أسلم قلعتي", data="war_castle"),
                PostbackAction(label="📊 عرض النتائج", data="war_results")
            ]
        )
    )
    line_bot_api.reply_message(reply_token, buttons)

def send_war_results(group_id, user_id=None, reply_token=None, include_laggards=False):
    """إرسال نتائج الحرب بشكل منسق وجميل"""
    war = group_data[group_id]["war"]
    members = list(group_data[group_id]["members"].keys())
    participants = [safe_get_profile(group_id, uid) for uid in war["participants"]]
    castles = [safe_get_profile(group_id, uid) for uid in war["castle_holders"]]
    laggards = [uid for uid in members if uid not in war["participants"] and uid not in war["castle_holders"]]

    # إنشاء رسالة منسقة مع إيموجيات وتنسيق جميل
    msg = "🎯 تحديث حي لاستفتاء الحرب\n"
    msg += "═" * 30 + "\n\n"
    
    # قسم المشاركون
    msg += "🗡️  المشاركون في القتال (" + str(len(participants)) + "):\n"
    if participants:
        for i, p in enumerate(participants):
            msg += f"   {i+1}⃝  {p}\n"
    else:
        msg += "   ⚠️  لا يوجد مشاركون بعد\n"
    msg += "\n"
    
    # قسم المسلمون
    msg += "🏰 المسلمون قلعهم (" + str(len(castles)) + "):\n"
    if castles:
        for i, p in enumerate(castles):
            msg += f"   {i+1}⃝  {p}\n"
    else:
        msg += "   ⚠️  لا يوجد مسلمون بعد\n"
    msg += "\n"
    
    # إضافة معلومات عن المستخدم الحالي إذا كان معطى
    if user_id:
        user_status = get_user_status(group_id, user_id)
        user_name = safe_get_profile(group_id, user_id)
        msg += f"📝 حالتك: {user_status} - {user_name}\n\n"
    
    # قسم الإحصائيات
    total_members = len(members)
    participating = len(participants) + len(castles)
    participation_rate = (participating / total_members * 100) if total_members > 0 else 0
    
    msg += f"📊 الإحصائيات:\n"
    msg += f"   👥 إجمالي الأعضاء: {total_members}\n"
    msg += f"   ✅ المشاركون: {participating}\n"
    msg += f"   📈 نسبة المشاركة: {participation_rate:.1f}%\n\n"
    
    # إضافة المتخاذلين إذا طلب
    if include_laggards and laggards:
        msg += "🐌 المتخاذلون:\n"
        for uid in laggards:
            msg += f"   ❌ {safe_get_profile(group_id, uid)}\n"
    elif include_laggards:
        msg += "🎉 لا يوجد متخاذلين! الكل مشارك!\n"

    # إضافة وقت التحديث
    update_time = datetime.now().strftime("%H:%M:%S")
    msg += f"\n🕒 آخر تحديث: {update_time}"

    # إرسال الرسالة
    if reply_token:
        line_bot_api.reply_message(reply_token, TextSendMessage(text=msg))
    else:
        line_bot_api.push_message(group_id, TextSendMessage(text=msg))

def send_admin_panel(group_id, reply_token):
    """إرسال لوحة تحكم الأدمن"""
    buttons = TemplateSendMessage(
        alt_text="لوحة تحكم الأدمن",
        template=ButtonsTemplate(
            title="لوحة التحكم",
            text="اختر الإعداد الذي تريد تعديله:",
            actions=[
                PostbackAction(label="⚙️ إعدادات التتبع", data="admin_lurkers"),
                PostbackAction(label="⚔️ إعدادات الحرب", data="admin_war"),
                PostbackAction(label="📊 إحصائيات المجموعة", data="admin_stats")
            ]
        )
    )
    line_bot_api.reply_message(reply_token, buttons)

# ==== التعامل مع الرسائل ====
@handler.add(MessageEvent, message=TextMessage)
def on_message(event):
    if not hasattr(event.source, "group_id"):
        # تجاهل الرسائل خارج المجموعات
        return

    group_id = event.source.group_id
    user_id = event.source.user_id
    text = (event.message.text or "").strip()
    
    # تهيئة المجموعة إذا لزم الأمر
    init_group(group_id)
    
    # تحديث معلومات الأعضاء
    group_data[group_id]["members"][user_id] = safe_get_profile(group_id, user_id)
    
    # تسجيل القراءة لكل عضو
    mark_lurker(group_id, user_id)
    
    # التحقق من إعادة التعيين التلقائي إذا كان مفعلًا
    if group_data[group_id]["settings"]["auto_reset_lurkers"]:
        auto_reset_lurkers_if_needed(group_id)
    
    save_data(group_data)

    # أوامر عامة
    if text.lower() == ".مساعد":
        help_msg = """
        🎮 أوامر البوت:
        
        ⚔️ نظام الحرب:
        .war - بدء استفتاء حرب
        .war r - عرض نتائج الحرب
        .war rl - عرض النتائج مع المتخاذلين
        .war s - إيقاف الاستفتاء
        
        👀 نظام التتبع:
        .lurkers - عرض المتخاذلين
        .lurkers reset - إعادة تعيين المتتبعين
        
        ⚙️ للأدمن فقط:
        .admin - لوحة تحكم الأدمن
        """
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=help_msg))
    
    # أوامر الأدمن
    if is_admin(group_id, user_id):
        if text.lower() == ".lurkers":
            show_lurkers(group_id, event.reply_token)
        elif text.lower() == ".lurkers reset":
            reset_lurkers(group_id)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="♻️ تم إعادة تعيين المتتبعين."))
        elif text.lower() == ".admin":
            send_admin_panel(group_id, event.reply_token)

        # أوامر الحرب
        elif text == ".war":
            group_data[group_id]["war"]["active"] = True
            group_data[group_id]["war"]["participants"] = []
            group_data[group_id]["war"]["castle_holders"] = []
            group_data[group_id]["war"]["start_time"] = datetime.now().isoformat()
            save_data(group_data)
            send_war_poll(group_id, event.reply_token)
        elif text == ".war r":
            send_war_results(group_id, user_id, event.reply_token)
        elif text == ".war rl":
            send_war_results(group_id, user_id, event.reply_token, include_laggards=True)
        elif text == ".war s":
            group_data[group_id]["war"]["active"] = False
            group_data[group_id]["war"]["participants"] = []
            group_data[group_id]["war"]["castle_holders"] = []
            group_data[group_id]["war"]["start_time"] = None
            save_data(group_data)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⛔ تم إيقاف الاستفتاء وإفراغ القوائم."))

# ==== التعامل مع الاختيارات ====
@handler.add(PostbackEvent)
def on_postback(event):
    group_id = event.source.group_id
    user_id = event.source.user_id
    data = event.postback.data
    name = safe_get_profile(group_id, user_id)
    
    init_group(group_id)
    
    # معالجة أوامر الأدمن
    if data == "admin_lurkers":
        if not is_admin(group_id, user_id):
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ ليس لديك صلاحية للوصول إلى هذه اللوحة."))
            return
            
        confirm = TemplateSendMessage(
            alt_text="إعدادات التتبع",
            template=ConfirmTemplate(
                text="اختر الإعداد الذي تريد تعديله:",
                actions=[
                    PostbackAction(label="تفعيل إعادة التعيين التلقائي", data="lurkers_auto_on"),
                    PostbackAction(label="تعطيل إعادة التعيين التلقائي", data="lurkers_auto_off")
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, confirm)
        
    elif data == "lurkers_auto_on":
        group_data[group_id]["settings"]["auto_reset_lurkers"] = True
        save_data(group_data)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ تم تفعيل إعادة التعيين التلقائي للمتتبعين."))
        
    elif data == "lurkers_auto_off":
        group_data[group_id]["settings"]["auto_reset_lurkers"] = False
        save_data(group_data)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ تم تعطيل إعادة التعيين التلقائي للمتتبعين."))
    
    # معالجة استفتاء الحرب
    elif data.startswith("war_"):
        war = group_data[group_id]["war"]
        
        if not war["active"]:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ الاستفتاء متوقف."))
            return
            
        if is_war_expired(group_id):
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⏰ انتهت مدة هذا الاستفتاء."))
            return

        if data == "war_join":
            if user_id not in war["participants"]:
                war["participants"].append(user_id)
            if user_id in war["castle_holders"]:
                war["castle_holders"].remove(user_id)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"✅ تم تسجيلك كمشارك في الحرب، {name}"))
                
        elif data == "war_castle":
            if user_id not in war["castle_holders"]:
                war["castle_holders"].append(user_id)
            if user_id in war["participants"]:
                war["participants"].remove(user_id)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"✅ تم تسجيلك كمسلم للقلعة، {name}"))
                
        elif data == "war_results":
            send_war_results(group_id, user_id, event.reply_token)
            
        save_data(group_data)
        
        # بعد أي اختيار، نرسل تحديث النتائج للمجموعة (عدا طلب عرض النتائج فقط)
        if data != "war_results":
            send_war_results(group_id, user_id)

# ==== تشغيل السيرفر ====
app = Flask(__name__)

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    
    logger.info("Request received: %s", body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.error("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return "OK"

@app.route("/", methods=["GET"])
def home():
    return "Bot is running!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
