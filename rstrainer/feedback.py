"""Prägnante Rückmeldung zu einem Analyse-Durchgang: was ist gut, was ist als
Nächstes zu üben. Rein deterministisch aus den bereits klassifizierten Funden
dieses Durchgangs abgeleitet – kein zusätzlicher Aufruf des Sprachmodells.

Gilt für alle drei Modi (Diktat, Freitextmodus, Freies Diktat):
Jeder Durchgang deckt einen bekannten Satz von Bereichen ab (Diktat- und
Freitextmodus A, freie Analyse B–E), und nur dafür lässt sich «keine
Auffälligkeiten» ehrlich behaupten.
"""

from __future__ import annotations

from dataclasses import dataclass

BEREICH_NAME = {
    "A": "Rechtschreibung",
    "B": "Grammatik und Morphologie",
    "C": "Satzbau und Syntax",
    "D": "Zeichensetzung",
    "E": "Textebene",
}


@dataclass(frozen=True)
class Fund:
    kategorie_nr: str
    wort_schueler: str = ""
    wort_original: str = ""


def feedback_erstellen(bereiche_geprueft: list[str], funde: list[Fund], reg,
                       hoechstens: int = 3) -> tuple[list[str], list[str]]:
    """Liefert (gut, verbessern) als Listen kurzer, konkreter Sätze."""
    nach_bereich: dict[str, list[Fund]] = {b: [] for b in bereiche_geprueft}
    zaehler: dict[str, int] = {}
    beispiel: dict[str, Fund] = {}
    for f in funde:
        bereich = reg.bereich(f.kategorie_nr)
        nach_bereich.setdefault(bereich, []).append(f)
        zaehler[f.kategorie_nr] = zaehler.get(f.kategorie_nr, 0) + 1
        beispiel.setdefault(f.kategorie_nr, f)

    gut: list[str] = []
    if not funde:
        gut.append("Kein einziger Fehler in diesem Durchgang gefunden.")
    else:
        for bereich in bereiche_geprueft:
            if not nach_bereich.get(bereich):
                gut.append(f"Keine Auffälligkeiten im Bereich {BEREICH_NAME.get(bereich, bereich)}.")

    verbessern: list[str] = []
    for nr, anzahl in sorted(zaehler.items(), key=lambda kv: (-kv[1], kv[0]))[:hoechstens]:
        f = beispiel[nr]
        beispiel_text = (
            f' (z. B. „{f.wort_schueler}“ statt „{f.wort_original}“)'
            if f.wort_schueler and f.wort_original and f.wort_schueler != f.wort_original
            else ""
        )
        verbessern.append(f"{reg.label(nr)}: {anzahl}×{beispiel_text}")
    return gut, verbessern
