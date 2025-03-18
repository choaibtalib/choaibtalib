#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module de base pour le bot de surveillance des tags
Ce module contient les fonctions principales pour la détection et la gestion des tags @All
"""

import os
import json
import logging
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TagMonitorBot:
    """Classe principale pour le bot de surveillance des tags"""
    
    def __init__(self, line_bot_api, group_data):
        """Initialisation du bot de surveillance des tags"""
        self.line_bot_api = line_bot_api
        self.group_data = group_data
        logger.info("Bot de surveillance des tags initialisé")
    
    def check_tag_usage(self, group_id, user_id, message_text, event_source):
        """Vérifie si le message contient un tag @All et si l'utilisateur est autorisé"""
        if '@All' not in message_text:
            return False, None
        
        logger.info(f"Tag @All détecté dans le message de l'utilisateur {user_id} dans le groupe {group_id}")
        
        # Vérifier si la surveillance est active
        if not self._is_tag_monitor_active(group_id):
            logger.info(f"Surveillance des tags désactivée pour le groupe {group_id}, aucune action prise")
            return False, None
        
        # Vérifier si l'utilisateur est autorisé
        if self._is_allowed_tagger(group_id, user_id) or user_id == os.environ.get('ADMIN_USER_ID'):
            logger.info(f"Utilisateur {user_id} autorisé à utiliser le tag @All dans le groupe {group_id}")
            return False, None
        
        # L'utilisateur n'est pas autorisé
        logger.warning(f"Utilisateur {user_id} non autorisé à utiliser le tag @All dans le groupe {group_id}")
        
        # Enregistrer la violation
        self._record_tag_violation(group_id, user_id, message_text, datetime.now().isoformat())
        
        return True, self._create_warning_response(user_id)
    
    def _is_tag_monitor_active(self, group_id):
        """Vérifie si la surveillance des tags est active pour ce groupe"""
        return (group_id in self.group_data and 
                'tag_monitor_active' in self.group_data[group_id] and 
                self.group_data[group_id]['tag_monitor_active'])
    
    def _is_allowed_tagger(self, group_id, user_id):
        """Vérifie si l'utilisateur est autorisé à utiliser le tag @All"""
        return (group_id in self.group_data and 
                'allowed_taggers' in self.group_data[group_id] and 
                user_id in self.group_data[group_id]['allowed_taggers'])
    
    def _record_tag_violation(self, group_id, user_id, message, timestamp):
        """Enregistre une violation de tag"""
        if 'tag_violations' not in self.group_data[group_id]:
            self.group_data[group_id]['tag_violations'] = []
        
        self.group_data[group_id]['tag_violations'].append({
            'user_id': user_id,
            'message': message,
            'timestamp': timestamp
        })
        logger.info(f"Violation de tag enregistrée: utilisateur {user_id} dans le groupe {group_id}")
    
    def _create_warning_response(self, user_id):
        """Crée un message d'avertissement pour l'utilisateur"""
        return "⚠️ غير مسموح لك باستخدام التاغ الجماعي @All. هذا مخالف لقوانين المجموعة."
    
    def notify_admin(self, group_id, user_id):
        """Notifie l'administrateur d'une violation"""
        try:
            admin_id = os.environ.get('ADMIN_USER_ID')
            if admin_id:
                admin_message = f"تنبيه: المستخدم {user_id} استخدم التاغ الجماعي @All في المجموعة {group_id} دون إذن."
                self.line_bot_api.push_message(
                    admin_id,
                    {"type": "text", "text": admin_message}
                )
                logger.info(f"Notification envoyée à l'administrateur {admin_id}")
                return True
        except Exception as e:
            logger.error(f"Erreur lors de la notification de l'administrateur: {str(e)}")
        return False
    
    def add_allowed_tagger(self, group_id, user_id):
        """Ajoute un utilisateur à la liste des utilisateurs autorisés"""
        if 'allowed_taggers' not in self.group_data[group_id]:
            self.group_data[group_id]['allowed_taggers'] = []
        
        if user_id not in self.group_data[group_id]['allowed_taggers']:
            self.group_data[group_id]['allowed_taggers'].append(user_id)
            logger.info(f"Utilisateur {user_id} ajouté à la liste des utilisateurs autorisés dans le groupe {group_id}")
            return True
        return False
    
    def remove_allowed_tagger(self, group_id, user_id):
        """Supprime un utilisateur de la liste des utilisateurs autorisés"""
        if (group_id in self.group_data and 
            'allowed_taggers' in self.group_data[group_id] and 
            user_id in self.group_data[group_id]['allowed_taggers']):
            self.group_data[group_id]['allowed_taggers'].remove(user_id)
            logger.info(f"Utilisateur {user_id} supprimé de la liste des utilisateurs autorisés dans le groupe {group_id}")
            return True
        return False
    
    def toggle_tag_monitor(self, group_id, active=True):
        """Active ou désactive la surveillance des tags"""
        self.group_data[group_id]['tag_monitor_active'] = active
        status = "activée" if active else "désactivée"
        logger.info(f"Surveillance des tags {status} pour le groupe {group_id}")
        return True
    
    def get_status(self, group_id):
        """Récupère l'état actuel de la surveillance des tags"""
        status = "مفعل" if self.group_data[group_id].get('tag_monitor_active', False) else "غير مفعل"
        allowed_users = self.group_data[group_id].get('allowed_taggers', [])
        
        status_message = f"حالة مراقبة التاغ الجماعي: {status}\n"
        if allowed_users:
            status_message += "المستخدمون المسموح لهم:\n"
            for user in allowed_users:
                status_message += f"- {user}\n"
        else:
            status_message += "لا يوجد مستخدمون مسموح لهم حالياً."
        
        return status_message
