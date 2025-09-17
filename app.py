import os
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    PostbackEvent, TemplateSendMessage, ButtonsTemplate, 
    PostbackAction, QuickReply, QuickReplyButton
)

# --- إعدادات التسجيل ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- متغيرات البيئة ---
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")
ADMIN_USER_ID = os.getenv("USER_ID")

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    raise Exception("يرجى ضبط متغيرات البيئة CHANNEL_ACCESS_TOKEN و CHANNEL_SECRET")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# --- بيانات المجموعات ---
DATA_FILE = "group_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"خطأ في تحميل البيانات: {e}")
            return {}
    return {}

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"خطأ في حفظ البيانات: {e}")

group_data = load_data()

# === نظام التذكير بالصلاة على النبي ===
def start_prayer_reminder():
    """بدء نظام التذكير بالصلاة على النبي كل نصف ساعة"""
    def reminder_loop():
        last_reminder_hour = -1
        while True:
            try:
                now = datetime.now()
                current_minute = now.minute
                current_hour = now.hour
                
                # التذكير كل 30 دقيقة (عند الدقيقة 00 و 30)
                if current_minute in [0, 30] and now.second == 0:
                    # منع التكرار في نفس الساعة والدقيقة
                    if last_reminder_hour != current_hour or (current_minute == 30 and last_reminder_hour != current_hour):
                        prayer_message = "🕌 *تذكير:* صلوا على النبي محمد صلى الله عليه وسلم\n\n" \
                                        "ﷺ اللهم صل على محمد وعلى آل محمد كما صليت على إبراهيم وعلى آل إبراهيم " \
                                        "إنك حميد مجيد، اللهم بارك على محمد وعلى آل محمد كما باركت على إبراهيم " \
                                        "وعلى آل إبراهيم إنك حميد مجيد ﷺ"
                        
                        # إرسال التذكير لجميع المجموعات
                        for group_id in list(group_data.keys()):
                            try:
                                if group_data[group_id]["settings"]["prayer_reminders"]:
                                    line_bot_api.push_message(group_id, TextSendMessage(text=prayer_message))
                                    logger.info(f"تم إرسال تذكير الصلاة على النبي للمجموعة {group_id}")
                            except Exception as e:
                                logger.error(f"خطأ في إرسال التذكير للمجموعة {group_id}: {e}")
                        
                        last_reminder_hour = current_hour
                
                time.sleep(1)  # التحقق كل ثانية
            except Exception as e:
                logger.error(f"خطأ في حلقة التذكير: {e}")
                time.sleep(60)  # الانتظار دقيقة قبل إعادة المحاولة
    
    # بدء التذكير في خيط منفصل
    thread = threading.Thread(target=reminder_loop, daemon=True)
    thread.start()
    logger.info("نظام التذكير بالصلاة على النبي مفعل")

# === نظام التتبع المتقدم ===
def init_group(group_id):
    if group_id not in group_data:
        group_data[group_id] = {
            "admins": [ADMIN_USER_ID] if ADMIN_USER_ID else [],
            "members": {},
            "war": {
                "active": False,
                "participants": [],        # مشاركون ومستعدون
                "castle_holders": [],      # مسلمو القلاع
                "reserve_players": [],     # لاعبون احتياطيون
                "call_start_time": None,
                "last_update_message_id": None
            },
            "settings": {
                "auto_end_call_hours": 2,
                "notify_non_responders": True,
                "prayer_reminders": True  # مفعل افتراضياً
            },
            "created_at": datetime.now().isoformat()
        }
        save_data(group_data)

def safe_get_profile(group_id, user_id):
    try:
        profile = line_bot_api.get_group_member_profile(group_id, user_id)
        return profile.display_name
    except Exception as e:
        logger.error(f"خطأ في الحصول على الملف الشخصي: {e}")
        return "مجهول"

def is_admin(group_id, user_id):
    return user_id in group_data.get(group_id, {}).get("admins", [])

def create_war_poll_message():
    """إنشاء رسالة استفتاء الحرب بشكل جميل"""
    return TemplateSendMessage(
        alt_text="⚔️ استفتاء الحرب - تحديث حي",
        template=ButtonsTemplate(
            title="⚔️ استفتاء الحرب",
            text="اختر حالتك في المعركة القادمة:",
            actions=[
                PostbackAction(label="✅ مشارك ومستعد", data="war_participate"),
                PostbackAction(label="🏰 أسلم قلعتي", data="war_surrender"),
                PostbackAction(label="🛡️ لاعب احتياطي", data="war_reserve"),
                PostbackAction(label="📊 عرض النتائج", data="war_show_results")
            ]
        )
    )

def send_war_update(group_id):
    """إرسال تحديث النتائج بعد كل اختيار"""
    war = group_data[group_id]["war"]
    
    # إنشاء تقرير النتائج المحدث
    participants = [safe_get_profile(group_id, uid) for uid in war["participants"]]
    castles = [safe_get_profile(group_id, uid) for uid in war["castle_holders"]]
    reserves = [safe_get_profile(group_id, uid) for uid in war["reserve_players"]]
    
    total_members = len(group_data[group_id]["members"])
    total_responded = len(participants) + len(castles) + len(reserves)
    
    # الرسالة الأساسية
    message = TextSendMessage(
        text=f"⚔️ تحديث حي لاستفتاء الحرب ⚔️\n\n"
             f"✅ المشاركون: {len(participants)}\n"
             f"🏰 المسلمون: {len(castles)}\n"
             f"🛡️ الاحتياط: {len(reserves)}\n"
             f"📊 الاستجابة: {total_responded}/{total_members}\n\n"
             f"اختر حالتك من الأزرار أدناه:",
        quick_reply=QuickReply(items=[
            QuickReplyButton(action=PostbackAction(label="✅ مشارك", data="war_participate")),
            QuickReplyButton(action=PostbackAction(label="🏰 أسلم قلعتي", data="war_surrender")),
            QuickReplyButton(action=PostbackAction(label="🛡️ احتياطي", data="war_reserve")),
            QuickReplyButton(action=PostbackAction(label="📊 النتائج", data="war_show_results"))
        ])
    )
    
    # إرسال الرسالة الجديدة وحفظ معرفها
    result = line_bot_api.push_message(group_id, message)
    war["last_update_message_id"] = result.message_id
    save_data(group_data)

def start_war_poll(group_id, reply_token=None):
    """بدء استفتاء الحرب"""
    init_group(group_id)
    war = group_data[group_id]["war"]
    
    # إعادة تعيين البيانات
    war["active"] = True
    war["participants"] = []
    war["castle_holders"] = []
    war["reserve_players"] = []
    war["call_start_time"] = datetime.now().isoformat()
    war["last_update_message_id"] = None
    
    # إرسال رسالة الاستفتاء الأولى
    poll_message = create_war_poll_message()
    
    if reply_token:
        line_bot_api.reply_message(reply_token, poll_message)
    else:
        result = line_bot_api.push_message(group_id, poll_message)
        war["last_update_message_id"] = result.message_id
    
    save_data(group_data)
    return True

def process_war_response(group_id, user_id, response_type):
    """معالجة ردود الأعضاء على الاستفتاء"""
    war = group_data[group_id]["war"]
    user_name = safe_get_profile(group_id, user_id)
    
    # إزالة المستخدم من جميع القوائم أولاً
    if user_id in war["participants"]:
        war["participants"].remove(user_id)
    if user_id in war["castle_holders"]:
        war["castle_holders"].remove(user_id)
    if user_id in war["reserve_players"]:
        war["reserve_players"].remove(user_id)
    
    # إضافة المستخدم إلى القائمة المناسبة
    response_text = ""
    if response_type == "participate":
        war["participants"].append(user_id)
        response_text = f"✅ {user_name} تم تسجيلك كمشارك في المعركة!"
    elif response_type == "surrender":
        war["castle_holders"].append(user_id)
        response_text = f"🏰 {user_name} تم تسجيلك كمسلم للقلعة!"
    elif response_type == "reserve":
        war["reserve_players"].append(user_id)
        response_text = f"🛡️ {user_name} تم تسجيلك كلاعب احتياطي!"
    
    save_data(group_data)
    
    # إرسال تأكيد للمستخدم
    try:
        line_bot_api.push_message(user_id, TextSendMessage(text=response_text))
    except Exception as e:
        logger.error(f"لا يمكن إرسال رسالة للمستخدم {user_id}: {e}")
    
    # إرسال رسالة تأكيد للمجموعة مع اسم المستخدم
    group_message = f"{user_name} قام بتحديث اختياره!\n{response_text}"
    line_bot_api.push_message(group_id, TextSendMessage(text=group_message))
    
    # إرسال تحديث النتائج للمجموعة (يعيد الاستفتاء)
    send_war_update(group_id)
    
    return True

def show_war_results(group_id, reply_token=None, detailed=False):
    """عرض نتائج الاستفتاء"""
    war = group_data[group_id]["war"]
    
    participants = [safe_get_profile(group_id, uid) for uid in war["participants"]]
    castles = [safe_get_profile(group_id, uid) for uid in war["castle_holders"]]
    reserves = [safe_get_profile(group_id, uid) for uid in war["reserve_players"]]
    
    total_members = len(group_data[group_id]["members"])
    total_responded = len(participants) + len(castles) + len(reserves)
    
    # إنشاء التقرير
    report = "📊 تقرير استفتاء الحرب 📊\n\n"
    report += f"⏰ وقت البدء: {datetime.fromisoformat(war['call_start_time']).strftime('%H:%M:%S')}\n"
    report += f"👥 إجمالي الأعضاء: {total_members}\n"
    report += f"📊 المستجيبون: {total_responded}\n\n"
    
    report += "✅ المشاركون في المعركة:\n"
    if participants:
        for i, member in enumerate(participants, 1):
            report += f"{i}. {member}\n"
    else:
        report += "⚠️ لا يوجد مشاركون\n"
    
    report += "\n🏰 مسلمو القلاع:\n"
    if castles:
        for i, member in enumerate(castles, 1):
            report += f"{i}. {member}\n"
    else:
        report += "⚠️ لا يوجد مسلمون\n"
    
    report += "\n🛡️ اللاعبون الاحتياطيون:\n"
    if reserves:
        for i, member in enumerate(reserves, 1):
            report += f"{i}. {member}\n"
    else:
        report += "⚠️ لا يوجد احتياطيون\n"
    
    report += f"\n📈 نسبة الاستجابة: {(total_responded/total_members*100):.1f}%"
    
    if reply_token:
        line_bot_api.reply_message(reply_token, TextSendMessage(text=report))
    else:
        line_bot_api.push_message(group_id, TextSendMessage(text=report))

def end_war_poll(group_id):
    """إنهاء استفتاء الحرب"""
    war = group_data[group_id]["war"]
    war["active"] = False
    
    # عرض النتائج النهائية
    show_war_results(group_id)
    save_data(group_data)
    return True

def toggle_prayer_reminder(group_id):
    """تبديل حالة التذكير بالصلاة على النبي"""
    current_state = group_data[group_id]["settings"]["prayer_reminders"]
    group_data[group_id]["settings"]["prayer_reminders"] = not current_state
    save_data(group_data)
    
    new_state = group_data[group_id]["settings"]["prayer_reminders"]
    status = "تفعيل" if new_state else "تعطيل"
    return f"✅ تم {status} التذكير بالصلاة على النبي."

# === معالجة الأحداث ===
@handler.add(MessageEvent, message=TextMessage)
def on_message(event):
    if not hasattr(event.source, "group_id"):
        return

    group_id = event.source.group_id
    user_id = event.source.user_id
    text = event.message.text.strip()
    
    init_group(group_id)
    group_data[group_id]["members"][user_id] = safe_get_profile(group_id, user_id)
    save_data(group_data)

    # أوامر الأدمن
    if is_admin(group_id, user_id):
        if text == ".w":
            start_war_poll(group_id, event.reply_token)
        elif text == ".war":
            end_war_poll(group_id)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ تم إنهاء الاستفتاء وعرض النتائج النهائية."))
        elif text == ".ws":
            show_war_results(group_id, event.reply_token, detailed=True)
        elif text == ".s":
            result = toggle_prayer_reminder(group_id)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=result))
        elif text == ".حالة التذكير":
            # أمر جديد للتحقق من حالة التذكير
            current_state = group_data[group_id]["settings"]["prayer_reminders"]
            status = "مفعل" if current_state else "معطل"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"حالة التذكير: {status}"))

@handler.add(PostbackEvent)
def on_postback(event):
    group_id = event.source.group_id
    user_id = event.source.user_id
    data = event.postback.data
    
    if data == "war_participate":
        process_war_response(group_id, user_id, "participate")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ تم تسجيلك كمشارك في المعركة!"))
    elif data == "war_surrender":
        process_war_response(group_id, user_id, "surrender")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🏰 تم تسجيلك كمسلم للقلعة!"))
    elif data == "war_reserve":
        process_war_response(group_id, user_id, "reserve")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🛡️ تم تسجيلك كلاعب احتياطي!"))
    elif data == "war_show_results":
        show_war_results(group_id, event.reply_token)

# === تشغيل السيرفر ===
app = Flask(__name__)

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    except Exception as e:
        logger.error(f"خطأ في معالجة الطلب: {e}")
        abort(500)

    return "OK"

@app.route("/", methods=["GET"])
def home():
    return "✅ البوت المتكامل يعمل بشكل صحيح"

@app.route("/test_reminder", methods=["GET"])
def test_reminder():
    """مسار لاختبار التذكير يدوياً"""
    prayer_message = "🕌 *تذكير اختباري:* صلوا على النبي محمد صلى الله عليه وسلم\n\n" \
                    "ﷺ اللهم صل على محمد وعلى آل محمد كما صليت على إبراهيم وعلى آل إبراهيم " \
                    "إنك حميد مجيد، اللهم بارك على محمد وعلى آل محمد كما باركت على إبراهيم " \
                    "وعلى آل إبراهيم إنك حميد مجيد ﷺ"
    
    for group_id in list(group_data.keys()):
        try:
            if group_data[group_id]["settings"]["prayer_reminders"]:
                line_bot_api.push_message(group_id, TextSendMessage(text=prayer_message))
                logger.info(f"تم إرسال تذكير اختباري للمجموعة {group_id}")
        except Exception as e:
            logger.error(f"خطأ في إرسال التذكير الاختباري للمجموعة {group_id}: {e}")
    
    return "تم إرسال التذكير الاختباري"

if __name__ == "__main__":
    # بدء نظام التذكير بالصلاة على النبي
    start_prayer_reminder()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
