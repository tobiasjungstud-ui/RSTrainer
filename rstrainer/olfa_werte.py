"""OLFA-Kennwerte nach dem Original (Thomé/Thomé, OLFA 3–9+, 7. Aufl. 2023).

Alles hier trägt eine Seitenzahl des Originals. Nichts wird geschätzt:
Prozentanteile (S. 32), Fehler auf 100 Wörter F/100 (S. 32), tolerierte
Fehlerzahl TF nach Tabelle 5 (S. 30), Kompetenzwert KW (S. 34), relativer
Fehlerwert RF und Leistungswert LW (S. 34–35), Deutung (S. 36) und die
Wächter, die das Original vorschreibt (S. 15, 26, 28, 49).

Zählregel für Wörter (S. 16): Zahlen, Ziffern und Einzelbuchstaben zählen
nicht; ein fehlerhaft getrenntes Kompositum zählt als ein Wort (das leistet
die Ausrichtung im Diktatmodus, hier wird nur der Text gezählt).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from .olfa_engine import GRUPPEN

#: Tabelle 5, S. 30: tolerierte Fehler auf 100 Wörter. Schlüssel: Zeitpunkt.
#: Bis Ende 4. Klasse gilt ein Wert für alle Schulformen (Grundschule =
#: Realschulniveau); ab 5. Klasse nach Schulform Gymnasium / Realschule /
#: Haupt- und Gesamtschule.
TF_TABELLE: dict[str, dict[str, float]] = {
    "3 Mitte": {"alle": 21.5},
    "3 Ende / 4 Anfang": {"alle": 16.4},
    "4 Mitte": {"alle": 13.3},
    "4 Ende / 5 Anfang": {"alle": 11.1},
    "5 Mitte": {"gymnasium": 7.2, "realschule": 9.7, "hauptschule": 12.2},
    "5 Ende": {"gymnasium": 6.0, "realschule": 8.7, "hauptschule": 11.5},
    "6 Mitte": {"gymnasium": 5.0, "realschule": 8.0, "hauptschule": 11.0},
    "6 Ende": {"gymnasium": 4.3, "realschule": 7.5, "hauptschule": 10.8},
    "7 Mitte": {"gymnasium": 3.7, "realschule": 7.2, "hauptschule": 10.7},
    "7 Ende": {"gymnasium": 3.2, "realschule": 7.0, "hauptschule": 10.7},
    "8 Mitte": {"gymnasium": 2.8, "realschule": 6.8, "hauptschule": 10.8},
    "8 Ende": {"gymnasium": 2.5, "realschule": 6.7, "hauptschule": 11.0},
    "9 Mitte": {"gymnasium": 2.2, "realschule": 6.7, "hauptschule": 11.2},
}
ZEITPUNKTE = list(TF_TABELLE)
#: Schulformen des Originals mit der Schweizer Entsprechung (Sekundarstufe I).
SCHULFORMEN = {
    "gymnasium": "Gymnasium / Langzeitgymnasium",
    "realschule": "Sekundarschule, erweiterte Anforderungen (Realschulniveau)",
    "hauptschule": "Sekundarschule, Grundanforderungen (Haupt-/Gesamtschulniveau)",
}

#: Mindestmengen (S. 6, 15): etwa 350 Wörter und etwa 50 Fehler.
MIN_WOERTER = 350
MIN_FEHLER = 50

_WORT = re.compile(r"[^\W\d_][\w]*(?:[-'’][\w]+)*", re.UNICODE)


def woerter_zaehlen(text: str) -> int:
    """Zählregel S. 16: Zahlen, Ziffern und Einzelbuchstaben sind keine Wörter
    («Ich gehe in die Klasse 9a der IGS.» = 7 Wörter; «ca» zählt, «13» nicht)."""
    return sum(1 for m in _WORT.finditer(text or "") if len(m.group(0)) > 1)


def tf(zeitpunkt: str, schulform: str = "gymnasium") -> float | None:
    """Tolerierte Fehlerzahl auf 100 Wörter (Tabelle 5, S. 30)."""
    zeile = TF_TABELLE.get(zeitpunkt)
    if not zeile:
        return None
    return zeile.get("alle", zeile.get(schulform))


def tf_formel(klasse: float, schulform: str = "gymnasium") -> float:
    """Näherungsformeln S. 29 (nur zur Kontrolle, massgeblich ist Tabelle 5):
    Gymnasium 180/KL², Realschule + KL/2, Haupt-/Gesamtschule + KL."""
    basis = 180 / (klasse ** 2)
    if schulform == "realschule":
        return basis + klasse / 2
    if schulform == "hauptschule":
        return basis + klasse
    return basis


def _runde(x: float, stellen: int = 1) -> float:
    return round(x + 1e-9, stellen)


@dataclass
class Werte:
    woerter: int
    gesamt: int                       # Nrn. 1–37 (S. 32)
    gruppen: dict[str, int]           # I, II, III (Nrn. 1–35)
    ohne_gruppe: dict[str, int]       # 36, 37
    prozent: dict[str, float]         # Anteile je Gruppe, Summe 100,0 (S. 32)
    f100: float | None                # Fehler auf 100 Wörter (S. 32)
    kw: float | None                  # (II + III) − I (S. 34)
    tf: float | None = None           # Tabelle 5 (S. 30)
    rf: float | None = None           # F/100 : TF (S. 34)
    lw: float | None = None           # (II + III) − I · RF (S. 35)
    warnungen: list[str] = field(default_factory=list)
    rechenweg: list[str] = field(default_factory=list)


def _prozente(gruppen: dict[str, int]) -> dict[str, float]:
    """Anteile auf eine Nachkommastelle; das Original rundet so, dass die
    Summe 100,0 ergibt (S. 49: 66,2 / 26,5 / 7,3). Grösster-Rest-Verfahren."""
    summe = sum(gruppen.values())
    if not summe:
        return {"I": 0.0, "II": 0.0, "III": 0.0}
    roh = {g: 1000 * gruppen[g] / summe for g in ("I", "II", "III")}
    grund = {g: int(roh[g]) for g in roh}
    rest = 1000 - sum(grund.values())
    for g in sorted(roh, key=lambda g: -(roh[g] - grund[g]))[:rest]:
        grund[g] += 1
    return {g: grund[g] / 10 for g in grund}


def berechnen(kategorien: Iterable[str], woerter: int, zeitpunkt: str | None = None,
              schulform: str = "gymnasium", gruppen_karte: dict[str, str] | None = None) -> Werte:
    """Alle Kennwerte aus der Liste der Kategorienummern eines Textes (oder
    mehrerer Texte aus kurzem Zeitraum, S. 15).

    Nur Kategorien 01–37 werden gezählt; Grammatik- und andere Bereiche gehören
    nicht in die OLFA-Liste."""
    karte = gruppen_karte or GRUPPEN
    gruppen = {"I": 0, "II": 0, "III": 0}
    ohne = {"36": 0, "37": 0}
    gesamt = 0
    for nr in kategorien:
        nr = str(nr).zfill(2)
        if nr in karte:
            gruppen[karte[nr]] += 1; gesamt += 1
        elif nr in ohne:
            ohne[nr] += 1; gesamt += 1
    prozent = _prozente(gruppen)
    f100 = _runde(100 * gesamt / woerter) if woerter else None
    kw = _runde((prozent["II"] + prozent["III"]) - prozent["I"], 0) if sum(gruppen.values()) else None
    w = Werte(woerter=woerter, gesamt=gesamt, gruppen=gruppen, ohne_gruppe=ohne, prozent=prozent, f100=f100, kw=kw)
    w.rechenweg.append(f"Fehler in Gruppen I/II/III: {gruppen['I']}/{gruppen['II']}/{gruppen['III']} "
                       f"(Summe {sum(gruppen.values())}); 36: {ohne['36']}, 37: {ohne['37']}; Gesamtfehler {gesamt} (S. 32).")
    w.rechenweg.append(f"Anteile: {prozent['I']} % / {prozent['II']} % / {prozent['III']} % (S. 32, Rundung auf Summe 100).")
    if f100 is not None:
        w.rechenweg.append(f"F/100 = {gesamt} × 100 / {woerter} = {f100} (S. 32).")
    if kw is not None:
        w.rechenweg.append(f"KW = ({prozent['II']} + {prozent['III']}) − {prozent['I']} = {kw:g} (S. 34).")
    if zeitpunkt:
        w.tf = tf(zeitpunkt, schulform)
        if w.tf and f100 is not None:
            w.rf = _runde(f100 / w.tf)
            w.lw = _runde((prozent["II"] + prozent["III"]) - prozent["I"] * w.rf, 0)
            w.rechenweg.append(f"TF ({zeitpunkt}, {SCHULFORMEN.get(schulform, schulform)}) = {w.tf} (Tabelle 5, S. 30).")
            w.rechenweg.append(f"RF = F/100 : TF = {f100} : {w.tf} = {w.rf} (S. 34).")
            w.rechenweg.append(f"LW = ({prozent['II']} + {prozent['III']}) − {prozent['I']} × {w.rf} = {w.lw:g} (S. 35).")
    w.warnungen = warnungen(w)
    return w


def warnungen(w: Werte) -> list[str]:
    aus: list[str] = []
    if w.woerter < MIN_WOERTER or w.gesamt < MIN_FEHLER:
        aus.append(f"Textmenge: {w.woerter} Wörter, {w.gesamt} Fehler – das Original verlangt etwa {MIN_WOERTER} Wörter "
                   f"und etwa {MIN_FEHLER} Fehler (S. 6, 15); bei geringer Menge werden KW und LW ungenauer (S. 49). "
                   "Mehrere Texte aus kurzem Zeitraum dürfen zusammengefasst werden.")
    if w.gesamt and w.ohne_gruppe["37"] / w.gesamt > 0.03 and w.ohne_gruppe["37"] >= 2:
        aus.append(f"{w.ohne_gruppe['37']} von {w.gesamt} Fehlern liegen in 37 (Sonstige) – mehr als 3 %: "
                   "Zuordnung noch einmal überprüfen (S. 26), sofern es nicht überwiegend Fremdwörter sind.")
    summe = sum(w.gruppen.values())
    if summe >= 10 and w.gruppen["I"] / summe > 0.5:
        aus.append("Überwiegend Fehler der Gruppe I (03, 06, 11, 12, 29–35): Förderung vorrangig im lautlichen "
                   "Grundlagenbereich (S. 24, 49); bei sehr hohem Anteil OLFA 1–2 erwägen (S. 28).")
    if w.tf and w.f100 is not None and w.f100 < 2 * w.tf:
        aus.append(f"F/100 = {w.f100} liegt unter dem Zweifachen der tolerierten Fehlerzahl ({w.tf}): "
                   "Eine OLFA ist erst ab dem Zwei- bis Dreifachen sinnvoll (S. 6, 15); F/100 genügt dann zur Verlaufskontrolle (S. 37).")
    return aus


def deutung_kw(kw: float | None) -> str:
    """Bedeutung des Kompetenzwerts, S. 36."""
    if kw is None:
        return "Kein Kompetenzwert: keine Fehler in den Gruppen I–III."
    if kw > 70:
        return ("KW über 70: Das orthographische Fundament ist gefestigt – fast ausschliesslich an orthographischen "
                "Themen arbeiten (Gruppe III, horizontale Auswertung nach Rechtschreibbereichen).")
    if kw > 50:
        return ("KW 50–70: Förderung in den üblichen Rechtschreibbereichen (horizontale Auswertung), zusätzlich "
                "Übungen zur phonologischen Bewusstheit (z. B. Phonemanalysen).")
    if kw > 0:
        return ("KW 0–50: Ernste Probleme auf der Lautebene – länger anhaltender Förderbedarf; Lautgliederung und "
                "Lautdifferenzierung, besonders die Vokalquantität (Länge/Kürze), bis zur Sicherheit üben.")
    return ("KW um oder unter 0: wie unter 50, in deutlich verstärktem Mass; ärztliche Diagnostik unbedingt angeraten "
            "(auditive Wahrnehmung und Verarbeitung: Phoniater, Pädaudiologe, HNO).")


def deutung_lw(kw: float | None, lw: float | None) -> str:
    """S. 37: LW liegt in der Regel unter KW; die Differenz ist der Grad der
    orthographischen Verunsicherung. Beide sollen im Verlauf steigen und sich
    annähern."""
    if kw is None or lw is None:
        return ""
    diff = kw - lw
    return (f"Abstand KW − LW = {diff:g}: Grad der orthographischen Verunsicherung (S. 37). Bei erfolgreicher Förderung "
            "steigen beide Werte und nähern sich an; alle zwei bis drei Monate eintragen.")


def tabelle_zeilen(kategorien: Iterable[str], labels: dict[str, str] | None = None) -> list[dict]:
    """Die OLFA-Liste als Zeilen (Kopiervorlage S. 57/59): Nr, Name, Anzahl, Gruppe."""
    zaehler: dict[str, int] = {}
    for nr in kategorien:
        nr = str(nr).zfill(2)
        zaehler[nr] = zaehler.get(nr, 0) + 1
    labels = labels or {}
    zeilen = []
    for nr in [f"{i:02d}" for i in range(1, 38)]:
        if nr in ("21", "22"):
            continue
        zeilen.append({"nr": nr, "name": labels.get(nr, ""), "anzahl": zaehler.get(nr, 0),
                       "gruppe": GRUPPEN.get(nr, "–"),
                       "gesperrt_ch": nr in ("13", "14", "15", "16")})
    return zeilen
