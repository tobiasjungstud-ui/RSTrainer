"""Testmodus: frei erfundene Beispieldaten.

Alle Namen, Diktate und Fehler hier sind ausgedacht. Der Testmodus dient
dazu, neue Funktionen auszuprobieren, ohne echte Schülerdaten anzufassen.

Die Demoprofile sind am Namenspräfix erkennbar (``DEMO –``) und lassen sich
mit :func:`demodaten_entfernen` in einem Zug wieder löschen.
"""

from __future__ import annotations

import random
import sqlite3
from datetime import date, timedelta

from . import db

DEMO_PRAEFIX = "DEMO – "

#: Fehlerprofile der Demoschüler:innen: Kategorie → (Fehler pro 100 Wörter, Entwicklung)
#: Entwicklung: "abnehmend", "stagnierend", "zunehmend"
DEMO_PROFILE = {
    "Lena B.": {
        "klasse": "5a",
        "notiz": "Frei erfundenes Demoprofil. Schwerpunkt Vokallänge und Silbenrand.",
        "muster": {"07": (6, "abnehmend"), "09": (5, "stagnierend"),
                    "01": (3, "zunehmend"), "19": (6, "stagnierend"),
                    "36": (5, "abnehmend")},
    },
    "Tim K.": {
        "klasse": "6b",
        "notiz": "Frei erfundenes Demoprofil. Schwerpunkt Groß-/Kleinschreibung.",
        "muster": {"01": (8, "stagnierend"), "02": (6, "stagnierend"),
                    "27": (4, "zunehmend"), "07": (3, "abnehmend")},
    },
    "Sara M.": {
        "klasse": "4c",
        "notiz": "Frei erfundenes Demoprofil. Wenige Diktate, noch keine Trendaussage.",
        "muster": {"36": (4, "stagnierend"), "29": (4, "stagnierend")},
    },
}

DEMO_DIKTATE = [
    ("Der Ausflug in den Wald",
     "Am Montagmorgen packten die Kinder ihre Rucksäcke und machten sich auf den "
     "Weg in den Wald. Der schmale Pfad führte an einem Bach vorbei. Tim entdeckte "
     "einen Frosch, der schnell ins Wasser sprang. Lena sammelte bunte Blätter und "
     "legte sie sorgfältig in ihr Heft. Am Mittag setzten sich alle auf einen "
     "grossen Baumstamm und assen ihre Brote. Die Sonne schien warm durch die Äste. "
     "Auf dem Rückweg zählten sie die verschiedenen Bäume am Wegrand."),
    ("Ein Tag am See",
     "Der See lag ruhig in der Morgensonne. Ein alter Mann sass am Ufer und "
     "wartete geduldig auf einen Fisch. Kinder rannten über den schmalen Steg und "
     "sprangen lachend ins kühle Wasser. Eine Familie breitete eine karierte Decke "
     "aus und stellte einen Korb mit Äpfeln darauf. Am Nachmittag zog ein Gewitter "
     "auf, und alle packten schnell ihre Sachen zusammen."),
    ("Das neue Fahrrad",
     "Anna bekam zum Geburtstag ein neues Fahrrad. Es war rot und hatte einen "
     "breiten Sattel. Gleich am ersten Tag fuhr sie damit zur Schule. Der Weg "
     "führte über eine steile Strasse und an einer alten Mauer entlang. Vor dem "
     "Schulhaus stellte sie das Rad ab und schloss es sorgfältig an. In der Pause "
     "erzählte sie ihren Freundinnen begeistert davon."),
    ("Im Zirkus",
     "Am Samstagabend gingen wir in den Zirkus. Das grosse Zelt stand mitten auf "
     "der Wiese. Unter der Kuppel schwangen Artisten an langen Seilen hin und her. "
     "Ein Clown stolperte über seine eigenen Schuhe und brachte alle zum Lachen. "
     "Später trat eine Frau mit drei weissen Pferden auf. Zum Schluss klatschten "
     "die Zuschauer lange und gingen zufrieden nach Hause."),
    ("Der verlorene Schlüssel",
     "Paul suchte seinen Schlüssel im ganzen Zimmer. Er schaute unter dem Bett, "
     "in der Schublade und sogar im Kühlschrank. Seine Schwester half ihm und "
     "durchsuchte die Jackentaschen. Schliesslich fanden sie den Schlüssel im "
     "Schuh neben der Tür. Paul war erleichtert und versprach, künftig besser "
     "aufzupassen."),
    ("Winter im Dorf",
     "Über Nacht hatte es geschneit. Die Dächer waren weiss, und auf der Strasse "
     "knirschte der Schnee unter den Stiefeln. Kinder bauten einen dicken "
     "Schneemann und gaben ihm einen Hut aus Papier. Am Hang fuhren sie mit "
     "Schlitten hinunter. Als es dunkel wurde, leuchteten die Fenster warm, und "
     "alle gingen zum Abendessen hinein."),
]

#: Beispielhafte Falschschreibungen je Kategorie (erfunden, aber realistisch).
DEMO_FEHLERWOERTER = {
    "01": [("Wald", "wald"), ("Kinder", "kinder"), ("Sonne", "sonne"),
           ("Schule", "schule"), ("Strasse", "strasse")],
    "02": [("schnell", "Schnell"), ("alter", "Alter"), ("kühle", "Kühle")],
    "07": [("rannten", "ranten"), ("Sonne", "Sone"), ("schwammen", "schwamen"),
           ("Schlitten", "Schliten"), ("Wasser", "Waser")],
    "09": [("Bahn", "Ban"), ("führte", "fürte"), ("Zahn", "Zan"),
           ("Schuh", "Schu"), ("Wiese", "Wise"), ("Boot", "Bot")],
    "19": [("Hund", "Hunt"), ("Wald", "Walt"), ("Korb", "Korp"),
           ("Weg", "Wek"), ("Abend", "Abent")],
    "27": [("wenig", "wenich"), ("ruhig", "ruhich"), ("richtig", "richtich")],
    "29": [("Schule", "Sule"), ("Pferde", "Ferde"), ("schwangen", "swangen")],
    "36": [("Bäume", "Baume"), ("kühle", "kuhle"), ("Äste", "Aste"),
           ("Rucksäcke", "Rucksacke")],
}

_ENTWICKLUNG = {
    "abnehmend": lambda i, n: max(0.15, 1.0 - 0.85 * (i / max(n - 1, 1))),
    "stagnierend": lambda i, n: 1.0,
    "zunehmend": lambda i, n: 0.2 + 1.1 * (i / max(n - 1, 1)),
}


def demodaten_anlegen(con: sqlite3.Connection, seed: int = 20260911) -> list[int]:
    """Legt die Demoprofile samt Diktaten und Fehlern an.

    Der Zufallsgenerator ist mit einem festen Startwert versehen, damit die
    Demodaten reproduzierbar sind – zwei Aufrufe erzeugen dieselben Zahlen.
    """
    zufall = random.Random(seed)
    heute = date.today()
    angelegt: list[int] = []

    for name, profil in DEMO_PROFILE.items():
        schueler_id = db.schueler_anlegen(
            con, f"{DEMO_PRAEFIX}{name}",
            kuerzel="".join(teil[0] for teil in name.split() if teil),
            klasse=profil["klasse"], notiz=profil["notiz"],
        )
        angelegt.append(schueler_id)

        anzahl = 2 if name == "Sara M." else len(DEMO_DIKTATE)
        uebertrag: dict[str, float] = {}
        for i, (titel, text) in enumerate(DEMO_DIKTATE[:anzahl]):
            datum = (heute - timedelta(days=7 * (anzahl - i))).isoformat()
            ziel = list(profil["muster"])[:3]
            diktat_id = db.diktat_anlegen(
                con, schueler_id, titel, text, datum=datum,
                ziel_kategorien=ziel,
                notiz="Demodaten – frei erfunden.",
                quelle="demo", freigegeben=True, korrektur_gelesen=True,
            )
            db.diktat_aktualisieren(
                con, diktat_id, schuelertext=_schuelertext_bauen(text, profil, i, anzahl, zufall)
            )

            eintraege = []
            wortzahl = db.diktat_holen(con, diktat_id)["wortzahl"]
            for kategorie_nr, (start, entwicklung) in profil["muster"].items():
                faktor = _ENTWICKLUNG[entwicklung](i, anzahl)
                # "start" ist eine Rate pro 100 Wörter. Die Demodiktate sind
                # unterschiedlich lang; ohne diese Umrechnung würde ein kurzes
                # Diktat fälschlich wie eine Verschlechterung aussehen.
                erwartet = start * faktor * wortzahl / 100.0
                # Fehlerzahlen sind ganze Zahlen, die Sollrate ist es nicht.
                # Würde jedes Diktat für sich gerundet, summierten sich die
                # Rundungsfehler bei kurzen Texten zu einem Scheintrend. Der
                # Rest wird deshalb ins nächste Diktat übertragen, sodass die
                # tatsächliche Rate der eingestellten folgt.
                rest = uebertrag.get(kategorie_nr, 0.0)
                menge = max(0, int(erwartet + rest + 0.5))
                uebertrag[kategorie_nr] = erwartet + rest - menge
                woerter = DEMO_FEHLERWOERTER.get(kategorie_nr, [("Wort", "Wor")])
                for _ in range(menge):
                    richtig, falsch = zufall.choice(woerter)
                    eintraege.append({
                        "diktat_id": diktat_id,
                        "kategorie_nr": kategorie_nr,
                        "wort_original": richtig,
                        "wort_schueler": falsch,
                        "kontext": f"… [{richtig}] …",
                        "datum": datum,
                        "notiz": "",
                    })
            db.fehler_mehrere_anlegen(con, schueler_id, eintraege)

    return angelegt


def _schuelertext_bauen(text: str, profil: dict, i: int, anzahl: int,
                        zufall: random.Random) -> str:
    """Baut einen fehlerhaften Schülertext, damit der Diff etwas zu tun hat."""
    ergebnis = text
    for kategorie_nr, (start, entwicklung) in profil["muster"].items():
        faktor = _ENTWICKLUNG[entwicklung](i, anzahl)
        if faktor < 0.3:
            continue
        for richtig, falsch in DEMO_FEHLERWOERTER.get(kategorie_nr, []):
            if richtig in ergebnis and zufall.random() < 0.6 * faktor:
                ergebnis = ergebnis.replace(richtig, falsch, 1)
    return ergebnis


def demodaten_vorhanden(con: sqlite3.Connection) -> bool:
    treffer = con.execute(
        "SELECT COUNT(*) FROM schueler WHERE anzeigename LIKE ?",
        (f"{DEMO_PRAEFIX}%",),
    ).fetchone()[0]
    return treffer > 0


def demodaten_entfernen(con: sqlite3.Connection) -> int:
    """Löscht alle Demoprofile samt zugehöriger Daten."""
    zeilen = con.execute(
        "SELECT id FROM schueler WHERE anzeigename LIKE ?",
        (f"{DEMO_PRAEFIX}%",),
    ).fetchall()
    for zeile in zeilen:
        db.schueler_loeschen(con, zeile["id"])
    return len(zeilen)
