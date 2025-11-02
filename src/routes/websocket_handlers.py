"""WebSocket event handlers"""

import logging
from flask import session
from flask_socketio import emit

logger = logging.getLogger(__name__)


def register_handlers(socketio, order_manager):
    """Registriert die WebSocket-Handler"""
    
    @socketio.on('connect')
    def handle_connect():
        """Behandelt neue WebSocket-Verbindungen"""
        if session.get('is_admin'):
            logger.info("Admin-WebSocket-Verbindung hergestellt")
            emit('connection_response', {'data': 'Verbunden'})
        else:
            logger.debug("WebSocket-Verbindung hergestellt")
            emit('connection_response', {'data': 'Verbunden'})
    
    @socketio.on('order_status_update')
    def handle_order_status_update(data):
        """Behandelt Status-Updates von Bestellungen"""
        if not session.get('is_admin'):
            return
        
        try:
            order_id = data.get('order_id')
            new_status = data.get('status')
            
            if new_status not in ['neu', 'erledigt', 'archiviert']:
                return
            
            if order_manager.update_order_status(order_id, new_status):
                order_manager.save_orders()
                
                # Sende Update an alle Clients
                emit('order_updated', {
                    'order_id': order_id,
                    'status': new_status
                }, broadcast=True)
                
                logger.info(f"Bestellung {order_id} Status aktualisiert zu {new_status}")
        except Exception as e:
            logger.error(f"Fehler beim WebSocket-Status-Update: {str(e)}")
            emit('error', {'message': 'Fehler beim Aktualisieren des Status'})
    
    @socketio.on('order_delete')
    def handle_order_delete(data):
        """Behandelt das Löschen von Bestellungen"""
        if not session.get('is_admin'):
            return
        
        try:
            order_id = data.get('order_id')
            
            if order_manager.delete_order(order_id):
                order_manager.save_orders()
                
                # Sende Update an alle Clients
                emit('order_deleted', {
                    'order_id': order_id
                }, broadcast=True)
                
                logger.info(f"Bestellung {order_id} gelöscht")
        except Exception as e:
            logger.error(f"Fehler beim WebSocket-Löschen: {str(e)}")
            emit('error', {'message': 'Fehler beim Löschen der Bestellung'})
    
    @socketio.on('comment_update')
    def handle_comment_update(data):
        """Behandelt Kommentar-Updates"""
        if not session.get('is_admin'):
            emit('error', {'message': 'Keine Berechtigung'})
            return
        
        try:
            order_id = data.get('order_id')
            comment = str(data.get('comment', '')).strip()[:200]
            
            if not order_id:
                emit('error', {'message': 'Keine Bestellungs-ID angegeben'})
                return
            
            # Finde und aktualisiere Bestellung
            for order in order_manager.orders:
                if order['id'] == order_id:
                    order['kommentar'] = comment
                    order_manager.save_orders()
                    
                    # Sende Update an alle Clients
                    emit('comment_updated', {
                        'order_id': order_id,
                        'comment': comment
                    }, broadcast=True)
                    
                    logger.info(f"Kommentar für Bestellung {order_id} aktualisiert")
                    return
            
            emit('error', {'message': 'Bestellung nicht gefunden'})
        except Exception as e:
            logger.error(f"Fehler beim WebSocket-Kommentar-Update: {str(e)}")
            emit('error', {'message': 'Interner Serverfehler'})
