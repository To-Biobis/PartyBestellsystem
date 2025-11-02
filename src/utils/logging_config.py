"""Logging configuration"""

import logging
from logging import handlers


def setup_logging(log_file, log_level, log_format, max_bytes, backup_count):
    """Konfiguriert das Logging-System
    
    Args:
        log_file (str): Pfad zur Log-Datei
        log_level (int): Logging-Level (z.B. logging.INFO)
        log_format (str): Format-String für Log-Einträge
        max_bytes (int): Maximale Größe der Log-Datei in Bytes
        backup_count (int): Anzahl der Backup-Log-Dateien
        
    Returns:
        logging.Logger: Konfigurierter Logger
    """
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count
            ),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)
