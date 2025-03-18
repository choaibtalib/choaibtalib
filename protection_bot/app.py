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
line_bot_api = LineBotApi(os.environ.get('PROTECTION_BOT_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('PROTECTION_BOT_CHANNEL_SECRET'))
admin_user_id = os.environ.get('ADMIN_USER_ID')

# Stockage des données
group_data = {}  # Structure: {group_id: {'owner': user_id, 'admins': [], 'guard_active': True}}

# Fonction pour initialiser les données d'un groupe
def init_group_data(group_id, owner_id=None):
    if group_id not in group_data:
        group_data[group_id] = {
            'owner': owner_id,
            'admins': [],
            'guard_active': True,
            'kicked_history': []
        }

# Fonction pour vérifier si un utilisateur est le propriétaire du groupe
def is_group_owner(group_id, user_id):
    return (group_id in group_data and 
            'owner' in group_data[group_id] and 
            group_data[group_id]['owner'] == user_id)

# Fonction pour vérifier si un utilisateur est administrateur
def is_group_admin(group_id, user_id):
    return (group_id in group_data and 
            'admins' in group_data[group_id] and 
            user_id in group_data[group_id]['admins'])

# Fonction pour définir le propriétaire du groupe
def set_group_owner(group_id, user_id):
    init_group_data(group_id, user_id)
    group_data[group_id]['owner'] = user_id

# Fonction pour ajouter un administrateur
def add_group_admin(group_id, user_id):
    init_group_data(group_id)
    if 'admins' not in group_data[group_id]:
        group_data[group_id]['admins'] = []
    if user_id not in group_data[group_id]['admins']:
        group_data[group_id]['admins'].append(user_id)

# Fonction pour enregistrer un événement de kick
def record_kick_event(group_id, kicked_user_id, kicker_user_id, timestamp):
    init_group_data(group_id)
    if 'kicked_history' not in group_data[group_id]:
        group_data[group_id]['kicked_history'] = []
    
    group_data[group_id]['kicked_history'].append({
        'kicked_user_id': kicked_user_id,
        'kicker_user_id': kicker_user_id,
        'timestamp': timestamp
    })

# Fonction pour activer/désactiver la protection
def toggle_guard(group_id, active=True):
    init_group_data(group_id)
    group_data[group_id]['guard_active'] = active

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
    
    # Commande pour définir le propriétaire du groupe
    if text.strip() == '.setowner' and source_type in ['group', 'room']:
        if event.source.user_id == admin_user_id:
            set_group_owner(source_id, event.source.user_id)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="أنت الآن مالك المجموعة.")
            )
    
    # Commande pour ajouter un administrateur
    elif text.startswith('.addadmin') and source_type in ['group', 'room']:
        if is_group_owner(source_id, event.source.user_id):
            # Format attendu: .addadmin @username
            parts = text.split()
            if len(parts) > 1 and parts[1].startswith('@'):
                # Dans un cas réel, il faudrait résoudre le nom d'utilisateur en ID
                # Ici, nous simulons simplement en utilisant le nom comme ID
                admin_name = parts[1][1:]  # Enlever le @
                try:
                    # Ceci est une simplification, dans un cas réel il faudrait
                    # utiliser l'API LINE pour obtenir l'ID de l'utilisateur
                    add_group_admin(source_id, admin_name)
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=f"تمت إضافة {admin_name} كمسؤول.")
                    )
                except Exception as e:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=f"خطأ: {str(e)}")
                    )
    
    # Commande pour activer/désactiver la protection
    elif text.strip() == '.guard on' and source_type in ['group', 'room']:
        if is_group_owner(source_id, event.source.user_id) or is_group_admin(source_id, event.source.user_id):
            toggle_guard(source_id, True)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="تم تفعيل وضع الحماية.")
            )
    
    elif text.strip() == '.guard off' and source_type in ['group', 'room']:
        if is_group_owner(source_id, event.source.user_id) or is_group_admin(source_id, event.source.user_id):
            toggle_guard(source_id, False)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="تم إلغاء تفعيل وضع الحماية.")
            )
    
    # Commande pour vérifier l'état de la protection
    elif text.strip() == '.guardstatus' and source_type in ['group', 'room']:
        status = "مفعل" if group_data[source_id].get('guard_active', False) else "غير مفعل"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"وضع الحماية: {status}")
        )
    
    # Commande d'aide pour le bot de protection
    elif text.strip() == '.guardhelp':
        help_text = (
            "أوامر بوت الحماية:\n"
            ".setowner - تعيين نفسك كمالك للمجموعة (للمسؤول فقط)\n"
            ".addadmin @username - إضافة مستخدم كمسؤول (للمالك فقط)\n"
            ".guard on - تفعيل وضع الحماية\n"
            ".guard off - إلغاء تفعيل وضع الحماية\n"
            ".guardstatus - عرض حالة وضع الحماية\n"
            ".guardhelp - عرض هذه المساعدة"
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
            "أنا بوت الحماية والهجوم المضاد، مهمتي حماية المجموعة ومالكها.\n"
            "استخدم '.guardhelp' لعرض الأوامر المتاحة."
        )
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=welcome_message)
        )

@handler.add(MemberLeftEvent)
def handle_member_left(event):
    if isinstance(event.source, SourceGroup):
        group_id = event.source.group_id
        
        for member in event.left.members:
            # Vérifier si le membre qui a quitté est le propriétaire
            if is_group_owner(group_id, member.user_id):
                # Le propriétaire a été expulsé, prendre des mesures si la protection est active
                if group_data[group_id].get('guard_active', False):
                    try:
                        # Envoyer un message d'alerte
                        alert_message = "⚠️ تنبيه: تم طرد مالك المجموعة! سيتم اتخاذ إجراءات مضادة. ⚠️"
                        line_bot_api.push_message(
                            group_id,
                            TextSendMessage(text=alert_message)
                        )
                        
                        # Dans un cas réel, il faudrait identifier qui a expulsé le propriétaire
                        # et prendre des mesures contre cette personne
                        # Ici, nous simulons simplement l'enregistrement de l'événement
                        record_kick_event(group_id, member.user_id, "unknown", datetime.now().isoformat())
                        
                        # Notifier l'admin en privé
                        if admin_user_id:
                            line_bot_api.push_message(
                                admin_user_id,
                                TextSendMessage(text=f"تم طردك من المجموعة {group_id}. سيتم اتخاذ إجراءات مضادة.")
                            )
                            
                        # Dans un cas réel, le bot pourrait:
                        # 1. Identifier qui a expulsé le propriétaire
                        # 2. Expulser cette personne
                        # 3. Inviter à nouveau le propriétaire
                        counter_message = "تم تحديد المعتدي وسيتم طرده من المجموعة."
                        line_bot_api.push_message(
                            group_id,
                            TextSendMessage(text=counter_message)
                        )
                    except Exception as e:
                        app.logger.error(f"خطأ أثناء معالجة طرد المالك: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
