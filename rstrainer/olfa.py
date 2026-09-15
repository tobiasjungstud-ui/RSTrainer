"""Laden, Speichern und Auswerten der OLFA-Kategorienliste.

Die Liste ist eine *Referenzliste*: fest genug, um überall gleich zu sein,
aber jederzeit durch die Lehrperson editierbar. Die mitgelieferte Datei in
``data/`` dient nur als Vorlage; sobald eine lokale Fassung unter
``daten/olfa_kategorien.json`` existiert, hat diese Vorrang.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import config


@dataclass(frozen=True)
class Kategorie:
    nr: str
    name: str
    kurzbeschreibung: str = ""
    beispiel: str = ""
    gruppe: str | None = None
    bereich: str = "Sonstiges"
    heuristik: tuple[str, ...] = ()
    geprueft: bool = False
    #: Gesperrte Nummern bleiben in der Liste, sind aber nicht mehr wählbar –
    #: entweder im Original unbesetzt oder in der Schweiz nicht anwendbar.
    gesperrt: bool = False
    grund: str = ""

    @property
    def label(self) -> str:
        """Einheitliche Darstellung in Menüs und Prompts: ``01 – Name``."""
        return f"{self.nr} – {self.name}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "nr": self.nr,
            "name": self.name,
            "kurzbeschreibung": self.kurzbeschreibung,
            "beispiel": self.beispiel,
            "gruppe": self.gruppe,
            "bereich": self.bereich,
            "heuristik": list(self.heuristik),
            "geprueft": self.geprueft,
            "gesperrt": self.gesperrt,
            "grund": self.grund,
        }


@dataclass
class Kategorienliste:
    kategorien: list[Kategorie] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    quelle: Path | None = None

    def __iter__(self):
        return iter(self.kategorien)

    def __len__(self) -> int:
        return len(self.kategorien)

    def get(self, nr: str) -> Kategorie | None:
        for k in self.kategorien:
            if k.nr == nr:
                return k
        return None

    def label(self, nr: str) -> str:
        """Label einer Kategorie – auch für Nummern, die es nicht mehr gibt."""
        k = self.get(nr)
        return k.label if k else f"{nr} – (unbekannte Kategorie)"

    def nach_bereich(self) -> dict[str, list[Kategorie]]:
        gruppiert: dict[str, list[Kategorie]] = {}
        for k in self.kategorien:
            gruppiert.setdefault(k.bereich, []).append(k)
        return gruppiert

    def mit_heuristik(self, marker: str) -> list[Kategorie]:
        return [k for k in self.kategorien if marker in k.heuristik]

    @property
    def waehlbar(self) -> list[Kategorie]:
        """Kategorien, die für neue Einträge zur Verfügung stehen."""
        return [k for k in self.kategorien if not k.gesperrt]

    @property
    def alle_geprueft(self) -> bool:
        return bool(self.kategorien) and all(k.geprueft for k in self.kategorien)

    @property
    def anzahl_ungeprueft(self) -> int:
        return sum(1 for k in self.kategorien if not k.geprueft)


def _kategorie_aus_dict(roh: dict[str, Any]) -> Kategorie:
    return Kategorie(
        nr=str(roh["nr"]),
        name=str(roh.get("name", "")).strip(),
        kurzbeschreibung=str(roh.get("kurzbeschreibung", "") or ""),
        beispiel=str(roh.get("beispiel", "") or ""),
        gruppe=roh.get("gruppe") or None,
        bereich=str(roh.get("bereich") or "Sonstiges"),
        heuristik=tuple(roh.get("heuristik") or ()),
        geprueft=bool(roh.get("geprueft", False)),
        gesperrt=bool(roh.get("gesperrt", False)),
        grund=str(roh.get("grund", "") or ""),
    )


def laden(pfad: Path | None = None) -> Kategorienliste:
    """Lädt die Kategorienliste.

    Reihenfolge: ausdrücklich angegebener Pfad → lokale Fassung der
    Lehrperson → mitgelieferte Vorlage.
    """
    if pfad is None:
        pfad = (
            config.OLFA_DATEI_LOKAL
            if config.OLFA_DATEI_LOKAL.exists()
            else config.OLFA_DATEI_MITGELIEFERT
        )
    with open(pfad, encoding="utf-8") as fh:
        roh = json.load(fh)
    kategorien = [_kategorie_aus_dict(k) for k in roh.get("kategorien", [])]
    return Kategorienliste(kategorien=kategorien, meta=roh.get("_meta", {}), quelle=pfad)


def speichern(liste: Kategorienliste, pfad: Path | None = None) -> Path:
    """Schreibt die Liste als lokale Fassung (Standard: ``daten/``)."""
    pfad = pfad or config.OLFA_DATEI_LOKAL
    pfad.parent.mkdir(parents=True, exist_ok=True)
    inhalt = {
        "_meta": liste.meta,
        "kategorien": [k.as_dict() for k in liste.kategorien],
    }
    with open(pfad, "w", encoding="utf-8") as fh:
        json.dump(inhalt, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return pfad
