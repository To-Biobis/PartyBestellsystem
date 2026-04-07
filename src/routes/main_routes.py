"""Main application routes"""

import logging
import re
from flask import render_template, request, redirect, url_for, flash, session

logger = logging.getLogger(__name__)

TABLE_NUMBER_PATTERN = re.compile(r'^\d{1,3}$')


def register_routes(app, order_manager):
    """Registriert die Haupt-Routes"""

    @app.route('/', methods=['GET'])
    def table_selection():
        """Tischauswahl"""
        if 'current_table' in session:
            return redirect(url_for('order_page'))
        return render_template('table_selection.html')

    @app.route('/set-table', methods=['POST'])
    def set_table():
        """Setzt die Tischnummer in der Session"""
        table = request.form.get('table', '').strip()
        if not TABLE_NUMBER_PATTERN.match(table):
            flash('Ungültige Tischnummer. Bitte geben Sie eine Zahl zwischen 1 und 999 ein.')
            return redirect(url_for('table_selection'))
        session['current_table'] = table
        logger.info(f"Tisch {table} ausgewählt")
        return redirect(url_for('order_page'))

    @app.route('/new-table')
    def new_table():
        """Setzt die Tischauswahl zurück"""
        session.pop('current_table', None)
        return redirect(url_for('table_selection'))

    @app.route('/orders', methods=['GET'])
    def order_page():
        """Bestellseite für einen Tisch"""
        if 'current_table' not in session:
            logger.warning("Zugriff auf /orders ohne Tischnummer")
            return redirect(url_for('table_selection'))

        # Lade aktuelle Daten
        order_manager.reload_data()
        tisch = str(session['current_table'])
        tisch_bestellungen = order_manager.get_orders_by_table(tisch)

        # Berechne Gesamtpreis
        gesamtpreis = order_manager.calculate_table_total(tisch)

        return render_template(
            'index.html',
            kategorien=order_manager.categories,
            produkte=order_manager.products,
            bestellungen=tisch_bestellungen,
            gesamtpreis=gesamtpreis
        )

    @app.route('/receipt')
    def print_receipt():
        """Druckbare Bon-Ansicht für den aktuellen Tisch.

        Öffnet automatisch den System-Druckdialog (Android-Druckdienst).
        Die Seite kann auch manuell über den 'Bon drucken'-Button erreicht
        werden und funktioniert vollständig ohne CUPS-Verbindung.
        """
        if 'current_table' not in session:
            return redirect(url_for('table_selection'))

        order_manager.reload_data()
        tisch = str(session['current_table'])
        tisch_bestellungen = order_manager.get_orders_by_table(tisch)
        gesamtpreis = order_manager.calculate_table_total(tisch)

        return render_template(
            'print_receipt.html',
            tisch=tisch,
            kategorien=order_manager.categories,
            bestellungen=tisch_bestellungen,
            gesamtpreis=gesamtpreis,
        )

    @app.before_request
    def before_request():
        """Hook vor jeder Anfrage"""
        session.permanent = True
        session.modified = True

    @app.after_request
    def after_request(response):
        """Hook nach jeder Anfrage"""
        return response
