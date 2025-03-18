#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
from datetime import datetime
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    SourceGroup, SourceRoom, SourceUser,
    JoinEvent, LeaveEvent, MemberJoinedEvent, MemberLeftEvent,
    PostbackEvent
)
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)

# Configuration LINE API
line_bot_api = LineBotApi(os.environ.get('TAG_MONITOR_BOT_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('TAG_MONITOR_BOT_CHANNEL_SECRET'))
admin_user_id = os.environ.get('ADMIN_USER_ID')

# Stockage des données
group_data = {}  # Structure: {group_id: {'allowed_taggers': [], 'tag_monitor_active': True}}

# Fonction pour initialiser les données d'un groupe
def init_group_data(group_id):
    if group_id not in group_data:
        group_data[group_id] = {
            'allowed_taggers': [],
            'tag_monitor_active': True,
            'tag_violations': []
        }

# Fonction pour vérifier si un utilisateur est autorisé à utiliser le tag @All
def is_allowed_tagger(group_id, user_id):
    return (group_id in group_data and 
            'allowed_taggers' in group_data[group_id] and 
            user_id in group_data[group_id]['allowed_taggers'])

# Fonction pour ajouter un utilisateur autorisé
def add_allowed_tagger(group_id, user_id):
    init_group_data(group_id)
    if 'allowed_taggers' not in group_data[group_id]:
        group_data[group_id]['allowed_taggers'] = []
    if user_id not in group_data[group_id]['allowed_taggers']:
        group_data[group_id]['allowed_taggers'].append(user_id)

# Fonction pour supprimer un utilisateur autorisé
def remove_allowed_tagger(group_id, user_id):
    if (group_id in group_data and 
        'allowed_taggers' in group_data[group_id] and 
        user_id in group_data[group_id]['allowed_taggers']):
        group_data[group_id]['allowed_taggers'].remove(user_id)

# Fonction pour activer/désactiver la surveillance des tags
def toggle_tag_monitor(group_id, active=True):
    init_group_data(group_id)
    group_data[group_id]['tag_monitor_active'] = active

# Fonction pour enregistrer une violation de tag
def record_tag_violation(group_id, user_id, message, timestamp):
    init_group_data(group_id)
    if 'tag_violations' not in group_data[group_id]:
        group_data[group_id]['tag_violations'] = []
    
    group_data[group_id]['tag_violations'].append({
        'user_id': user_id,
        'message': message,
        'timestamp': timestamp
    })

@app.route("/callback", methods=['POST'])
def callback():
    # Récupérer la signature X-Line-Signature de l'en-tête HTTP
    signature = request.headers['X-Line-Signature']

    # Récupérer le corps de la requête
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # Gérer le webhook
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    text = event.message.text
    
    # Déterminer la source du message
    if isinstance(event.source, SourceGroup):
        source_id = event.source.group_id
        source_type = 'group'
    elif isinstance(event.source, SourceRoom):
        source_id = event.source.room_id
        source_type = 'room'
    elif isinstance(event.source, SourceUser):
        source_id = event.source.user_id
        source_type = 'user'
    else:
        return
    
    # Initialiser les données du groupe si nécessaire
    if source_type in ['group', 'room']:
        init_group_data(source_id)
    
    # Vérifier si le message contient @All et si la surveillance est active
    if '@All' in text and source_type in ['group', 'room'] and group_data[source_id]['tag_monitor_active']:
        # Vérifier si l'utilisateur est autorisé
        if not is_allowed_tagger(source_id, event.source.user_id) and event.source.user_id != admin_user_id:
            # Enregistrer la violation
            record_tag_violation(source_id, event.source.user_id, text, event.timestamp)
            
            # Avertir l'utilisateur
            warning_message = "⚠️ غير مسموح لك باستخدام التاغ الجماعي @All. هذا مخالف لقوانين المجموعة."
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=warning_message)
            )
            
            # Dans un cas réel, le bot pourrait également:
            # 1. Supprimer le message (si l'API LINE le permet)
            # 2. Expulser l'utilisateur après plusieurs violations
            # 3. Notifier les administrateurs
            
            try:
                # Notifier l'admin
                if admin_user_id:
                    admin_message = f"تنبيه: المستخدم {event.source.user_id} استخدم التاغ الجماعي @All في المجموعة {source_id} دون إذن."
                    line_bot_api.push_message(
                        admin_user_id,
                        TextSendMessage(text=admin_message)
                    )
            except Exception as e:
                app.logger.error(f"خطأ أثناء إرسال التنبيه للمسؤول: {str(e)}")
    
    # Commande pour ajouter un utilisateur autorisé
    elif text.startswith('.addtaguser') and source_type in ['group', 'room']:
        if event.source.user_id == admin_user_id:
            # Format attendu: .addtaguser @username
            parts = text.split()
            if len(parts) > 1 and parts[1].startswith('@'):
                # Dans un cas réel, il faudrait résoudre le nom d'utilisateur en ID
                # Ici, nous simulons simplement en utilisant le nom comme ID
                user_name = parts[1][1:]  # Enlever le @
                try:
                    # Ceci est une simplification, dans un cas réel il faudrait
                    # utiliser l'API LINE pour obtenir l'ID de l'utilisateur
                    add_allowed_tagger(source_id, user_name)
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=f"تمت إضافة {user_name} إلى قائمة المستخدمين المسموح لهم باستخدام التاغ الجماعي.")
                    )
                except Exception as e:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=f"خطأ: {str(e)}")
                    )
    
    # Commande pour supprimer un utilisateur autorisé
    elif text.startswith('.removetaguser') and source_type in ['group', 'room']:
        if event.source.user_id == admin_user_id:
            # Format attendu: .removetaguser @username
            parts = text.split()
            if len(parts) > 1 and parts[1].startswith('@'):
                user_name = parts[1][1:]  # Enlever le @
                try:
                    remove_allowed_tagger(source_id, user_name)
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=f"تمت إزالة {user_name} من قائمة المستخدمين المسموح لهم باستخدام التاغ الجماعي.")
                    )
                except Exception as e:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=f"خطأ: {str(e)}")
                    )
    
    # Commande pour activer/désactiver la surveillance des tags
    elif text.strip() == '.tagguard on' and source_type in ['group', 'room']:
        if event.source.user_id == admin_user_id:
            toggle_tag_monitor(source_id, True)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="تم تفعيل مراقبة التاغ الجماعي.")
            )
    
    elif text.strip() == '.tagguard off' and source_type in ['group', 'room']:
        if event.source.user_id == admin_user_id:
            toggle_tag_monitor(source_id, False)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="تم إلغاء تفعيل مراقبة التاغ الجماعي.")
            )
    
    # Commande pour vérifier l'état de la surveillance des tags
    elif text.strip() == '.tagstatus' and source_type in ['group', 'room']:
        status = "مفعل" if group_data[source_id].get('tag_monitor_active', False) else "غير مفعل"
        allowed_users = group_data[source_id].get('allowed_taggers', [])
        
        status_message = f"حالة مراقبة التاغ الجماعي: {status}\n"
        if allowed_users:
            status_message += "المستخدمون المسموح لهم:\n"
            for user in allowed_users:
                status_message += f"- {user}\n"
        else:
            status_message += "لا يوجد مستخدمون مسموح لهم حالياً."
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=status_message)
        )
    
    # Commande d'aide pour le bot de surveillance des tags
    elif text.strip() == '.taghelp':
        help_text = (
            "أوامر بوت مراقبة التاغ الجماعي:\n"
            ".addtaguser @username - إضافة مستخدم إلى قائمة المسموح لهم باستخدام التاغ الجماعي (للمسؤول فقط)\n"
            ".removetaguser @username - إزالة مستخدم من قائمة المسموح لهم (للمسؤول فقط)\n"
            ".tagguard on - تفعيل مراقبة التاغ الجماعي (للمسؤول فقط)\n"
            ".tagguard off - إلغاء تفعيل مراقبة التاغ الجماعي (للمسؤول فقط)\n"
            ".tagstatus - عرض حالة مراقبة التاغ الجماعي والمستخدمين المسموح لهم\n"
            ".taghelp - عرض هذه المساعدة"
        )
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=help_text)
        )

@handler.add(JoinEvent)
def handle_join(event):
    if isinstance(event.source, SourceGroup):
        group_id = event.source.group_id
        init_group_data(group_id)
        
        welcome_message = (
            "شكراً لإضافتي إلى هذه المجموعة!\n"
            "أنا بوت مراقبة التاغ الجماعي، مهمتي منع استخدام التاغ @All من قبل المستخدمين غير المصرح لهم.\n"
            "استخدم '.taghelp' لعرض الأوامر المتاحة."
        )
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=welcome_message)
        )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
