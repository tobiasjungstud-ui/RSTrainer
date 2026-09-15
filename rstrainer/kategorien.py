"""Gemeinsame Sicht auf beide Kategoriensysteme.

Ein Fehlereintrag trägt in ``kategorie_nr`` entweder eine OLFA-Nummer (``07``)
oder die Kennung einer gelernten Fehlerart (``X-a1b2c3d4``). Alles, was
auswertet, gruppiert stumpf nach diesem Feld – deshalb braucht es nur eine
Stelle, die aus einer Kennung eine Beschriftung macht.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import taxonomie
from .olfa import Kategorienliste
from .taxonomie import Sammlung

OLFA_OBERBEGRIFF = "Rechtschreibung (OLFA)"


@dataclass(frozen=True)
class Register:
    """Feste OLFA-Liste und gelernte Arten unter einem Dach."""

    liste: Kategorienliste
    sammlung: Sammlung

    def label(self, nr: str) -> str:
        kategorie = self.liste.get(nr)
        if kategorie is not None:
            return kategorie.label
        art = self.sammlung.get(nr)
        if art is not None:
            return art.label
        return f"{nr} – (unbekannt)"

    def name(self, nr: str) -> str:
        """Nur die Bezeichnung, ohne vorangestellte Nummer.

        Für Exportspalten, in denen die Kennung ohnehin daneben steht – dort
        wäre «07 – …» eine Dopplung.
        """
        kategorie = self.liste.get(nr)
        if kategorie is not None:
            return kategorie.name
        art = self.sammlung.get(nr)
        return art.label if art is not None else "(unbekannt)"

    def kurz(self, nr: str, laenge: int = 34) -> str:
        voll = self.label(nr)
        return voll[:laenge - 1] + "…" if len(voll) > laenge else voll

    def oberbegriff(self, nr: str) -> str:
        if self.liste.get(nr) is not None:
            return OLFA_OBERBEGRIFF
        art = self.sammlung.get(nr)
        return art.oberbegriff if art else "Sonstiges"

    def existiert(self, nr: str) -> bool:
        return self.liste.get(nr) is not None or self.sammlung.get(nr) is not None

    def waehlbar(self) -> list[tuple[str, str]]:
        """Alle auswählbaren Kennungen als ``(nr, label)``, OLFA zuerst."""
        eintraege = [(k.nr, k.label) for k in self.liste.waehlbar]
        eintraege += [(a.id, a.label) for a in self.sammlung]
        return eintraege

    def bereinigen(self, nr: str) -> str:
        """Kennungen, die es nicht mehr gibt, auf die Auffangkategorie lenken."""
        if self.existiert(nr) and not (self.liste.get(nr) and self.liste.get(nr).gesperrt):
            return nr
        return "37"


def laden(liste: Kategorienliste | None = None,
          sammlung: Sammlung | None = None) -> Register:
    from . import olfa
    return Register(liste=liste or olfa.laden(),
                    sammlung=sammlung if sammlung is not None else taxonomie.laden())


# ---------------------------------------------------------------------------
# Schwerpunkte einer einzelnen Auswertung
# ---------------------------------------------------------------------------

@dataclass
class Schwerpunkte:
    liste: list[tuple[str, int]]
    rest: int
    gesamt: int


def schwerpunkte(fehler, hoechstens: int = 5) -> Schwerpunkte:
    """Die auffälligsten Kategorien eines Textes mit ihrer Anzahl.

    Der lange Schwanz bleibt draussen: alles unter einem Fünftel des
    Spitzenwerts und alles ab Platz ``hoechstens``. Einzelvorkommen kommen nur
    durch, wenn es ohnehin nichts Häufigeres gibt – sonst stünde bei einem
    Text mit lauter Einzelfällen gar nichts da.
    """
    zaehler: dict[str, int] = {}
    for f in fehler:
        nr = f["kategorie_nr"] if isinstance(f, dict) else f.kategorie_nr
        zaehler[nr] = zaehler.get(nr, 0) + 1
    if not zaehler:
        return Schwerpunkte([], 0, 0)

    sortiert = sorted(zaehler.items(), key=lambda x: (-x[1], x[0]))
    groesste = sortiert[0][1]
    schwelle = max(2, -(-groesste // 5))
    auswahl = [x for x in sortiert if x[1] >= schwelle][:hoechstens]
    if not auswahl:
        auswahl = sortiert[:hoechstens]
    return Schwerpunkte(auswahl, len(sortiert) - len(auswahl), sum(zaehler.values()))
