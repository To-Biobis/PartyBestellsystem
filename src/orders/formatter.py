"""Order formatting for printing"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class OrderFormatter:
    """Formatiert Bestellungen für den Druck"""
    
    def __init__(self, paper_width=32):
        """Initialisiert den OrderFormatter"""
        self.paper_width = paper_width
    
    def format_orders_for_category(self, table, category_name, orders):
        """Formatiert Bestellungen einer Kategorie für den Druck"""
        lines = []
        
        # Header
        lines.append(f"Tisch {table} - {category_name}\n")
        lines.append("=" * self.paper_width + "\n")
        
        # Bestellungen
        total_price = 0.0
        for order in orders:
            zeitpunkt = datetime.fromisoformat(order['zeitpunkt']).strftime('%H:%M')
            einzelpreis = order.get('price', 0.0)
            gesamtpreis = einzelpreis * order['menge']
            total_price += gesamtpreis
            
            lines.append(f"{order['menge']}x {order['produkt']}\n")
            lines.append(f"   {order['menge']} x {einzelpreis:.2f}€ = {gesamtpreis:.2f}€\n")
            
            if order.get('kommentar'):
                lines.append(f"   Kommentar: {order['kommentar']}\n")
            
            lines.append(f"   Zeit: {zeitpunkt}\n")
            lines.append("-" * self.paper_width + "\n")
        
        # Gesamtpreis
        lines.append(f"\nGesamtpreis {category_name}: {total_price:.2f}€\n")
        lines.append("=" * self.paper_width + "\n\n")
        
        return "".join(lines)
    
    def format_receipt(self, table, orders, template=None):
        """Formatiert einen kompletten Beleg"""
        if template is None:
            template = self._get_default_template()
        
        lines = []
        
        # Header
        if template.get('header'):
            header = template['header']
            lines.append(header.get('text', ''))
        
        lines.append(f"\nTisch {table}\n")
        lines.append("=" * self.paper_width + "\n")
        
        # Bestellungen
        total_price = 0.0
        for order in orders:
            zeitpunkt = datetime.fromisoformat(order['zeitpunkt']).strftime('%H:%M')
            einzelpreis = order.get('price', 0.0)
            gesamtpreis = einzelpreis * order['menge']
            total_price += gesamtpreis
            
            lines.append(f"{order['menge']}x {order['produkt']}\n")
            lines.append(f"   {einzelpreis:.2f}€ x {order['menge']} = {gesamtpreis:.2f}€\n")
            
            if order.get('kommentar'):
                lines.append(f"   Kommentar: {order['kommentar']}\n")
        
        # Gesamtpreis
        lines.append("-" * self.paper_width + "\n")
        lines.append(f"GESAMT: {total_price:.2f}€\n")
        lines.append("=" * self.paper_width + "\n")
        
        # Footer
        if template.get('footer'):
            footer = template['footer']
            lines.append(footer.get('text', ''))
        
        return "".join(lines)
    
    def _get_default_template(self):
        """Gibt ein Standard-Template zurück"""
        return {
            'header': {'text': 'Bestellung\n'},
            'footer': {'text': '\nVielen Dank!\n'}
        }
