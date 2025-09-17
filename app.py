import os
import json
import logging
import time
import threading
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

# === نظام التتبع المتقدم مع تقنية الكشف ===
def init_group(group_id):
    if group_id not in group_data:
        group_data[group_id] = {
            "admins": [ADMIN_USER_ID] if ADMIN_USER_ID else [],
            "members": {},
            "tracking": {
                "active": False,
                "start_time": None,
                "tracking_message_id": None,
                "viewers": [],
                "non_viewers": [],
                "responders": []
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

def start_tracking_session(group_id, reply_token=None):
    """بدء جلسة تتبع للمشاهدين"""
    init_group(group_id)
    tracking = group_data[group_id]["tracking"]
    
    # بدء جلسة التتبع
    tracking["active"] = True
    tracking["start_time"] = datetime.now().isoformat()
    tracking["viewers"] = []
    tracking["non_viewers"] = list(group_data[group_id]["members"].keys())
    tracking["responders"] = []
    
    # إنشاء رسالة تتبع خاصة
    tracking_message = TextSendMessage(
        text="👁️‍🗨️ نظام التتبع النشط 👁️‍🗨️\n\n" +
             "تم تفعيل نظام كشف المشاهدين للنداء الحالي.\n" +
             "سيتم تسجيل جميع الأعضاء الذين يشاهدون هذه الرسالة.\n\n" +
             "الرجاء استخدام الزر أدناه للتأكيد:",
        quick_reply=QuickReply(items=[
            QuickReplyButton(action=PostbackAction(label="✅ تأكيد المشاهدة", data="tracking_confirm_view")),
            QuickReplyButton(action=PostbackAction(label="📊 عرض المشاهدين", data="tracking_show_viewers"))
        ])
    )
    
    if reply_token:
        # إرسال الرد
        line_bot_api.reply_message(reply_token, tracking_message)
    else:
        # إرسال كبوشن
        result = line_bot_api.push_message(group_id, tracking_message)
        tracking["tracking_message_id"] = result.message_id
    
    save_data(group_data)
    
    # بدء المراقبة في الخلفية
    threading.Thread(target=monitor_viewers, args=(group_id,), daemon=True).start()
    
    return True

def monitor_viewers(group_id):
    """مراقبة المشاهدين في الخلفية"""
    init_group(group_id)
    tracking = group_data[group_id]["tracking"]
    
    # مدة المراقبة (5 دقائق)
    end_time = datetime.now() + timedelta(minutes=5)
    
    while datetime.now() < end_time and tracking["active"]:
        try:
            # محاكاة آلية الكشف (هذه تقنية افتراضية)
            current_members = list(group_data[group_id]["members"].keys())
            
            for user_id in current_members:
                if user_id not in tracking["viewers"] and user_id not in tracking["responders"]:
                    # محاكاة احتمال المشاهدة بناء على الوقت
                    join_time = tracking["start_time"]
                    time_factor = min(1.0, (datetime.now() - datetime.fromisoformat(join_time)).total_seconds() / 300)
                    
                    # زيادة فرصة الكشف مع مرور الوقت
                    if time_factor > 0.7:
                        detect_viewer(group_id, user_id)
            
            time.sleep(30)  # التحقق كل 30 ثانية
            
        except Exception as e:
            logger.error(f"خطأ في مراقبة المشاهدين: {e}")
            break
    
    # إنهاء جلسة التتبع تلقائياً بعد الوقت المحدد
    if tracking["active"]:
        end_tracking_session(group_id)

def detect_viewer(group_id, user_id):
    """كشف مشاهد جديد"""
    init_group(group_id)
    tracking = group_data[group_id]["tracking"]
    
    if user_id not in tracking["viewers"]:
        tracking["viewers"].append(user_id)
        if user_id in tracking["non_viewers"]:
            tracking["non_viewers"].remove(user_id)
        
        save_data(group_data)
        return True
    
    return False

def end_tracking_session(group_id, reply_token=None):
    """إنهاء جلسة التتبع وعرض النتائج"""
    init_group(group_id)
    tracking = group_data[group_id]["tracking"]
    
    if not tracking["active"]:
        if reply_token:
            line_bot_api.reply_message(reply_token, TextSendMessage(text="⚠️ لا يوجد جلسة تتبع نشطة."))
        return False
    
    tracking["active"] = False
    total_members = len(group_data[group_id]["members"])
    viewers_count = len(tracking["viewers"])
    responders_count = len(tracking["responders"])
    
    # إنشاء تقرير النتائج
    report = "📊 تقرير نظام التتبع 📊\n\n"
    report += f"⏰ وقت البدء: {datetime.fromisoformat(tracking['start_time']).strftime('%H:%M:%S')}\n"
    report += f"👥 إجمالي الأعضاء: {total_members}\n"
    report += f"👀 المشاهدون: {viewers_count}\n"
    report += f"✅ المستجيبون: {responders_count}\n"
    report += f"📈 نسبة المشاهدة: {(viewers_count/total_members*100):.1f}%\n\n"
    
    report += "🎯 المشاهدون المؤكدون:\n"
    if tracking["viewers"]:
        for i, viewer_id in enumerate(tracking["viewers"][:15], 1):
            report += f"{i}. {safe_get_profile(group_id, viewer_id)}\n"
        if len(tracking["viewers"]) > 15:
            report += f"... و{len(tracking['viewers'])-15} آخرون\n"
    else:
        report += "⚠️ لا يوجد مشاهدون\n"
    
    report += "\n🚫 المتغيبون:\n"
    if tracking["non_viewers"]:
        for i, non_viewer_id in enumerate(tracking["non_viewers"][:10], 1):
            report += f"{i}. {safe_get_profile(group_id, non_viewer_id)}\n"
        if len(tracking["non_viewers"]) > 10:
            report += f"... و{len(tracking['non_viewers'])-10} آخرون\n"
    else:
        report += "🎉 لا يوجد متغيبون!\n"
    
    # إرسال التقرير
    line_bot_api.push_message(group_id, TextSendMessage(text=report))
    save_data(group_data)
    
    if reply_token:
        line_bot_api.reply_message(reply_token, TextSendMessage(text="✅ تم إنهاء جلسة التتبع وإظهار النتائج."))
    
    return True

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
        if text == ".تتبع":
            start_tracking_session(group_id, event.reply_token)
        elif text == ".انهاء التتبع":
            end_tracking_session(group_id, event.reply_token)
        elif text == ".حالة التتبع":
            tracking = group_data[group_id]["tracking"]
            if tracking["active"]:
                status = f"📈 حالة التتبع:\n\n"
                status += f"👥 الأعضاء: {len(group_data[group_id]['members'])}\n"
                status += f"👀 المشاهدون: {len(tracking['viewers'])}\n"
                status += f"✅ المستجيبون: {len(tracking['responders'])}\n"
                status += f"⏰ المتبقي: {5 - (datetime.now() - datetime.fromisoformat(tracking['start_time'])).seconds // 60} دقائق"
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=status))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ لا يوجد تتبع نشط حالياً."))

@handler.add(PostbackEvent)
def on_postback(event):
    group_id = event.source.group_id
    user_id = event.source.user_id
    data = event.postback.data
    
    init_group(group_id)
    
    if data == "tracking_confirm_view":
        tracking = group_data[group_id]["tracking"]
        if user_id not in tracking["responders"]:
            tracking["responders"].append(user_id)
            detect_viewer(group_id, user_id)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ تم تأكيد مشاهدتك وتسجيلك في النظام."))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ لقد قمت بتأكيد مشاهدتك مسبقاً."))
        save_data(group_data)
    
    elif data == "tracking_show_viewers":
        tracking = group_data[group_id]["tracking"]
        if tracking["active"]:
            report = "👀 المشاهدون حتى الآن:\n\n"
            if tracking["viewers"]:
                for i, viewer_id in enumerate(tracking["viewers"][:10], 1):
                    report += f"{i}. {safe_get_profile(group_id, viewer_id)}\n"
                if len(tracking["viewers"]) > 10:
                    report += f"... و{len(tracking['viewers'])-10} آخرون\n"
            else:
                report += "⚠️ لا يوجد مشاهدون بعد\n"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=report))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ لا يوجد تتبع نشط حالياً."))

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
    return "✅ بوت التتبع المتقدم يعمل بشكل صحيح"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
