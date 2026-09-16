"""Gemeinsame Sicht auf beide Kategoriensysteme.

Ein Fehlereintrag trägt in ``kategorie_nr`` entweder eine OLFA-Nummer (``07``)
oder die Kennung einer gelernten Fehlerart (``X-a1b2c3d4``). Alles, was
auswertet, gruppiert stumpf nach diesem Feld – deshalb braucht es nur eine
Stelle, die aus einer Kennung eine Beschriftung macht.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import grammatik, taxonomie
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
        if grammatik.bereich_von(nr) != "A":
            return grammatik.label(nr)
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
        if art is not None:
            return art.label
        g = grammatik.get(nr)
        if g is not None:
            return g.name
        return "(unbekannt)"

    def kurz(self, nr: str, laenge: int = 34) -> str:
        voll = self.label(nr)
        return voll[:laenge - 1] + "…" if len(voll) > laenge else voll

    def oberbegriff(self, nr: str) -> str:
        if self.liste.get(nr) is not None:
            return OLFA_OBERBEGRIFF
        art = self.sammlung.get(nr)
        if art:
            return art.oberbegriff
        b = grammatik.bereich_von(nr)
        return grammatik.bereich_name(b) if b != "A" else "Sonstiges"

    def bereich(self, nr: str) -> str:
        """Bereich A–E: OLFA-Nummern sind A, Katalogkennungen tragen ihren
        Buchstaben, gelernte Arten werden über den Oberbegriff zugeordnet."""
        if self.liste.get(nr) is not None:
            return "A"
        art = self.sammlung.get(nr)
        if art:
            return {"Grammatik": "B", "Zeichensetzung": "D", "Wortschatz": "E"}.get(art.oberbegriff, "E")
        return grammatik.bereich_von(nr)

    def existiert(self, nr: str) -> bool:
        return (self.liste.get(nr) is not None or self.sammlung.get(nr) is not None
                or grammatik.ist_katalog(nr))

    def waehlbar(self) -> list[tuple[str, str]]:
        """Alle auswählbaren Kennungen als ``(nr, label)``, OLFA zuerst."""
        eintraege = [(k.nr, k.label) for k in self.liste.waehlbar]
        eintraege += [(k.id, k.label) for k in grammatik.KATALOG.values()]
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


# ---------------------------------------------------------------------------
# Förderbereiche F1–F10 (Ergänzung B.2) – die eigentliche Ausgabeebene
# ---------------------------------------------------------------------------

from . import olfa_engine as _engine  # noqa: E402

FOERDERBEREICHE = _engine.FOERDERBEREICHE
FB_REIHE = ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10"]


def foerderbereich_von(nr: str) -> str | None:
    """Förderbereich einer OLFA-Nummer; ``None`` für B–E und Unbekanntes."""
    return _engine.AREA_MAP.get(str(nr))


def bereich_von(nr: str) -> str:
    """Bereich A–E einer Kennung: OLFA-Nummern sind A, ``B:Kasus`` ist B."""
    nr = str(nr or "")
    if len(nr) > 2 and nr[1] == ":" and nr[0] in "BCDE":
        return nr[0]
    return "A"


def fehler_nach_foerderbereich(fehler) -> list[dict]:
    """Fehler aus Bereich A auf ihre Förderbereiche umgeschlüsselt – damit
    Trend und Empfehlung auf zehn Reihen rechnen statt auf 37."""
    aus = []
    for f in fehler:
        d = dict(f) if not isinstance(f, dict) else dict(f)
        nr = str(d.get("kategorie_nr", ""))
        fb = foerderbereich_von(nr)
        if bereich_von(nr) == "A" and fb:
            d["kategorie_nr"] = fb
            aus.append(d)
    return aus


def verteilung_foerderbereiche(fehler) -> dict[str, int]:
    z: dict[str, int] = {}
    for f in fehler_nach_foerderbereich(fehler):
        z[f["kategorie_nr"]] = z.get(f["kategorie_nr"], 0) + 1
    return z


def foerderbereich_label(f: str) -> str:
    b = FOERDERBEREICHE.get(f)
    return f"{f} – {b['name']}" if b else f
