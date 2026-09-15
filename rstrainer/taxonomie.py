"""Gelernte Fehlerarten – die wachsende Sammlung neben der festen OLFA-Liste.

Die OLFA-Liste deckt die Rechtschreibung ab. Alles andere – vor allem
Grammatik – benennt das Sprachmodell bei der Analyse selbst und ordnet es
hierarchisch ein, etwa ``Grammatik › Kasus › Dativ statt Akkusativ``.

Die Einträge werden **ohne Rückfrage angelegt**. Damit die Sammlung dabei
nicht zuwächst, greifen drei Vorkehrungen:

1. Die oberste Ebene ist nicht frei, sondern auf :data:`OBERBEGRIFFE`
   beschränkt. Sonst stünden nach zwanzig Texten «Grammatik»,
   «Grammatikalisch» und «Sprachrichtigkeit» nebeneinander.
2. Pfade werden beim Speichern begradigt und erst danach auf Dubletten
   geprüft – exakt gleiche werden zusammengelegt.
3. Ähnliche Paare werden nur **gemeldet**, nie automatisch verschmolzen:
   «Dativ statt Akkusativ» und «Akkusativ statt Dativ» teilen fast alle
   Wörter, meinen aber das Gegenteil.
"""

from __future__ import annotations

import json
import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable

from . import config

#: Die oberste Ebene jedes Pfades. Bewusst kurz gehalten.
OBERBEGRIFFE = ["Grammatik", "Zeichensetzung", "Wortschatz", "Formales", "Sonstiges"]

#: Kennungen gelernter Arten beginnen damit – so sind sie von OLFA-Nummern
#: unterscheidbar, ohne dass die Auswertung zwei Datenwege braucht.
PRAEFIX = "X-"


@dataclass
class Fehlerart:
    id: str
    pfad: tuple[str, ...]
    beschreibung: str = ""
    angelegt: str = ""
    herkunft: str = "modell"
    #: Noch nicht von der Lehrperson angesehen.
    neu: bool = True

    @property
    def label(self) -> str:
        return " › ".join(self.pfad)

    @property
    def oberbegriff(self) -> str:
        return self.pfad[0] if self.pfad else "Sonstiges"

    def as_dict(self) -> dict:
        return {"id": self.id, "pfad": list(self.pfad), "beschreibung": self.beschreibung,
                "angelegt": self.angelegt, "herkunft": self.herkunft, "neu": self.neu}


def kennung() -> str:
    return PRAEFIX + secrets.token_hex(4)


def ist_gelernt(nr: str) -> bool:
    return str(nr or "").startswith(PRAEFIX)


def _gross_erstes(wort: str) -> str:
    return wort[0].upper() + wort[1:] if wort else wort


def pfad_normalisieren(pfad: Iterable[str]) -> tuple[str, ...]:
    """Begradigt einen Pfad: Leerraum weg, erster Buchstabe gross, oberste
    Ebene auf :data:`OBERBEGRIFFE` gezwungen, höchstens drei Stufen."""
    stufen = [re.sub(r"\s+", " ", str(x)).strip() for x in (pfad or [])]
    stufen = [x for x in stufen if x]
    if not stufen:
        return ("Sonstiges", "Unbenannt")
    passend = next((o for o in OBERBEGRIFFE if o.lower() == stufen[0].lower()), None)
    stufen[0] = passend or "Sonstiges"
    return tuple(_gross_erstes(x) for x in stufen[:3])


def pfad_schluessel(pfad: Iterable[str]) -> str:
    return " > ".join(str(x).strip().lower() for x in (pfad or []))


def _wortmenge(text: str) -> set[str]:
    return {w for w in re.split(r"[^a-zäöüß]+", str(text).lower()) if len(w) > 2}


def aehnlichkeit(a: str, b: str) -> float:
    """Anteil gemeinsamer Wörter – rein zur Anzeige, nie zum Verschmelzen."""
    ta, tb = _wortmenge(a), _wortmenge(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(len(ta), len(tb))


@dataclass
class Sammlung:
    arten: list[Fehlerart] = field(default_factory=list)

    def __iter__(self):
        return iter(self.arten)

    def __len__(self) -> int:
        return len(self.arten)

    def get(self, kennung_: str) -> Fehlerart | None:
        return next((a for a in self.arten if a.id == kennung_), None)

    def nach_pfad(self, pfad: Iterable[str]) -> Fehlerart | None:
        schluessel = pfad_schluessel(pfad)
        return next((a for a in self.arten if pfad_schluessel(a.pfad) == schluessel), None)

    def label(self, kennung_: str) -> str:
        art = self.get(kennung_)
        return art.label if art else f"{kennung_} – (unbekannt)"

    def nach_oberbegriff(self) -> dict[str, list[Fehlerart]]:
        gruppen: dict[str, list[Fehlerart]] = {}
        for a in self.arten:
            gruppen.setdefault(a.oberbegriff, []).append(a)
        return gruppen

    @property
    def ungesehen(self) -> list[Fehlerart]:
        return [a for a in self.arten if a.neu]

    def anlegen(self, pfad: Iterable[str], beschreibung: str = "",
                herkunft: str = "modell") -> Fehlerart:
        """Legt eine Art an – oder gibt die bestehende mit gleichem Pfad zurück."""
        sauber = pfad_normalisieren(pfad)
        vorhanden = self.nach_pfad(sauber)
        if vorhanden:
            return vorhanden
        art = Fehlerart(id=kennung(), pfad=sauber, beschreibung=beschreibung.strip(),
                        angelegt=datetime.now().isoformat(timespec="seconds"),
                        herkunft=herkunft, neu=True)
        self.arten.append(art)
        self._sortieren()
        return art

    def umbenennen(self, kennung_: str, pfad: Iterable[str]) -> Fehlerart | None:
        art = self.get(kennung_)
        if art is None:
            return None
        art.pfad = pfad_normalisieren(pfad)
        self._sortieren()
        return art

    def loeschen(self, kennung_: str) -> bool:
        vorher = len(self.arten)
        self.arten = [a for a in self.arten if a.id != kennung_]
        return len(self.arten) < vorher

    def aehnliche_paare(self, schwelle: float = 0.6) -> list[tuple[Fehlerart, Fehlerart, int]]:
        """Paare, die sich womöglich doppeln – gleiche oberste Ebene, stark
        überlappende Benennung. Nur ein Hinweis, kein Automatismus."""
        paare = []
        for i, a in enumerate(self.arten):
            for b in self.arten[i + 1:]:
                if a.oberbegriff != b.oberbegriff:
                    continue
                wert = aehnlichkeit(" ".join(a.pfad[1:]), " ".join(b.pfad[1:]))
                if wert >= schwelle:
                    paare.append((a, b, round(wert * 100)))
        return sorted(paare, key=lambda x: -x[2])

    def _sortieren(self) -> None:
        self.arten.sort(key=lambda a: a.label)


# ---------------------------------------------------------------------------
# Speichern und Laden
# ---------------------------------------------------------------------------

def dateipfad() -> Path:
    return config.DATEN_DIR / "fehlerarten.json"


def laden(pfad: Path | None = None) -> Sammlung:
    pfad = pfad or dateipfad()
    if not pfad.exists():
        return Sammlung()
    with open(pfad, encoding="utf-8") as fh:
        roh = json.load(fh)
    arten = [
        Fehlerart(
            id=str(a["id"]),
            pfad=tuple(a.get("pfad") or ()),
            beschreibung=str(a.get("beschreibung", "") or ""),
            angelegt=str(a.get("angelegt", "") or ""),
            herkunft=str(a.get("herkunft", "modell") or "modell"),
            neu=bool(a.get("neu", False)),
        )
        for a in roh.get("arten", [])
    ]
    sammlung = Sammlung(arten=arten)
    sammlung._sortieren()
    return sammlung


def speichern(sammlung: Sammlung, pfad: Path | None = None) -> Path:
    pfad = pfad or dateipfad()
    pfad.parent.mkdir(parents=True, exist_ok=True)
    inhalt = {
        "hinweis": "Von der Analyse gelernte Fehlerarten. Enthält keine "
                   "personenbezogenen Daten, aber Rückschlüsse auf den Unterricht.",
        "arten": [a.as_dict() for a in sammlung],
    }
    with open(pfad, "w", encoding="utf-8") as fh:
        json.dump(inhalt, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return pfad
