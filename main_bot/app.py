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
line_bot_api = LineBotApi(os.environ.get('MAIN_BOT_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('MAIN_BOT_CHANNEL_SECRET'))
admin_user_id = os.environ.get('ADMIN_USER_ID')

# Stockage des données
group_data = {}  # Structure: {group_id: {'members': {}, 'active_bots': [], 'settings': {}}}

# Fonction pour initialiser les données d'un groupe
def init_group_data(group_id, owner_id=None):
    if group_id not in group_data:
        group_data[group_id] = {
            'owner': owner_id,
            'members': {},
            'active_bots': [],
            'settings': {
                'tracking_enabled': True,
                'auto_response_enabled': True
            },
            'connected_users': {},
            'last_readers': []
        }

# Fonction pour enregistrer un utilisateur connecté
def track_user_connection(group_id, user_id, display_name):
    init_group_data(group_id)
    
    if user_id not in group_data[group_id]['connected_users']:
        group_data[group_id]['connected_users'][user_id] = {
            'display_name': display_name,
            'first_seen': datetime.now().isoformat(),
            'last_active': datetime.now().isoformat(),
            'message_count': 0,
            'read_count': 0
        }
    else:
        group_data[group_id]['connected_users'][user_id]['last_active'] = datetime.now().isoformat()
        group_data[group_id]['connected_users'][user_id]['message_count'] += 1

# Fonction pour enregistrer un lecteur
def track_reader(group_id, user_id, display_name):
    init_group_data(group_id)
    
    # Mettre à jour les informations de l'utilisateur
    if user_id not in group_data[group_id]['connected_users']:
        track_user_connection(group_id, user_id, display_name)
    
    # Ajouter à la liste des derniers lecteurs
    if user_id not in group_data[group_id]['last_readers']:
        group_data[group_id]['last_readers'].append(user_id)
    
    # Incrémenter le compteur de lectures
    group_data[group_id]['connected_users'][user_id]['read_count'] += 1

# Fonction pour obtenir la liste des utilisateurs connectés
def get_connected_users(group_id):
    if group_id in group_data and 'connected_users' in group_data[group_id]:
        users = []
        for user_id, user_data in group_data[group_id]['connected_users'].items():
            users.append({
                'user_id': user_id,
                'display_name': user_data.get('display_name', 'Utilisateur inconnu'),
                'last_active': user_data.get('last_active', 'Inconnu')
            })
        return users
    return []

# Fonction pour obtenir la liste des lecteurs
def get_readers_list(group_id):
    if group_id in group_data and 'last_readers' in group_data[group_id]:
        readers = []
        for user_id in group_data[group_id]['last_readers']:
            if user_id in group_data[group_id]['connected_users']:
                readers.append(group_data[group_id]['connected_users'][user_id]['display_name'])
            else:
                readers.append(user_id)  # Fallback si le nom n'est pas disponible
        return readers
    return []

# Importer le module de réponse automatique
from auto_response_module import AutoResponseBot

# Initialiser le bot de réponse automatique
auto_response_bot = AutoResponseBot()

# Fonction pour répondre automatiquement à certains messages
def auto_respond(text):
    return auto_response_bot.process_message(text)

# Importer le module de coordination des bots
from bot_coordinator import BotCoordinator

# Initialiser le coordinateur de bots
bot_coordinator = BotCoordinator(line_bot_api, group_data)

# Fonction pour ajouter un bot virtuel
def add_virtual_bot(group_id, bot_type):
    return bot_coordinator.add_bot(group_id, bot_type)

# Fonction pour vérifier si un bot virtuel est actif
def is_bot_active(group_id, bot_type):
    return bot_coordinator.is_bot_active(group_id, bot_type)

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
        
        # Obtenir le nom d'affichage de l'utilisateur
        try:
            profile = line_bot_api.get_group_member_profile(source_id, event.source.user_id)
            display_name = profile.display_name
        except:
            display_name = "Utilisateur inconnu"
        
        # Suivre la connexion de l'utilisateur
        track_user_connection(source_id, event.source.user_id, display_name)
        
        # Suivre la lecture du message
        track_reader(source_id, event.source.user_id, display_name)
    
    # Commande pour ajouter tous les bots virtuels
    if text.strip() == '.add' and source_type in ['group', 'room']:
        if event.source.user_id == admin_user_id:
            # Utiliser le coordinateur pour ajouter tous les bots virtuels
            bots_added = bot_coordinator.add_all_bots(source_id)
            
            if bots_added:
                response = "تمت إضافة البوتات التالية:\n" + "\n".join([f"- {bot}" for bot in bots_added])
            else:
                response = "جميع البوتات مضافة بالفعل."
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=response)
            )
    
    # Commande pour afficher les utilisateurs connectés (bot virtuel de suivi)
    elif text.strip() == '.online' and source_type in ['group', 'room']:
        if is_bot_active(source_id, 'user_tracking'):
            users = get_connected_users(source_id)
            if users:
                response = "المستخدمون المتصلون:\n"
                for user in users:
                    response += f"- {user['display_name']}\n"
            else:
                response = "لا يوجد مستخدمون متصلون حالياً."
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=response)
            )
    
    # Commande pour afficher les lecteurs (bot virtuel de suivi)
    elif text.strip() == '.r' and source_type in ['group', 'room']:
        if is_bot_active(source_id, 'user_tracking'):
            readers = get_readers_list(source_id)
            if readers:
                response = "قائمة القراء:\n" + "\n".join([f"- {reader}" for reader in readers])
            else:
                response = "لا يوجد قراء مسجلون."
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=response)
            )
    
    # Réponse automatique (bot virtuel de réponse automatique)
    elif is_bot_active(source_id, 'auto_response'):
        auto_response = auto_respond(text)
        if auto_response:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=auto_response)
            )
    
    # Commande d'aide pour le bot principal
    elif text.strip() == '.help':
        help_text = (
            "أوامر البوت الرئيسي:\n"
            ".add - إضافة جميع البوتات الوهمية (للمسؤول فقط)\n"
            ".online - عرض قائمة المستخدمين المتصلين\n"
            ".r - عرض قائمة القراء\n"
            ". - الصلاة على النبي\n"
            ".help - عرض هذه المساعدة"
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
            "أنا البوت الرئيسي الذي يدير مجموعة من البوتات الوهمية لحماية وإدارة المجموعة.\n"
            "يمكن للمسؤول استخدام الأمر '.add' لإضافة جميع البوتات الوهمية.\n"
            "استخدم '.help' لعرض الأوامر المتاحة."
        )
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=welcome_message)
        )

@handler.add(MemberJoinedEvent)
def handle_member_joined(event):
    if isinstance(event.source, SourceGroup):
        group_id = event.source.group_id
        
        for member in event.joined.members:
            try:
                profile = line_bot_api.get_group_member_profile(group_id, member.user_id)
                track_user_connection(group_id, member.user_id, profile.display_name)
                
                welcome_message = f"مرحباً {profile.display_name} في المجموعة!"
                line_bot_api.push_message(
                    group_id,
                    TextSendMessage(text=welcome_message)
                )
            except Exception as e:
                app.logger.error(f"Erreur lors de l'accueil d'un nouveau membre: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
