@echo off
REM Starte das Programm mit erhöhten Rechten
powershell -Command "Start-Process pythonw -ArgumentList 'D:\Tobias\AProgrammieren\Bestellungssystem\app.py' -Verb RunAs" 