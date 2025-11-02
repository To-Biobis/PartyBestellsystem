"""Print queue management with instant printing"""

import logging
import time
import threading
from queue import Queue, Empty
from threading import Lock

logger = logging.getLogger(__name__)


class PrintQueueManager:
    """Verwaltet die Druckwarteschlange mit sofortiger Verarbeitung"""
    
    def __init__(self, printer_manager, max_retries=3, retry_delay=1):
        """Initialisiert den Queue Manager"""
        self.printer_manager = printer_manager
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.print_queue = Queue()
        self.print_lock = Lock()
        self.worker_thread = None
        self.worker_active = False
        self._callbacks = {}
    
    def start_worker(self):
        """Startet den Hintergrund-Worker"""
        if self.worker_thread and self.worker_thread.is_alive():
            logger.info("Print worker bereits aktiv")
            return True
        
        # Teste Druckerverbindung vor dem Start
        if not self.printer_manager.test_connection():
            logger.error("Druckerverbindung konnte nicht hergestellt werden")
            return False
        
        self.worker_active = True
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="PrintWorker"
        )
        self.worker_thread.start()
        logger.info("Print worker gestartet")
        return True
    
    def stop_worker(self):
        """Stoppt den Hintergrund-Worker"""
        if self.worker_active:
            self.worker_active = False
            self.print_queue.put(None)  # Poison pill
            if self.worker_thread:
                self.worker_thread.join(timeout=5)
            logger.info("Print worker gestoppt")
    
    def add_print_job(self, content, job_id, callback=None):
        """Fügt einen Druckauftrag zur Warteschlange hinzu
        
        Args:
            content: Der zu druckende Inhalt
            job_id: Eindeutige ID für den Auftrag
            callback: Optional - Funktion die bei Erfolg/Fehler aufgerufen wird
        """
        self.print_queue.put((content, 0, job_id))
        if callback:
            self._callbacks[job_id] = callback
        logger.info(f"Druckauftrag {job_id} zur Warteschlange hinzugefügt")
        return True
    
    def _worker_loop(self):
        """Haupt-Worker-Loop für die Druckverarbeitung"""
        logger.info("Print worker Loop gestartet")
        
        while self.worker_active:
            try:
                # Hole nächsten Auftrag (mit Timeout für sauberes Beenden)
                try:
                    job = self.print_queue.get(timeout=1)
                except Empty:
                    continue
                
                if job is None:  # Poison pill
                    logger.info("Poison pill erhalten, beende Worker")
                    break
                
                content, retry_count, job_id = job
                
                # Verarbeite Druckauftrag SOFORT
                success = self._process_print_job(content, retry_count, job_id)
                
                # Rufe Callback auf falls vorhanden
                if job_id in self._callbacks:
                    callback = self._callbacks.pop(job_id)
                    try:
                        callback(success, job_id)
                    except Exception as e:
                        logger.error(f"Fehler beim Callback für Job {job_id}: {str(e)}")
                
                self.print_queue.task_done()
                
            except Exception as e:
                logger.error(f"Fehler im Print Worker Loop: {str(e)}")
                time.sleep(1)
        
        logger.info("Print worker Loop beendet")
    
    def _process_print_job(self, content, retry_count, job_id):
        """Verarbeitet einen einzelnen Druckauftrag"""
        try:
            with self.print_lock:
                printer = self.printer_manager.get_printer()
                
                if not printer:
                    logger.error(f"Drucker nicht verfügbar für Job {job_id}")
                    return self._handle_print_failure(content, retry_count, job_id)
                
                # SOFORTIGER Druck ohne künstliche Verzögerungen
                printer.text(content)
                printer.cut()
                
                logger.info(f"Druckauftrag {job_id} erfolgreich ausgeführt")
                return True
                
        except Exception as e:
            logger.error(f"Druckfehler für Job {job_id}: {str(e)}")
            return self._handle_print_failure(content, retry_count, job_id)
    
    def _handle_print_failure(self, content, retry_count, job_id):
        """Behandelt Druckfehler mit Retry-Logik"""
        if retry_count < self.max_retries:
            # Exponentielles Backoff bei Wiederholungen
            delay = self.retry_delay * (2 ** retry_count)
            time.sleep(delay)
            
            logger.info(f"Wiederhole Druckauftrag {job_id} (Versuch {retry_count + 2})")
            self.print_queue.put((content, retry_count + 1, job_id))
            return False
        else:
            logger.error(f"Maximale Wiederholungen für Job {job_id} erreicht")
            return False
    
    def get_queue_size(self):
        """Gibt die aktuelle Größe der Warteschlange zurück"""
        return self.print_queue.qsize()
    
    def is_queue_empty(self):
        """Prüft ob die Warteschlange leer ist"""
        return self.print_queue.empty()
