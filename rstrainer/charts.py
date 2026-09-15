"""Diagramme zur Fehlerentwicklung.

Farbwahl
--------
Die Palette ist bewusst festgelegt und nicht dekorativ:

* Das Balkendiagramm zeigt **eine** Grösse (Häufigkeit) und bekommt deshalb
  genau **einen** Farbton, kein Regenbogen und keine Legende.
* Das Verlaufsdiagramm zeigt **Identität** (welche Kategorie) und verwendet
  eine kategoriale Palette in fester Reihenfolge – Kategorie 3 bekommt immer
  dieselbe Farbe, egal wie viele Linien gerade sichtbar sind.
* Höchstens 5 Linien gleichzeitig. Mehr Linien lassen sich nicht mehr
  zuverlässig auseinanderhalten; der Rest wandert in die Tabelle darunter.
* Jede Linie wird zusätzlich am rechten Ende direkt beschriftet. Die Farbe
  allein trägt die Information also nie – das ist zugleich die nötige
  Absicherung für die helleren Farbtöne der Palette.

Die Diagramme sind für den hellen Druck ausgelegt (Elterngespräch, Ausdruck,
Word-Bericht); es gibt bewusst keine Dunkelvariante.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from .analysis import Diktatpunkt  # noqa: E402
from .kategorien import Register  # noqa: E402

# --- Palette (geprüft auf Farbfehlsichtigkeit, helle Fläche) -----------------
FLAECHE = "#ffffff"
TINTE = "#0b0b0b"
TINTE_ZWEIT = "#52514e"
GEDAEMPFT = "#898781"
GITTER = "#e1e0d9"
ACHSE = "#c3c2b7"

#: Feste Reihenfolge – niemals durchrotieren lassen.
SERIENFARBEN = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
EINZELFARBE = "#2a78d6"

MAX_SERIEN = 5


def _grundgeruest(figur: Figure, achse) -> None:
    figur.patch.set_facecolor(FLAECHE)
    achse.set_facecolor(FLAECHE)
    for rand in ("top", "right"):
        achse.spines[rand].set_visible(False)
    for rand in ("left", "bottom"):
        achse.spines[rand].set_color(ACHSE)
        achse.spines[rand].set_linewidth(0.8)
    achse.tick_params(colors=GEDAEMPFT, labelsize=9, length=0)
    for beschriftung in achse.get_xticklabels() + achse.get_yticklabels():
        beschriftung.set_color(TINTE_ZWEIT)


def balken_kategorien(haeufigkeit: dict[str, int], register: Register,
                      titel: str = "Fehler nach Fehlerart",
                      hoechstens: int = 12) -> Figure:
    """Waagrechte Balken: wie oft kam welche Kategorie insgesamt vor."""
    daten = sorted(haeufigkeit.items(), key=lambda x: (-x[1], x[0]))[:hoechstens]
    figur, achse = plt.subplots(figsize=(9, max(2.4, 0.42 * len(daten) + 1.2)))
    _grundgeruest(figur, achse)

    if not daten:
        achse.text(0.5, 0.5, "Noch keine Fehler erfasst.", ha="center", va="center",
                   color=GEDAEMPFT, fontsize=11, transform=achse.transAxes)
        achse.set_xticks([])
        achse.set_yticks([])
        return figur

    # Gelernte Pfade werden lang («Grammatik › Kasus › Dativ statt …»).
    # Ungekürzt schieben sie die Balken aus dem Bild.
    beschriftungen = [register.kurz(nr, 36) for nr, _ in daten]
    werte = [anzahl for _, anzahl in daten]
    stellen = range(len(daten))

    achse.barh(list(stellen), werte, height=0.6, color=EINZELFARBE, zorder=3)
    achse.set_yticks(list(stellen))
    achse.set_yticklabels(beschriftungen, fontsize=9)
    achse.invert_yaxis()
    achse.xaxis.grid(True, color=GITTER, linewidth=0.8, zorder=0)
    achse.set_axisbelow(True)
    achse.set_xlabel("Anzahl Fehler", color=GEDAEMPFT, fontsize=9)

    # Direktbeschriftung am Balkenende statt Ablesen an der Achse.
    abstand = max(werte) * 0.015 if werte else 0.1
    for stelle, wert in zip(stellen, werte):
        achse.text(wert + abstand, stelle, str(wert), va="center", ha="left",
                   fontsize=9, color=TINTE_ZWEIT)
    achse.set_xlim(0, max(werte) * 1.12)

    achse.set_title(titel, color=TINTE, fontsize=12, fontweight="bold",
                    loc="left", pad=12)
    figur.tight_layout()
    return figur


def verlauf_linien(diktate: Sequence[Diktatpunkt], reihen: dict[str, list[int]],
                   register: Register,
                   titel: str = "Fehlerentwicklung über die Zeit",
                   hoechstens: int = MAX_SERIEN) -> tuple[Figure, list[str]]:
    """Linien je Kategorie: Fehler pro 100 Wörter über die Diktate hinweg.

    Rückgabe: ``(Figur, angezeigte_kategorien)`` – die nicht gezeigten
    Kategorien gehören in die Tabelle unter dem Diagramm.
    """
    figur, achse = plt.subplots(figsize=(9.5, 4.6))
    _grundgeruest(figur, achse)

    if not diktate or not reihen:
        achse.text(0.5, 0.5, "Noch keine auswertbaren Diktate vorhanden.",
                   ha="center", va="center", color=GEDAEMPFT, fontsize=11,
                   transform=achse.transAxes)
        achse.set_xticks([])
        achse.set_yticks([])
        return figur, []

    # Nach Gesamthäufigkeit auswählen – stabile, nachvollziehbare Reihenfolge.
    rangfolge = sorted(reihen.items(), key=lambda x: (-sum(x[1]), x[0]))
    gezeigt = [nr for nr, _ in rangfolge[:hoechstens]]

    x = list(range(len(diktate)))
    for stelle, nr in enumerate(gezeigt):
        reihe = reihen[nr]
        raten = [
            100.0 * anzahl / d.wortzahl if d.wortzahl else 0.0
            for anzahl, d in zip(reihe, diktate)
        ]
        farbe = SERIENFARBEN[stelle % len(SERIENFARBEN)]
        achse.plot(x, raten, color=farbe, linewidth=2.0, marker="o",
                   markersize=6, markeredgecolor=FLAECHE, markeredgewidth=1.5,
                   label=register.kurz(nr, 40), zorder=3)
        # Direktbeschriftung am rechten Linienende.
        achse.annotate(nr, xy=(x[-1], raten[-1]), xytext=(6, 0),
                       textcoords="offset points", va="center", fontsize=9,
                       fontweight="bold", color=TINTE_ZWEIT)

    achse.set_xticks(x)
    achse.set_xticklabels(
        [f"{d.datum[5:]}\n{d.titel[:14]}" for d in diktate], fontsize=8
    )
    achse.yaxis.grid(True, color=GITTER, linewidth=0.8, zorder=0)
    achse.set_axisbelow(True)
    achse.set_ylim(bottom=0)
    achse.set_ylabel("Fehler pro 100 Wörter", color=GEDAEMPFT, fontsize=9)
    achse.set_title(titel, color=TINTE, fontsize=12, fontweight="bold",
                    loc="left", pad=12)

    legende = achse.legend(loc="upper left", bbox_to_anchor=(0, -0.18),
                           ncol=2, frameon=False, fontsize=9)
    for text in legende.get_texts():
        text.set_color(TINTE_ZWEIT)
    figur.subplots_adjust(right=0.94)
    figur.tight_layout()
    return figur, gezeigt


def speichern(figur: Figure, pfad: Path | str, dpi: int = 200) -> Path:
    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    figur.savefig(pfad, dpi=dpi, bbox_inches="tight", facecolor=FLAECHE)
    return pfad
