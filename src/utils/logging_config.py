"""Logging configuration"""

import logging
from logging import handlers


def setup_logging(log_file, log_level, log_format, max_bytes, backup_count):
    """Konfiguriert das Logging-System"""
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
