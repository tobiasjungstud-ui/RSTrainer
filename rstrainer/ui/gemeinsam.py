"""Gemeinsame Bausteine der Oberfläche."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

import streamlit as st

from .. import config, db, olfa
from ..validation import Befund

NAMENSMODUS_SCHLUESSEL = "namensmodus"
VARIANTE_SCHLUESSEL = "rechtschreibvariante"


@st.cache_resource
def verbindung() -> sqlite3.Connection:
    config.verzeichnisse_anlegen()
    return db.verbinden()


def kategorienliste() -> olfa.Kategorienliste:
    """Kategorienliste aus dem Sitzungsspeicher (nach Änderungen neu laden)."""
    if "kategorienliste" not in st.session_state:
        st.session_state["kategorienliste"] = olfa.laden()
    return st.session_state["kategorienliste"]


def kategorien_neu_laden() -> None:
    st.session_state.pop("kategorienliste", None)


def namensmodus(con) -> str:
    """``klarname`` oder ``kuerzel`` – bestimmt, was auf Blättern erscheint."""
    return db.einstellung_holen(con, NAMENSMODUS_SCHLUESSEL, "kuerzel")


def rechtschreibvariante(con) -> str:
    return db.einstellung_holen(con, VARIANTE_SCHLUESSEL, "schweiz")


def anzeigename(con, schueler: sqlite3.Row) -> str:
    """Name für Ausdrucke und Exporte – je nach Einstellung Kürzel oder Klarname."""
    if namensmodus(con) == "kuerzel" and schueler["kuerzel"]:
        return schueler["kuerzel"]
    return schueler["anzeigename"]


def aktive_schueler_id() -> int | None:
    return st.session_state.get("schueler_id")


def kategorien_auswahl(liste: olfa.Kategorienliste, beschriftung: str,
                       vorauswahl: list[str] | None = None,
                       schluessel: str = "kategorien",
                       hoechstens: int | None = None) -> list[str]:
    """Mehrfachauswahl über alle Kategorien, gruppiert nach Bereich."""
    optionen = [k.nr for k in liste]
    beschriftungen = {k.nr: f"{k.bereich} · {k.label}" for k in liste}
    gewaehlt = st.multiselect(
        beschriftung, optionen,
        default=[nr for nr in (vorauswahl or []) if nr in optionen],
        format_func=lambda nr: beschriftungen.get(nr, nr),
        key=schluessel,
    )
    if hoechstens and len(gewaehlt) > hoechstens:
        st.warning(
            f"Es sind höchstens {hoechstens} Kategorien sinnvoll. "
            f"Aktuell gewählt: {len(gewaehlt)}. Die Aufgaben werden sonst zu "
            "breit und verlieren ihre Förderwirkung."
        )
    return gewaehlt


def befunde_anzeigen(befunde: list[Befund]) -> None:
    """Zeigt Plausibilitätshinweise – nie blockierend, immer sichtbar."""
    if not befunde:
        return
    warnungen = [b for b in befunde if b.stufe == "warnung"]
    if warnungen:
        st.error(f"{len(warnungen)} Punkt(e) brauchen Ihre Aufmerksamkeit.")
    for b in befunde:
        st.markdown(f"{b.symbol} **{b.titel}** — {b.text}")


def prompt_anzeigen(prompt_text: str, code: str) -> None:
    """Zeigt den fertigen Prompt zum Kopieren."""
    st.caption(
        f"Auftragsnummer **{code}** — steht im Prompt und sollte in der Antwort "
        "wieder auftauchen. Daran erkennt die App, dass das eingefügte Ergebnis "
        "zu diesem Auftrag gehört."
    )
    st.code(prompt_text, language="markdown")
    st.caption(
        "Oben rechts im grauen Feld auf das Kopier-Symbol klicken, in einen "
        "Claude-Chat einfügen, Antwort abwarten und die komplette Antwort "
        "hierher zurückkopieren."
    )


def json_liste(wert: Any) -> list[str]:
    """Liest ein JSON-Feld aus der Datenbank tolerant als Liste."""
    if isinstance(wert, list):
        return [str(x) for x in wert]
    try:
        geladen = json.loads(wert or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    return [str(x) for x in geladen] if isinstance(geladen, list) else []


def merken(text: str, art: str = "success") -> None:
    """Meldung für den NÄCHSTEN Durchlauf vormerken.

    ``st.success(...)`` direkt vor ``st.rerun()`` ist wirkungslos: Der Neuaufbau
    verwirft die Meldung, bevor sie jemand sieht. Deshalb wird sie hier
    zwischengespeichert und beim nächsten Durchlauf oben ausgegeben.
    """
    st.session_state.setdefault("meldungen", []).append((art, text))


def meldungen_anzeigen() -> None:
    """Gibt vorgemerkte Meldungen aus und leert den Zwischenspeicher."""
    for art, text in st.session_state.pop("meldungen", []):
        getattr(st, art, st.info)(text)


def kein_profil_hinweis() -> None:
    st.info(
        "Es ist noch kein Schülerprofil ausgewählt. Bitte links unter "
        "**Profile** ein Profil anlegen oder auswählen."
    )


def datenschutz_fussnote() -> None:
    st.caption(
        "🔒 Alle Daten bleiben lokal in `daten/`. Dieses Verzeichnis ist von der "
        "Versionsverwaltung ausgeschlossen und wird nicht hochgeladen."
    )
