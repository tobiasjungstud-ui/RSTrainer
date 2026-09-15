"""Trendanalyse und Empfehlungslogik für Förderschwerpunkte.

Dokumentierte Annahmen
----------------------
* **Normierung:** Verglichen werden nicht absolute Fehlerzahlen, sondern
  *Fehler pro 100 Wörter*. Ein 60-Wort-Diktat und ein 180-Wort-Diktat sind
  sonst nicht vergleichbar. Diktate ohne hinterlegte Wortzahl werden mit
  ihrer tatsächlichen Wortzahl aus dem Text berechnet; ist auch die 0,
  fließt das Diktat nicht in die Rate ein.
* **Trendfenster:** Verglichen werden die letzten ``fenster`` Diktate mit den
  ``fenster`` davor. Standard ist 3. Es braucht also mindestens 4 Diktate,
  bevor überhaupt ein Trend ausgewiesen wird – vorher lautet die Einstufung
  ``zu_wenig_daten``.
* **Schwellen:** Eine Veränderung gilt erst ab 20 % relativer Abweichung als
  Trend. Zusätzlich muss die absolute Differenz mindestens 0,5 Fehler pro
  100 Wörter betragen, damit aus 1 statt 2 Einzelfehlern kein "Trend" wird.
* **Rundung:** Alle ausgewiesenen Raten werden auf 2 Nachkommastellen
  gerundet. Die Klassifikation rechnet mit den ungerundeten Werten.
* **Zeitgewichtung:** Exponentieller Abfall mit einer Halbwertszeit von 3
  Diktaten. Das jüngste Diktat hat Gewicht 1,0, das drittletzte 0,5 usw.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from . import config

ABNEHMEND = "abnehmend"
STAGNIEREND = "stagnierend"
ZUNEHMEND = "zunehmend"
NEU = "neu"
ZU_WENIG_DATEN = "zu_wenig_daten"

TREND_SYMBOL = {
    ABNEHMEND: "↓",
    STAGNIEREND: "→",
    ZUNEHMEND: "↑",
    NEU: "✦",
    ZU_WENIG_DATEN: "·",
}

TREND_TEXT = {
    ABNEHMEND: "abnehmend",
    STAGNIEREND: "stagnierend",
    ZUNEHMEND: "zunehmend",
    NEU: "neu aufgetreten",
    ZU_WENIG_DATEN: "zu wenig Daten",
}

#: Wie stark der Trend in die Priorisierung eingeht.
TREND_FAKTOR = {
    ABNEHMEND: 0.6,
    STAGNIEREND: 1.0,
    ZUNEHMEND: 1.35,
    NEU: 1.1,
    ZU_WENIG_DATEN: 1.0,
}


@dataclass
class Diktatpunkt:
    """Ein Diktat als Messpunkt der Zeitreihe."""

    diktat_id: int
    datum: str
    titel: str
    wortzahl: int
    #: Was vor dem Schreiben als Ziel gesetzt war. Nur die Sondierung braucht
    #: das: Eine Kategorie, die schon einmal Ziel war und trotzdem keinen
    #: Fehler brachte, ist weniger unerforscht als eine nie geprüfte.
    ziel_kategorien: tuple[str, ...] = ()


@dataclass
class Trend:
    kategorie_nr: str
    einstufung: str
    rate_aktuell: float
    rate_vorher: float
    veraenderung: float | None
    summe_gesamt: int
    diktate_mit_fehler: int
    diktate_gesamt: int

    @property
    def symbol(self) -> str:
        return TREND_SYMBOL[self.einstufung]

    @property
    def text(self) -> str:
        return TREND_TEXT[self.einstufung]


@dataclass
class Empfehlung:
    kategorie_nr: str
    punktzahl: float
    trend: Trend
    begruendung: str
    details: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Zeitreihe aufbauen
# ---------------------------------------------------------------------------

def zeitreihe(diktate: Sequence[Diktatpunkt],
              fehler: Iterable[dict]) -> dict[str, list[int]]:
    """Fehler je Kategorie und Diktat, in der Reihenfolge von ``diktate``.

    ``fehler`` sind Abbildungen mit den Schlüsseln ``kategorie_nr`` und
    ``diktat_id``. Fehler ohne zuordenbares Diktat werden ignoriert, weil sie
    sich keinem Zeitpunkt zuordnen lassen.
    """
    index = {d.diktat_id: i for i, d in enumerate(diktate)}
    reihen: dict[str, list[int]] = {}
    for f in fehler:
        diktat_id = f.get("diktat_id")
        if diktat_id not in index:
            continue
        nr = str(f["kategorie_nr"])
        reihe = reihen.setdefault(nr, [0] * len(diktate))
        reihe[index[diktat_id]] += 1
    return reihen


def _raten(reihe: Sequence[int], diktate: Sequence[Diktatpunkt]) -> list[float]:
    """Rechnet absolute Fehlerzahlen in Fehler pro 100 Wörter um."""
    raten = []
    for anzahl, d in zip(reihe, diktate):
        if d.wortzahl > 0:
            raten.append(100.0 * anzahl / d.wortzahl)
        else:
            raten.append(0.0)
    return raten


def _mittel(werte: Sequence[float]) -> float:
    return sum(werte) / len(werte) if werte else 0.0


# ---------------------------------------------------------------------------
# Trend
# ---------------------------------------------------------------------------

def trend_bestimmen(reihe: Sequence[int], diktate: Sequence[Diktatpunkt],
                    kategorie_nr: str = "",
                    fenster: int = config.TREND_FENSTER,
                    schwelle: float = config.TREND_SCHWELLE,
                    mindestdifferenz: float = config.TREND_MINDESTDIFFERENZ) -> Trend:
    """Stuft eine Kategorie als abnehmend / stagnierend / zunehmend ein."""
    raten = _raten(reihe, diktate)
    summe = int(sum(reihe))
    mit_fehler = sum(1 for x in reihe if x > 0)

    basis = Trend(
        kategorie_nr=kategorie_nr,
        einstufung=ZU_WENIG_DATEN,
        rate_aktuell=round(_mittel(raten[-fenster:]), 2) if raten else 0.0,
        rate_vorher=0.0,
        veraenderung=None,
        summe_gesamt=summe,
        diktate_mit_fehler=mit_fehler,
        diktate_gesamt=len(diktate),
    )

    if len(diktate) < fenster + 1:
        return basis

    aktuell_roh = raten[-fenster:]
    vorher_roh = raten[-2 * fenster:-fenster]
    if not vorher_roh:
        return basis

    aktuell = _mittel(aktuell_roh)
    vorher = _mittel(vorher_roh)
    basis.rate_aktuell = round(aktuell, 2)
    basis.rate_vorher = round(vorher, 2)

    if vorher == 0 and aktuell == 0:
        basis.einstufung = STAGNIEREND
        basis.veraenderung = 0.0
        return basis

    if vorher == 0:
        # Die Kategorie taucht erst im aktuellen Fenster auf.
        basis.einstufung = NEU
        basis.veraenderung = None
        return basis

    veraenderung = (aktuell - vorher) / vorher
    basis.veraenderung = round(veraenderung, 3)

    if abs(aktuell - vorher) < mindestdifferenz or abs(veraenderung) < schwelle:
        basis.einstufung = STAGNIEREND
    elif veraenderung < 0:
        basis.einstufung = ABNEHMEND
    else:
        basis.einstufung = ZUNEHMEND
    return basis


def trends_bestimmen(diktate: Sequence[Diktatpunkt], fehler: Iterable[dict],
                     **kwargs) -> dict[str, Trend]:
    reihen = zeitreihe(diktate, fehler)
    return {
        nr: trend_bestimmen(reihe, diktate, kategorie_nr=nr, **kwargs)
        for nr, reihe in reihen.items()
    }


# ---------------------------------------------------------------------------
# Empfehlung
# ---------------------------------------------------------------------------

def _gewichte(anzahl: int, halbwertszeit: float) -> list[float]:
    """Exponentielle Gewichte: jüngstes Diktat 1.0, dann abfallend."""
    if anzahl <= 0:
        return []
    return [
        math.pow(0.5, (anzahl - 1 - i) / halbwertszeit)
        for i in range(anzahl)
    ]


def empfehlungen(diktate: Sequence[Diktatpunkt], fehler: Iterable[dict],
                 anzahl: int = config.MAX_FOERDERSCHWERPUNKTE,
                 fenster: int = config.TREND_FENSTER,
                 halbwertszeit: float = config.GEWICHT_HALBWERTSZEIT,
                 blockieren: Iterable[str] = ()) -> list[Empfehlung]:
    """Schlägt bis zu ``anzahl`` Förderschwerpunkte vor.

    Punktzahl = zeitgewichtete Fehlerrate × Trendfaktor × Verbreitungsfaktor.

    * *zeitgewichtete Fehlerrate*: Fehler pro 100 Wörter, wobei jüngere
      Diktate exponentiell stärker zählen (Halbwertszeit 3 Diktate).
    * *Trendfaktor*: Kategorien, die sich bereits bessern, werden mit 0,6
      abgewertet; zunehmende mit 1,35 aufgewertet. Genau das ist der Wunsch,
      stagnierende und zunehmende Fehler zu bevorzugen.
    * *Verbreitungsfaktor*: Eine Kategorie, die in vielen der letzten Diktate
      vorkommt, ist verlässlicher als ein einmaliger Ausreißer.
      0,5 + 0,5 × (Diktate mit Fehler / betrachtete Diktate).
    """
    fehler = list(fehler)
    reihen = zeitreihe(diktate, fehler)
    blockiert = set(blockieren)
    gewichte = _gewichte(len(diktate), halbwertszeit)
    gewichtssumme = sum(gewichte) or 1.0

    ergebnisse: list[Empfehlung] = []
    for nr, reihe in reihen.items():
        if nr in blockiert or sum(reihe) == 0:
            continue
        trend = trend_bestimmen(reihe, diktate, kategorie_nr=nr, fenster=fenster)
        raten = _raten(reihe, diktate)

        gewichtete_rate = sum(r * g for r, g in zip(raten, gewichte)) / gewichtssumme
        betrachtet = min(len(diktate), 2 * fenster)
        mit_fehler_jung = sum(1 for x in reihe[-betrachtet:] if x > 0)
        verbreitung = 0.5 + 0.5 * (mit_fehler_jung / betrachtet if betrachtet else 0)
        punktzahl = gewichtete_rate * TREND_FAKTOR[trend.einstufung] * verbreitung

        ergebnisse.append(
            Empfehlung(
                kategorie_nr=nr,
                punktzahl=round(punktzahl, 3),
                trend=trend,
                begruendung=_begruendung(nr, trend, mit_fehler_jung, betrachtet),
                details={
                    "gewichtete_rate": round(gewichtete_rate, 2),
                    "verbreitung": round(verbreitung, 2),
                    "trendfaktor": TREND_FAKTOR[trend.einstufung],
                    "fehler_gesamt": int(sum(reihe)),
                    "reihe": list(reihe),
                },
            )
        )

    ergebnisse.sort(key=lambda e: (-e.punktzahl, e.kategorie_nr))
    return ergebnisse[:anzahl]


def _begruendung(nr: str, trend: Trend, mit_fehler_jung: int, betrachtet: int) -> str:
    teile = [
        f"Kategorie {nr} in {mit_fehler_jung} von {betrachtet} betrachteten Diktaten",
        f"{trend.summe_gesamt} Fehler insgesamt",
    ]
    if trend.einstufung == ABNEHMEND:
        teile.append(
            f"Besserung erkennbar ({trend.rate_vorher} → {trend.rate_aktuell} "
            "Fehler/100 Wörter) – daher niedriger gewichtet"
        )
    elif trend.einstufung == ZUNEHMEND:
        teile.append(
            f"Zunahme ({trend.rate_vorher} → {trend.rate_aktuell} Fehler/100 Wörter)"
        )
    elif trend.einstufung == STAGNIEREND:
        teile.append("keine Besserung erkennbar")
    elif trend.einstufung == NEU:
        teile.append("neu im aktuellen Zeitraum aufgetreten")
    else:
        teile.append("noch zu wenige Diktate für eine Trendaussage")
    return "; ".join(teile) + "."


# ---------------------------------------------------------------------------
# Klassiker gegen Sondierung
# ---------------------------------------------------------------------------

def sondierungsvorrat(diktate: Sequence[Diktatpunkt], fehler: Iterable[dict],
                      register) -> list[str]:
    """Kategorien, zu denen dieses Kind noch keinen Fehler hat.

    Noch nie als Ziel gesetzte kommen zuerst, danach wird breit über die
    Rechtschreibbereiche gestreut. Das Fenster wandert mit der Zahl der Texte
    weiter, damit nicht immer dieselben Kandidaten geprüft werden.
    """
    gesehen = {str(f["kategorie_nr"]) for f in fehler}
    war_ziel: set[str] = set()
    for d in diktate:
        for nr in d.ziel_kategorien or ():
            war_ziel.add(str(nr))

    kandidaten = [
        (k.nr, k.bereich) for k in register.liste.waehlbar if k.nr not in gesehen
    ] + [
        (a.id, a.oberbegriff) for a in register.sammlung if a.id not in gesehen
    ]
    kandidaten.sort(key=lambda x: (x[0] in war_ziel, x[0]))

    nach_bereich: dict[str, list[str]] = {}
    for nr, bereich in kandidaten:
        nach_bereich.setdefault(bereich, []).append(nr)

    gestreut: list[str] = []
    runde = 0
    while len(gestreut) < len(kandidaten):
        for eintraege in nach_bereich.values():
            if runde < len(eintraege):
                gestreut.append(eintraege[runde])
        runde += 1

    if not gestreut:
        return []
    versatz = len(diktate) % len(gestreut)
    return gestreut[versatz:] + gestreut[:versatz]


@dataclass
class Mischung:
    klassiker: list[str]
    sondierung: list[str]

    @property
    def alle(self) -> list[str]:
        return [*self.klassiker, *self.sondierung]


def kategorien_mischen(diktate: Sequence[Diktatpunkt], fehler: Iterable[dict],
                       register, anzahl: int = 4,
                       neu_anteil: float = 0.25) -> Mischung:
    """Mischt bekannte Schwerpunkte und unerprobte Kategorien.

    ``neu_anteil`` 0 liefert nur Klassiker, 1 nur Sondierung. Fehlt eine der
    beiden Seiten – etwa bei einem neuen Profil ohne Fehler –, füllt die
    andere auf.
    """
    fehler = list(fehler)
    anzahl = max(1, anzahl)
    rang = [e.kategorie_nr for e in empfehlungen(diktate, fehler, anzahl=anzahl)]
    vorrat = sondierungsvorrat(diktate, fehler, register)

    wunsch_neu = min(round(anzahl * neu_anteil), len(vorrat))
    wunsch_alt = min(anzahl - wunsch_neu, len(rang))
    wunsch_neu = min(anzahl - wunsch_alt, len(vorrat))

    klassiker = rang[:wunsch_alt]
    sondierung = [nr for nr in vorrat if nr not in klassiker][:wunsch_neu]
    return Mischung(klassiker=klassiker, sondierung=sondierung)
