"""Zentrale Pfade und Einstellungen.

Datenschutz-Grundsatz: Alles, was echte Schülerdaten enthalten kann, liegt
unterhalb von DATEN_DIR. Dieses Verzeichnis ist in .gitignore ausgeschlossen
und verlässt den lokalen Rechner nicht.
"""

from __future__ import annotations

import os
from pathlib import Path

# Projektwurzel = Verzeichnis oberhalb des Pakets
PROJEKT_DIR = Path(__file__).resolve().parent.parent

# Referenzdaten (versionsverwaltet, enthalten KEINE Schülerdaten)
REFERENZ_DIR = PROJEKT_DIR / "data"
OLFA_DATEI_MITGELIEFERT = REFERENZ_DIR / "olfa_kategorien.json"

# Arbeitsdaten (NICHT versionsverwaltet)
DATEN_DIR = Path(os.environ.get("RSTRAINER_DATEN_DIR", PROJEKT_DIR / "daten"))
DB_PFAD = Path(os.environ.get("RSTRAINER_DB", DATEN_DIR / "rstrainer.sqlite3"))
EXPORT_DIR = Path(os.environ.get("RSTRAINER_EXPORT_DIR", DATEN_DIR / "export"))

# Eine eigene, von der Lehrperson bearbeitete Kategorienliste hat Vorrang
# vor der mitgelieferten Vorlage.
OLFA_DATEI_LOKAL = DATEN_DIR / "olfa_kategorien.json"

# --- Fachliche Voreinstellungen (alle in der App änderbar) -------------------

#: Wie viele der jüngsten Diktate bilden das "aktuelle" Fenster der Trendanalyse.
TREND_FENSTER = 3
#: Ab welcher relativen Veränderung gilt ein Trend als zu-/abnehmend (20 %).
TREND_SCHWELLE = 0.20
#: Fehler pro 100 Wörter, unterhalb derer Unterschiede als Rauschen gelten.
TREND_MINDESTDIFFERENZ = 0.5
#: Halbwertszeit der Zeitgewichtung, gemessen in Diktaten.
GEWICHT_HALBWERTSZEIT = 3.0
#: So viele Förderschwerpunkte schlägt das Tool maximal vor.
MAX_FOERDERSCHWERPUNKTE = 3


def verzeichnisse_anlegen() -> None:
    """Legt die lokalen Arbeitsverzeichnisse an, falls sie fehlen."""
    DATEN_DIR.mkdir(parents=True, exist_ok=True)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
