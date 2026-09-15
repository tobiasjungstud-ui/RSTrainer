"""Rohdaten-Export pro Schülerprofil (CSV und JSON).

Der Export enthält echte Schülerdaten und gehört deshalb ausschliesslich in
das lokale, nicht versionsverwaltete ``daten/export``-Verzeichnis.
"""

from __future__ import annotations

import csv
import io
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from . import db
from .kategorien import Register

FEHLER_SPALTEN = [
    "fehler_id", "datum", "diktat_id", "diktat_titel", "kategorie_nr",
    "kategorie_name", "oberbegriff", "wort_original", "wort_schueler",
    "kontext", "notiz",
]
DIKTAT_SPALTEN = [
    "diktat_id", "datum", "art", "titel", "wortzahl", "ziel_kategorien",
    "quelle", "freigegeben", "freigegeben_am", "notiz",
]


def _zeilen_fehler(con: sqlite3.Connection, schueler_id: int,
                   register: Register) -> list[dict]:
    diktattitel = {
        z["id"]: z["titel"] for z in db.diktat_liste(con, schueler_id)
    }
    zeilen = []
    for f in db.fehler_liste(con, schueler_id):
        # Über das Register, nicht über die OLFA-Liste allein: Ein Fehler kann
        # auch einer gelernten Art zugeordnet sein, die dort nicht steht.
        zeilen.append({
            "fehler_id": f["id"],
            "datum": f["datum"],
            "diktat_id": f["diktat_id"],
            "diktat_titel": diktattitel.get(f["diktat_id"], ""),
            "kategorie_nr": f["kategorie_nr"],
            "kategorie_name": register.name(f["kategorie_nr"]),
            "oberbegriff": register.oberbegriff(f["kategorie_nr"]),
            "wort_original": f["wort_original"],
            "wort_schueler": f["wort_schueler"],
            "kontext": f["kontext"],
            "notiz": f["notiz"],
        })
    return zeilen


def _zeilen_diktate(con: sqlite3.Connection, schueler_id: int) -> list[dict]:
    zeilen = []
    for d in db.diktat_liste(con, schueler_id):
        zeilen.append({
            "diktat_id": d["id"],
            "datum": d["datum"],
            "art": d["art"],
            "titel": d["titel"],
            "wortzahl": d["wortzahl"],
            "ziel_kategorien": ", ".join(json.loads(d["ziel_kategorien"] or "[]")),
            "quelle": d["quelle"],
            "freigegeben": bool(d["freigegeben"]),
            "freigegeben_am": d["freigegeben_am"] or "",
            "notiz": d["notiz"],
        })
    return zeilen


def csv_text(zeilen: list[dict], spalten: list[str]) -> str:
    """CSV mit Semikolon – so öffnet Excel die Datei direkt richtig."""
    puffer = io.StringIO()
    schreiber = csv.DictWriter(puffer, fieldnames=spalten, delimiter=";",
                               extrasaction="ignore", lineterminator="\n")
    schreiber.writeheader()
    schreiber.writerows(zeilen)
    return puffer.getvalue()


def fehler_csv(con: sqlite3.Connection, schueler_id: int, register: Register) -> str:
    return csv_text(_zeilen_fehler(con, schueler_id, register), FEHLER_SPALTEN)


def diktate_csv(con: sqlite3.Connection, schueler_id: int) -> str:
    return csv_text(_zeilen_diktate(con, schueler_id), DIKTAT_SPALTEN)


def gesamt_json(con: sqlite3.Connection, schueler_id: int, register: Register,
                mit_texten: bool = True) -> str:
    """Vollständiger Datenbestand eines Profils als JSON."""
    schueler = db.schueler_holen(con, schueler_id)
    if schueler is None:
        raise ValueError(f"Kein Profil mit der ID {schueler_id}.")

    diktate = []
    for d in db.diktat_liste(con, schueler_id):
        eintrag: dict[str, Any] = {
            "id": d["id"],
            "art": d["art"],
            "titel": d["titel"],
            "datum": d["datum"],
            "wortzahl": d["wortzahl"],
            "ziel_kategorien": json.loads(d["ziel_kategorien"] or "[]"),
            "quelle": d["quelle"],
            "notiz": d["notiz"],
            "freigegeben": bool(d["freigegeben"]),
            "freigegeben_am": d["freigegeben_am"],
        }
        if mit_texten:
            eintrag["text_original"] = d["text_original"]
            eintrag["schuelertext"] = d["schuelertext"]
        diktate.append(eintrag)

    inhalt = {
        "exportiert_am": datetime.now().isoformat(timespec="seconds"),
        "hinweis": "Enthält personenbezogene Daten. Nicht weitergeben, "
                   "nicht in ein Repository einchecken.",
        "schueler": {
            "id": schueler["id"],
            "anzeigename": schueler["anzeigename"],
            "notiz": schueler["notiz"],
        },
        "kategorienliste": {
            "quelle": str(register.liste.quelle) if register.liste.quelle else None,
            "anzahl": len(register.liste),
            "ungeprueft": register.liste.anzahl_ungeprueft,
            "gesperrt": [k.nr for k in register.liste if k.gesperrt],
        },
        "gelernte_fehlerarten": [a.as_dict() for a in register.sammlung],
        "diktate": diktate,
        "fehler": _zeilen_fehler(con, schueler_id, register),
        "blaetter": [
            {
                "id": b["id"],
                "titel": b["titel"],
                "datum": b["datum"],
                "kategorien": json.loads(b["kategorien"] or "[]"),
                "freigegeben": bool(b["freigegeben"]),
                "freigegeben_am": b["freigegeben_am"],
            }
            for b in db.blatt_liste(con, schueler_id)
        ],
    }
    return json.dumps(inhalt, ensure_ascii=False, indent=2)


def in_datei_schreiben(inhalt: str, pfad: Path | str) -> Path:
    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(inhalt, encoding="utf-8")
    return pfad
