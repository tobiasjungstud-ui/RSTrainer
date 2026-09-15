"""Gemeinsame Bausteine der Oberfläche."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

import streamlit as st

from .. import config, db, kategorien, olfa, taxonomie
from ..kategorien import Register
from ..validation import Befund


@st.cache_resource
def verbindung() -> sqlite3.Connection:
    config.verzeichnisse_anlegen()
    return db.verbinden()


def kategorienliste() -> olfa.Kategorienliste:
    """Nur die feste OLFA-Liste – für die Heuristiken der Plausibilitätsprüfung."""
    return register().liste


def sammlung() -> taxonomie.Sammlung:
    """Nur die gelernten Fehlerarten."""
    return register().sammlung


def register() -> Register:
    """Beide Kategoriensysteme aus dem Sitzungsspeicher.

    Die gelernten Arten ändern sich im Betrieb – nach jedem Schreiben muss
    :func:`kategorien_neu_laden` aufgerufen werden, sonst zeigt die Oberfläche
    den Stand vom Seitenaufbau.
    """
    if "register" not in st.session_state:
        st.session_state["register"] = kategorien.laden()
    return st.session_state["register"]


def kategorien_neu_laden() -> None:
    st.session_state.pop("register", None)


def sammlung_speichern(neue: taxonomie.Sammlung) -> None:
    taxonomie.speichern(neue)
    kategorien_neu_laden()


def anzeigename(con, schueler: sqlite3.Row) -> str:
    """Name für Ausdrucke und Exporte.

    Ein eigenes Kürzelfeld gibt es nicht mehr: Wer den Klarnamen nicht auf dem
    Blatt haben will, trägt schon als Anzeigename ein Pseudonym ein.
    """
    return schueler["anzeigename"]


def aktive_schueler_id() -> int | None:
    return st.session_state.get("schueler_id")


def kategorien_auswahl(reg: Register, beschriftung: str,
                       vorauswahl: list[str] | None = None,
                       schluessel: str = "kategorien",
                       hoechstens: int | None = None) -> list[str]:
    """Mehrfachauswahl über beide Kategoriensysteme.

    Gesperrte OLFA-Kategorien stehen nicht zur Wahl: 13 und 15 beschreiben,
    dass ein ß *nicht* geschrieben wurde – in der Schweiz ist genau das richtig.
    """
    optionen = [k.nr for k in reg.liste.waehlbar] + [a.id for a in reg.sammlung]
    beschriftungen = {k.nr: f"{k.bereich} · {k.label}" for k in reg.liste.waehlbar}
    beschriftungen.update({a.id: f"{a.oberbegriff} · {a.label}" for a in reg.sammlung})
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
