"""Multi-printer management with category-based routing"""

import logging
from typing import Dict, Optional
from threading import Lock

from .manager import PrinterManager
from .config import PrinterConfig, PrinterConfigManager

logger = logging.getLogger(__name__)


class MultiPrinterManager:
    """Manages multiple printers with category-based routing"""
    
    def __init__(self, config_manager: PrinterConfigManager):
        """Initialize multi-printer manager
        
        Args:
            config_manager: PrinterConfigManager instance
        """
        self.config_manager = config_manager
        self.printer_managers: Dict[str, PrinterManager] = {}
        self._lock = Lock()
        self._initialize_printers()
    
    def _initialize_printers(self):
        """Initialize all printer managers based on configuration"""
        with self._lock:
            enabled_printers = self.config_manager.get_enabled_printers()
            
            for printer_config in enabled_printers:
                try:
                    printer_manager = PrinterManager(
                        vendor_id=printer_config.vendor_id,
                        product_id=printer_config.product_id
                    )
                    self.printer_managers[printer_config.printer_id] = printer_manager
                    logger.info(f"Initialized printer: {printer_config.name} "
                              f"(ID: {printer_config.printer_id})")
                except Exception as e:
                    logger.error(f"Failed to initialize printer {printer_config.name}: {str(e)}")
    
    def get_printer_for_category(self, category_name: str) -> Optional[PrinterManager]:
        """Get the printer manager that should handle a specific category
        
        Args:
            category_name: Name of the category
            
        Returns:
            PrinterManager instance or None
        """
        printer_config = self.config_manager.get_printer_for_category(category_name)
        
        if not printer_config:
            logger.warning(f"No printer configured for category: {category_name}")
            return None
        
        printer_manager = self.printer_managers.get(printer_config.printer_id)
        
        if not printer_manager:
            logger.error(f"Printer manager not found for: {printer_config.printer_id}")
            return None
        
        return printer_manager
    
    def get_printer_by_id(self, printer_id: str) -> Optional[PrinterManager]:
        """Get a printer manager by its ID
        
        Args:
            printer_id: Printer identifier
            
        Returns:
            PrinterManager instance or None
        """
        return self.printer_managers.get(printer_id)
    
    def get_default_printer(self) -> Optional[PrinterManager]:
        """Get the default printer (first enabled printer or 'default')
        
        Returns:
            PrinterManager instance or None
        """
        # Try to get 'default' printer
        if 'default' in self.printer_managers:
            return self.printer_managers['default']
        
        # Return first available printer
        if self.printer_managers:
            return next(iter(self.printer_managers.values()))
        
        return None
    
    def reload_configuration(self):
        """Reload printer configuration and reinitialize printers"""
        logger.info("Reloading printer configuration...")
        self.config_manager.load_config()
        
        # Release existing printers
        with self._lock:
            for printer_manager in self.printer_managers.values():
                try:
                    printer_manager.release_printer()
                except Exception as e:
                    logger.error(f"Error releasing printer: {e}")
            
            self.printer_managers.clear()
        
        # Reinitialize
        self._initialize_printers()
        logger.info("Printer configuration reloaded")
    
    def test_printer(self, printer_id: str) -> bool:
        """Test a specific printer connection
        
        Args:
            printer_id: Printer identifier
            
        Returns:
            True if test successful, False otherwise
        """
        printer_manager = self.get_printer_by_id(printer_id)
        
        if not printer_manager:
            logger.error(f"Printer not found: {printer_id}")
            return False
        
        return printer_manager.test_connection()
    
    def test_all_printers(self) -> Dict[str, bool]:
        """Test all printers
        
        Returns:
            Dictionary mapping printer_id to test result
        """
        results = {}
        
        for printer_id, printer_manager in self.printer_managers.items():
            try:
                results[printer_id] = printer_manager.test_connection()
            except Exception as e:
                logger.error(f"Error testing printer {printer_id}: {str(e)}")
                results[printer_id] = False
        
        return results
    
    def get_printer_info(self) -> Dict[str, Dict]:
        """Get information about all configured printers
        
        Returns:
            Dictionary with printer information
        """
        info = {}
        
        for printer_id, printer_config in self.config_manager.printers.items():
            info[printer_id] = {
                'name': printer_config.name,
                'vendor_id': hex(printer_config.vendor_id),
                'product_id': hex(printer_config.product_id),
                'categories': printer_config.categories,
                'enabled': printer_config.enabled,
                'initialized': printer_id in self.printer_managers
            }
        
        return info
