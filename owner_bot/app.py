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
line_bot_api = LineBotApi(os.environ.get('OWNER_BOT_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('OWNER_BOT_CHANNEL_SECRET'))
admin_user_id = os.environ.get('ADMIN_USER_ID')

# Stockage des données
group_data = {}  # Structure: {group_id: {'owner': user_id, 'members': {}, 'settings': {}}}

# Fonction pour initialiser les données d'un groupe
def init_group_data(group_id, owner_id=None):
    if group_id not in group_data:
        group_data[group_id] = {
            'owner': owner_id,
            'members': {},
            'settings': {
                'strict_mode': True,  # Mode strict: seul le propriétaire peut utiliser les commandes
                'command_log': True   # Enregistrer toutes les commandes
            },
            'command_history': []
        }

# Fonction pour vérifier si un utilisateur est le propriétaire du groupe
def is_group_owner(group_id, user_id):
    return (group_id in group_data and 
            'owner' in group_data[group_id] and 
            group_data[group_id]['owner'] == user_id)

# Fonction pour définir le propriétaire du groupe
def set_group_owner(group_id, user_id):
    init_group_data(group_id, user_id)
    group_data[group_id]['owner'] = user_id

# Fonction pour enregistrer une commande
def log_command(group_id, user_id, command, timestamp, success=True):
    init_group_data(group_id)
    if 'command_history' not in group_data[group_id]:
        group_data[group_id]['command_history'] = []
    
    group_data[group_id]['command_history'].append({
        'user_id': user_id,
        'command': command,
        'timestamp': timestamp,
        'success': success
    })

# Fonction pour obtenir l'historique des commandes
def get_command_history(group_id, limit=10):
    if group_id in group_data and 'command_history' in group_data[group_id]:
        return group_data[group_id]['command_history'][-limit:]
    return []

# Fonction pour changer un paramètre
def change_setting(group_id, setting_name, value):
    init_group_data(group_id)
    if 'settings' not in group_data[group_id]:
        group_data[group_id]['settings'] = {}
    
    group_data[group_id]['settings'][setting_name] = value

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
        
        # Si l'utilisateur n'est pas encore enregistré comme propriétaire et qu'il s'agit de l'admin
        if (not group_data[source_id]['owner'] and 
            event.source.user_id == admin_user_id):
            set_group_owner(source_id, admin_user_id)
    
    # Vérifier si l'utilisateur est le propriétaire pour les commandes réservées
    is_owner = is_group_owner(source_id, event.source.user_id) or event.source.user_id == admin_user_id
    
    # Commandes réservées au propriétaire
    if text.startswith('.') and source_type in ['group', 'room']:
        # Vérifier si le mode strict est activé et si l'utilisateur n'est pas le propriétaire
        if (group_data[source_id].get('settings', {}).get('strict_mode', True) and 
            not is_owner):
            # Enregistrer la tentative de commande
            log_command(source_id, event.source.user_id, text, event.timestamp, False)
            
            # Informer l'utilisateur qu'il n'a pas les droits
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="⚠️ هذا الأمر متاح فقط لمالك المجموعة.")
            )
            return
        
        # Enregistrer la commande si l'enregistrement est activé
        if group_data[source_id].get('settings', {}).get('command_log', True):
            log_command(source_id, event.source.user_id, text, event.timestamp)
    
    # Commande pour définir le propriétaire du groupe
    if text.strip() == '.setowner' and source_type in ['group', 'room']:
        if event.source.user_id == admin_user_id:
            set_group_owner(source_id, event.source.user_id)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="تم تعيينك كمالك للمجموعة.")
            )
    
    # Commande pour activer/désactiver le mode strict
    elif text.strip() == '.strict on' and source_type in ['group', 'room'] and is_owner:
        change_setting(source_id, 'strict_mode', True)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="تم تفعيل الوضع الصارم. الأوامر متاحة فقط لمالك المجموعة.")
        )
    
    elif text.strip() == '.strict off' and source_type in ['group', 'room'] and is_owner:
        change_setting(source_id, 'strict_mode', False)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="تم إلغاء تفعيل الوضع الصارم. الأوامر متاحة للجميع.")
        )
    
    # Commande pour activer/désactiver l'enregistrement des commandes
    elif text.strip() == '.log on' and source_type in ['group', 'room'] and is_owner:
        change_setting(source_id, 'command_log', True)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="تم تفعيل تسجيل الأوامر.")
        )
    
    elif text.strip() == '.log off' and source_type in ['group', 'room'] and is_owner:
        change_setting(source_id, 'command_log', False)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="تم إلغاء تفعيل تسجيل الأوامر.")
        )
    
    # Commande pour afficher l'historique des commandes
    elif text.strip() == '.history' and source_type in ['group', 'room'] and is_owner:
        history = get_command_history(source_id)
        if history:
            history_text = "سجل الأوامر الأخيرة:\n"
            for cmd in history:
                status = "✅" if cmd['success'] else "❌"
                history_text += f"{status} {cmd['command']} (من: {cmd['user_id']})\n"
        else:
            history_text = "لا توجد أوامر مسجلة."
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=history_text)
        )
    
    # Commande pour expulser un utilisateur (réservée au propriétaire)
    elif text.startswith('.kick') and source_type in ['group', 'room'] and is_owner:
        # Format attendu: .kick @username
        parts = text.split()
        if len(parts) > 1 and parts[1].startswith('@'):
            user_name = parts[1][1:]  # Enlever le @
            try:
                # Dans un cas réel, il faudrait utiliser l'API LINE pour obtenir l'ID de l'utilisateur
                # et ensuite l'expulser. Ici, nous simulons simplement.
                kick_message = f"تم طرد المستخدم {user_name} من المجموعة."
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=kick_message)
                )
            except Exception as e:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"خطأ: {str(e)}")
                )
    
    # Commande pour bannir un utilisateur (réservée au propriétaire)
    elif text.startswith('.ban') and source_type in ['group', 'room'] and is_owner:
        # Format attendu: .ban @username
        parts = text.split()
        if len(parts) > 1 and parts[1].startswith('@'):
            user_name = parts[1][1:]  # Enlever le @
            try:
                # Dans un cas réel, il faudrait utiliser l'API LINE pour obtenir l'ID de l'utilisateur
                # et ensuite le bannir. Ici, nous simulons simplement.
                ban_message = f"تم حظر المستخدم {user_name} من المجموعة."
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=ban_message)
                )
            except Exception as e:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"خطأ: {str(e)}")
                )
    
    # Commande pour débannir un utilisateur (réservée au propriétaire)
    elif text.startswith('.unban') and source_type in ['group', 'room'] and is_owner:
        # Format attendu: .unban @username
        parts = text.split()
        if len(parts) > 1 and parts[1].startswith('@'):
            user_name = parts[1][1:]  # Enlever le @
            try:
                # Dans un cas réel, il faudrait utiliser l'API LINE pour obtenir l'ID de l'utilisateur
                # et ensuite le débannir. Ici, nous simulons simplement.
                unban_message = f"تم إلغاء حظر المستخدم {user_name} من المجموعة."
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=unban_message)
                )
            except Exception as e:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"خطأ: {str(e)}")
                )
    
    # Commande d'aide pour le bot de réponse au propriétaire
    elif text.strip() == '.ownerhelp':
        help_text = (
            "أوامر بوت الاستجابة للمالك فقط:\n"
            ".setowner - تعيين نفسك كمالك للمجموعة (للمسؤول فقط)\n"
            ".strict on - تفعيل الوضع الصارم (الأوامر للمالك فقط)\n"
            ".strict off - إلغاء تفعيل الوضع الصارم\n"
            ".log on - تفعيل تسجيل الأوامر\n"
            ".log off - إلغاء تفعيل تسجيل الأوامر\n"
            ".history - عرض سجل الأوامر الأخيرة\n"
            ".kick @username - طرد مستخدم من المجموعة\n"
            ".ban @username - حظر مستخدم من المجموعة\n"
            ".unban @username - إلغاء حظر مستخدم من المجموعة\n"
            ".ownerhelp - عرض هذه المساعدة"
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
            "أنا بوت الاستجابة للمالك فقط، مهمتي تنفيذ الأوامر الإدارية من مالك المجموعة فقط.\n"
            "استخدم '.ownerhelp' لعرض الأوامر المتاحة."
        )
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=welcome_message)
        )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    app.run(host="0.0.0.0", port=port)
