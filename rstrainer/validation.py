"""Plausibilitätsprüfungen vor der Freigabe.

Grundsatz: Diese Prüfungen **blockieren nie**. Sie zeigen Hinweise, die
Lehrperson entscheidet. Die App speichert erst nach ausdrücklicher Freigabe.

Was die Prüfungen NICHT können: beurteilen, ob ein Text sprachlich gut oder
altersangemessen ist. Das bleibt Sache der Lehrperson – die App fragt aktiv
danach, statt es stillschweigend anzunehmen.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .olfa import Kategorienliste
from .textwerkzeuge import woerter

OK = "ok"
HINWEIS = "hinweis"
WARNUNG = "warnung"

#: Rangfolge für die Sortierung der Befunde.
_RANG = {WARNUNG: 0, HINWEIS: 1, OK: 2}

#: Wortmuster je Heuristik-Marker, mit dem sich prüfen lässt, ob ein Text
#: überhaupt Wörter enthält, an denen die Kategorie sichtbar werden kann.
#: Bewusst grosszügig: ein Treffer heisst "könnte passen", nicht "passt".
KATEGORIE_MUSTER: dict[str, re.Pattern] = {
    # Groß- und Kleinschreibung
    "klein_statt_gross": re.compile(r"^[A-ZÄÖÜ]"),
    "gross_statt_klein": re.compile(r"^[a-zäöü]"),
    "gross_im_wort": re.compile(r"^\w{2,}$"),
    # Getrennt- und Zusammenschreibung
    "getrennt_statt_zusammen": re.compile(r"^\w{9,}$"),
    "zusammen_statt_getrennt": re.compile(r"^\w{5,}$"),
    "wortgrenze": re.compile(r"^\w{6,}$"),
    # Konsonantenverdoppelung
    "doppelkonsonant_fehlt": re.compile(r"([bdfgklmnprst])\1", re.I),
    "ck": re.compile(r"ck", re.I),
    "tz": re.compile(r"tz", re.I),
    "doppelkonsonant_zuviel": re.compile(
        r"[aeiouäöü][bdfgklmnprst]([aeiouäöü]|$)", re.I),
    # Vokallänge
    "dehnungs_h_fehlt": re.compile(r"[aeiouäöü]h", re.I),
    "doppelvokal_fehlt": re.compile(r"aa|ee|oo", re.I),
    "ie_fehlt": re.compile(r"ie", re.I),
    "dehnungs_h_zuviel": re.compile(r"^\w{3,}$"),
    "doppelvokal_zuviel": re.compile(r"[aeiouäöü]", re.I),
    "ie_zuviel": re.compile(r"i(?!e)", re.I),
    "laenge_bei_kurzvokal": re.compile(r"[aeiouäöü]", re.I),
    # s-Schreibung
    "s_statt_sz": re.compile(r"ß"),
    "sz_statt_s": re.compile(r"s(?!s)", re.I),
    "ss_statt_sz": re.compile(r"ß"),
    "sz_statt_ss": re.compile(r"ss", re.I),
    # Umlautschreibung
    "e_statt_ae": re.compile(r"ä", re.I),
    "eu_statt_aeu": re.compile(r"äu", re.I),
    "ae_statt_e": re.compile(r"e", re.I),
    "aeu_statt_eu": re.compile(r"eu", re.I),
    "umlaut_fehlt": re.compile(r"[äöü]", re.I),
    # Silbenrand
    "auslautverhaertung": re.compile(r"[bdg]$", re.I),
    "stimmhaft_statt_stimmlos": re.compile(r"[ptk]$", re.I),
    # v-, f- und w-Schreibung
    "f_statt_v": re.compile(r"v", re.I),
    "v_statt_f": re.compile(r"f", re.I),
    "w_statt_v": re.compile(r"v", re.I),
    "v_statt_w": re.compile(r"w", re.I),
    # ch- und g-Schreibung
    "ch_statt_g": re.compile(r"g$|ig$", re.I),
    "g_statt_ch": re.compile(r"ch$", re.I),
    # Vollständigkeit des Wortes
    "konsonant_fehlt": re.compile(r"[bcdfghjklmnpqrstvwxz]{2}", re.I),
    "konsonant_zuviel": re.compile(r"[bcdfghjklmnpqrstvwxz]", re.I),
    "vokal_fehlt": re.compile(r"[aeiouäöü]", re.I),
    "vokal_zuviel": re.compile(r"[aeiouäöü]", re.I),
    "dreher": re.compile(r"^\w{4,}$"),
    # Falsche Zeichen
    "konsonant_verwechselt": re.compile(r"[bpdtgkwfvszmn]", re.I),
    "vokal_verwechselt": re.compile(r"[aeiou]", re.I),
    # Sonstiges
    "fremdwort": re.compile(r"ph|th|y|v|c[^hk]", re.I),
    "wort_fehlt": re.compile(r"."),
    "sonstige": re.compile(r"."),
}


@dataclass
class Befund:
    stufe: str
    titel: str
    text: str

    @property
    def symbol(self) -> str:
        return {OK: "✅", HINWEIS: "ℹ️", WARNUNG: "⚠️"}[self.stufe]


def _sortiert(befunde: list[Befund]) -> list[Befund]:
    return sorted(befunde, key=lambda b: _RANG[b.stufe])


def kategorie_treffer(text: str, kategorie_nr: str,
                      liste: Kategorienliste) -> list[str]:
    """Wörter im Text, an denen die Kategorie sichtbar werden könnte."""
    kategorie = liste.get(kategorie_nr)
    if kategorie is None:
        return []
    muster = [KATEGORIE_MUSTER[m] for m in kategorie.heuristik if m in KATEGORIE_MUSTER]
    if not muster:
        return []
    treffer = []
    for wort in woerter(text):
        if any(m.search(wort) for m in muster):
            treffer.append(wort)
    # Dubletten entfernen, Reihenfolge erhalten
    gesehen: list[str] = []
    for w in treffer:
        if w not in gesehen:
            gesehen.append(w)
    return gesehen


# ---------------------------------------------------------------------------
# Diktat
# ---------------------------------------------------------------------------

def diktat_pruefen(text: str, soll_wortzahl: int, kategorien: list[str],
                   liste: Kategorienliste,
                   toleranz: float = 0.20,
                   mindesttreffer: int = 3) -> list[Befund]:
    """Prüft einen frisch eingefügten Diktattext.

    Annahmen: Abweichungen der Wortzahl bis ``toleranz`` (20 %) gelten als
    unproblematisch – der Prompt fordert 10 %, hier wird grosszügiger
    gemessen, damit nicht jedes Diktat einen Hinweis auslöst.
    """
    befunde: list[Befund] = []
    ist = len(woerter(text))

    if not text.strip():
        return [Befund(WARNUNG, "Kein Text", "Es wurde kein Diktattext eingefügt.")]

    if soll_wortzahl > 0:
        abweichung = abs(ist - soll_wortzahl) / soll_wortzahl
        if abweichung <= toleranz:
            befunde.append(Befund(
                OK, "Wortanzahl",
                f"{ist} Wörter – passt zur Vorgabe von {soll_wortzahl}."))
        else:
            richtung = "kürzer" if ist < soll_wortzahl else "länger"
            befunde.append(Befund(
                HINWEIS, "Wortanzahl",
                f"{ist} Wörter statt {soll_wortzahl} – der Text ist "
                f"{abweichung:.0%} {richtung} als gewünscht."))
    else:
        befunde.append(Befund(OK, "Wortanzahl", f"{ist} Wörter."))

    for nr in kategorien:
        kategorie = liste.get(nr)
        name = kategorie.label if kategorie else nr
        treffer = kategorie_treffer(text, nr, liste)
        if len(treffer) >= mindesttreffer:
            beispiele = ", ".join(treffer[:6])
            befunde.append(Befund(
                OK, f"Kategorie {name}",
                f"{len(treffer)} mögliche Zielwörter gefunden: {beispiele}"
                + (" …" if len(treffer) > 6 else "")))
        elif treffer:
            befunde.append(Befund(
                HINWEIS, f"Kategorie {name}",
                f"Nur {len(treffer)} mögliche Zielwörter gefunden "
                f"({', '.join(treffer)}). Reicht das für ein Übungsdiktat?"))
        else:
            befunde.append(Befund(
                WARNUNG, f"Kategorie {name}",
                "Keine Wörter gefunden, an denen diese Kategorie sichtbar "
                "werden könnte. Bitte prüfen, ob der Text zum Auftrag passt."))

    befunde.append(Befund(
        HINWEIS, "Korrekturlesen",
        "Dieser Text wird später zur Referenz für den maschinellen Abgleich "
        "mit dem Schülertext. Jeder Tippfehler darin zählt dann als "
        "Schülerfehler. Bitte Wort für Wort gegenlesen."))
    return _sortiert(befunde)


# ---------------------------------------------------------------------------
# Übungsblatt / Mini-Test
# ---------------------------------------------------------------------------

#: Formulierungen, die auf verratene Lösungen auf der Aufgabenseite hindeuten.
LOESUNGS_SIGNALE = [
    (re.compile(r"\bLösung(en)?\s*[:=]", re.I), "Das Wort «Lösung:» steht im Aufgabenteil."),
    (re.compile(r"\bAntwort\s*[:=]", re.I), "Das Wort «Antwort:» steht im Aufgabenteil."),
    (re.compile(r"\(\s*richtig\s*[:=]", re.I), "«(richtig: …)» steht im Aufgabenteil."),
    (re.compile(r"→\s*\w+"), "Ein Pfeil «→ Wort» kann eine verratene Lösung sein."),
    (re.compile(r"_{2,}\s*\(\s*\w+\s*\)"), "Nach einer Lücke steht ein Wort in Klammern."),
]


def blatt_pruefen(inhalt_uebung: str, inhalt_test: str, loesungen: str,
                  kategorien: list[str], liste: Kategorienliste,
                  mindestnennungen: int = 1) -> list[Befund]:
    """Prüft ein frisch eingefügtes Übungsblatt samt Mini-Test."""
    befunde: list[Befund] = []

    if not inhalt_uebung.strip():
        befunde.append(Befund(WARNUNG, "Übungsteil", "Der Übungsteil ist leer."))
    if not inhalt_test.strip():
        befunde.append(Befund(WARNUNG, "Mini-Test", "Der Mini-Test ist leer."))

    aufgabenseiten = f"{inhalt_uebung}\n{inhalt_test}"

    # 1) Sind die Aufgaben erkennbar den gewählten Kategorien zugeordnet?
    for nr in kategorien:
        kategorie = liste.get(nr)
        name = kategorie.label if kategorie else nr
        nennungen = len(re.findall(rf"\b{re.escape(nr)}\b", aufgabenseiten))
        treffer = kategorie_treffer(aufgabenseiten, nr, liste)
        if nennungen >= mindestnennungen:
            befunde.append(Befund(
                OK, f"Zuordnung {name}",
                f"Die Kategorienummer {nr} wird {nennungen}× im Blatt genannt."))
        elif len(treffer) >= 5:
            befunde.append(Befund(
                HINWEIS, f"Zuordnung {name}",
                f"Die Nummer {nr} steht nirgends im Blatt, es gibt aber "
                f"{len(treffer)} inhaltlich passende Wörter. Zuordnung bitte "
                "selbst prüfen."))
        else:
            befunde.append(Befund(
                WARNUNG, f"Zuordnung {name}",
                f"Weder die Nummer {nr} noch erkennbar passende Wörter "
                "gefunden. Gehört diese Kategorie wirklich zum Blatt?"))

    # 2) Stehen Lösungen versehentlich auf der Aufgabenseite?
    verdacht = [meldung for muster, meldung in LOESUNGS_SIGNALE
                if muster.search(aufgabenseiten)]
    if verdacht:
        befunde.append(Befund(
            WARNUNG, "Lösungen sichtbar?",
            "Mögliche Lösungshinweise auf der Aufgabenseite: "
            + " ".join(verdacht)))
    else:
        befunde.append(Befund(
            OK, "Lösungen sichtbar?",
            "Keine typischen Lösungsformulierungen im Aufgabenteil gefunden. "
            "Das ersetzt den eigenen Blick aufs Blatt nicht."))

    # 3) Überschneiden sich Übungs- und Testwörter zu stark?
    if inhalt_uebung.strip() and inhalt_test.strip():
        uebung_w = {w.lower() for w in woerter(inhalt_uebung) if len(w) > 4}
        test_w = {w.lower() for w in woerter(inhalt_test) if len(w) > 4}
        if test_w:
            anteil = len(uebung_w & test_w) / len(test_w)
            if anteil > 0.5:
                befunde.append(Befund(
                    HINWEIS, "Übung und Test zu ähnlich",
                    f"{anteil:.0%} der längeren Testwörter kommen schon im "
                    "Übungsteil vor. Der Test misst dann eher das Merken als "
                    "das Können."))
            else:
                befunde.append(Befund(
                    OK, "Übung und Test",
                    f"Nur {anteil:.0%} Wortüberschneidung – der Test verwendet "
                    "überwiegend anderes Material."))

    if not loesungen.strip():
        befunde.append(Befund(
            HINWEIS, "Lösungsblatt",
            "Es wurde kein Lösungsabschnitt eingefügt. Ohne Lösungen muss beim "
            "Korrigieren alles von Hand geprüft werden."))

    befunde.append(Befund(
        HINWEIS, "Schwierigkeitsgrad",
        "Ob das Niveau zur Altersstufe passt, kann die App nicht beurteilen. "
        "Bitte das Blatt einmal ganz durchlesen und bewusst bestätigen."))
    return _sortiert(befunde)
