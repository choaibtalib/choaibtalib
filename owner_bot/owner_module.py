#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module de base pour le bot de réponse au propriétaire
Ce module contient les fonctions principales pour la vérification des permissions et l'exécution des commandes
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

class OwnerResponseBot:
    """Classe principale pour le bot de réponse au propriétaire"""
    
    def __init__(self, line_bot_api, group_data):
        """Initialisation du bot de réponse au propriétaire"""
        self.line_bot_api = line_bot_api
        self.group_data = group_data
        self.admin_id = os.environ.get('ADMIN_USER_ID')
        logger.info("Bot de réponse au propriétaire initialisé")
    
    def check_permission(self, group_id, user_id, command):
        """Vérifie si l'utilisateur a la permission d'exécuter la commande"""
        # Vérifier si le groupe existe dans les données
        if group_id not in self.group_data:
            logger.warning(f"Groupe {group_id} non trouvé dans les données")
            return False, "المجموعة غير مسجلة في النظام."
        
        # Vérifier si le mode strict est activé
        strict_mode = self.group_data[group_id].get('settings', {}).get('strict_mode', True)
        
        # Si le mode strict est désactivé, tout le monde peut exécuter les commandes
        if not strict_mode:
            logger.info(f"Mode strict désactivé pour le groupe {group_id}, permission accordée")
            return True, None
        
        # Vérifier si l'utilisateur est le propriétaire ou l'administrateur
        is_owner = self._is_group_owner(group_id, user_id)
        is_admin = (user_id == self.admin_id)
        
        if is_owner or is_admin:
            logger.info(f"Utilisateur {user_id} est propriétaire ou admin, permission accordée")
            return True, None
        
        # L'utilisateur n'a pas la permission
        logger.warning(f"Utilisateur {user_id} n'a pas la permission d'exécuter la commande {command}")
        return False, "⚠️ هذا الأمر متاح فقط لمالك المجموعة."
    
    def execute_command(self, group_id, user_id, command, args=None):
        """Exécute une commande administrative"""
        # Enregistrer la commande si l'enregistrement est activé
        if self.group_data[group_id].get('settings', {}).get('command_log', True):
            self._log_command(group_id, user_id, command, datetime.now().isoformat(), True)
        
        # Exécuter la commande en fonction de son type
        if command == 'kick':
            return self._kick_user(group_id, args)
        elif command == 'ban':
            return self._ban_user(group_id, args)
        elif command == 'unban':
            return self._unban_user(group_id, args)
        elif command == 'strict_on':
            return self._toggle_strict_mode(group_id, True)
        elif command == 'strict_off':
            return self._toggle_strict_mode(group_id, False)
        elif command == 'log_on':
            return self._toggle_command_log(group_id, True)
        elif command == 'log_off':
            return self._toggle_command_log(group_id, False)
        elif command == 'history':
            return self._get_command_history(group_id)
        else:
            logger.warning(f"Commande inconnue: {command}")
            return f"أمر غير معروف: {command}"
    
    def _is_group_owner(self, group_id, user_id):
        """Vérifie si l'utilisateur est le propriétaire du groupe"""
        return (group_id in self.group_data and 
                'owner' in self.group_data[group_id] and 
                self.group_data[group_id]['owner'] == user_id)
    
    def _log_command(self, group_id, user_id, command, timestamp, success=True):
        """Enregistre une commande dans l'historique"""
        if 'command_history' not in self.group_data[group_id]:
            self.group_data[group_id]['command_history'] = []
        
        self.group_data[group_id]['command_history'].append({
            'user_id': user_id,
            'command': command,
            'timestamp': timestamp,
            'success': success
        })
        logger.info(f"Commande {command} enregistrée pour l'utilisateur {user_id} dans le groupe {group_id}")
    
    def _kick_user(self, group_id, user_name):
        """Expulse un utilisateur du groupe"""
        # Dans un cas réel, il faudrait utiliser l'API LINE pour obtenir l'ID de l'utilisateur
        # et ensuite l'expulser. Ici, nous simulons simplement.
        logger.info(f"Simulation d'expulsion de l'utilisateur {user_name} du groupe {group_id}")
        return f"تم طرد المستخدم {user_name} من المجموعة."
    
    def _ban_user(self, group_id, user_name):
        """Bannit un utilisateur du groupe"""
        # Dans un cas réel, il faudrait utiliser l'API LINE pour obtenir l'ID de l'utilisateur
        # et ensuite le bannir. Ici, nous simulons simplement.
        logger.info(f"Simulation de bannissement de l'utilisateur {user_name} du groupe {group_id}")
        return f"تم حظر المستخدم {user_name} من المجموعة."
    
    def _unban_user(self, group_id, user_name):
        """Débannit un utilisateur du groupe"""
        # Dans un cas réel, il faudrait utiliser l'API LINE pour obtenir l'ID de l'utilisateur
        # et ensuite le débannir. Ici, nous simulons simplement.
        logger.info(f"Simulation de débannissement de l'utilisateur {user_name} du groupe {group_id}")
        return f"تم إلغاء حظر المستخدم {user_name} من المجموعة."
    
    def _toggle_strict_mode(self, group_id, active=True):
        """Active ou désactive le mode strict"""
        if 'settings' not in self.group_data[group_id]:
            self.group_data[group_id]['settings'] = {}
        
        self.group_data[group_id]['settings']['strict_mode'] = active
        
        if active:
            logger.info(f"Mode strict activé pour le groupe {group_id}")
            return "تم تفعيل الوضع الصارم. الأوامر متاحة فقط لمالك المجموعة."
        else:
            logger.info(f"Mode strict désactivé pour le groupe {group_id}")
            return "تم إلغاء تفعيل الوضع الصارم. الأوامر متاحة للجميع."
    
    def _toggle_command_log(self, group_id, active=True):
        """Active ou désactive l'enregistrement des commandes"""
        if 'settings' not in self.group_data[group_id]:
            self.group_data[group_id]['settings'] = {}
        
        self.group_data[group_id]['settings']['command_log'] = active
        
        if active:
            logger.info(f"Enregistrement des commandes activé pour le groupe {group_id}")
            return "تم تفعيل تسجيل الأوامر."
        else:
            logger.info(f"Enregistrement des commandes désactivé pour le groupe {group_id}")
            return "تم إلغاء تفعيل تسجيل الأوامر."
    
    def _get_command_history(self, group_id, limit=10):
        """Récupère l'historique des commandes"""
        if 'command_history' not in self.group_data[group_id]:
            logger.info(f"Aucun historique de commandes trouvé pour le groupe {group_id}")
            return "لا توجد أوامر مسجلة."
        
        history = self.group_data[group_id]['command_history'][-limit:]
        
        if not history:
            logger.info(f"Historique de commandes vide pour le groupe {group_id}")
            return "لا توجد أوامر مسجلة."
        
        history_text = "سجل الأوامر الأخيرة:\n"
        for cmd in history:
            status = "✅" if cmd['success'] else "❌"
            history_text += f"{status} {cmd['command']} (من: {cmd['user_id']})\n"
        
        logger.info(f"Historique de commandes récupéré pour le groupe {group_id}")
        return history_text
    
    def set_group_owner(self, group_id, user_id):
        """Définit le propriétaire du groupe"""
        if group_id not in self.group_data:
            self.group_data[group_id] = {
                'owner': None,
                'members': {},
                'settings': {
                    'strict_mode': True,
                    'command_log': True
                },
                'command_history': []
            }
        
        self.group_data[group_id]['owner'] = user_id
        logger.info(f"Propriétaire du groupe {group_id} défini: {user_id}")
        return f"تم تعيين المستخدم {user_id} كمالك للمجموعة."
