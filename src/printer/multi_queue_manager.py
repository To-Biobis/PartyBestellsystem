"""Multi-printer queue management with category-based routing"""

import logging
from typing import Dict, Optional, Callable
from threading import Lock

from .queue_manager import PrintQueueManager
from .multi_manager import MultiPrinterManager

logger = logging.getLogger(__name__)


class MultiPrinterQueueManager:
    """Manages print queues for multiple printers with category routing"""
    
    def __init__(self, multi_printer_manager: MultiPrinterManager, 
                 max_retries: int = 3, retry_delay: int = 1):
        """Initialize multi-printer queue manager
        
        Args:
            multi_printer_manager: MultiPrinterManager instance
            max_retries: Maximum number of print retries
            retry_delay: Delay between retries in seconds
        """
        self.multi_printer_manager = multi_printer_manager
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.queue_managers: Dict[str, PrintQueueManager] = {}
        self._lock = Lock()
        self._initialize_queues()
    
    def _initialize_queues(self):
        """Initialize queue managers for all printers"""
        with self._lock:
            for printer_id, printer_manager in self.multi_printer_manager.printer_managers.items():
                try:
                    queue_manager = PrintQueueManager(
                        printer_manager=printer_manager,
                        max_retries=self.max_retries,
                        retry_delay=self.retry_delay
                    )
                    self.queue_managers[printer_id] = queue_manager
                    logger.info(f"Initialized queue for printer: {printer_id}")
                except Exception as e:
                    logger.error(f"Failed to initialize queue for printer {printer_id}: {str(e)}")
    
    def start_all_workers(self) -> Dict[str, bool]:
        """Start all print queue workers
        
        Returns:
            Dictionary mapping printer_id to start success status
        """
        results = {}
        
        for printer_id, queue_manager in self.queue_managers.items():
            try:
                success = queue_manager.start_worker()
                results[printer_id] = success
                if success:
                    logger.info(f"Started worker for printer: {printer_id}")
                else:
                    logger.error(f"Failed to start worker for printer: {printer_id}")
            except Exception as e:
                logger.error(f"Error starting worker for printer {printer_id}: {str(e)}")
                results[printer_id] = False
        
        return results
    
    def stop_all_workers(self):
        """Stop all print queue workers"""
        for printer_id, queue_manager in self.queue_managers.items():
            try:
                queue_manager.stop_worker()
                logger.info(f"Stopped worker for printer: {printer_id}")
            except Exception as e:
                logger.error(f"Error stopping worker for printer {printer_id}: {str(e)}")
    
    def add_print_job_for_category(self, content: str, category_name: str, 
                                   job_id: str, callback: Optional[Callable] = None) -> bool:
        """Add a print job to the appropriate printer queue based on category
        
        Args:
            content: Content to print
            category_name: Category name to determine printer
            job_id: Unique job identifier
            callback: Optional callback function
            
        Returns:
            True if job was added successfully, False otherwise
        """
        # Get the printer for this category
        printer_manager = self.multi_printer_manager.get_printer_for_category(category_name)
        
        if not printer_manager:
            logger.error(f"No printer available for category: {category_name}")
            if callback:
                callback(False, job_id)
            return False
        
        # Find the corresponding queue manager
        printer_id = None
        for pid, pm in self.multi_printer_manager.printer_managers.items():
            if pm == printer_manager:
                printer_id = pid
                break
        
        if not printer_id or printer_id not in self.queue_managers:
            logger.error(f"Queue manager not found for category: {category_name}")
            if callback:
                callback(False, job_id)
            return False
        
        queue_manager = self.queue_managers[printer_id]
        
        logger.info(f"Routing print job {job_id} to printer {printer_id} for category {category_name}")
        return queue_manager.add_print_job(content, job_id, callback)
    
    def add_print_job_to_printer(self, content: str, printer_id: str, 
                                job_id: str, callback: Optional[Callable] = None) -> bool:
        """Add a print job to a specific printer queue
        
        Args:
            content: Content to print
            printer_id: Target printer identifier
            job_id: Unique job identifier
            callback: Optional callback function
            
        Returns:
            True if job was added successfully, False otherwise
        """
        if printer_id not in self.queue_managers:
            logger.error(f"Printer not found: {printer_id}")
            if callback:
                callback(False, job_id)
            return False
        
        queue_manager = self.queue_managers[printer_id]
        return queue_manager.add_print_job(content, job_id, callback)
    
    def add_print_job_to_default(self, content: str, job_id: str, 
                                callback: Optional[Callable] = None) -> bool:
        """Add a print job to the default printer
        
        Args:
            content: Content to print
            job_id: Unique job identifier
            callback: Optional callback function
            
        Returns:
            True if job was added successfully, False otherwise
        """
        printer_manager = self.multi_printer_manager.get_default_printer()
        
        if not printer_manager:
            logger.error("No default printer available")
            if callback:
                callback(False, job_id)
            return False
        
        # Find printer_id for default printer
        printer_id = None
        for pid, pm in self.multi_printer_manager.printer_managers.items():
            if pm == printer_manager:
                printer_id = pid
                break
        
        if not printer_id or printer_id not in self.queue_managers:
            logger.error("Default printer queue manager not found")
            if callback:
                callback(False, job_id)
            return False
        
        queue_manager = self.queue_managers[printer_id]
        return queue_manager.add_print_job(content, job_id, callback)
    
    def get_queue_status(self) -> Dict[str, Dict]:
        """Get status of all printer queues
        
        Returns:
            Dictionary with queue status for each printer
        """
        status = {}
        
        for printer_id, queue_manager in self.queue_managers.items():
            status[printer_id] = {
                'queue_size': queue_manager.get_queue_size(),
                'is_empty': queue_manager.is_queue_empty(),
                'worker_active': queue_manager.worker_active
            }
        
        return status
    
    def reload_configuration(self):
        """Reload printer configuration and reinitialize queues"""
        logger.info("Reloading printer configuration for queues...")
        
        # Stop all workers
        self.stop_all_workers()
        
        # Clear existing queues
        with self._lock:
            self.queue_managers.clear()
        
        # Reload printer configuration
        self.multi_printer_manager.reload_configuration()
        
        # Reinitialize queues
        self._initialize_queues()
        
        # Restart workers
        self.start_all_workers()
        
        logger.info("Queue configuration reloaded")
