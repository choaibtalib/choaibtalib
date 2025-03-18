#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module de réponse automatique pour le bot principal
Ce module contient les fonctions pour la réponse automatique à des commandes spécifiques
"""

import os
import json
import logging
import random
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AutoResponseBot:
    """Classe pour les fonctionnalités de réponse automatique"""
    
    def __init__(self):
        """Initialisation du module de réponse automatique"""
        self.prayers = [
            "اللهم صل وسلم على نبينا محمد",
            "اللهم صل وسلم وبارك على سيدنا محمد",
            "صلى الله عليه وسلم",
            "عليه أفضل الصلاة والسلام"
        ]
        
        self.quotes = [
            "خير الناس أنفعهم للناس",
            "من جد وجد ومن زرع حصد",
            "العلم نور والجهل ظلام",
            "الصبر مفتاح الفرج",
            "من طلب العلا سهر الليالي",
            "الوقت كالسيف إن لم تقطعه قطعك"
        ]
        
        self.greetings = {
            "صباح الخير": "صباح النور والسرور",
            "مساء الخير": "مساء النور والسعادة",
            "السلام عليكم": "وعليكم السلام ورحمة الله وبركاته",
            "مرحبا": "مرحبا بك، كيف حالك؟"
        }
        
        logger.info("Module de réponse automatique initialisé")
    
    def process_message(self, message_text):
        """Traite un message et retourne une réponse automatique si nécessaire"""
        # Commande pour la prière sur le Prophète
        if message_text.strip() == '.':
            return self._get_random_prayer()
        
        # Commande pour une citation aléatoire
        elif message_text.strip() == '.quote':
            return self._get_random_quote()
        
        # Commande pour l'heure actuelle
        elif message_text.strip() == '.time':
            return self._get_current_time()
        
        # Commande pour la date actuelle
        elif message_text.strip() == '.date':
            return self._get_current_date()
        
        # Réponses aux salutations
        elif message_text.strip() in self.greetings:
            return self.greetings[message_text.strip()]
        
        # Pas de réponse automatique pour ce message
        return None
    
    def _get_random_prayer(self):
        """Retourne une prière aléatoire sur le Prophète"""
        prayer = random.choice(self.prayers)
        logger.info(f"Prière générée: {prayer}")
        return prayer
    
    def _get_random_quote(self):
        """Retourne une citation aléatoire"""
        quote = random.choice(self.quotes)
        logger.info(f"Citation générée: {quote}")
        return quote
    
    def _get_current_time(self):
        """Retourne l'heure actuelle"""
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        logger.info(f"Heure demandée: {time_str}")
        return f"الوقت الحالي: {time_str}"
    
    def _get_current_date(self):
        """Retourne la date actuelle"""
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        logger.info(f"Date demandée: {date_str}")
        return f"التاريخ الحالي: {date_str}"
    
    def get_help_text(self):
        """Retourne le texte d'aide pour les commandes de réponse automatique"""
        help_text = (
            "أوامر الرد التلقائي:\n"
            ". - الصلاة على النبي\n"
            ".quote - عرض اقتباس عشوائي\n"
            ".time - عرض الوقت الحالي\n"
            ".date - عرض التاريخ الحالي"
        )
        return help_text
