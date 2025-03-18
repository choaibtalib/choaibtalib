#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script pour créer un fichier ZIP du projet LINE Protection Bot
"""

import os
import zipfile
import shutil

def create_zip():
    """Crée un fichier ZIP du projet en excluant les fichiers sensibles"""
    project_dir = '/home/ubuntu/line-protection-bot'
    output_zip = '/home/ubuntu/line-protection-bot.zip'
    
    # Fichiers à exclure
    exclude_files = ['.env', '.git', '__pycache__']
    
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(project_dir):
            # Exclure les répertoires
            dirs[:] = [d for d in dirs if d not in exclude_files]
            
            for file in files:
                if file not in exclude_files and not file.endswith('.pyc'):
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, project_dir)
                    zipf.write(file_path, arcname)
    
    print(f"Archive créée avec succès: {output_zip}")
    return output_zip

if __name__ == "__main__":
    create_zip()
