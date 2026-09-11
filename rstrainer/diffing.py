"""Wortweiser Abgleich von Originaldiktat und Schülertext.

Zweistufiges Verfahren:

1. **Ausrichtung** der beiden Texte auf Wortebene über ``difflib``. Verglichen
   wird dabei die *normalisierte* Form (klein, ohne Rand-Satzzeichen), damit
   ein reiner Großschreibfehler nicht die Ausrichtung zerstört.
2. **Abweichungsbestimmung** auf den Originalformen. Zusätzlich wird
   buchstabenweise analysiert, welche OLFA-Kategorien in Frage kommen.

Die Lehrperson bestätigt jede vorgeschlagene Abweichung und wählt die
Kategorie – das Tool schlägt nur vor, es entscheidet nicht.

Dokumentierte Annahmen
----------------------
* Satzzeichen werden gar nicht verglichen: Die Tokenisierung verwirft sie,
  weil sie beim Abtippen des Schülertexts erfahrungsgemäß unzuverlässig
  übertragen werden. Satzzeichenfehler bitte von Hand erfassen.
* Zahlen werden wie Wörter behandelt.
* Die Kategorie-Vorschläge sind Heuristik, keine linguistische Analyse. Sie
  sind nach Plausibilität sortiert; der erste Vorschlag ist der wahrscheinlichste.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field

from .olfa import Kategorie, Kategorienliste
from .textwerkzeuge import (
    AEHNLICHE_KONSONANTEN,
    MEHRGRAPHEME,
    UMLAUT_GRUNDFORM,
    VOKALE,
    normalisieren,
    satz_kontext,
    woerter,
)

#: Abweichungsarten
ERSETZT = "ersetzt"      # Wort steht da, ist aber anders geschrieben
FEHLT = "fehlt"          # Wort des Originals fehlt im Schülertext
ZUSAETZLICH = "zusaetzlich"  # Wort steht zusätzlich im Schülertext


@dataclass
class Abweichung:
    """Eine einzelne Stelle, an der Schülertext und Original auseinandergehen."""

    art: str
    wort_original: str
    wort_schueler: str
    position: int
    kontext: str
    marker: tuple[str, ...] = ()
    vorschlaege: list[Kategorie] = field(default_factory=list)

    @property
    def darstellung(self) -> str:
        if self.art == ERSETZT:
            return f"{self.wort_original} → {self.wort_schueler}"
        if self.art == FEHLT:
            return f"{self.wort_original} → (fehlt)"
        return f"(zusätzlich) → {self.wort_schueler}"


# ---------------------------------------------------------------------------
# Buchstabenebene: Marker bestimmen
# ---------------------------------------------------------------------------

def _ist_dreher(a: str, b: str) -> bool:
    """True, wenn b aus a durch genau eine Vertauschung zweier Nachbarn entsteht."""
    if len(a) != len(b) or a == b:
        return False
    unterschiede = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    if len(unterschiede) != 2:
        return False
    i, j = unterschiede
    return j == i + 1 and a[i] == b[j] and a[j] == b[i]


def _ist_vokal(zeichen: str) -> bool:
    return bool(zeichen) and zeichen[0] in VOKALE


def _aehnliche_konsonanten(a: str, b: str) -> bool:
    return any({a, b} == paar for paar in AEHNLICHE_KONSONANTEN)


def _marker_loeschung(orig: str, i1: int, i2: int) -> str:
    """Im Original steht etwas, das im Schülertext fehlt."""
    teil = orig[i1:i2]
    davor = orig[i1 - 1] if i1 > 0 else ""
    danach = orig[i2] if i2 < len(orig) else ""

    if teil == "h":
        return "dehnungs_h_fehlt"
    if teil == "e" and davor == "i":
        return "ie_fehlt"
    if teil == "i" and danach == "e":
        return "ie_fehlt"
    if teil == "c" and danach == "k":
        return "ck"
    if teil == "t" and danach == "z":
        return "tz"
    if len(teil) == 1 and teil == davor:
        return "doppelvokal" if _ist_vokal(teil) else "doppelkonsonant_fehlt"
    if teil in MEHRGRAPHEME or any(teil in mg for mg in MEHRGRAPHEME if len(teil) > 1):
        return "mehrgraphem"
    return "vokal_fehlt" if _ist_vokal(teil) else "konsonant_fehlt"


def _marker_einfuegung(schueler: str, j1: int, j2: int) -> str:
    """Im Schülertext steht etwas zu viel."""
    teil = schueler[j1:j2]
    davor = schueler[j1 - 1] if j1 > 0 else ""
    danach = schueler[j2] if j2 < len(schueler) else ""

    if teil == "h":
        return "dehnungs_h_zuviel"
    if teil == "e" and davor == "i":
        return "ie_zuviel"
    if teil == "i" and danach == "e":
        return "ie_zuviel"
    if len(teil) == 1 and teil == davor:
        return "doppelvokal" if _ist_vokal(teil) else "doppelkonsonant_zuviel"
    return "vokal_zuviel" if _ist_vokal(teil) else "konsonant_zuviel"


def _marker_ersetzung(orig: str, schueler: str, i1: int, i2: int,
                      j1: int, j2: int) -> str:
    a = orig[i1:i2]
    b = schueler[j1:j2]
    danach_a = orig[i2] if i2 < len(orig) else ""
    am_wortende = i2 == len(orig)

    paar = {a, b}
    if paar == {"äu", "eu"}:
        return "aeu_eu"
    if paar == {"ä", "e"}:
        return "ae_e"
    if a in UMLAUT_GRUNDFORM and b == UMLAUT_GRUNDFORM[a]:
        return "umlaut_fehlt"
    if b in UMLAUT_GRUNDFORM and a == UMLAUT_GRUNDFORM[b]:
        return "umlaut_fehlt"
    if "ck" in (a, b) or (a == "k" and b in {"kk", "ck"}) or (b == "k" and a == "ck"):
        return "ck"
    if "tz" in (a, b) or (a == "t" and danach_a == "z") or (a == "z" and b == "tz"):
        return "tz"
    if paar in ({"ss", "s"}, {"ss", "z"}):
        return "s_statt_ss"
    if "ß" in paar:
        return "ss_statt_sz"
    if a == "s" or b == "s":
        return "s_stimmhaft"
    if am_wortende and a in {"b", "d", "g"} and b in {"p", "t", "k"}:
        return "auslautverhaertung"
    if a in {"v", "f"} and b in {"f", "v", "w"}:
        return "stamm_sonstige"
    if am_wortende and {a, b} in ({"er", "a"}, {"en", "n"}, {"ig", "ich"}, {"g", "ch"}):
        return "endung"
    if len(a) == 1 and len(b) == 1 and _aehnliche_konsonanten(a, b):
        return "konsonant_verwechselt"
    if a in MEHRGRAPHEME or b in MEHRGRAPHEME:
        return "mehrgraphem"
    if _ist_vokal(a) and _ist_vokal(b):
        return "vokal_verwechselt"
    if len(a) == 1 and len(b) == 1:
        return "konsonant_verwechselt"
    return "sonstige"


def marker_bestimmen(wort_original: str, wort_schueler: str) -> tuple[str, ...]:
    """Bestimmt technische Marker für ein falsch geschriebenes Wortpaar."""
    if not wort_schueler:
        return ("wort_fehlt",)
    if wort_original == wort_schueler:
        return ()

    # Bewusst .lower() statt .casefold(): casefold() bildet "ß" auf "ss" ab und
    # würde "Straße/Strasse" als reinen Großschreibfehler durchgehen lassen.
    if wort_original.lower() == wort_schueler.lower():
        # Unterschied liegt ausschließlich in der Groß-/Kleinschreibung.
        o_gross = wort_original[:1].isupper()
        s_gross = wort_schueler[:1].isupper()
        if o_gross and not s_gross:
            return ("klein_statt_gross",)
        if s_gross and not o_gross:
            return ("gross_statt_klein",)
        return ("gross_statt_klein",)

    orig = wort_original.lower()
    schueler = wort_schueler.lower()

    marker: list[str] = []
    if _ist_dreher(orig, schueler):
        # Ein Buchstabendreher erklärt das ganze Wort. Eine zusätzliche
        # buchstabenweise Analyse erzeugt hier nur Rauschen.
        return ("dreher",)

    matcher = difflib.SequenceMatcher(None, orig, schueler, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag == "delete":
            marker.append(_marker_loeschung(orig, i1, i2))
        elif tag == "insert":
            marker.append(_marker_einfuegung(schueler, j1, j2))
        else:
            marker.append(_marker_ersetzung(orig, schueler, i1, i2, j1, j2))

    # Zusätzlicher Hinweis, wenn obendrein die Großschreibung abweicht.
    if wort_original[:1].isupper() != wort_schueler[:1].isupper():
        marker.append("klein_statt_gross" if wort_original[:1].isupper()
                      else "gross_statt_klein")

    # Reihenfolge erhalten, Dubletten entfernen.
    gesehen: list[str] = []
    for m in marker:
        if m not in gesehen:
            gesehen.append(m)
    return tuple(gesehen) or ("sonstige",)


def kategorie_vorschlaege(marker: tuple[str, ...],
                          liste: Kategorienliste) -> list[Kategorie]:
    """Übersetzt Marker in konkrete Kategorien der geladenen Liste."""
    treffer: list[Kategorie] = []
    for m in marker:
        for kategorie in liste.mit_heuristik(m):
            if kategorie not in treffer:
                treffer.append(kategorie)
    return treffer


# ---------------------------------------------------------------------------
# Wortebene: Texte vergleichen
# ---------------------------------------------------------------------------

def vergleiche(text_original: str, text_schueler: str,
               liste: Kategorienliste | None = None) -> list[Abweichung]:
    """Liefert alle Stellen, an denen der Schülertext vom Original abweicht."""
    worte_o = woerter(text_original)
    worte_s = woerter(text_schueler)
    norm_o = [normalisieren(w) for w in worte_o]
    norm_s = [normalisieren(w) for w in worte_s]

    abweichungen: list[Abweichung] = []
    matcher = difflib.SequenceMatcher(None, norm_o, norm_s, autojunk=False)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            # Gleich in der Vergleichsform – Originalformen können sich aber
            # in der Groß-/Kleinschreibung unterscheiden.
            for versatz in range(i2 - i1):
                o = worte_o[i1 + versatz]
                s = worte_s[j1 + versatz]
                if o == s:
                    continue
                abweichungen.append(_abweichung(ERSETZT, o, s, i1 + versatz, worte_o))
        elif tag == "replace":
            laenge = max(i2 - i1, j2 - j1)
            for versatz in range(laenge):
                o = worte_o[i1 + versatz] if i1 + versatz < i2 else ""
                s = worte_s[j1 + versatz] if j1 + versatz < j2 else ""
                if o and s:
                    abweichungen.append(_abweichung(ERSETZT, o, s, i1 + versatz, worte_o))
                elif o:
                    abweichungen.append(_abweichung(FEHLT, o, "", i1 + versatz, worte_o))
                else:
                    abweichungen.append(
                        _abweichung(ZUSAETZLICH, "", s, min(i2, len(worte_o) - 1), worte_o)
                    )
        elif tag == "delete":
            for versatz in range(i2 - i1):
                o = worte_o[i1 + versatz]
                abweichungen.append(_abweichung(FEHLT, o, "", i1 + versatz, worte_o))
        elif tag == "insert":
            for versatz in range(j2 - j1):
                s = worte_s[j1 + versatz]
                abweichungen.append(
                    _abweichung(ZUSAETZLICH, "", s, min(i1, max(len(worte_o) - 1, 0)), worte_o)
                )

    if liste is not None:
        for a in abweichungen:
            a.vorschlaege = kategorie_vorschlaege(a.marker, liste)
    return abweichungen


def _abweichung(art: str, original: str, schueler: str, position: int,
                worte_o: list[str]) -> Abweichung:
    if art == FEHLT:
        marker = ("wort_fehlt",)
    elif art == ZUSAETZLICH:
        marker = ("sonstige",)
    else:
        marker = marker_bestimmen(original, schueler)
    kontext = satz_kontext(worte_o, position) if worte_o else ""
    return Abweichung(
        art=art,
        wort_original=original,
        wort_schueler=schueler,
        position=position,
        kontext=kontext,
        marker=marker,
    )


def kennzahlen(text_original: str, text_schueler: str) -> dict[str, int | float]:
    """Kurzstatistik für das Informationsblatt."""
    abweichungen = vergleiche(text_original, text_schueler)
    wortzahl = len(woerter(text_original))
    treffer = wortzahl - len(abweichungen)
    return {
        "wortzahl_original": wortzahl,
        "wortzahl_schueler": len(woerter(text_schueler)),
        "abweichungen": len(abweichungen),
        "richtig_geschrieben": max(treffer, 0),
        "fehlerquote_prozent": round(100 * len(abweichungen) / wortzahl, 1) if wortzahl else 0.0,
    }
