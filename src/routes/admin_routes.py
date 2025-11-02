"""Admin routes for management interface"""

import logging
from functools import wraps
from flask import render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import check_password_hash

logger = logging.getLogger(__name__)


def admin_required(f):
    """Decorator für Admin-geschützte Routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Bitte als Admin einloggen')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


def register_routes(app, order_manager, storage):
    """Registriert die Admin-Routes"""
    
    @app.route('/admin/login', methods=['GET', 'POST'])
    def admin_login():
        """Admin-Login"""
        if request.method == 'POST':
            password = request.form.get('password', '')
            logger.info("Admin-Login-Versuch")
            
            if not password:
                flash('Bitte geben Sie ein Passwort ein')
                return render_template('admin_login.html')
            
            if check_password_hash(app.config['ADMIN_PASSWORD_HASH'], password):
                session.clear()
                session['is_admin'] = True
                session.permanent = True
                logger.info("Admin-Login erfolgreich")
                return redirect(url_for('admin_panel'))
            
            logger.warning("Admin-Login fehlgeschlagen")
            flash('Falsches Passwort')
        
        return render_template('admin_login.html')
    
    @app.route('/admin/logout')
    def admin_logout():
        """Admin-Logout"""
        if session.get('is_admin'):
            logger.info("Admin-Logout")
        session.pop('is_admin', None)
        return redirect(url_for('table_selection'))
    
    @app.route('/admin', methods=['GET', 'POST'])
    @admin_required
    def admin_panel():
        """Admin-Panel"""
        if request.method == 'POST':
            try:
                action = request.form.get('action')
                
                if action == 'add_kategorie':
                    name = request.form.get('kategorie_name', '').strip()
                    if name and name not in [k['name'] for k in order_manager.categories]:
                        order_manager.categories.append({
                            'id': len(order_manager.categories) + 1,
                            'name': name
                        })
                        storage.save_data(order_manager.categories_file, order_manager.categories)
                        flash('Kategorie hinzugefügt')
                
                elif action == 'add_produkt':
                    name = request.form.get('produkt_name', '').strip()
                    kategorie_id = int(request.form.get('kategorie_id', 0))
                    price = float(request.form.get('price', 0.0))
                    
                    if name and kategorie_id and any(k['id'] == kategorie_id for k in order_manager.categories):
                        order_manager.products.append({
                            'id': len(order_manager.products) + 1,
                            'name': name,
                            'kategorie': kategorie_id,
                            'price': price
                        })
                        storage.save_data(order_manager.products_file, order_manager.products)
                        flash('Produkt hinzugefügt')
                
                elif action == 'update_price':
                    produkt_id = int(request.form.get('produkt_id', 0))
                    new_price = float(request.form.get('price', 0.0))
                    
                    for produkt in order_manager.products:
                        if produkt['id'] == produkt_id:
                            produkt['price'] = new_price
                            break
                    storage.save_data(order_manager.products_file, order_manager.products)
                    flash('Preis aktualisiert')
                
                elif action == 'delete_kategorie':
                    kategorie_id = int(request.form.get('kategorie_id', 0))
                    order_manager.categories = [k for k in order_manager.categories if k['id'] != kategorie_id]
                    order_manager.products = [p for p in order_manager.products if p['kategorie'] != kategorie_id]
                    storage.save_data(order_manager.categories_file, order_manager.categories)
                    storage.save_data(order_manager.products_file, order_manager.products)
                    flash('Kategorie gelöscht')
                
                elif action == 'delete_produkt':
                    produkt_id = int(request.form.get('produkt_id', 0))
                    order_manager.products = [p for p in order_manager.products if p['id'] != produkt_id]
                    storage.save_data(order_manager.products_file, order_manager.products)
                    flash('Produkt gelöscht')
                
                order_manager.reload_data()
                return redirect(url_for('admin_panel'))
                
            except Exception as e:
                logger.error(f"Fehler im Admin-Panel: {str(e)}")
                flash('Ein Fehler ist aufgetreten')
                return redirect(url_for('admin_panel'))
        
        # Lade aktuelle Daten
        order_manager.reload_data()
        
        from datetime import datetime
        return render_template(
            'admin_panel.html',
            kategorien=order_manager.categories,
            produkte=order_manager.products,
            bestellungen=order_manager.orders,
            current_time=datetime.now()
        )
    
    @app.route('/admin/cleanup-orders', methods=['POST'])
    @admin_required
    def cleanup_orders():
        """Löscht erledigte Bestellungen"""
        try:
            deleted_count = order_manager.delete_completed_orders()
            return jsonify({
                'success': True,
                'message': f'{deleted_count} erledigte Bestellungen gelöscht'
            })
        except Exception as e:
            logger.error(f"Fehler beim Aufräumen: {str(e)}")
            return jsonify({'success': False, 'message': 'Fehler beim Löschen'})
    
    @app.route('/delete-order/<int:order_id>', methods=['POST'])
    @admin_required
    def delete_order(order_id):
        """Löscht eine Bestellung"""
        try:
            if order_manager.delete_order(order_id):
                order_manager.save_orders()
                return jsonify({'success': True})
            return jsonify({'success': False, 'message': 'Bestellung nicht gefunden'})
        except Exception as e:
            logger.error(f"Fehler beim Löschen: {str(e)}")
            return jsonify({'success': False, 'message': 'Fehler beim Löschen'})
    
    @app.route('/update-order-status/<int:order_id>', methods=['POST'])
    @admin_required
    def update_order_status(order_id):
        """Aktualisiert den Bestellstatus"""
        try:
            data = request.get_json()
            new_status = data.get('status')
            
            if new_status not in ['neu', 'erledigt', 'archiviert']:
                return jsonify({'success': False, 'message': 'Ungültiger Status'})
            
            if order_manager.update_order_status(order_id, new_status):
                order_manager.save_orders()
                return jsonify({'success': True})
            
            return jsonify({'success': False, 'message': 'Bestellung nicht gefunden'})
        except Exception as e:
            logger.error(f"Fehler beim Status-Update: {str(e)}")
            return jsonify({'success': False, 'message': 'Fehler beim Aktualisieren'})
