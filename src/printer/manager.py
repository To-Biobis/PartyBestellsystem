"""Printer connection management"""

import logging
import time
from threading import Lock
from escpos.printer import Usb

logger = logging.getLogger(__name__)


class PrinterManager:
    """Singleton-Klasse zur Verwaltung der Druckerverbindung"""
    
    _instance = None
    _lock = Lock()
    
    @classmethod
    def get_instance(cls, vendor_id=0x04b8, product_id=0x0e15):
        """Gibt die Singleton-Instanz zurück"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(vendor_id, product_id)
        return cls._instance
    
    def __init__(self, vendor_id, product_id):
        """Initialisiert den PrinterManager"""
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.printer = None
        self.last_used = 0
        self._connection_lock = Lock()
    
    def get_printer(self):
        """Gibt eine Druckerverbindung zurück oder erstellt eine neue"""
        with self._connection_lock:
            current_time = time.time()
            
            # Erstelle neue Verbindung wenn nötig
            if self.printer is None or (current_time - self.last_used) > 5:
                try:
                    if self.printer is not None:
                        try:
                            self.printer.close()
                        except:
                            pass
                    
                    self.printer = self._connect_printer()
                    self.last_used = current_time
                except Exception as e:
                    logger.error(f"Fehler beim Verbinden mit Drucker: {str(e)}")
                    self.printer = None
            
            return self.printer
    
    def _connect_printer(self):
        """Stellt Verbindung zum Drucker her"""
        try:
            # Versuche Standard-Endpunkte
            printer = Usb(
                idVendor=self.vendor_id,
                idProduct=self.product_id,
                in_ep=0x82,
                out_ep=0x01,
                timeout=0
            )
            logger.info("Drucker erfolgreich verbunden (Standard-Endpunkte)")
            return printer
        except Exception as e1:
            logger.debug(f"Standard-Endpunkte fehlgeschlagen: {str(e1)}")
            try:
                # Versuche alternative Endpunkte
                printer = Usb(
                    idVendor=self.vendor_id,
                    idProduct=self.product_id,
                    in_ep=0x81,
                    out_ep=0x03,
                    timeout=0
                )
                logger.info("Drucker erfolgreich verbunden (Alternative Endpunkte)")
                return printer
            except Exception as e2:
                logger.error(f"Beide Verbindungsversuche fehlgeschlagen: {str(e2)}")
                raise
    
    def release_printer(self):
        """Gibt die Druckerverbindung frei"""
        with self._connection_lock:
            if self.printer is not None:
                try:
                    self.printer.close()
                except:
                    pass
                self.printer = None
    
    def test_connection(self):
        """Testet die Druckerverbindung"""
        try:
            printer = self.get_printer()
            if printer:
                printer.text("Verbindungstest\n")
                printer.cut()
                logger.info("Druckertest erfolgreich")
                return True
            return False
        except Exception as e:
            logger.error(f"Druckertest fehlgeschlagen: {str(e)}")
            return False
