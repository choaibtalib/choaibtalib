#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module de coordination pour le bot principal
Ce module contient les fonctions pour la coordination des bots virtuels
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

class BotCoordinator:
    """Classe pour la coordination des bots virtuels"""
    
    def __init__(self, line_bot_api, group_data):
        """Initialisation du coordinateur de bots"""
        self.line_bot_api = line_bot_api
        self.group_data = group_data
        self.admin_id = os.environ.get('ADMIN_USER_ID')
        self.available_bots = {
            'protection': {
                'name': 'بوت الحماية',
                'description': 'يقوم بحماية المجموعة من خطر الطرد ويتخذ إجراءات مضادة'
            },
            'tag_monitor': {
                'name': 'بوت مراقبة التاغ',
                'description': 'يمنع استخدام التاغ الجماعي @All من قبل المستخدمين غير المصرح لهم'
            },
            'owner_response': {
                'name': 'بوت الاستجابة للمالك',
                'description': 'ينفذ الأوامر الإدارية من مالك المجموعة فقط'
            },
            'user_tracking': {
                'name': 'بوت تتبع المتصلين',
                'description': 'يتتبع المستخدمين المتصلين والقراء في المجموعة'
            },
            'auto_response': {
                'name': 'بوت الرد التلقائي',
                'description': 'يستجيب تلقائياً لأوامر محددة مثل الصلاة على النبي'
            }
        }
        logger.info("Coordinateur de bots initialisé")
    
    def add_all_bots(self, group_id):
        """Ajoute tous les bots virtuels à un groupe"""
        if group_id not in self.group_data:
            self.group_data[group_id] = {
                'active_bots': [],
                'settings': {}
            }
        
        bots_added = []
        for bot_type in self.available_bots:
            if self.add_bot(group_id, bot_type):
                bots_added.append(self.available_bots[bot_type]['name'])
        
        return bots_added
    
    def add_bot(self, group_id, bot_type):
        """Ajoute un bot virtuel spécifique à un groupe"""
        if bot_type not in self.available_bots:
            logger.warning(f"Type de bot inconnu: {bot_type}")
            return False
        
        if 'active_bots' not in self.group_data[group_id]:
            self.group_data[group_id]['active_bots'] = []
        
        if bot_type not in self.group_data[group_id]['active_bots']:
            self.group_data[group_id]['active_bots'].append(bot_type)
            logger.info(f"Bot {bot_type} ajouté au groupe {group_id}")
            return True
        
        logger.info(f"Bot {bot_type} déjà actif dans le groupe {group_id}")
        return False
    
    def remove_bot(self, group_id, bot_type):
        """Supprime un bot virtuel d'un groupe"""
        if (group_id in self.group_data and 
            'active_bots' in self.group_data[group_id] and 
            bot_type in self.group_data[group_id]['active_bots']):
            self.group_data[group_id]['active_bots'].remove(bot_type)
            logger.info(f"Bot {bot_type} supprimé du groupe {group_id}")
            return True
        
        logger.warning(f"Bot {bot_type} non trouvé dans le groupe {group_id}")
        return False
    
    def is_bot_active(self, group_id, bot_type):
        """Vérifie si un bot virtuel est actif dans un groupe"""
        return (group_id in self.group_data and 
                'active_bots' in self.group_data[group_id] and 
                bot_type in self.group_data[group_id]['active_bots'])
    
    def get_active_bots(self, group_id):
        """Récupère la liste des bots virtuels actifs dans un groupe"""
        if group_id in self.group_data and 'active_bots' in self.group_data[group_id]:
            active_bots = []
            for bot_type in self.group_data[group_id]['active_bots']:
                if bot_type in self.available_bots:
                    active_bots.append(self.available_bots[bot_type]['name'])
            return active_bots
        return []
    
    def get_bot_status(self, group_id):
        """Récupère l'état des bots virtuels dans un groupe"""
        active_bots = self.get_active_bots(group_id)
        
        if active_bots:
            status_text = "البوتات النشطة في المجموعة:\n"
            for bot_name in active_bots:
                status_text += f"- {bot_name}\n"
        else:
            status_text = "لا توجد بوتات نشطة في المجموعة."
        
        return status_text
    
    def process_command(self, group_id, user_id, command, args=None):
        """Traite une commande de coordination"""
        # Vérifier si l'utilisateur est l'administrateur
        if user_id != self.admin_id:
            logger.warning(f"Utilisateur {user_id} non autorisé à exécuter la commande {command}")
            return "⚠️ هذا الأمر متاح فقط للمسؤول."
        
        # Commande pour ajouter tous les bots
        if command == 'add_all':
            bots_added = self.add_all_bots(group_id)
            
            if bots_added:
                response = "تمت إضافة البوتات التالية:\n" + "\n".join([f"- {bot}" for bot in bots_added])
            else:
                response = "جميع البوتات مضافة بالفعل."
            
            return response
        
        # Commande pour ajouter un bot spécifique
        elif command == 'add_bot' and args:
            bot_type = args
            if self.add_bot(group_id, bot_type):
                return f"تمت إضافة {self.available_bots[bot_type]['name']} إلى المجموعة."
            else:
                return f"البوت {bot_type} غير معروف أو مضاف بالفعل."
        
        # Commande pour supprimer un bot spécifique
        elif command == 'remove_bot' and args:
            bot_type = args
            if self.remove_bot(group_id, bot_type):
                return f"تمت إزالة {self.available_bots[bot_type]['name']} من المجموعة."
            else:
                return f"البوت {bot_type} غير موجود في المجموعة."
        
        # Commande pour afficher l'état des bots
        elif command == 'status':
            return self.get_bot_status(group_id)
        
        # Commande inconnue
        else:
            logger.warning(f"Commande inconnue: {command}")
            return f"أمر غير معروف: {command}"
