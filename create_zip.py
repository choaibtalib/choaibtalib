#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import zipfile
import shutil

def create_zip():
    """Crée un fichier zip du projet LINE Multi-Bot System"""
    
    # Définir le répertoire source et le nom du fichier zip
    source_dir = '/home/ubuntu/line-multi-bot-system'
    zip_filename = '/home/ubuntu/line-multi-bot-system.zip'
    
    # Créer un fichier zip temporaire
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Parcourir tous les fichiers et dossiers dans le répertoire source
        for root, dirs, files in os.walk(source_dir):
            # Exclure les dossiers __pycache__ et les fichiers .pyc
            if '__pycache__' in dirs:
                dirs.remove('__pycache__')
            
            # Ajouter chaque fichier au zip
            for file in files:
                # Exclure les fichiers .pyc et .env
                if not file.endswith('.pyc'):
                    file_path = os.path.join(root, file)
                    # Calculer le chemin relatif pour le zip
                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname)
    
    print(f"Fichier zip créé avec succès: {zip_filename}")
    return zip_filename

if __name__ == "__main__":
    create_zip()
