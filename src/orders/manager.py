"""Order management and processing"""

import logging
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class OrderManager:
    """Verwaltet Bestellungen und deren Verarbeitung"""
    
    def __init__(self, storage, products_file, categories_file, orders_file):
        """Initialisiert den OrderManager"""
        self.storage = storage
        self.products_file = products_file
        self.categories_file = categories_file
        self.orders_file = orders_file
        
        # Lade initiale Daten
        self.products = self.storage.load_data(products_file, [])
        self.categories = self.storage.load_data(categories_file, [])
        self.orders = self.storage.load_data(orders_file, [])
    
    def reload_data(self):
        """Lädt alle Daten neu"""
        self.products = self.storage.load_data(self.products_file, [])
        self.categories = self.storage.load_data(self.categories_file, [])
        self.orders = self.storage.load_data(self.orders_file, [])
    
    def get_product_by_id(self, product_id):
        """Findet ein Produkt anhand seiner ID"""
        return next((p for p in self.products if str(p['id']) == str(product_id)), None)
    
    def get_category_by_id(self, category_id):
        """Findet eine Kategorie anhand ihrer ID"""
        return next((c for c in self.categories if c['id'] == category_id), None)
    
    def create_order(self, table, product_id, quantity, comment=''):
        """Erstellt eine neue Bestellung"""
        product = self.get_product_by_id(product_id)
        if not product:
            logger.warning(f"Produkt nicht gefunden: {product_id}")
            return None
        
        if quantity <= 0 or quantity > 99:
            logger.warning(f"Ungültige Menge: {quantity}")
            return None
        
        order = {
            'id': self._get_next_order_id(),
            'tisch': str(table),
            'produkt': product['name'],
            'menge': int(quantity),
            'kommentar': str(comment).strip()[:200],
            'kategorie': product['kategorie'],
            'price': product.get('price', 0.0),
            'zeitpunkt': datetime.now().isoformat(),
            'status': 'neu'
        }
        
        self.orders.append(order)
        logger.info(f"Neue Bestellung erstellt: ID={order['id']}, Tisch={table}, Produkt={product['name']}")
        return order
    
    def _get_next_order_id(self):
        """Ermittelt die nächste freie Bestellungs-ID"""
        if not self.orders:
            return 1
        return max(o['id'] for o in self.orders) + 1
    
    def save_orders(self):
        """Speichert alle Bestellungen"""
        return self.storage.save_data(self.orders_file, self.orders)
    
    def get_orders_by_table(self, table):
        """Gibt alle Bestellungen für einen Tisch zurück"""
        return [o for o in self.orders if str(o['tisch']) == str(table)]
    
    def get_orders_by_status(self, status):
        """Gibt alle Bestellungen mit einem bestimmten Status zurück"""
        return [o for o in self.orders if o['status'] == status]
    
    def get_new_orders_by_table(self, table):
        """Gibt neue Bestellungen für einen Tisch zurück"""
        return [o for o in self.orders 
                if str(o['tisch']) == str(table) and o['status'] == 'neu']
    
    def group_orders_by_category(self, orders):
        """Gruppiert Bestellungen nach Kategorien"""
        grouped = defaultdict(list)
        for order in orders:
            category_id = order.get('kategorie')
            grouped[category_id].append(order)
        return dict(grouped)
    
    def update_order_status(self, order_id, new_status):
        """Aktualisiert den Status einer Bestellung"""
        for order in self.orders:
            if order['id'] == order_id:
                order['status'] = new_status
                if new_status == 'erledigt':
                    order['erledigt_um'] = datetime.now().isoformat()
                logger.info(f"Bestellung {order_id} Status aktualisiert: {new_status}")
                return True
        return False
    
    def delete_order(self, order_id):
        """Löscht eine Bestellung"""
        original_count = len(self.orders)
        self.orders = [o for o in self.orders if o['id'] != order_id]
        deleted = len(self.orders) < original_count
        if deleted:
            logger.info(f"Bestellung {order_id} gelöscht")
        return deleted
    
    def delete_completed_orders(self):
        """Löscht alle erledigten Bestellungen"""
        before_count = len(self.orders)
        self.orders = [o for o in self.orders if o['status'] in ['neu', 'in_druck', 'archiviert']]
        deleted_count = before_count - len(self.orders)
        
        if deleted_count > 0:
            self.save_orders()
            logger.info(f"{deleted_count} erledigte Bestellungen gelöscht")
        return deleted_count
    
    def calculate_order_total(self, order):
        """Berechnet den Gesamtpreis einer Bestellung"""
        product = next((p for p in self.products if p['name'] == order['produkt']), None)
        if product and 'price' in product:
            return float(product['price']) * order['menge']
        return 0.0
    
    def calculate_table_total(self, table):
        """Berechnet den Gesamtpreis aller Bestellungen eines Tisches"""
        table_orders = self.get_orders_by_table(table)
        return sum(self.calculate_order_total(o) for o in table_orders)
