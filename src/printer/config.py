"""Modular printer configuration management"""

import json
import logging
import os
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class PrinterConfig:
    """Configuration for a single printer"""
    
    def __init__(self, printer_id: str, name: str, vendor_id: int, product_id: int, 
                 categories: List[str] = None, enabled: bool = True):
        """Initialize printer configuration
        
        Args:
            printer_id: Unique identifier for the printer
            name: Human-readable printer name
            vendor_id: USB vendor ID in decimal format (e.g., 0x04b8 = 1208)
            product_id: USB product ID in decimal format (e.g., 0x0e15 = 3605)
            categories: List of category names this printer handles
            enabled: Whether the printer is active
        """
        self.printer_id = printer_id
        self.name = name
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.categories = categories or []
        self.enabled = enabled
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'printer_id': self.printer_id,
            'name': self.name,
            'vendor_id': self.vendor_id,
            'product_id': self.product_id,
            'categories': self.categories,
            'enabled': self.enabled
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'PrinterConfig':
        """Create from dictionary"""
        return PrinterConfig(
            printer_id=data['printer_id'],
            name=data['name'],
            vendor_id=data['vendor_id'],
            product_id=data['product_id'],
            categories=data.get('categories', []),
            enabled=data.get('enabled', True)
        )


class PrinterConfigManager:
    """Manages printer configurations"""
    
    def __init__(self, config_file: str):
        """Initialize printer configuration manager
        
        Args:
            config_file: Path to printer configuration JSON file
        """
        self.config_file = config_file
        self.printers: Dict[str, PrinterConfig] = {}
        self.load_config()
    
    def load_config(self):
        """Load printer configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                for printer_data in data.get('printers', []):
                    printer = PrinterConfig.from_dict(printer_data)
                    self.printers[printer.printer_id] = printer
                
                logger.info(f"Loaded {len(self.printers)} printer configurations")
            else:
                logger.info("No printer configuration file found, using defaults")
                self._create_default_config()
        except Exception as e:
            logger.error(f"Error loading printer config: {str(e)}")
            self._create_default_config()
    
    def _create_default_config(self):
        """Create default printer configuration"""
        # Default printer configuration
        default_printer = PrinterConfig(
            printer_id="default",
            name="Default Printer",
            vendor_id=0x04b8,  # Epson
            product_id=0x0e15,  # TM-T20II
            categories=[],  # Empty means all categories
            enabled=True
        )
        self.printers['default'] = default_printer
        self.save_config()
    
    def save_config(self):
        """Save printer configuration to file"""
        try:
            data = {
                'printers': [p.to_dict() for p in self.printers.values()]
            }
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info("Printer configuration saved")
        except Exception as e:
            logger.error(f"Error saving printer config: {str(e)}")
    
    def add_printer(self, printer: PrinterConfig):
        """Add or update a printer configuration"""
        self.printers[printer.printer_id] = printer
        self.save_config()
        logger.info(f"Added printer: {printer.name}")
    
    def remove_printer(self, printer_id: str):
        """Remove a printer configuration"""
        if printer_id in self.printers:
            del self.printers[printer_id]
            self.save_config()
            logger.info(f"Removed printer: {printer_id}")
    
    def get_printer(self, printer_id: str) -> Optional[PrinterConfig]:
        """Get printer by ID"""
        return self.printers.get(printer_id)
    
    def get_printer_for_category(self, category_name: str) -> Optional[PrinterConfig]:
        """Get the printer that should handle a specific category
        
        Args:
            category_name: Name of the category
            
        Returns:
            PrinterConfig for the category, or default printer, or None
        """
        # Find printer with this category assigned
        for printer in self.printers.values():
            if not printer.enabled:
                continue
            if category_name in printer.categories:
                return printer
        
        # Fall back to printer with empty categories (handles all)
        for printer in self.printers.values():
            if not printer.enabled:
                continue
            if not printer.categories:  # Empty means handles all categories
                return printer
        
        # No suitable printer found
        logger.warning(f"No printer configured for category: {category_name}")
        return None
    
    def get_all_printers(self) -> List[PrinterConfig]:
        """Get all printer configurations"""
        return list(self.printers.values())
    
    def get_enabled_printers(self) -> List[PrinterConfig]:
        """Get all enabled printer configurations"""
        return [p for p in self.printers.values() if p.enabled]
