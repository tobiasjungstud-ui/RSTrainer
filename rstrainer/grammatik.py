"""Feste Kategorienliste für die Bereiche B–E: Grammatik, Syntax,
Zeichensetzung, Textebene.

Die OLFA-Liste deckt die Rechtschreibung ab (Bereich A). Für alles andere gab
es bisher nur die *gelernten* Fehlerarten – vom Sprachmodell bei der Analyse
frei benannt. Das ist beweglich, aber nicht vergleichbar: Was in einem Text
«Grammatik › Kasus › Dativ statt Akkusativ» hiess, hiess im nächsten
«Grammatik › Fall». Ein Längsschnitt braucht eine stabile Liste.

Diese Liste ist deshalb **vorgegeben** (``data/grammatik_kategorien.json``)
und fachlich begründet: schulgrammatische Standardterminologie, Kommaregeln
nach amtlichem Regelwerk, Helvetismen ausdrücklich zulässig. Die gelernten
Arten bleiben als Ergänzung für das, was hier nicht steht.

Kennungen folgen der Konvention des Artefakts: ``B:Kasus`` – Bereichsbuchstabe,
Doppelpunkt, Kurzname. So sind sie von OLFA-Nummern (``07``) und gelernten
Arten (``X-…``) unterscheidbar, ohne dass die Auswertung drei Datenwege braucht.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DATEI = Path(__file__).resolve().parent.parent / "data" / "grammatik_kategorien.json"

#: Bereichsbuchstaben in der Reihenfolge der Anzeige. A ist die OLFA-Liste.
BEREICH_REIHE = ["A", "B", "C", "D", "E"]


@dataclass(frozen=True)
class Grammatikkategorie:
    id: str
    name: str
    beschreibung: str
    beispiel: str
    foerdern: str

    @property
    def bereich(self) -> str:
        return self.id.split(":", 1)[0]

    @property
    def label(self) -> str:
        return f"{BEREICHE[self.bereich]['name']} › {self.name}"


def _laden() -> tuple[dict[str, dict], dict[str, Grammatikkategorie]]:
    with open(DATEI, encoding="utf-8") as fh:
        roh = json.load(fh)
    bereiche = {"A": {"name": "Rechtschreibung", "foerdern": "Förderbereiche F1–F10 (siehe Auswertung)."}}
    bereiche.update(roh["bereiche"])
    katalog = {k["id"]: Grammatikkategorie(k["id"], k["name"], k.get("beschreibung", ""),
                                           k.get("beispiel", ""), k.get("foerdern", ""))
               for k in roh["kategorien"]}
    return bereiche, katalog


BEREICHE, KATALOG = _laden()


def get(kennung: str) -> Grammatikkategorie | None:
    return KATALOG.get(str(kennung or ""))


def ist_katalog(kennung: str) -> bool:
    return str(kennung or "") in KATALOG


def bereich_von(kennung: str) -> str:
    """Bereich A–E einer Kennung: OLFA-Nummern und Unbekanntes sind A,
    ``B:Kasus`` ist B – auch wenn der Kurzname nicht im Katalog steht."""
    k = str(kennung or "")
    if len(k) > 2 and k[1] == ":" and k[0] in "BCDE":
        return k[0]
    return "A"


def bereich_name(bereich: str) -> str:
    return BEREICHE.get(bereich, {}).get("name", bereich)


def nach_bereich(bereich: str) -> list[Grammatikkategorie]:
    return [k for k in KATALOG.values() if k.bereich == bereich]


def label(kennung: str) -> str:
    """Beschriftung auch für Kennungen, die nur der Konvention folgen
    (Altbestand aus dem Artefakt): ``B:Fall`` → «Grammatik / Morphologie › Fall»."""
    k = get(kennung)
    if k is not None:
        return k.label
    b = bereich_von(kennung)
    if b != "A":
        return f"{bereich_name(b)} › {str(kennung).split(':', 1)[1]}"
    return f"{kennung} – (unbekannt)"


def prompt_zeilen(bereiche: list[str] | None = None) -> str:
    """Die Liste, wie sie im Analyse-Prompt steht: Kennung, Name, Beschreibung,
    Beispiel – damit das Modell die vorhandenen Kategorien trifft, statt eigene
    zu erfinden."""
    zeilen = []
    for b in (bereiche or ["B", "C", "D", "E"]):
        zeilen.append(f"[{b}] {bereich_name(b)}")
        for k in nach_bereich(b):
            zeile = f"{k.id} = {k.name}. {k.beschreibung}"
            if k.beispiel:
                zeile += f" Beispiel: {k.beispiel}"
            zeilen.append(zeile)
    return "\n".join(zeilen)
