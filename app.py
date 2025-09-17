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
    PostbackAction, ConfirmTemplate, URIAction,
    QuickReply, QuickReplyButton, CarouselTemplate, CarouselColumn
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

# === نظام التتبع المتقدم ===
def init_group(group_id):
    if group_id not in group_data:
        group_data[group_id] = {
            "admins": [ADMIN_USER_ID] if ADMIN_USER_ID else [],
            "members": {},
            "war": {
                "active": False,
                "participants": [],
                "castle_holders": [],
                "call_active": False,
                "call_start_time": None,
                "call_message_id": None,
                "responded_members": [],
                "pending_members": []
            },
            "settings": {
                "auto_end_call_hours": 2,
                "notify_non_responders": True
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

# === نظام نداء الحرب ===
def start_war_call(group_id, reply_token=None):
    """بدء نداء الحرب وتتبع المستجيبين"""
    init_group(group_id)
    war = group_data[group_id]["war"]
    
    # بدء النداء
    war["call_active"] = True
    war["call_start_time"] = datetime.now().isoformat()
    war["responded_members"] = []
    war["pending_members"] = list(group_data[group_id]["members"].keys())
    
    # إرسال رسالة النداء
    message = TextSendMessage(
        text="⚔️ نداء حرب ⚔️\n\n" +
             "تم تفعيل نظام التتبع للنداء الحالي.\n" +
             "سيتم تسجيل جميع الأعضاء الذين يشاهدون هذه الرسالة ويقومون بالرد.\n\n" +
             "الرجاء استخدام الأزرار أدناه للرد:",
        quick_reply=QuickReply(items=[
            QuickReplyButton(action=PostbackAction(label="✅ متواجد ومستعد", data="call_response_ready")),
            QuickReplyButton(action=PostbackAction(label="❌ غير متاح", data="call_response_not_available")),
            QuickReplyButton(action=PostbackAction(label="📊 عرض المتواجدين", data="call_show_responders"))
        ])
    )
    
    if reply_token:
        # إذا كان نداء مباشر من أدمن
        line_bot_api.reply_message(reply_token, message)
        # حفظ معرف الرسالة للنداء
        war["call_message_id"] = "direct_call"
    else:
        # إذا كان نداء تلقائي
        result = line_bot_api.push_message(group_id, message)
        war["call_message_id"] = result.message_id
    
    save_data(group_data)
    return True

def process_call_response(group_id, user_id, response_type):
    """معالجة ردود الأعضاء على النداء"""
    if group_id not in group_data or not group_data[group_id]["war"]["call_active"]:
        return False
    
    war = group_data[group_id]["war"]
    user_name = safe_get_profile(group_id, user_id)
    
    # إضافة المستخدم إلى القائمة المناسبة
    if response_type == "ready" and user_id not in war["responded_members"]:
        war["responded_members"].append(user_id)
        response_text = f"✅ تم تسجيل {user_name} كمستعد للمعركة!"
    elif response_type == "not_available" and user_id in war["pending_members"]:
        war["pending_members"].remove(user_id)
        response_text = f"❌ {user_name} غير متاح حالياً."
    else:
        response_text = f"⚠️ {user_name}، لقد قمت بالرد مسبقاً."
    
    # إرسال تأكيد للمستخدم
    try:
        line_bot_api.push_message(user_id, TextSendMessage(text=response_text))
    except Exception as e:
        logger.error(f"لا يمكن إرسال رسالة للمستخدم {user_id}: {e}")
    
    save_data(group_data)
    return True

def get_call_status(group_id, detailed=False):
    """الحصول على حالة النداء الحالي"""
    if group_id not in group_data or not group_data[group_id]["war"]["call_active"]:
        return None
    
    war = group_data[group_id]["war"]
    total_members = len(group_data[group_id]["members"])
    responded = len(war["responded_members"])
    pending = len(war["pending_members"])
    
    status = {
        "total_members": total_members,
        "responded": responded,
        "pending": pending,
        "response_rate": (responded / total_members * 100) if total_members > 0 else 0,
        "start_time": war["call_start_time"]
    }
    
    if detailed:
        status["responded_members"] = [safe_get_profile(group_id, uid) for uid in war["responded_members"]]
        status["pending_members"] = [safe_get_profile(group_id, uid) for uid in war["pending_members"]]
    
    return status

def end_war_call(group_id):
    """إنهاء نداء الحرب وعرض النتائج"""
    if group_id not in group_data or not group_data[group_id]["war"]["call_active"]:
        return False
    
    war = group_data[group_id]["war"]
    war["call_active"] = False
    
    status = get_call_status(group_id, detailed=True)
    
    # إنشاء تقرير النتائج
    report = f"📊 تقرير نداء الحرب 📊\n\n"
    report += f"⏰ مدة النداء: {datetime.fromisoformat(war['call_start_time']).strftime('%Y-%m-%d %H:%M')}\n"
    report += f"👥 إجمالي الأعضاء: {status['total_members']}\n"
    report += f"✅ المستجيبون: {status['responded']}\n"
    report += f"📊 نسبة الاستجابة: {status['response_rate']:.1f}%\n\n"
    
    report += "🎖️ المستعدون للمعركة:\n"
    if status['responded_members']:
        for i, member in enumerate(status['responded_members'], 1):
            report += f"{i}. {member}\n"
    else:
        report += "⚠️ لا يوجد مستعدون\n"
    
    report += "\n👤 المتخاذلون:\n"
    if status['pending_members']:
        for i, member in enumerate(status['pending_members'], 1):
            report += f"{i}. {member}\n"
    else:
        report += "🎉 لا يوجد متخاذلون! الكل مستعد!"
    
    # إرسال التقرير
    line_bot_api.push_message(group_id, TextSendMessage(text=report))
    save_data(group_data)
    
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
        if text == ".نداء":
            start_war_call(group_id, event.reply_token)
        elif text == ".انهاء النداء":
            end_war_call(group_id)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ تم إنهاء النداء وإظهار النتائج."))
        elif text == ".حالة النداء":
            status = get_call_status(group_id, detailed=True)
            if status:
                report = f"📈 حالة النداء الحالي:\n\n"
                report += f"👥 الأعضاء: {status['total_members']}\n"
                report += f"✅ المستجيبون: {status['responded']}\n"
                report += f"⏳ المنتظرون: {status['pending']}\n"
                report += f"📊 النسبة: {status['response_rate']:.1f}%\n"
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=report))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ لا يوجد نداء نشط حالياً."))

@handler.add(PostbackEvent)
def on_postback(event):
    group_id = event.source.group_id
    user_id = event.source.user_id
    data = event.postback.data
    
    if data == "call_response_ready":
        process_call_response(group_id, user_id, "ready")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ تم تسجيلك كمستعد للمعركة!"))
    elif data == "call_response_not_available":
        process_call_response(group_id, user_id, "not_available")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ تم تسجيلك كغير متاح حالياً."))
    elif data == "call_show_responders":
        status = get_call_status(group_id, detailed=True)
        if status:
            report = "🎖️ المستعدون حتى الآن:\n\n"
            if status['responded_members']:
                for i, member in enumerate(status['responded_members'], 1):
                    report += f"{i}. {member}\n"
            else:
                report += "⚠️ لا يوجد مستعدون بعد\n"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=report))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ لا يوجد نداء نشط حالياً."))

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
    return "✅ بوت إدارة المجموعة يعمل بشكل صحيح"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
