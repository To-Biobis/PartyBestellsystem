"""Order processing routes"""

import logging
import threading
from flask import request, session, redirect, url_for, jsonify

logger = logging.getLogger(__name__)


def register_routes(app, order_manager, order_formatter, print_queue_manager):
    """Registriert die Bestellungs-Routes"""
    
    @app.route('/orders', methods=['POST'])
    def create_orders():
        """Erstellt neue Bestellungen und druckt sie sofort"""
        try:
            if 'current_table' not in session:
                return jsonify({
                    'success': False,
                    'message': 'Keine Tischnummer ausgewählt'
                }), 400
            
            data = request.get_json()
            if not data or 'orders' not in data:
                return jsonify({
                    'success': False,
                    'message': 'Keine Bestellungen empfangen'
                }), 400
            
            orders_data = data['orders']
            if not isinstance(orders_data, list) or not orders_data:
                return jsonify({
                    'success': False,
                    'message': 'Ungültiges Bestellungsformat'
                }), 400
            
            table = str(session['current_table'])
            logger.info(f"Neue Bestellung für Tisch {table}: {len(orders_data)} Artikel")
            
            # Erstelle Bestellungen
            created_orders = []
            for order_data in orders_data:
                if not isinstance(order_data, dict):
                    continue
                
                product_id = order_data.get('produkt')
                quantity = order_data.get('menge')
                comment = order_data.get('kommentar', '')
                
                if not product_id or not quantity:
                    continue
                
                order = order_manager.create_order(table, product_id, quantity, comment)
                if order:
                    created_orders.append(order)
            
            if not created_orders:
                return jsonify({
                    'success': False,
                    'message': 'Keine gültigen Bestellungen'
                }), 400
            
            # Speichere Bestellungen
            if not order_manager.save_orders():
                return jsonify({
                    'success': False,
                    'message': 'Fehler beim Speichern der Bestellungen'
                }), 500
            
            # Drucke Bestellungen asynchron aber SOFORT
            def print_orders_async():
                try:
                    _print_new_orders(table, created_orders, order_manager, order_formatter, print_queue_manager)
                except Exception as e:
                    logger.error(f"Fehler beim Drucken: {str(e)}")
            
            # Starte Druckthread
            print_thread = threading.Thread(target=print_orders_async, daemon=True)
            print_thread.start()
            
            return jsonify({
                'success': True,
                'message': f'{len(created_orders)} Bestellungen erfolgreich gespeichert und werden gedruckt'
            })
            
        except Exception as e:
            logger.error(f"Fehler bei der Bestellungsverarbeitung: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Interner Serverfehler'
            }), 500


def _print_new_orders(table, orders, order_manager, order_formatter, print_queue_manager):
    """Druckt neue Bestellungen sofort, gruppiert nach Kategorien"""
    try:
        # Markiere als "in_druck"
        order_ids = [o['id'] for o in orders]
        for order_id in order_ids:
            order_manager.update_order_status(order_id, 'in_druck')
        order_manager.save_orders()
        
        # Gruppiere nach Kategorien
        grouped = order_manager.group_orders_by_category(orders)
        
        # Erstelle Druckaufträge für jede Kategorie
        for category_id, category_orders in grouped.items():
            category = order_manager.get_category_by_id(category_id)
            category_name = category['name'] if category else f"Kategorie {category_id}"
            
            # Formatiere Druckinhalt
            content = order_formatter.format_orders_for_category(
                table,
                category_name,
                category_orders
            )
            
            # Erstelle Job-ID
            job_order_ids = [o['id'] for o in category_orders]
            job_id = f"{table}_{category_id}_{'-'.join(map(str, job_order_ids))}"
            
            # Callback für Druckerfolg/-fehler
            def print_callback(success, job_id_param):
                try:
                    # Extrahiere Order-IDs aus Job-ID
                    parts = job_id_param.split('_')
                    order_ids_str = parts[-1].split('-')
                    callback_order_ids = [int(oid) for oid in order_ids_str]
                    
                    if success:
                        # Markiere als erledigt
                        for oid in callback_order_ids:
                            order_manager.update_order_status(oid, 'erledigt')
                        logger.info(f"Bestellungen {callback_order_ids} erfolgreich gedruckt")
                    else:
                        # Setze auf "neu" zurück bei Fehler
                        for oid in callback_order_ids:
                            order_manager.update_order_status(oid, 'neu')
                        logger.error(f"Druck für Bestellungen {callback_order_ids} fehlgeschlagen")
                    
                    order_manager.save_orders()
                except Exception as e:
                    logger.error(f"Fehler im Print-Callback: {str(e)}")
            
            # Füge zur Druckwarteschlange hinzu
            print_queue_manager.add_print_job(content, job_id, print_callback)
            logger.info(f"Druckauftrag für Kategorie {category_name} erstellt: {job_id}")
        
    except Exception as e:
        logger.error(f"Fehler beim Drucken der Bestellungen: {str(e)}")
        # Setze Status zurück bei Fehler
        for order in orders:
            order_manager.update_order_status(order['id'], 'neu')
        order_manager.save_orders()
