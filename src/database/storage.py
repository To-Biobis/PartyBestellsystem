"""Data storage and persistence layer"""

import json
import os
import shutil
import tempfile
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class DataStorage:
    """Handles data loading, saving, and backup operations"""
    
    def __init__(self, data_dir, backup_dir, max_backups=5):
        self.data_dir = data_dir
        self.backup_dir = backup_dir
        self.max_backups = max_backups
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(backup_dir, exist_ok=True)
    
    def load_data(self, file_path, default=None):
        """Lädt Daten aus einer JSON-Datei"""
        try:
            if not os.path.exists(file_path):
                if default is None:
                    default = []
                self.save_data(file_path, default)
                return default
                
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Daten geladen aus {file_path}: {len(data)} Einträge")
            return data
        except json.JSONDecodeError:
            logger.error(f"Fehler beim Laden der Daten aus {file_path}: Ungültiges JSON")
            return self._load_from_backup(file_path, default)
        except Exception as e:
            logger.error(f"Fehler beim Laden der Daten aus {file_path}: {str(e)}")
            return default if default is not None else []
    
    def save_data(self, file_path, data):
        """Speichert Daten atomar in eine JSON-Datei"""
        try:
            # Erstelle temporäre Datei
            temp_file = tempfile.NamedTemporaryFile(
                mode='w', 
                delete=False, 
                dir=os.path.dirname(file_path)
            )
            
            # Schreibe Daten
            json.dump(data, temp_file, ensure_ascii=False, indent=2)
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_file.close()
            
            # Backup erstellen
            if os.path.exists(file_path):
                self._create_backup(file_path)
            
            # Verschiebe temporäre Datei
            shutil.move(temp_file.name, file_path)
            
            logger.info(f"Daten gespeichert in {file_path}: {len(data)} Einträge")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Daten in {file_path}: {str(e)}")
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            return False
    
    def _create_backup(self, file_path):
        """Erstellt ein Backup einer Datei"""
        try:
            if not os.path.exists(file_path):
                return
                
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_dir = os.path.join(self.backup_dir, os.path.basename(file_path))
            os.makedirs(backup_dir, exist_ok=True)
            backup_file = os.path.join(backup_dir, f"{timestamp}.json")
            
            shutil.copy2(file_path, backup_file)
            
            # Lösche alte Backups
            backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.json')])
            while len(backups) > self.max_backups:
                os.remove(os.path.join(backup_dir, backups.pop(0)))
                
            logger.debug(f"Backup erstellt: {backup_file}")
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Backups für {file_path}: {str(e)}")
    
    def _load_from_backup(self, file_path, default):
        """Lädt Daten aus dem neuesten Backup"""
        backup_dir = os.path.join(self.backup_dir, os.path.basename(file_path))
        if os.path.exists(backup_dir):
            backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.json')], reverse=True)
            if backups:
                backup_file = os.path.join(backup_dir, backups[0])
                try:
                    with open(backup_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    logger.info(f"Daten aus Backup geladen: {backup_file}")
                    self.save_data(file_path, data)
                    return data
                except Exception as e:
                    logger.error(f"Fehler beim Laden des Backups {backup_file}: {str(e)}")
        return default if default is not None else []
