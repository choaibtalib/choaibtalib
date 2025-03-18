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
line_bot_api = LineBotApi(os.environ.get('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET'))
admin_user_id = os.environ.get('USER_ID')

# Stockage des données
group_data = {}  # Structure: {group_id: {'members': {}, 'last_readers': [], 'owner': user_id}}

# Fonction pour initialiser les données d'un groupe
def init_group_data(group_id, owner_id=None):
    if group_id not in group_data:
        group_data[group_id] = {
            'members': {},
            'last_readers': [],
            'owner': owner_id,
            'last_message': None,
            'rules_violated': {}
        }

# Fonction pour enregistrer un message
def record_message(group_id, message_id, user_id, timestamp):
    init_group_data(group_id)
    group_data[group_id]['last_message'] = {
        'id': message_id,
        'user_id': user_id,
        'timestamp': timestamp,
        'readers': []
    }
    # Réinitialiser la liste des lecteurs pour ce nouveau message
    group_data[group_id]['last_readers'] = []

# Fonction pour enregistrer un lecteur
def record_reader(group_id, user_id, display_name):
    if group_id in group_data and 'last_message' in group_data[group_id]:
        if user_id not in group_data[group_id]['last_readers']:
            group_data[group_id]['last_readers'].append(user_id)
        
        # Mettre à jour les informations du membre
        if user_id not in group_data[group_id]['members']:
            group_data[group_id]['members'][user_id] = {
                'display_name': display_name,
                'joined_at': datetime.now().isoformat(),
                'last_active': datetime.now().isoformat()
            }
        else:
            group_data[group_id]['members'][user_id]['last_active'] = datetime.now().isoformat()

# Fonction pour obtenir la liste des lecteurs
def get_readers_list(group_id):
    if group_id in group_data and 'last_readers' in group_data[group_id]:
        readers = []
        for user_id in group_data[group_id]['last_readers']:
            if user_id in group_data[group_id]['members']:
                readers.append(group_data[group_id]['members'][user_id]['display_name'])
            else:
                readers.append(user_id)  # Fallback si le nom n'est pas disponible
        return readers
    return []

# Fonction pour vérifier si un utilisateur est le propriétaire du groupe
def is_group_owner(group_id, user_id):
    return (group_id in group_data and 
            'owner' in group_data[group_id] and 
            group_data[group_id]['owner'] == user_id)

# Fonction pour définir le propriétaire du groupe
def set_group_owner(group_id, user_id):
    init_group_data(group_id, user_id)
    group_data[group_id]['owner'] = user_id

# Fonction pour enregistrer une violation des règles
def record_rule_violation(group_id, user_id, violation_type):
    if group_id in group_data:
        if user_id not in group_data[group_id]['rules_violated']:
            group_data[group_id]['rules_violated'][user_id] = []
        
        group_data[group_id]['rules_violated'][user_id].append({
            'type': violation_type,
            'timestamp': datetime.now().isoformat()
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
        
        # Enregistrer le message pour le suivi des lecteurs
        record_message(source_id, event.message.id, event.source.user_id, event.timestamp)
        
        # Si l'utilisateur n'est pas encore enregistré comme propriétaire et qu'il s'agit de l'admin
        if (not group_data[source_id]['owner'] and 
            event.source.user_id == admin_user_id):
            set_group_owner(source_id, admin_user_id)
        
        # Obtenir le nom d'affichage de l'utilisateur
        try:
            profile = line_bot_api.get_group_member_profile(source_id, event.source.user_id)
            display_name = profile.display_name
        except:
            display_name = "Utilisateur inconnu"
        
        # Enregistrer l'utilisateur comme lecteur
        record_reader(source_id, event.source.user_id, display_name)
    
    # Commande pour afficher les lecteurs
    if text.strip() == '.r' and source_type in ['group', 'room']:
        readers = get_readers_list(source_id)
        if readers:
            response = "Derniers lecteurs:\n" + "\n".join([f"- {reader}" for reader in readers])
        else:
            response = "Aucun lecteur enregistré pour le dernier message."
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=response)
        )
    
    # Commande pour définir le propriétaire du groupe
    elif text.strip() == '.setowner' and source_type in ['group', 'room']:
        if event.source.user_id == admin_user_id:
            set_group_owner(source_id, event.source.user_id)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="Vous êtes maintenant défini comme propriétaire de ce groupe.")
            )
    
    # Commande pour afficher l'aide
    elif text.strip() == '.help':
        help_text = (
            "Commandes disponibles:\n"
            ".r - Afficher les lecteurs du dernier message\n"
            ".setowner - Définir l'utilisateur actuel comme propriétaire (admin uniquement)\n"
            ".help - Afficher ce message d'aide"
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
            "Merci de m'avoir ajouté à ce groupe!\n"
            "Je suis un bot de protection qui peut suivre les lecteurs et protéger le propriétaire du groupe.\n"
            "Utilisez '.help' pour voir les commandes disponibles."
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
                record_reader(group_id, member.user_id, profile.display_name)
                
                welcome_message = f"Bienvenue {profile.display_name} dans le groupe!"
                line_bot_api.push_message(
                    group_id,
                    TextSendMessage(text=welcome_message)
                )
            except Exception as e:
                app.logger.error(f"Erreur lors de l'accueil d'un nouveau membre: {str(e)}")

@handler.add(MemberLeftEvent)
def handle_member_left(event):
    if isinstance(event.source, SourceGroup):
        group_id = event.source.group_id
        
        for member in event.left.members:
            # Vérifier si le membre qui a quitté est le propriétaire
            if is_group_owner(group_id, member.user_id):
                # Le propriétaire a été expulsé, prendre des mesures
                try:
                    # Envoyer un message d'alerte
                    alert_message = "⚠️ ALERTE: Le propriétaire du groupe a été expulsé! ⚠️"
                    line_bot_api.push_message(
                        group_id,
                        TextSendMessage(text=alert_message)
                    )
                    
                    # Notifier l'admin en privé
                    if admin_user_id:
                        line_bot_api.push_message(
                            admin_user_id,
                            TextSendMessage(text=f"Vous avez été expulsé du groupe {group_id}.")
                        )
                except Exception as e:
                    app.logger.error(f"Erreur lors de la gestion de l'expulsion du propriétaire: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
