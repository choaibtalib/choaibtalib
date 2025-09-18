# -*- coding: utf-8 -*-
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    TemplateSendMessage, ButtonsTemplate, URITemplateAction
)
import os
import random

app = Flask(__name__)

# --- متغيرات البيئة ---
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.environ.get("CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ===== قائمة المناصب =====
JOBS = [
    "ملك المملكة", "سلطان الصحراء", "قائد الحرس", "حارس القصر",
    "منشد البلاط", "طباخ القصر", "سائق الإبل", "منظف الإسطبل",
    "مهرّج البلاط", "مغنّي الساحة", "كاتب الأسرار", "أمين الخزانة",
    "رامٍ محترف", "مروّض التنانين", "حدّاد القلعة", "منظف الثلج",
    "حارس البوابة", "طبيب القصر", "ساحر المملكة", "جاسوس الملك",
    "مصاص دماء سري", "قرصان متمرّد", "ساقي النبيذ", "ملاح البحيرة",
    "فارس الصيد", "ممثل الحكايات", "شرير القصة", "جني المصباح",
    "صائد الجرذان", "منظم الاحتفالات", "قاطع الأشجار", "صياد السمك",
    "صقار الصقور", "صانع العسل", "خياط القصر", "صانع الصابون",
    "مخترع غريب", "صانع الدمى", "قارئ الطالع", "جندي الحدود",
    "طباخ الملكة", "مطفئ الحرائق", "مسؤول الأمن", "لاعب النبال",
    "لاعب محترف", "عازف القيثارة", "راصد النجوم", "حارس الأحلام",
    "مربي الدجاج", "موزع العصير", "مشوي الدواجن", "خباز القصر",
    "صانع المعجنات", "صانع الحلوى", "صانع الشاي", "موزع الحليب",
    "قصاب القصر", "خبير العصائر", "رسام اللوحات", "مزخرف الجدران",
    "راوي القصص", "أمين المكتبة", "مربي الحمام", "مربي النحل",
    "مروض الخيول", "مروض الفيلة", "مروض القردة", "حارس التنانين",
    "جامع الدمى", "بطل البولينج", "حامل الجوائز", "حارس الفضاء"
]

# حالة اللعبة وتوزيع المناصب
game_active = False
assigned = {}  # user_id -> {"name": ..., "job": ..., "pic": ...}

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global game_active, assigned
    text = event.message.text.strip()

    # تشغيل اللعبة
    if text.lower() == ".g":
        game_active = True
        assigned = {}
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="🎮 تم تفعيل لعبة المناصب! اكتب: منصب")
        )
        return

    # إيقاف اللعبة
    if text.lower() == ".go":
        game_active = False
        assigned = {}
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="⛔ تم إيقاف اللعبة، تم مسح جميع القوائم.")
        )
        return

    # طلب منصب
    if text == "منصب":
        if not game_active:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="⚠️ اللعبة غير مفعّلة حاليًا.")
            )
            return

        user_id = event.source.user_id

        # إذا تم إعطاء العضو منصب سابقاً
        if user_id in assigned:
            data = assigned[user_id]
        else:
            try:
                profile = line_bot_api.get_profile(user_id)
                name = profile.display_name
                profile_pic = profile.picture_url or "https://via.placeholder.com/240"
            except:
                name = "العضو"
                profile_pic = "https://via.placeholder.com/240"
            job = random.choice(JOBS)
            data = {"name": name, "job": job, "pic": profile_pic}
            assigned[user_id] = data

        # إنشاء بطاقة ButtonsTemplate
        buttons_template = ButtonsTemplate(
            thumbnail_image_url=data["pic"],
            title=data["name"],
            text=f"منصبه: {data['job']}",
            actions=[URITemplateAction(label="عرض الصورة", uri=data["pic"])]
        )
        template_message = TemplateSendMessage(
            alt_text="منصب العضو",
            template=buttons_template
        )

        line_bot_api.reply_message(event.reply_token, template_message)

if __name__ == "__main__":
    app.run(port=5000)
    
