"""Kleine Textbausteine, die an mehreren Stellen gebraucht werden."""

from __future__ import annotations

import re
import unicodedata

#: Ein "Wort" ist eine Folge aus Buchstaben, Ziffern, Bindestrich und Apostroph.
WORT_MUSTER = re.compile(r"[^\W_]+(?:[-'’][^\W_]+)*", re.UNICODE)

VOKALE = set("aeiouäöüáàâéèêíìîóòôúùû")
UMLAUT_GRUNDFORM = {"ä": "a", "ö": "o", "ü": "u"}
#: Konsonantenpaare, die lautlich nah beieinander liegen.
AEHNLICHE_KONSONANTEN = [
    {"b", "p"}, {"d", "t"}, {"g", "k"}, {"w", "f"}, {"v", "f"}, {"v", "w"},
    {"s", "z"}, {"m", "n"},
]
MEHRGRAPHEME = ("sch", "ch", "ng", "nk", "pf", "qu", "st", "sp")


def woerter(text: str) -> list[str]:
    """Zerlegt einen Text in Wörter (Satzzeichen werden verworfen)."""
    return WORT_MUSTER.findall(text or "")


def woerter_zaehlen(text: str) -> int:
    return len(woerter(text))


def normalisieren(wort: str) -> str:
    """Vergleichsform für die Wort-Ausrichtung: klein, ohne Rand-Satzzeichen.

    Bewusste Annahme: Für die *Ausrichtung* zweier Texte wird die Groß-/
    Kleinschreibung ignoriert, damit ein reiner Großschreibfehler als
    "gleiches Wort, andere Schreibung" erkannt wird und nicht als
    Wort-gelöscht-plus-Wort-eingefügt. Die *Abweichung* selbst wird
    anschließend auf den Originalformen bestimmt.
    """
    wort = unicodedata.normalize("NFC", wort or "")
    return wort.strip("»«\"'’„“”.,;:!?()[]{}–—-").casefold()


def satz_kontext(worte: list[str], index: int, fenster: int = 4) -> str:
    """Gibt ein paar Wörter links und rechts als Kontext zurück."""
    start = max(0, index - fenster)
    ende = min(len(worte), index + fenster + 1)
    teile = list(worte[start:ende])
    stelle = index - start
    if 0 <= stelle < len(teile):
        teile[stelle] = f"[{teile[stelle]}]"
    vorn = "… " if start > 0 else ""
    hinten = " …" if ende < len(worte) else ""
    return f"{vorn}{' '.join(teile)}{hinten}"


def gemeinsame_woerter(text_a: str, text_b: str) -> set[str]:
    return {normalisieren(w) for w in woerter(text_a)} & {
        normalisieren(w) for w in woerter(text_b)
    }
