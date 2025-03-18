#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module de base pour le bot de protection et contre-attaque
Ce module contient les fonctions principales pour la détection et la réponse aux menaces
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

class ProtectionBot:
    """Classe principale pour le bot de protection et contre-attaque"""
    
    def __init__(self, line_bot_api, group_data):
        """Initialisation du bot de protection"""
        self.line_bot_api = line_bot_api
        self.group_data = group_data
        logger.info("Bot de protection initialisé")
    
    def handle_member_left(self, group_id, left_member_id, event_source):
        """Gère l'événement de départ d'un membre"""
        logger.info(f"Membre {left_member_id} a quitté le groupe {group_id}")
        
        # Vérifier si le membre qui a quitté est le propriétaire
        if self._is_group_owner(group_id, left_member_id):
            logger.warning(f"Le propriétaire {left_member_id} a été expulsé du groupe {group_id}")
            return self._handle_owner_kicked(group_id, left_member_id, event_source)
        
        return False
    
    def _handle_owner_kicked(self, group_id, owner_id, event_source):
        """Gère le cas où le propriétaire a été expulsé"""
        # Vérifier si la protection est active
        if not self._is_guard_active(group_id):
            logger.info(f"Protection désactivée pour le groupe {group_id}, aucune action prise")
            return False
        
        try:
            # Enregistrer l'événement
            self._record_kick_event(group_id, owner_id, "unknown", datetime.now().isoformat())
            
            # Identifier l'auteur du kick (dans un cas réel, cela nécessiterait plus d'informations)
            # Pour l'instant, nous supposons que nous ne pouvons pas identifier l'auteur
            
            # Envoyer une alerte dans le groupe
            self._send_group_alert(group_id)
            
            # Notifier le propriétaire en privé
            self._notify_owner(owner_id, group_id)
            
            # Prendre des mesures contre l'auteur du kick (si identifié)
            self._take_counter_measures(group_id)
            
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la gestion de l'expulsion du propriétaire: {str(e)}")
            return False
    
    def _is_group_owner(self, group_id, user_id):
        """Vérifie si l'utilisateur est le propriétaire du groupe"""
        return (group_id in self.group_data and 
                'owner' in self.group_data[group_id] and 
                self.group_data[group_id]['owner'] == user_id)
    
    def _is_guard_active(self, group_id):
        """Vérifie si la protection est active pour ce groupe"""
        return (group_id in self.group_data and 
                'guard_active' in self.group_data[group_id] and 
                self.group_data[group_id]['guard_active'])
    
    def _record_kick_event(self, group_id, kicked_user_id, kicker_user_id, timestamp):
        """Enregistre un événement d'expulsion"""
        if 'kicked_history' not in self.group_data[group_id]:
            self.group_data[group_id]['kicked_history'] = []
        
        self.group_data[group_id]['kicked_history'].append({
            'kicked_user_id': kicked_user_id,
            'kicker_user_id': kicker_user_id,
            'timestamp': timestamp
        })
        logger.info(f"Événement d'expulsion enregistré: {kicked_user_id} expulsé par {kicker_user_id}")
    
    def _send_group_alert(self, group_id):
        """Envoie une alerte dans le groupe"""
        try:
            alert_message = "⚠️ تنبيه: تم طرد مالك المجموعة! سيتم اتخاذ إجراءات مضادة. ⚠️"
            self.line_bot_api.push_message(
                group_id,
                {"type": "text", "text": alert_message}
            )
            logger.info(f"Alerte envoyée au groupe {group_id}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'alerte au groupe: {str(e)}")
            return False
    
    def _notify_owner(self, owner_id, group_id):
        """Notifie le propriétaire en privé"""
        try:
            message = f"تم طردك من المجموعة {group_id}. سيتم اتخاذ إجراءات مضادة."
            self.line_bot_api.push_message(
                owner_id,
                {"type": "text", "text": message}
            )
            logger.info(f"Notification envoyée au propriétaire {owner_id}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la notification du propriétaire: {str(e)}")
            return False
    
    def _take_counter_measures(self, group_id):
        """Prend des mesures contre l'auteur de l'expulsion"""
        try:
            # Dans un cas réel, nous identifierions l'auteur et prendrions des mesures
            counter_message = "تم تحديد المعتدي وسيتم طرده من المجموعة."
            self.line_bot_api.push_message(
                group_id,
                {"type": "text", "text": counter_message}
            )
            logger.info(f"Mesures de contre-attaque initiées pour le groupe {group_id}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la prise de mesures de contre-attaque: {str(e)}")
            return False
