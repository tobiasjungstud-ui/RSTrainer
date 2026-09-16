"""Deterministische OLFA-Engine – Port von ``olfa_engine.js`` (Artefakt).

Umsetzung von «OLFA 3–9+ Technisches Manual» (§2–§4, §9–§11, §17, §19) und
der «Ergänzung» (A.3–A.5, B.2, C.1–C.2). Beide Fassungen müssen dieselben
Goldstandard-Tests bestehen; die Testliste ist hier wie dort dieselbe.

Grundsätze
----------
* Nie über den reinen Buchstabenvergleich klassifizieren – immer über
  Grapheme (``segmentiere``).
* Spezifische Kategorien vor generischen (29–37).
* Fehlt dem Baum ein Merkmal, liefert er ``needs_context`` mit Kandidaten,
  nie die wahrscheinlichste Kategorie.
* Konfidenz wird berechnet, nie geschätzt.
"""

from __future__ import annotations

import math
import re
from typing import Any, Iterable

# ---------------------------------------------------------------- Konstanten

# Längste zuerst. <chs> (Fuchs, sechs) und <ks> (links, Keks) stehen für /ks/
# und müssen als Einheit gelten, sonst zählt «Hekse» für «Hexe» doppelt. <th>,
# <ph>, <rh> sind Fremdgrapheme; <aah>, <eeh>, <ooh>, <ieh> fangen doppelte
# Längenzeichen («Baahn») ab, <ieh> ist zudem echt (sieht, Vieh). <nk> ist
# KEIN Graphem mehr: «Banck» für «Bank» wäre sonst nicht als ck→k lesbar.
MEHRGRAPHEME = ["sch", "chs", "aah", "eeh", "ooh", "ieh",
                "ch", "ck", "tz", "ie", "ah", "eh", "ih", "oh", "uh", "äh", "öh", "üh",
                "aa", "ee", "oo", "ei", "ai", "au", "eu", "äu", "oi", "pf", "qu", "ng", "ss",
                "ph", "th", "rh", "ks"]
VOKALBUCHSTABEN = "aeiouäöüy"
DIPHTHONGE = {"ei", "ai", "au", "eu", "äu", "oi"}
LAENGENMARKER = {"ah": "a", "eh": "e", "ih": "i", "oh": "o", "uh": "u", "äh": "ä", "öh": "ö", "üh": "ü",
                 "aa": "a", "ee": "e", "oo": "o", "ie": "i",
                 "aah": "a", "eeh": "e", "ooh": "o", "ieh": "i"}
#: Doppelt markiert («Baahn»): Grundvokal plus die einfache Markierung, die
#: das Zielwort tatsächlich trägt.
DOPPELMARKER = {"aah", "eeh", "ooh"}
#: Grapheme, die es nur in Fremdwörtern gibt. Ein Fehler genau an ihnen ist
#: ein Fremdwortfehler (37), keine Auslassung oder Ersetzung (Manual §9.4).
FREMDGRAPHEME = {"ph", "th", "rh", "y", "c"}
#: Nach diesen Graphemen lässt sich die Vokallänge nicht aus der Schreibung
#: lesen: sie werden nie verdoppelt (Buch/Bach, Fisch/Dusche).
LAENGE_UNLESBAR_VOR = {"ch", "sch", "chs", "ks", "x", "ß"}
#: Vor diesen Clustern ist der Vokal trotzdem lang – die Ausnahmen der
#: Faustregel «zwei Konsonanten, kurzer Vokal».
CLUSTER_LANG = {"obst", "mond", "trost", "krebs", "magd", "jagd", "vogt", "papst", "propst",
                "stets", "wüste", "husten", "ostern", "schuster", "kloster", "düster"}
VERDOPPELUNG = {"bb": "b", "dd": "d", "ff": "f", "gg": "g", "ll": "l", "mm": "m", "nn": "n", "pp": "p",
                "rr": "r", "ss": "s", "tt": "t", "ck": "k", "tz": "z"}
UMLAUT = {"ä": "a", "ö": "o", "ü": "u"}
STIMMLOS_FUER_STIMMHAFT = {"p": "b", "t": "d", "k": "g"}
STIMMHAFT_FUER_STIMMLOS = {"b": "p", "d": "t", "g": "k"}
PRAEFIXE = ["be", "ge", "ver", "ent", "emp", "er", "zer", "miss", "un", "vor", "an", "ab", "auf",
            "aus", "ein", "mit", "nach", "über", "unter", "um", "zu", "weg", "her", "hin", "los"]
UNSELBSTSTAENDIG = {"be", "ge", "ver", "ent", "emp", "er", "zer", "miss", "un",
                    "im", "mer", "ung", "heit", "keit", "lich", "ig", "chen", "lein", "ten", "te",
                    "en", "es", "st", "t", "e", "n", "s"}
#: Abgetrennte Suffixe: «Freund in» ist 06, obwohl «in» für sich ein Wort ist.
SUFFIXE = {"in", "innen", "ig", "lich", "isch", "sam", "bar", "haft", "los", "voll", "ung",
           "heit", "keit", "schaft", "tum", "chen", "lein", "nis", "ling", "er", "en", "ern"}
#: Endet ein Teil so und ist er kein bekanntes Wort, ist er unselbstständig
#: («sichtig» in «vor sichtig»).
GEBUNDENE_ENDUNGEN = ("ig", "lich", "isch", "sam", "bar", "haft", "ung", "heit", "keit", "schaft")

NEVER_ASSIGN = {"14", "16", "21", "22"}
REDEFINED_FOR_DE_CH = {"13": "s für ss", "15": "ss für s"}

FOERDERBEREICHE = {
    "F1": {"name": "Schärfung / Doppelkonsonant", "olfa": ["07", "08", "11"],
           "foerdern": "Kurzvokal hören, Verdoppelungsregel anwenden, Verlängerungsprobe"},
    "F2": {"name": "Vokallängenmarkierung", "olfa": ["09", "10", "12"],
           "foerdern": "Dehnungs-h, ie, Doppelvokal; Länge hören und markieren"},
    "F3": {"name": "Lexikalische s-Schreibung (CH)", "olfa": ["13", "15"],
           "foerdern": "Merkwortschatz: Fuss, Strasse, gross, heissen, weiss"},
    "F4": {"name": "Umlautableitung", "olfa": ["17", "18", "36"],
           "foerdern": "Ableiten vom Grundwort (Hände ← Hand), ä/e und äu/eu unterscheiden"},
    "F5": {"name": "Auslautverhärtung / Silbenrand", "olfa": ["19", "20", "27", "28"],
           "foerdern": "Verlängerungsprobe (Korb ← Körbe), -ig/-ich"},
    "F6": {"name": "Gross- und Kleinschreibung", "olfa": ["01", "02", "03"],
           "foerdern": "Nomenprobe, Satzanfang, Nominalisierung"},
    "F7": {"name": "Wortgrenzen", "olfa": ["04", "05", "06"],
           "foerdern": "Zusammen-/Getrenntschreibung, Wortbausteine erkennen"},
    "F8": {"name": "Merkwörter v / f / w", "olfa": ["23", "24", "25", "26"],
           "foerdern": "Lexikalischer Zugriff, Wortlisten"},
    "F9": {"name": "Durchgliederung und Sorgfalt", "olfa": ["29", "30", "31", "32", "35"],
           "foerdern": "Wort vollständig abhören, Silben segmentieren, Kontrolllesen"},
    "F10": {"name": "Restfehler / Einzelfälle", "olfa": ["33", "34", "37"],
            "foerdern": "Einzelbetrachtung, keine eigene Fördermassnahme"},
}
AREA_MAP = {nr: f for f, b in FOERDERBEREICHE.items() for nr in b["olfa"]}

KURZNAME = {
    "01": "Klein- für Grossschreibung", "02": "Gross- für Kleinschreibung", "03": "Grossschreibung im Wort",
    "04": "Getrennt- für Zusammenschreibung", "05": "Zusammen- für Getrenntschreibung",
    "06": "Getrenntschreibung unselbstständiger Teile",
    "07": "Einfachschreibung für Konsonantenverdoppelung",
    "08": "Verdoppelung für Einfachschreibung nach Kurzvokal",
    "09": "Einfache Vokalschreibung für markierte Länge",
    "10": "Markierte Länge für Einfachschreibung (Vokal lang)",
    "11": "Verdoppelung nach Langvokal, Konsonant oder am Morphemanfang",
    "12": "Markierte Länge bei kurzem Vokal", "13": "s für ss (de-CH)", "14": "unbesetzt (de-CH)",
    "15": "ss für s (de-CH)", "16": "unbesetzt (de-CH)", "17": "e/eu für ä/äu", "18": "ä/äu für e/eu",
    "19": "p/t/k für b/d/g am Silbenrand", "20": "b/d/g für p/t/k am Silbenrand",
    "21": "unbesetzt", "22": "unbesetzt", "23": "f für v", "24": "v für f", "25": "w für v", "26": "v für w",
    "27": "ch für g im Silbenende", "28": "g für ch im Silbenende",
    "29": "Konsonantenzeichen fehlt", "30": "Konsonantenzeichen zugefügt",
    "31": "Vokalzeichen fehlt", "32": "Vokalzeichen zugefügt", "33": "Falscher Konsonant",
    "34": "Falscher Vokal", "35": "Zeichenumstellung", "36": "Umlautbezeichnung", "37": "Sonstige Fehler",
}

KRITISCHE_PAARE = [
    ("07", "29"), ("08", "11"), ("09", "31"), ("10", "12"), ("17", "34"), ("18", "34"), ("36", "34"),
    ("19", "33"), ("20", "33"), ("23", "33"), ("24", "33"), ("25", "33"), ("26", "33"), ("27", "33"),
    ("28", "33"), ("35", "29"), ("07", "13"), ("08", "15"), ("11", "15"), ("23", "25"),
]

BAENDER = [(0.95, "praktisch eindeutig"), (0.80, "hohe Sicherheit"), (0.65, "plausibel"),
           (0.50, "mehrere Kategorien möglich"), (0.0, "manuelle Kontrolle")]


def band(k: float) -> str:
    return next(text for grenze, text in BAENDER if k >= grenze)


ZIELWORT_SCHWELLE = 0.85

# ----------------------------------------------------------- Vorgabe-Lexikon

VORGABE_LEXIKON: dict[str, dict[str, Any]] = {
    "tal": {"vokale": ["lang"]}, "kalt": {"vokale": ["kurz"]}, "fror": {"vokale": ["lang"]},
    "wind": {"vokale": ["kurz"]}, "bus": {"vokale": ["kurz"]}, "hat": {"vokale": ["kurz"]},
    "als": {"vokale": ["kurz"]}, "fahrrad": {"morpheme": "Fahr|rad", "vokale": ["lang", "kurz"]},
    "bekommen": {"morpheme": "be|kommen", "vokale": ["kurz", "kurz", "kurz"]},
    "scharf": {"vokale": ["kurz"]}, "hände": {"umlaut": True, "vokale": ["kurz", "kurz"]},
    "jetzt": {"umlaut": False, "vokale": ["kurz"]}, "geschäft": {"umlaut": True, "vokale": ["kurz", "kurz"]},
    "bäume": {"umlaut": True}, "leute": {"umlaut": False}, "führte": {"umlaut": True}, "gefährlich": {"umlaut": True},
    "vogel": {"v": "f", "vokale": ["lang", "kurz"]}, "vase": {"v": "v", "vokale": ["lang", "kurz"]},
    "vulkan": {"v": "v"}, "verlieren": {"v": "f", "morpheme": "ver|lieren"},
    "fuss": {"vokale": ["lang"]}, "strasse": {"vokale": ["lang", "kurz"]}, "gross": {"vokale": ["lang"]},
    "heissen": {"vokale": ["lang", "kurz"]}, "preise": {"vokale": ["lang", "kurz"]},
    "häuser": {"vokale": ["lang", "kurz"], "umlaut": True}, "müssen": {"vokale": ["kurz", "kurz"], "umlaut": True},
    "fluss": {"vokale": ["kurz"]}, "weiss": {"vokale": ["lang"]}, "grüsse": {"vokale": ["lang", "kurz"], "umlaut": True},
    "füsse": {"vokale": ["lang", "kurz"], "umlaut": True}, "wüste": {"vokale": ["lang", "kurz"]},
    "husten": {"vokale": ["lang", "kurz"]},
    "wasser": {"vokale": ["kurz", "kurz"]}, "kommen": {"vokale": ["kurz", "kurz"]},
    "zusammen": {"vokale": ["kurz", "kurz", "kurz"]}, "katze": {"vokale": ["kurz", "kurz"]},
    "packen": {"vokale": ["kurz", "kurz"]}, "sofort": {"vokale": ["lang", "kurz"]},
    "garten": {"vokale": ["kurz", "kurz"]}, "gesundheit": {"morpheme": "Gesund|heit", "vokale": ["kurz", "kurz", "lang"]},
    "korb": {"vokale": ["kurz"]}, "bald": {"vokale": ["kurz"]}, "weg": {"vokale": ["lang"]}, "quark": {"vokale": ["kurz"]},
    "platz": {"vokale": ["kurz"]}, "liebe": {"vokale": ["lang", "kurz"]}, "haben": {"vokale": ["lang", "kurz"]},
    "atmen": {"vokale": ["lang", "kurz"]}, "mädchen": {"vokale": ["lang", "kurz"], "umlaut": True},
    "weil": {"vokale": ["lang"]}, "jeweils": {"vokale": ["lang", "lang"]}, "freundlich": {"vokale": ["lang", "kurz"]},
    "lustig": {"vokale": ["kurz", "kurz"]}, "honig": {"vokale": ["lang", "kurz"]}, "teppich": {"vokale": ["kurz", "kurz"]},
    "fröhlich": {"vokale": ["lang", "kurz"], "umlaut": True}, "nicht": {"vokale": ["kurz"]},
    "geburtstag": {"morpheme": "Geburts|tag", "vokale": ["kurz", "kurz", "lang"]},
    "schule": {"vokale": ["lang", "kurz"]}, "zahn": {"vokale": ["lang"]}, "boot": {"vokale": ["lang"]},
    "wiese": {"vokale": ["lang", "kurz"]}, "dann": {"vokale": ["kurz"]}, "dass": {"vokale": ["kurz"]},
    "das": {"vokale": ["kurz"]}, "wahrscheinlich": {"vokale": ["lang", "lang", "kurz"]},
    "haus": {"vokale": ["lang"]}, "häuschen": {"umlaut": True},
    "hund": {"vokale": ["kurz"]}, "kind": {"vokale": ["kurz"]}, "kinder": {"vokale": ["kurz", "kurz"]},
    "sonne": {"vokale": ["kurz", "kurz"]}, "wald": {"vokale": ["kurz"]}, "tisch": {"vokale": ["kurz"]},
    "buch": {"vokale": ["lang"]}, "tag": {"vokale": ["lang"]}, "rad": {"vokale": ["lang"]},
    "glas": {"vokale": ["lang"]}, "gras": {"vokale": ["lang"]}, "los": {"vokale": ["lang"]},
    "gut": {"vokale": ["lang"]}, "mut": {"vokale": ["lang"]}, "rot": {"vokale": ["lang"]},
    "brot": {"vokale": ["lang"]}, "mond": {"vokale": ["lang"]}, "obst": {"vokale": ["lang"]},
    "arzt": {"vokale": ["lang"]}, "zahnarzt": {"morpheme": "Zahn|arzt", "vokale": ["lang", "lang"]},
    "weglaufen": {"morpheme": "weg|laufen"}, "vergraben": {"morpheme": "ver|graben", "v": "f"},
    "immer": {"vokale": ["kurz", "kurz"]}, "vater": {"v": "f", "vokale": ["lang", "kurz"]},
    "viel": {"v": "f", "vokale": ["lang"]}, "von": {"v": "f"}, "vor": {"v": "f"},
    "villa": {"v": "v"}, "vitamin": {"v": "v"}, "video": {"v": "v"}, "vertig": {"v": "f"},
    "für": {"vokale": ["lang"], "umlaut": True}, "fertig": {"vokale": ["kurz", "kurz"]}, "wie": {"vokale": ["lang"]},
    "schwierig": {"vokale": ["lang", "kurz"]},
    "erkältet": {"umlaut": True, "morpheme": "er|kältet", "vokale": ["kurz", "kurz", "kurz"]},
    "stadt": {"vokale": ["kurz"]}, "staat": {"vokale": ["lang"]}, "schiff": {"vokale": ["kurz"]},
    "schrift": {"vokale": ["kurz"]}, "fenster": {"vokale": ["kurz", "kurz"]}, "mutter": {"vokale": ["kurz", "kurz"]},
    "bruder": {"vokale": ["lang", "kurz"]}, "schwester": {"vokale": ["kurz", "kurz"]},
    "klasse": {"vokale": ["kurz", "kurz"]}, "lehrer": {"vokale": ["lang", "kurz"]},
    "lehrerin": {"vokale": ["lang", "kurz", "kurz"]},
    "grün": {"vokale": ["lang"], "umlaut": True}, "schön": {"vokale": ["lang"], "umlaut": True},
    "spät": {"vokale": ["lang"], "umlaut": True}, "käse": {"vokale": ["lang", "kurz"], "umlaut": True},
    "bär": {"vokale": ["lang"], "umlaut": True}, "bären": {"vokale": ["lang", "kurz"], "umlaut": True},
    "äpfel": {"vokale": ["kurz", "kurz"], "umlaut": True}, "bäcker": {"vokale": ["kurz", "kurz"], "umlaut": True},
    "fällt": {"vokale": ["kurz"], "umlaut": True}, "hälfte": {"vokale": ["kurz", "kurz"], "umlaut": True},
    "wände": {"vokale": ["kurz", "kurz"], "umlaut": True}, "gäste": {"vokale": ["kurz", "kurz"], "umlaut": True},
    "zähne": {"vokale": ["lang", "kurz"], "umlaut": True}, "räder": {"vokale": ["lang", "kurz"], "umlaut": True},
    "körbe": {"vokale": ["kurz", "kurz"], "umlaut": True}, "bücher": {"vokale": ["lang", "kurz"], "umlaut": True},
    "stück": {"vokale": ["kurz"], "umlaut": True}, "glück": {"vokale": ["kurz"], "umlaut": True},
    "über": {"vokale": ["lang", "kurz"], "umlaut": True}, "müde": {"vokale": ["lang", "kurz"], "umlaut": True},
    "hören": {"vokale": ["lang", "kurz"], "umlaut": True}, "mögen": {"vokale": ["lang", "kurz"], "umlaut": True},
    "können": {"vokale": ["kurz", "kurz"], "umlaut": True}, "dürfen": {"vokale": ["kurz", "kurz"], "umlaut": True},
    "täglich": {"vokale": ["lang", "kurz"], "umlaut": True}, "plötzlich": {"vokale": ["kurz", "kurz"], "umlaut": True},
    "nächste": {"vokale": ["lang", "kurz"], "umlaut": True}, "während": {"vokale": ["lang", "kurz"], "umlaut": True},
    "erzählen": {"vokale": ["kurz", "lang", "kurz"], "umlaut": True}, "wählen": {"vokale": ["lang", "kurz"], "umlaut": True},
    "zählen": {"vokale": ["lang", "kurz"], "umlaut": True}, "gefällt": {"vokale": ["kurz", "kurz"], "umlaut": True},
    "ende": {"umlaut": False}, "denn": {"umlaut": False}, "wenn": {"umlaut": False}, "gehen": {"umlaut": False},
    "sehen": {"umlaut": False}, "nehmen": {"umlaut": False}, "essen": {"umlaut": False}, "eltern": {"umlaut": False},
    "fest": {"umlaut": False, "vokale": ["kurz"]}, "echt": {"umlaut": False}, "gern": {"umlaut": False},
    "gestern": {"umlaut": False}, "beste": {"umlaut": False}, "letzte": {"umlaut": False}, "freund": {"umlaut": False},
    "heute": {"umlaut": False}, "neu": {"umlaut": False}, "treu": {"umlaut": False}, "feuer": {"umlaut": False},
    "teuer": {"umlaut": False},
}

# Vokallängen, die sich NICHT aus der Schreibung ergeben: ss nach kurzem und
# nach langem Vokal (Kasse/Strasse – in de-CH gleich geschrieben), einfaches
# s nach Langvokal (Hase), r + Konsonant (Karte/Erde), Kurzvokal vor
# einfachem Konsonanten (das, man, Bus), Länge vor ch/sch (Fisch/Buch).
# Ein Wort, das schon oben steht, behält seinen Eintrag.
VOKALLAENGEN: dict[str, dict[str, Any]] = {
    "ab": {"vokale": ['kurz']},
    "adresse": {"vokale": ['kurz', 'kurz', 'kurz']},
    "am": {"vokale": ['kurz']},
    "ameise": {"vokale": ['lang', 'lang', 'kurz']},
    "an": {"vokale": ['kurz']},
    "apotheke": {"vokale": ['kurz', 'lang', 'lang', 'kurz']},
    "arbeit": {"vokale": ['kurz', 'lang']},
    "arm": {"vokale": ['kurz']},
    "art": {"vokale": ['lang']},
    "arzt": {"vokale": ['lang']},
    "atlas": {"vokale": ['kurz', 'kurz']},
    "aussen": {"vokale": ['lang', 'kurz']},
    "ausser": {"vokale": ['lang', 'kurz']},
    "ausserdem": {"vokale": ['lang', 'kurz', 'lang']},
    "axt": {"vokale": ['kurz']},
    "bach": {"vokale": ['kurz']},
    "bad": {"vokale": ['lang']},
    "bahn": {"vokale": ['lang']},
    "bar": {"vokale": ['lang']},
    "barsch": {"vokale": ['kurz']},
    "bart": {"vokale": ['lang']},
    "bass": {"vokale": ['kurz']},
    "beissen": {"vokale": ['lang', 'kurz']},
    "beisst": {"vokale": ['lang']},
    "berg": {"vokale": ['kurz']},
    "berge": {"vokale": ['kurz', 'kurz']},
    "besen": {"vokale": ['lang', 'kurz']},
    "besser": {"vokale": ['kurz', 'kurz']},
    "beten": {"vokale": ['lang', 'kurz']},
    "bibel": {"vokale": ['lang', 'kurz']},
    "biene": {"vokale": ['lang', 'kurz']},
    "bin": {"vokale": ['kurz']},
    "birne": {"vokale": ['kurz', 'kurz']},
    "bis": {"vokale": ['kurz']},
    "biss": {"vokale": ['kurz']},
    "bisschen": {"vokale": ['kurz', 'kurz']},
    "bissen": {"vokale": ['kurz', 'kurz']},
    "blase": {"vokale": ['lang', 'kurz']},
    "bloss": {"vokale": ['lang']},
    "bläser": {"vokale": ['lang', 'kurz']},
    "blässe": {"vokale": ['kurz', 'kurz']},
    "bord": {"vokale": ['kurz']},
    "boss": {"vokale": ['kurz']},
    "brauch": {"vokale": ['lang']},
    "brause": {"vokale": ['lang', 'kurz']},
    "buche": {"vokale": ['lang', 'kurz']},
    "bum": {"vokale": ['kurz']},
    "bus": {"vokale": ['kurz']},
    "busch": {"vokale": ['kurz']},
    "busse": {"vokale": ['lang', 'kurz']},
    "böse": {"vokale": ['lang', 'kurz']},
    "bürste": {"vokale": ['kurz', 'kurz']},
    "büssen": {"vokale": ['lang', 'kurz']},
    "chip": {"vokale": ['kurz']},
    "computer": {"vokale": ['kurz', 'lang', 'kurz']},
    "cup": {"vokale": ['kurz']},
    "dach": {"vokale": ['kurz']},
    "das": {"vokale": ['kurz']},
    "dem": {"vokale": ['kurz']},
    "den": {"vokale": ['kurz']},
    "des": {"vokale": ['kurz']},
    "dich": {"vokale": ['kurz']},
    "doch": {"vokale": ['kurz']},
    "dorf": {"vokale": ['kurz']},
    "dose": {"vokale": ['lang', 'kurz']},
    "draussen": {"vokale": ['lang', 'kurz']},
    "drohen": {"vokale": ['lang', 'kurz']},
    "durst": {"vokale": ['kurz']},
    "dusche": {"vokale": ['lang', 'kurz']},
    "dürfen": {"vokale": ['kurz', 'kurz']},
    "düster": {"vokale": ['lang', 'kurz']},
    "ehe": {"vokale": ['lang', 'kurz']},
    "eis": {"vokale": ['lang']},
    "erbse": {"vokale": ['kurz', 'kurz']},
    "erde": {"vokale": ['lang', 'kurz']},
    "ernte": {"vokale": ['kurz', 'kurz']},
    "erz": {"vokale": ['lang']},
    "es": {"vokale": ['kurz']},
    "essen": {"vokale": ['kurz', 'kurz']},
    "fabrik": {"vokale": ['kurz', 'lang']},
    "fach": {"vokale": ['kurz']},
    "fahrt": {"vokale": ['lang']},
    "farbe": {"vokale": ['kurz', 'kurz']},
    "fase": {"vokale": ['lang', 'kurz']},
    "fass": {"vokale": ['kurz']},
    "fassade": {"vokale": ['kurz', 'lang', 'kurz']},
    "fassen": {"vokale": ['kurz', 'kurz']},
    "fasst": {"vokale": ['kurz']},
    "ferien": {"vokale": ['lang', 'lang']},
    "fessel": {"vokale": ['kurz', 'kurz']},
    "fisch": {"vokale": ['kurz']},
    "fit": {"vokale": ['kurz']},
    "flasche": {"vokale": ['kurz', 'kurz']},
    "fleiss": {"vokale": ['lang']},
    "fleissig": {"vokale": ['lang', 'kurz']},
    "fliege": {"vokale": ['lang', 'kurz']},
    "fliessen": {"vokale": ['lang', 'kurz']},
    "floss": {"vokale": ['lang']},
    "fluss": {"vokale": ['kurz']},
    "flüsse": {"vokale": ['kurz', 'kurz']},
    "form": {"vokale": ['kurz']},
    "frosch": {"vokale": ['kurz']},
    "fuchs": {"vokale": ['kurz']},
    "fuss": {"vokale": ['lang']},
    "fussball": {"vokale": ['lang', 'kurz']},
    "fässer": {"vokale": ['kurz', 'kurz']},
    "füsse": {"vokale": ['lang', 'kurz']},
    "gag": {"vokale": ['kurz']},
    "garten": {"vokale": ['kurz', 'kurz']},
    "gas": {"vokale": ['lang']},
    "gasse": {"vokale": ['kurz', 'kurz']},
    "gefäss": {"vokale": ['kurz', 'lang']},
    "gegossen": {"vokale": ['kurz', 'kurz', 'kurz']},
    "gehen": {"vokale": ['lang', 'kurz']},
    "geiss": {"vokale": ['lang']},
    "geist": {"vokale": ['lang']},
    "gemüse": {"vokale": ['kurz', 'lang', 'kurz']},
    "geniessen": {"vokale": ['kurz', 'lang', 'kurz']},
    "genuss": {"vokale": ['kurz', 'kurz']},
    "genüsse": {"vokale": ['kurz', 'kurz', 'kurz']},
    "gerste": {"vokale": ['kurz', 'kurz']},
    "geschlossen": {"vokale": ['kurz', 'kurz', 'kurz']},
    "geste": {"vokale": ['lang', 'kurz']},
    "gewiss": {"vokale": ['kurz', 'kurz']},
    "gewusst": {"vokale": ['kurz', 'kurz']},
    "giessen": {"vokale": ['lang', 'kurz']},
    "giesst": {"vokale": ['lang']},
    "glas": {"vokale": ['lang']},
    "gläser": {"vokale": ['lang', 'kurz']},
    "gras": {"vokale": ['lang']},
    "gross": {"vokale": ['lang']},
    "gruss": {"vokale": ['lang']},
    "grösse": {"vokale": ['lang', 'kurz']},
    "grösser": {"vokale": ['lang', 'kurz']},
    "grüsse": {"vokale": ['lang', 'kurz']},
    "grüssen": {"vokale": ['lang', 'kurz']},
    "grüsst": {"vokale": ['lang']},
    "guss": {"vokale": ['kurz']},
    "gut": {"vokale": ['lang']},
    "haken": {"vokale": ['lang', 'kurz']},
    "hart": {"vokale": ['kurz']},
    "harz": {"vokale": ['lang']},
    "hase": {"vokale": ['lang', 'kurz']},
    "hass": {"vokale": ['kurz']},
    "hassen": {"vokale": ['kurz', 'kurz']},
    "hat": {"vokale": ['kurz']},
    "haus": {"vokale": ['lang']},
    "heiss": {"vokale": ['lang']},
    "heissen": {"vokale": ['lang', 'kurz']},
    "heisst": {"vokale": ['lang']},
    "herbst": {"vokale": ['kurz']},
    "herd": {"vokale": ['lang']},
    "herde": {"vokale": ['lang', 'kurz']},
    "herr": {"vokale": ['kurz']},
    "herz": {"vokale": ['kurz']},
    "hexe": {"vokale": ['kurz', 'kurz']},
    "hin": {"vokale": ['kurz']},
    "hoch": {"vokale": ['lang']},
    "hof": {"vokale": ['lang']},
    "hose": {"vokale": ['lang', 'kurz']},
    "hotel": {"vokale": ['kurz', 'lang']},
    "husten": {"vokale": ['lang', 'kurz']},
    "hässlich": {"vokale": ['kurz', 'kurz']},
    "häuser": {"vokale": ['lang', 'kurz']},
    "hören": {"vokale": ['lang', 'kurz']},
    "hüte": {"vokale": ['lang', 'kurz']},
    "im": {"vokale": ['kurz']},
    "in": {"vokale": ['kurz']},
    "interesse": {"vokale": ['kurz', 'kurz', 'kurz', 'kurz']},
    "iris": {"vokale": ['lang', 'kurz']},
    "isst": {"vokale": ['kurz']},
    "jagd": {"vokale": ['lang']},
    "job": {"vokale": ['kurz']},
    "kam": {"vokale": ['lang']},
    "kamel": {"vokale": ['kurz', 'lang']},
    "kanal": {"vokale": ['kurz', 'lang']},
    "kap": {"vokale": ['kurz']},
    "karotte": {"vokale": ['kurz', 'kurz', 'kurz']},
    "karte": {"vokale": ['kurz', 'kurz']},
    "kasse": {"vokale": ['kurz', 'kurz']},
    "kassette": {"vokale": ['kurz', 'kurz', 'kurz']},
    "kerze": {"vokale": ['kurz', 'kurz']},
    "kessel": {"vokale": ['kurz', 'kurz']},
    "kino": {"vokale": ['lang', 'kurz']},
    "kirche": {"vokale": ['kurz', 'kurz']},
    "kirsche": {"vokale": ['kurz', 'kurz']},
    "kissen": {"vokale": ['kurz', 'kurz']},
    "klasse": {"vokale": ['kurz', 'kurz']},
    "kloster": {"vokale": ['lang', 'kurz']},
    "klub": {"vokale": ['kurz']},
    "koch": {"vokale": ['kurz']},
    "kohl": {"vokale": ['lang']},
    "kompass": {"vokale": ['kurz', 'kurz']},
    "kosmos": {"vokale": ['kurz', 'kurz']},
    "kran": {"vokale": ['lang']},
    "krebs": {"vokale": ['lang']},
    "kreis": {"vokale": ['lang']},
    "kuchen": {"vokale": ['lang', 'kurz']},
    "kurve": {"vokale": ['kurz', 'kurz']},
    "kuss": {"vokale": ['kurz']},
    "käse": {"vokale": ['lang', 'kurz']},
    "körper": {"vokale": ['kurz', 'kurz']},
    "küche": {"vokale": ['kurz', 'kurz']},
    "kühe": {"vokale": ['lang', 'kurz']},
    "kürbis": {"vokale": ['kurz', 'kurz']},
    "küsse": {"vokale": ['kurz', 'kurz']},
    "lachen": {"vokale": ['kurz', 'kurz']},
    "lassen": {"vokale": ['kurz', 'kurz']},
    "laus": {"vokale": ['lang']},
    "leise": {"vokale": ['lang', 'kurz']},
    "lesen": {"vokale": ['lang', 'kurz']},
    "liebe": {"vokale": ['lang', 'kurz']},
    "lob": {"vokale": ['lang']},
    "loch": {"vokale": ['kurz']},
    "los": {"vokale": ['lang']},
    "lose": {"vokale": ['lang', 'kurz']},
    "lässig": {"vokale": ['kurz', 'kurz']},
    "lässt": {"vokale": ['kurz']},
    "löser": {"vokale": ['lang', 'kurz']},
    "machen": {"vokale": ['kurz', 'kurz']},
    "magd": {"vokale": ['lang']},
    "man": {"vokale": ['kurz']},
    "marke": {"vokale": ['kurz', 'kurz']},
    "markt": {"vokale": ['kurz']},
    "marsch": {"vokale": ['kurz']},
    "maschine": {"vokale": ['kurz', 'lang', 'kurz']},
    "mass": {"vokale": ['lang']},
    "masse": {"vokale": ['lang', 'kurz']},
    "massig": {"vokale": ['lang', 'kurz']},
    "massstab": {"vokale": ['lang', 'lang']},
    "maus": {"vokale": ['lang']},
    "mehl": {"vokale": ['lang']},
    "mensch": {"vokale": ['kurz']},
    "messen": {"vokale": ['kurz', 'kurz']},
    "messer": {"vokale": ['kurz', 'kurz']},
    "mich": {"vokale": ['kurz']},
    "missgunst": {"vokale": ['kurz', 'kurz']},
    "misst": {"vokale": ['kurz']},
    "missverständnis": {"vokale": ['kurz', 'kurz', 'kurz', 'kurz']},
    "mit": {"vokale": ['kurz']},
    "mob": {"vokale": ['kurz']},
    "mond": {"vokale": ['lang']},
    "moos": {"vokale": ['lang']},
    "mord": {"vokale": ['kurz']},
    "morgen": {"vokale": ['kurz', 'kurz']},
    "motor": {"vokale": ['lang', 'kurz']},
    "mus": {"vokale": ['lang']},
    "museum": {"vokale": ['kurz', 'lang']},
    "musik": {"vokale": ['kurz', 'lang']},
    "musiker": {"vokale": ['lang', 'kurz', 'kurz']},
    "muss": {"vokale": ['kurz']},
    "musse": {"vokale": ['lang', 'kurz']},
    "mut": {"vokale": ['lang']},
    "mäuse": {"vokale": ['lang', 'kurz']},
    "mühe": {"vokale": ['lang', 'kurz']},
    "müssen": {"vokale": ['kurz', 'kurz']},
    "nach": {"vokale": ['lang']},
    "name": {"vokale": ['lang', 'kurz']},
    "nase": {"vokale": ['lang', 'kurz']},
    "nass": {"vokale": ['kurz']},
    "nation": {"vokale": ['kurz', 'lang', 'lang']},
    "noch": {"vokale": ['kurz']},
    "nord": {"vokale": ['kurz']},
    "not": {"vokale": ['lang']},
    "nuss": {"vokale": ['kurz']},
    "nämlich": {"vokale": ['lang', 'kurz']},
    "nässe": {"vokale": ['kurz', 'kurz']},
    "nüsse": {"vokale": ['kurz', 'kurz']},
    "nüstern": {"vokale": ['lang', 'kurz']},
    "oase": {"vokale": ['kurz', 'lang', 'kurz']},
    "ob": {"vokale": ['kurz']},
    "obst": {"vokale": ['lang']},
    "ort": {"vokale": ['kurz']},
    "ossi": {"vokale": ['kurz', 'kurz']},
    "osten": {"vokale": ['kurz', 'kurz']},
    "ostern": {"vokale": ['lang', 'kurz']},
    "papier": {"vokale": ['kurz', 'lang']},
    "papst": {"vokale": ['lang']},
    "park": {"vokale": ['kurz']},
    "pass": {"vokale": ['kurz']},
    "passen": {"vokale": ['kurz', 'kurz']},
    "passt": {"vokale": ['kurz']},
    "pause": {"vokale": ['lang', 'kurz']},
    "pesen": {"vokale": ['lang', 'kurz']},
    "pferd": {"vokale": ['lang']},
    "physik": {"vokale": ['kurz', 'lang']},
    "plan": {"vokale": ['lang']},
    "politik": {"vokale": ['kurz', 'kurz', 'lang']},
    "pop": {"vokale": ['kurz']},
    "prassen": {"vokale": ['kurz', 'kurz']},
    "preis": {"vokale": ['lang']},
    "preise": {"vokale": ['lang', 'kurz']},
    "presse": {"vokale": ['kurz', 'kurz']},
    "propst": {"vokale": ['lang']},
    "prozess": {"vokale": ['kurz', 'kurz']},
    "quarz": {"vokale": ['lang']},
    "rache": {"vokale": ['lang', 'kurz']},
    "rad": {"vokale": ['lang']},
    "rasen": {"vokale": ['lang', 'kurz']},
    "rasse": {"vokale": ['kurz', 'kurz']},
    "rassel": {"vokale": ['kurz', 'kurz']},
    "reihe": {"vokale": ['lang', 'kurz']},
    "reis": {"vokale": ['lang']},
    "reise": {"vokale": ['lang', 'kurz']},
    "reissen": {"vokale": ['lang', 'kurz']},
    "reisst": {"vokale": ['lang']},
    "rennrad": {"vokale": ['kurz', 'lang']},
    "republik": {"vokale": ['kurz', 'kurz', 'lang']},
    "rhythmus": {"vokale": ['kurz', 'kurz']},
    "riese": {"vokale": ['lang', 'kurz']},
    "riss": {"vokale": ['kurz']},
    "roboter": {"vokale": ['lang', 'kurz', 'kurz']},
    "rose": {"vokale": ['lang', 'kurz']},
    "ross": {"vokale": ['kurz']},
    "rosse": {"vokale": ['kurz', 'kurz']},
    "rot": {"vokale": ['lang']},
    "ruhe": {"vokale": ['lang', 'kurz']},
    "russ": {"vokale": ['kurz']},
    "russe": {"vokale": ['kurz', 'kurz']},
    "rösten": {"vokale": ['lang', 'kurz']},
    "sache": {"vokale": ['kurz', 'kurz']},
    "salat": {"vokale": ['kurz', 'lang']},
    "schiessen": {"vokale": ['lang', 'kurz']},
    "schliessen": {"vokale": ['lang', 'kurz']},
    "schliesst": {"vokale": ['lang']},
    "schloss": {"vokale": ['kurz']},
    "schlösser": {"vokale": ['kurz', 'kurz']},
    "schlüssel": {"vokale": ['kurz', 'kurz']},
    "schoss": {"vokale": ['lang']},
    "schuhe": {"vokale": ['lang', 'kurz']},
    "schule": {"vokale": ['lang', 'kurz']},
    "schuss": {"vokale": ['kurz']},
    "schuster": {"vokale": ['lang', 'kurz']},
    "schweiss": {"vokale": ['lang']},
    "schwert": {"vokale": ['lang']},
    "schüsse": {"vokale": ['kurz', 'kurz']},
    "schüssel": {"vokale": ['kurz', 'kurz']},
    "sehen": {"vokale": ['lang', 'kurz']},
    "sessel": {"vokale": ['kurz', 'kurz']},
    "sich": {"vokale": ['kurz']},
    "sorge": {"vokale": ['kurz', 'kurz']},
    "spass": {"vokale": ['lang']},
    "spassmacher": {"vokale": ['lang', 'kurz', 'kurz']},
    "spiess": {"vokale": ['lang']},
    "sprache": {"vokale": ['lang', 'kurz']},
    "spässe": {"vokale": ['lang', 'kurz']},
    "star": {"vokale": ['lang']},
    "stark": {"vokale": ['kurz']},
    "stets": {"vokale": ['lang']},
    "stoss": {"vokale": ['lang']},
    "stossen": {"vokale": ['lang', 'kurz']},
    "strasse": {"vokale": ['lang', 'kurz']},
    "strassen": {"vokale": ['lang', 'kurz']},
    "strauss": {"vokale": ['lang']},
    "sträusse": {"vokale": ['lang', 'kurz']},
    "stuhl": {"vokale": ['lang']},
    "sturm": {"vokale": ['kurz']},
    "stösst": {"vokale": ['lang']},
    "suchen": {"vokale": ['lang', 'kurz']},
    "system": {"vokale": ['kurz', 'lang']},
    "süss": {"vokale": ['lang']},
    "süsse": {"vokale": ['lang', 'kurz']},
    "tag": {"vokale": ['lang']},
    "tal": {"vokale": ['lang']},
    "tasche": {"vokale": ['kurz', 'kurz']},
    "tasse": {"vokale": ['kurz', 'kurz']},
    "tennis": {"vokale": ['kurz', 'kurz']},
    "text": {"vokale": ['kurz']},
    "theater": {"vokale": ['lang', 'lang', 'kurz']},
    "thema": {"vokale": ['lang', 'kurz']},
    "tiger": {"vokale": ['lang', 'kurz']},
    "tip": {"vokale": ['kurz']},
    "tomate": {"vokale": ['kurz', 'lang', 'kurz']},
    "ton": {"vokale": ['lang']},
    "top": {"vokale": ['kurz']},
    "tor": {"vokale": ['lang']},
    "trost": {"vokale": ['lang']},
    "tuch": {"vokale": ['lang']},
    "tur": {"vokale": ['lang']},
    "turm": {"vokale": ['kurz']},
    "typ": {"vokale": ['lang']},
    "tür": {"vokale": ['lang']},
    "türen": {"vokale": ['lang', 'kurz']},
    "um": {"vokale": ['kurz']},
    "vase": {"vokale": ['lang', 'kurz']},
    "vergessen": {"vokale": ['kurz', 'kurz', 'kurz']},
    "vogt": {"vokale": ['lang']},
    "vom": {"vokale": ['kurz']},
    "von": {"vokale": ['kurz']},
    "wach": {"vokale": ['kurz']},
    "wal": {"vokale": ['lang']},
    "warm": {"vokale": ['kurz']},
    "was": {"vokale": ['kurz']},
    "waschen": {"vokale": ['kurz', 'kurz']},
    "wasser": {"vokale": ['kurz', 'kurz']},
    "weg": {"vokale": ['lang']},
    "weiss": {"vokale": ['lang']},
    "weisst": {"vokale": ['lang']},
    "werden": {"vokale": ['lang', 'kurz']},
    "werk": {"vokale": ['kurz']},
    "wert": {"vokale": ['lang']},
    "wesen": {"vokale": ['lang', 'kurz']},
    "westen": {"vokale": ['kurz', 'kurz']},
    "wider": {"vokale": ['lang', 'kurz']},
    "wiese": {"vokale": ['lang', 'kurz']},
    "wissen": {"vokale": ['kurz', 'kurz']},
    "wort": {"vokale": ['kurz']},
    "wunsch": {"vokale": ['kurz']},
    "wurm": {"vokale": ['kurz']},
    "wurst": {"vokale": ['kurz']},
    "wurzel": {"vokale": ['kurz', 'kurz']},
    "wusste": {"vokale": ['kurz', 'kurz']},
    "wässrig": {"vokale": ['kurz', 'kurz']},
    "wörter": {"vokale": ['kurz', 'kurz']},
    "wüste": {"vokale": ['lang', 'kurz']},
    "zahl": {"vokale": ['lang']},
    "zart": {"vokale": ['lang']},
    "zebra": {"vokale": ['lang', 'kurz']},
    "ziege": {"vokale": ['lang', 'kurz']},
    "zug": {"vokale": ['lang']},
    "zum": {"vokale": ['kurz']},
    "zur": {"vokale": ['kurz']},
    "zwerg": {"vokale": ['kurz']},
    "äussern": {"vokale": ['lang', 'kurz']},
    "äusserst": {"vokale": ['lang', 'kurz']},
}
for _w, _e in VOKALLAENGEN.items():
    if _w not in VORGABE_LEXIKON:
        VORGABE_LEXIKON[_w] = dict(_e)
    elif "vokale" not in VORGABE_LEXIKON[_w]:
        VORGABE_LEXIKON[_w]["vokale"] = _e["vokale"]
for _eintrag in VORGABE_LEXIKON.values():
    _eintrag["quelle"] = "vorgabe"


# ---------------------------------------------------- Graphemsegmentierung

def ist_vokal_graphem(g: str | None) -> bool:
    return bool(g) and (g[0] in VOKALBUCHSTABEN or g in DIPHTHONGE or g in LAENGENMARKER)


def ist_konsonant_graphem(g: str | None) -> bool:
    return bool(g) and not ist_vokal_graphem(g)


def segmentiere(wort: str) -> list[dict[str, Any]]:
    """Gieriger Längstmatch, danach gleiche Nachbarkonsonanten verschmelzen."""
    w = str(wort or "").lower()
    aus: list[dict[str, Any]] = []
    i = 0
    while i < len(w):
        treffer = next((g for g in MEHRGRAPHEME if w.startswith(g, i)), None) or w[i]
        aus.append({"g": treffer, "at": i})
        i += len(treffer)
    verschmolzen: list[dict[str, Any]] = []
    for e in aus:
        letzt = verschmolzen[-1] if verschmolzen else None
        # Auch <zz>, <kk> werden verschmolzen: «Kazze» ist EINE (falsch
        # gewählte) Verdoppelung, nicht ein z zu viel plus ein z für tz.
        if (letzt and len(letzt["g"]) == 1 and letzt["g"] == e["g"]
                and ist_konsonant_graphem(e["g"]) and e["g"].isalpha()):
            letzt["g"] = letzt["g"] + e["g"]
        else:
            verschmolzen.append({"g": e["g"], "at": e["at"]})
    return verschmolzen


def grapheme(wort: str) -> list[str]:
    return [x["g"] for x in segmentiere(wort)]


# ----------------------------------------- Damerau-Levenshtein-Alignment

def _verwandt(a: str, b: str) -> bool:
    """Grapheme, die dieselbe Stelle im Wort besetzen können: eine Verdoppelung
    und ihr Grundzeichen, zwei Längenmarkierungen desselben Vokals, ein
    Umlautpaar. Sie werden im Alignment bevorzugt einander zugeordnet – so
    wird «komn»/«kommen» zu m→mm plus fehlendem e, nicht zu mm fehlt plus
    m→e."""
    if VERDOPPELUNG.get(a) == b or VERDOPPELUNG.get(b) == a:
        return True
    if LAENGENMARKER.get(a, a) == LAENGENMARKER.get(b, b):
        return True
    if UMLAUT.get(a) == b or UMLAUT.get(b) == a:
        return True
    return False


def _kosten(a: str, b: str) -> float:
    if a == b:
        return 0.0
    if _verwandt(a, b):
        return 0.9
    if ist_vokal_graphem(a) != ist_vokal_graphem(b):
        return 1.1
    return 1.0


def align(s: list[str], t: list[str]) -> tuple[list[dict[str, Any]], int]:
    n, m = len(s), len(t)
    D = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        D[i][0] = float(i)
    for j in range(m + 1):
        D[0][j] = float(j)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            kosten = _kosten(s[i - 1], t[j - 1])
            D[i][j] = min(D[i - 1][j] + 1, D[i][j - 1] + 1, D[i - 1][j - 1] + kosten)
            if i > 1 and j > 1 and s[i - 1] == t[j - 2] and s[i - 2] == t[j - 1] and s[i - 1] != s[i - 2]:
                D[i][j] = min(D[i][j], D[i - 2][j - 2] + 1)
    ops: list[dict[str, Any]] = []
    i, j = n, m
    while i > 0 or j > 0:
        if (i > 1 and j > 1 and s[i - 1] == t[j - 2] and s[i - 2] == t[j - 1] and s[i - 1] != s[i - 2]
                and D[i][j] == D[i - 2][j - 2] + 1):
            ops.append({"op": "trans", "si": i - 2, "ti": j - 2, "s": [s[i - 2], s[i - 1]], "t": [t[j - 2], t[j - 1]]})
            i -= 2; j -= 2
        elif i > 0 and j > 0 and s[i - 1] == t[j - 1] and abs(D[i][j] - D[i - 1][j - 1]) < 1e-9:
            ops.append({"op": "equal", "si": i - 1, "ti": j - 1, "s": s[i - 1], "t": t[j - 1]}); i -= 1; j -= 1
        elif i > 0 and j > 0 and abs(D[i][j] - (D[i - 1][j - 1] + _kosten(s[i - 1], t[j - 1]))) < 1e-9:
            ops.append({"op": "sub", "si": i - 1, "ti": j - 1, "s": s[i - 1], "t": t[j - 1]}); i -= 1; j -= 1
        elif i > 0 and abs(D[i][j] - (D[i - 1][j] + 1)) < 1e-9:
            ops.append({"op": "ins", "si": i - 1, "ti": j, "s": s[i - 1], "t": None}); i -= 1
        else:
            ops.append({"op": "del", "si": i, "ti": j - 1, "s": None, "t": t[j - 1]}); j -= 1
    ops.reverse()
    # Die Distanz zählt Operationen, nicht Kostenbruchteile.
    return ops, sum(1 for o in ops if o["op"] != "equal")


# ------------------------------------------------------ Strukturmerkmale

def _quelle(lex: dict | None) -> str:
    if not lex:
        return "lexikon"
    return "ki" if lex.get("quelle") == "ki" else (lex.get("quelle") or "lexikon")


def vokallaenge(t_seg: list[dict], idx: int, lex: dict | None) -> dict[str, Any]:
    g = t_seg[idx]["g"] if 0 <= idx < len(t_seg) else None
    if not g or not ist_vokal_graphem(g):
        return {"wert": None, "quelle": "unbekannt"}
    if g in LAENGENMARKER:
        return {"wert": "lang", "quelle": "schreibung", "grund": f"<{g}> ist markiert lang"}
    if g in DIPHTHONGE:
        return {"wert": "lang", "quelle": "schreibung", "grund": f"<{g}> ist ein Diphthong"}
    folgend = t_seg[idx + 1]["g"] if idx + 1 < len(t_seg) else None
    # Eine Verdoppelung belegt den Kurzvokal – ausser <ss>: In de-CH steht ss
    # auch nach Langvokal (Fuss, Strasse), Ergänzung A.2.
    if folgend and folgend in VERDOPPELUNG and len(folgend) == 2 and folgend != "ss":
        return {"wert": "kurz", "quelle": "schreibung", "grund": f"vor <{folgend}> (Schärfung) ist der Vokal kurz"}
    if lex and isinstance(lex.get("vokale"), list):
        vokal_index = sum(1 for x in t_seg[:idx] if ist_vokal_graphem(x["g"]))
        if vokal_index < len(lex["vokale"]) and lex["vokale"][vokal_index] in ("kurz", "lang"):
            w = lex["vokale"][vokal_index]
            return {"wert": w, "quelle": _quelle(lex), "grund": f"Lexikon: Vokal {vokal_index + 1} ist {w}"}
    return _laenge_heuristisch(t_seg, idx)


def _laenge_heuristisch(t_seg: list[dict], idx: int) -> dict[str, Any]:
    """Zwei Faustregeln der deutschen Orthografie, als Heuristik gekennzeichnet
    (Konfidenz 0.86 statt 0.97, und die Grenzfallprüfung darf nachfragen):

    1. Vor <ng> und vor zwei verschiedenen Konsonanten ist der Vokal kurz
       (Hand, Wald, Licht, fast). Ausnahmen stehen in CLUSTER_LANG; nach
       r + Konsonant gilt die Regel nicht (Karte kurz, Erde lang), dort
       entscheidet allein das Lexikon.
    2. Vor einem einzelnen Konsonanten, dem ein Vokal folgt oder der das Wort
       beendet, ist der Vokal lang (Name, Tal, Tiger) – sonst stünde eine
       Verdoppelung. Kurze Ausnahmen (das, man, Bus) stehen im Lexikon, das
       vorher greift. Nach <ch>, <sch>, <x> gilt die Regel nicht, sie werden
       nie verdoppelt.
    """
    wort = "".join(x["g"] for x in t_seg)
    folgend = [x["g"] for x in t_seg[idx + 1:idx + 3]]
    if not folgend:
        return {"wert": None, "quelle": "unbekannt", "grund": "Vokal am Wortende ohne Markierung"}
    g1 = folgend[0]
    if g1 in LAENGE_UNLESBAR_VOR:
        return {"wert": None, "quelle": "unbekannt", "grund": f"vor <{g1}> ist die Vokallänge nicht ablesbar"}
    if ist_vokal_graphem(g1):
        return {"wert": None, "quelle": "unbekannt", "grund": "Vokal vor Vokal – Länge nicht ablesbar"}
    if g1 == "ng":
        return {"wert": "kurz", "quelle": "heuristik", "grund": "vor <ng> ist der Vokal kurz"}
    g2 = folgend[1] if len(folgend) > 1 else None
    if g2 and ist_konsonant_graphem(g2) and g2 != g1:
        if g1 == "r":
            return {"wert": None, "quelle": "unbekannt", "grund": "vor r + Konsonant ist die Länge nicht ablesbar (Karte/Erde)"}
        if wort in CLUSTER_LANG:
            return {"wert": "lang", "quelle": "heuristik", "grund": f"«{wort}» ist eine bekannte Dehnung vor Konsonantenhäufung"}
        return {"wert": "kurz", "quelle": "heuristik",
                "grund": f"vor der Konsonantenhäufung <{g1}{g2}> ist der Vokal in der Regel kurz"}
    if len(g1) == 1 and g1.isalpha() and (g2 is None or ist_vokal_graphem(g2)):
        return {"wert": "lang", "quelle": "heuristik",
                "grund": f"vor einfachem <{g1}> {'am Wortende' if g2 is None else 'mit folgendem Vokal'} ist der Vokal in der Regel lang (sonst stünde eine Verdoppelung)"}
    return {"wert": None, "quelle": "unbekannt", "grund": "Vokallänge weder markiert noch im Lexikon"}


def morphemgrenze(ziel: str, at: int, lex: dict | None) -> dict[str, Any]:
    if lex and lex.get("morpheme"):
        grenzen, pos = set(), 0
        for ch in lex["morpheme"]:
            if ch == "|":
                grenzen.add(pos)
            else:
                pos += 1
        return {"wert": at in grenzen, "quelle": _quelle(lex)}
    kopf = ziel[:at].lower()
    if kopf in PRAEFIXE and len(ziel) - at >= 3:
        return {"wert": True, "quelle": "heuristik", "grund": f"«{kopf}-» ist ein Präfix"}
    return {"wert": None, "quelle": "unbekannt"}


def v_lautwert(lex: dict | None) -> dict[str, Any]:
    if lex and lex.get("v") in ("f", "v"):
        return {"wert": lex["v"], "quelle": _quelle(lex)}
    return {"wert": None, "quelle": "unbekannt"}


def umlaut_merkmal(lex: dict | None) -> dict[str, Any]:
    if lex and isinstance(lex.get("umlaut"), bool):
        return {"wert": lex["umlaut"], "quelle": _quelle(lex)}
    return {"wert": None, "quelle": "unbekannt"}


def am_silbenrand(t_seg: list[dict], idx: int) -> bool:
    folgend = t_seg[idx + 1]["g"] if idx + 1 < len(t_seg) else None
    return not folgend or ist_konsonant_graphem(folgend)


# ------------------------------------------------------ Entscheidungsbaum

def ereignis(**basis: Any) -> dict[str, Any]:
    e: dict[str, Any] = {"kategorie": None, "kandidaten": [], "reason": "", "excluded": [],
                         "featureSource": "schreibung", "status": "resolved", "definition": "de-DE",
                         "entscheidend": None, "studentGrapheme": "", "targetGrapheme": ""}
    e.update(basis)
    return e


def _excl(e: dict, category: str, reason: str) -> None:
    e["excluded"].append({"category": category, "reason": reason})


def verdoppelung_fehlt(op: dict, t_seg: list[dict], ziel: str, lex: dict | None) -> dict:
    doppel, einfach = op["t"], VERDOPPELUNG[op["t"]]
    vorher = t_seg[op["ti"] - 1] if op["ti"] > 0 else None
    e = ereignis(studentGrapheme=op["s"], targetGrapheme=doppel)
    if vorher and ist_konsonant_graphem(vorher["g"]):
        e["kategorie"] = "29"
        e["reason"] = f"<{einfach}> statt <{doppel}>; vor der Stelle steht ein Konsonant, also keine Schärfung – ein Konsonantenzeichen fehlt."
        _excl(e, "07", "Schärfung setzt einen Kurzvokal unmittelbar davor voraus.")
        return e
    laenge = vokallaenge(t_seg, op["ti"] - 1, lex) if vorher else {"wert": None, "quelle": "unbekannt"}
    grenze = morphemgrenze(ziel, t_seg[op["ti"]]["at"] + 1, lex)
    e["featureSource"] = laenge["quelle"]
    e["entscheidend"] = "Vokallänge vor der Stelle" + (" (s ↔ ss)" if doppel == "ss" else "")
    if grenze["wert"] is True:
        e["kategorie"] = "29"; e["featureSource"] = grenze["quelle"]
        e["reason"] = (f"<{einfach}> statt <{doppel}>: An dieser Stelle liegt eine Morphemgrenze "
                       f"({(lex or {}).get('morpheme') or 'Präfix'}) – zwei gleiche Konsonanten treffen aufeinander, "
                       "das ist keine orthografische Verdoppelung.")
        _excl(e, "07", "Keine Schärfung, sondern Morphemfuge (Manual §6.1).")
        return e
    if laenge["wert"] == "kurz":
        e["kategorie"] = "07"
        e["reason"] = (f"<{einfach}> steht für das Zielgraphem <{doppel}>; der Vokal davor ist kurz "
                       f"({laenge.get('grund')}) – die orthografische Verdoppelung wurde nicht realisiert.")
        _excl(e, "29", "Es fehlt kein eigenständiges Konsonantengraphem, nur die Verdoppelung.")
        if doppel == "ss":
            _excl(e, "13", "13-CH setzt einen langen Vokal oder Diphthong davor voraus.")
        return e
    if laenge["wert"] == "lang":
        if doppel == "ss":
            e["kategorie"] = "13"; e["definition"] = "de-CH"
            e["reason"] = f"<s> statt <ss> nach langem Vokal/Diphthong ({laenge.get('grund')}) – lexikalische ss-Schreibung (Ergänzung A.4)."
            _excl(e, "07", "Schärfung setzt einen Kurzvokal voraus; hier ist der Vokal lang.")
            return e
        e["kategorie"] = "29"
        e["reason"] = (f"<{einfach}> statt <{doppel}> nach langem Vokal ({laenge.get('grund')}) – keine Schärfung möglich, "
                       "die Verdoppelung entsteht durch eine Morphemgrenze.")
        _excl(e, "07", "Nach Langvokal gibt es keine orthografische Verdoppelung.")
        return e
    e["status"] = "needs_context"; e["featureSource"] = "unbekannt"
    e["kandidaten"] = ["07", "13"] if doppel == "ss" else ["07", "29"]
    e["reason"] = (f"<{einfach}> statt <{doppel}>. Ob der Vokal davor kurz (→ 07) oder lang "
                   f"(→ {'13-CH' if doppel == 'ss' else '29, Morphemfuge'}) ist, steht nicht im Lexikon.")
    return e


def verdoppelung_zuviel(op: dict, t_seg: list[dict], ziel: str, lex: dict | None) -> dict:
    doppel, einfach = op["s"], VERDOPPELUNG[op["s"]]
    vorher = t_seg[op["ti"] - 1] if op["ti"] > 0 else None
    e = ereignis(studentGrapheme=doppel, targetGrapheme=op["t"])
    grenze = morphemgrenze(ziel, t_seg[op["ti"]]["at"], lex)
    if grenze["wert"] is True:
        e["kategorie"] = "11"; e["featureSource"] = grenze["quelle"]
        e["reason"] = (f"<{doppel}> statt <{einfach}> am Morphemanfang ({(lex or {}).get('morpheme') or grenze.get('grund')}) "
                       "– Verdoppelung an einer Stelle, an der keine Schärfung stattfindet.")
        _excl(e, "08", "08 gilt nur direkt nach Kurzvokal, nicht am Morphemanfang (Manual §6.2).")
        return e
    if vorher and ist_konsonant_graphem(vorher["g"]):
        e["kategorie"] = "11"
        e["reason"] = f"<{doppel}> statt <{einfach}> nach einem Konsonanten (<{vorher['g']}>) – Verdoppelung ohne vorangehenden Kurzvokal."
        _excl(e, "08", "Vor der Stelle steht kein Vokal.")
        return e
    laenge = vokallaenge(t_seg, op["ti"] - 1, lex) if vorher else {"wert": None, "quelle": "unbekannt"}
    e["featureSource"] = laenge["quelle"]; e["entscheidend"] = "Vokallänge vor der Stelle"
    if laenge["wert"] == "kurz":
        e["kategorie"] = "08"
        e["reason"] = (f"<{doppel}> statt <{einfach}> nach kurzem Vokal ({laenge.get('grund')}) – unnötige Verdoppelung, "
                       "die Einfachschreibung ist lexikalisch festgelegt.")
        _excl(e, "11", "11 setzt Langvokal, Konsonant davor oder Morphemanfang voraus.")
        if doppel == "ss":
            _excl(e, "15", "15-CH setzt einen langen Vokal oder Diphthong davor voraus.")
        return e
    if laenge["wert"] == "lang":
        if doppel == "ss":
            e["kategorie"] = "15"; e["definition"] = "de-CH"
            e["reason"] = (f"<ss> statt <s> nach langem Vokal/Diphthong ({laenge.get('grund')}) – ss gesetzt, wo die "
                           "CH-Zielschreibung einfaches s verlangt (Ergänzung A.4).")
            _excl(e, "08", "08 setzt einen Kurzvokal voraus.")
            _excl(e, "11", "Der s/ss-Fall wird für de-CH über 15 geführt (Ergänzung A.5).")
            return e
        e["kategorie"] = "11"
        e["reason"] = f"<{doppel}> statt <{einfach}> nach langem Vokal ({laenge.get('grund')}) – Verdoppelung nach Langvokal."
        _excl(e, "08", "08 setzt einen Kurzvokal voraus.")
        return e
    e["status"] = "needs_context"; e["featureSource"] = "unbekannt"
    e["kandidaten"] = ["08", "15"] if doppel == "ss" else ["08", "11"]
    e["reason"] = (f"<{doppel}> statt <{einfach}>. Ob der Vokal davor kurz (→ 08) oder lang "
                   f"(→ {'15-CH' if doppel == 'ss' else '11'}) ist, steht nicht im Lexikon.")
    return e


def markierung_fehlt(op: dict) -> dict:
    e = ereignis(studentGrapheme=op["s"], targetGrapheme=op["t"], kategorie="09")
    e["reason"] = (f"Das Schülergraphem <{op['s']}> repräsentiert denselben langen Vokal wie das Zielgraphem <{op['t']}>. "
                   "Es fehlt kein eigenständiges Graphem; die orthografische Längenmarkierung wurde nicht realisiert.")
    _excl(e, "31", "Kein Vokalphonem wurde ausgelassen.")
    if op["t"] == "ie":
        _excl(e, "34", "<i> für <ie> bei langem /iː/ ist 09, kein Vokalersatz.")
    return e


def markierung_zuviel(op: dict, t_seg: list[dict], lex: dict | None) -> dict:
    e = ereignis(studentGrapheme=op["s"], targetGrapheme=op["t"])
    laenge = vokallaenge(t_seg, op["ti"], lex)
    e["featureSource"] = laenge["quelle"]; e["entscheidend"] = "Länge des Zielvokals"
    if laenge["wert"] == "lang":
        e["kategorie"] = "10"
        e["reason"] = f"<{op['s']}> statt <{op['t']}>: Der Zielvokal ist lang ({laenge.get('grund')}), die zusätzliche Markierung ist unnötig."
        _excl(e, "12", "12 setzt einen kurzen Zielvokal voraus.")
        _excl(e, "32", "Kein zusätzliches Vokalphonem, nur eine Markierung.")
        return e
    if laenge["wert"] == "kurz":
        e["kategorie"] = "12"
        e["reason"] = f"<{op['s']}> statt <{op['t']}>: Der Zielvokal ist kurz ({laenge.get('grund')}), eine Längenmarkierung ist falsch."
        _excl(e, "10", "10 setzt einen langen Zielvokal voraus.")
        _excl(e, "32", "Kein zusätzliches Vokalphonem, nur eine Markierung.")
        return e
    e["status"] = "needs_context"; e["featureSource"] = "unbekannt"; e["kandidaten"] = ["10", "12"]
    e["reason"] = f"<{op['s']}> statt <{op['t']}>: zusätzliche Längenmarkierung. Ob der Zielvokal lang (→ 10) oder kurz (→ 12) ist, steht nicht im Lexikon."
    return e


def fremdgraphem(op: dict) -> dict:
    """Ein Fehler genau an einem Fremdgraphem ist ein Fremdwortfehler (37)."""
    s, t = op.get("s") or "", op.get("t") or ""
    e = ereignis(studentGrapheme=s, targetGrapheme=t, kategorie="37")
    fremd = t if t in FREMDGRAPHEME else s
    e["reason"] = (f"<{s or '∅'}> für <{t or '∅'}>: <{fremd}> ist ein Fremdgraphem – die Schreibung folgt "
                   "nicht den Regeln des deutschen Grundwortschatzes, sondern ist am Fremdwort zu merken (Manual §9.4).")
    _excl(e, "29/30/33/34", "Fremdwortfehler werden nicht als Auslassung, Zufügung oder Ersetzung gezählt.")
    return e


def vokalersatz(op: dict, lex: dict | None) -> dict:
    s, t = op["s"], op["t"]
    if s in FREMDGRAPHEME or t in FREMDGRAPHEME:
        return fremdgraphem(op)
    e = ereignis(studentGrapheme=s, targetGrapheme=t)
    grund_s, grund_t = LAENGENMARKER.get(s, s), LAENGENMARKER.get(t, t)
    if grund_s == grund_t:
        if t in LAENGENMARKER and s not in LAENGENMARKER:
            return markierung_fehlt(op)
        if s in DOPPELMARKER and t in LAENGENMARKER:
            # «Baahn» für «Bahn»: Das Zielwort ist bereits markiert lang, die
            # zweite Markierung ist überflüssig (Manual §6: 10).
            e["kategorie"] = "10"
            e["reason"] = f"<{s}> statt <{t}>: doppelte Längenmarkierung; der Zielvokal ist bereits markiert lang."
            _excl(e, "32", "Kein zusätzliches Vokalphonem, nur eine überzählige Markierung.")
            return e
        e["kategorie"] = "37"
        e["reason"] = (f"<{s}> statt <{t}>: gleicher Vokal, aber die Längenmarkierung vertauscht (z. B. ee/eh) – "
                       "weder fehlt eine Markierung (09) noch ist eine zu viel (10).")
        _excl(e, "34", "Der Vokal selbst ist richtig.")
        return e
    # Die Oppositionen 17/18 sind graphemisch definiert (Manual §7.2): e für ä
    # ist 17, auch wenn das ä nicht ableitbar ist (Käse, Bär). Das Lexikon
    # liefert nur die Erklärung für die Förderung.
    um = umlaut_merkmal(lex)
    if (s, t) in {("e", "ä"), ("eu", "äu"), ("eh", "äh"), ("ee", "äh")}:
        e["kategorie"] = "17"
        zusatz = " Das Zielwort ist ableitbar (Umlaut vom Grundwort)." if um["wert"] is True else (
                 " Das ä ist hier nicht ableitbar – ein Merkwort." if um["wert"] is False else "")
        e["reason"] = f"<{s}> für <{t}>: Umlautschreibung nicht realisiert.{zusatz}"
        _excl(e, "34", "e ↔ ä ist die spezifische Opposition 17 (Manual §7.2).")
        return e
    if (s, t) in {("ä", "e"), ("äu", "eu"), ("äh", "eh")}:
        e["kategorie"] = "18"
        e["reason"] = f"<{s}> für <{t}>: Umlautschreibung gesetzt, wo das Zielwort keinen Umlaut hat (Übergeneralisierung)."
        _excl(e, "34", "ä ↔ e ist die spezifische Opposition 18 (Manual §7.2).")
        return e
    einfach_s = s if len(s) == 1 else None
    einfach_t = t if len(t) == 1 else None

    def paar(a: str | None, b: str | None) -> bool:
        return bool(a and b and (UMLAUT.get(a) == b or UMLAUT.get(b) == a))

    if (paar(einfach_s, einfach_t) or paar(LAENGENMARKER.get(s), LAENGENMARKER.get(t))
            or (s, t) in {("au", "äu"), ("äu", "au")}):
        e["kategorie"] = "36"
        e["reason"] = f"<{s}> für <{t}>: Umlautbezeichnung (a/o/u ↔ ä/ö/ü) nicht bzw. falsch gesetzt."
        _excl(e, "34", "a/o/u ↔ ä/ö/ü ist spezifisch 36 (Manual §7.2).")
        return e
    e["kategorie"] = "34"
    e["reason"] = f"<{s}> für <{t}>: Vokalersatz ohne spezifische Regel."
    _excl(e, "09", "Keine fehlende Längenmarkierung desselben Vokals.")
    _excl(e, "17", "Nicht e/eu ↔ ä/äu.")
    _excl(e, "36", "Kein Umlautpaar a/o/u ↔ ä/ö/ü.")
    return e


def konsonantersatz(op: dict, t_seg: list[dict], lex: dict | None) -> dict:
    s, t = op["s"], op["t"]
    if s in FREMDGRAPHEME or t in FREMDGRAPHEME:
        return fremdgraphem(op)
    rest = "".join(x["g"] for x in t_seg[op["ti"]:])
    if t == "t" and s in ("z", "tz") and rest.startswith("tion"):
        e = ereignis(studentGrapheme=s, targetGrapheme=t, kategorie="37")
        e["reason"] = "<z> für <t> in der Fremdendung -tion: t steht hier für /ts/ – Fremdwortschreibung, kein Konsonantenersatz."
        _excl(e, "33", "Die Endung -tion ist eine Merkschreibung des Fremdworts.")
        return e
    if s in VERDOPPELUNG and t in VERDOPPELUNG and s != t:
        # «Bladd» für «Blatt»: Die Verdoppelung stimmt, das Zeichen nicht –
        # beurteilt wird das Grundzeichen (d für t am Silbenrand).
        innen = konsonantersatz({**op, "s": VERDOPPELUNG[s], "t": VERDOPPELUNG[t]}, t_seg, lex)
        innen["studentGrapheme"], innen["targetGrapheme"] = s, t
        innen["reason"] = f"<{s}> für <{t}>, verdoppelt: " + innen["reason"]
        return innen
    e = ereignis(studentGrapheme=s, targetGrapheme=t)
    rand = am_silbenrand(t_seg, op["ti"])
    if STIMMLOS_FUER_STIMMHAFT.get(s) == t:
        if rand:
            e["kategorie"] = "19"; e["reason"] = f"<{s}> für <{t}> am Silbenrand – Auslautverhärtung verschriftet."
            _excl(e, "33", "p/t/k ↔ b/d/g am Silbenrand ist spezifisch 19 (Manual §7.3).")
        else:
            e["kategorie"] = "33"; e["reason"] = f"<{s}> für <{t}>, aber nicht am Silbenrand – 19 gilt nur dort."
            _excl(e, "19", "Stelle liegt nicht am Silbenrand.")
        return e
    if STIMMHAFT_FUER_STIMMLOS.get(s) == t:
        if rand:
            e["kategorie"] = "20"; e["reason"] = f"<{s}> für <{t}> am Silbenrand – Umkehrung der Auslautverhärtung."
            _excl(e, "33", "b/d/g ↔ p/t/k am Silbenrand ist spezifisch 20.")
        else:
            e["kategorie"] = "33"; e["reason"] = f"<{s}> für <{t}>, aber nicht am Silbenrand."
            _excl(e, "20", "Stelle liegt nicht am Silbenrand.")
        return e
    if t == "v":
        lw = v_lautwert(lex)
        e["featureSource"] = lw["quelle"]; e["entscheidend"] = "Lautwert des Ziel-<v> (/f/ oder /v/)"
        if s == "f":
            if lw["wert"] == "f":
                e["kategorie"] = "23"; e["reason"] = "<f> für <v>; das Ziel-<v> wird /f/ gesprochen (Lexikon)."
                _excl(e, "25", "25 setzt Lautwert /v/ voraus."); _excl(e, "33", "f/v ist spezifisch 23.")
            elif lw["wert"] == "v":
                e["kategorie"] = "33"; e["reason"] = "<f> für <v>, aber das Ziel-<v> wird /v/ gesprochen – kein Merkwortfall 23."
                _excl(e, "23", "23 setzt Lautwert /f/ voraus.")
            else:
                e["kategorie"] = "23"; e["status"] = "needs_context"; e["kandidaten"] = ["23", "33"]
                e["reason"] = "<f> für <v>. Lautwert des Ziel-<v> unbekannt."
            return e
        if s == "w":
            if lw["wert"] == "v":
                e["kategorie"] = "25"; e["reason"] = "<w> für <v>; das Ziel-<v> wird /v/ gesprochen (Lexikon)."
                _excl(e, "23", "23 setzt Lautwert /f/ voraus."); _excl(e, "33", "w/v ist spezifisch 25.")
            elif lw["wert"] == "f":
                e["kategorie"] = "33"; e["reason"] = "<w> für <v>, aber das Ziel-<v> wird /f/ gesprochen."
                _excl(e, "25", "25 setzt Lautwert /v/ voraus.")
            else:
                e["kategorie"] = "25"; e["status"] = "needs_context"; e["kandidaten"] = ["25", "33"]
                e["reason"] = "<w> für <v>. Lautwert des Ziel-<v> unbekannt."
            return e
    if s == "v" and t == "f":
        e["kategorie"] = "24"; e["reason"] = "<v> für <f> – Merkwortfall."; _excl(e, "33", "v/f ist spezifisch 24."); return e
    if s == "v" and t == "w":
        e["kategorie"] = "26"; e["reason"] = "<v> für <w> – Merkwortfall."; _excl(e, "33", "v/w ist spezifisch 26."); return e
    if s == "ch" and t == "g":
        if rand:
            e["kategorie"] = "27"; e["reason"] = "<ch> für <g> im Silbenende (-ig → -ich)."; _excl(e, "33", "ch/g im Silbenende ist spezifisch 27.")
        else:
            e["kategorie"] = "33"; e["reason"] = "<ch> für <g>, aber nicht im Silbenende."; _excl(e, "27", "Nicht im Silbenende.")
        return e
    if s == "g" and t == "ch":
        if rand:
            e["kategorie"] = "28"; e["reason"] = "<g> für <ch> im Silbenende (-ich → -ig)."; _excl(e, "33", "g/ch im Silbenende ist spezifisch 28.")
        else:
            e["kategorie"] = "33"; e["reason"] = "<g> für <ch>, aber nicht im Silbenende."; _excl(e, "28", "Nicht im Silbenende.")
        return e
    e["kategorie"] = "33"
    e["reason"] = f"<{s}> für <{t}>: Konsonantenersatz ohne spezifische Regel."
    _excl(e, "19/20", "Kein p/t/k ↔ b/d/g-Paar am Silbenrand.")
    _excl(e, "23–28", "Kein f/v/w- oder ch/g-Fall.")
    return e


def graphem_fehlt(op: dict) -> dict:
    if op["t"] in FREMDGRAPHEME:
        return fremdgraphem({"s": "", "t": op["t"]})
    e = ereignis(studentGrapheme="", targetGrapheme=op["t"])
    if not op["t"].isalpha():
        e["kategorie"] = "37"; e["reason"] = f"Zeichen <{op['t']}> fehlt – kein Graphem, Sonstiges."
        return e
    if ist_vokal_graphem(op["t"]):
        e["kategorie"] = "31"; e["reason"] = f"Vokalgraphem <{op['t']}> fehlt – eine vokalische Einheit wurde ausgelassen."
        _excl(e, "09", "Es fehlt nicht nur eine Markierung, sondern der Vokal selbst.")
    else:
        e["kategorie"] = "29"; e["reason"] = f"Konsonantengraphem <{op['t']}> fehlt."
        _excl(e, "07", "Keine fehlende Verdoppelung, ein eigenständiges Graphem fehlt.")
    return e


def graphem_zuviel(op: dict) -> dict:
    if op["s"] in FREMDGRAPHEME:
        return fremdgraphem({"s": op["s"], "t": ""})
    e = ereignis(studentGrapheme=op["s"], targetGrapheme="")
    if not op["s"].isalpha():
        e["kategorie"] = "37"; e["reason"] = f"Zeichen <{op['s']}> zugefügt (Apostroph, Bindestrich o. Ä.) – kein Graphem, Sonstiges."
        return e
    if ist_vokal_graphem(op["s"]):
        e["kategorie"] = "32"; e["reason"] = f"Vokalgraphem <{op['s']}> zugefügt."
        _excl(e, "10/12", "Keine Längenmarkierung, sondern ein zusätzliches Vokalgraphem.")
    else:
        e["kategorie"] = "30"; e["reason"] = f"Konsonantengraphem <{op['s']}> zugefügt."
        _excl(e, "08/11", "Keine Verdoppelung, ein eigenständiges Graphem ist zu viel.")
    return e


def teilgraphem(op: dict) -> dict:
    s, t = op["s"], op["t"]
    if t.endswith(s) or t.startswith(s):
        rest = t[len(s):] if t.startswith(s) else t[:len(t) - len(s)]
        e = graphem_fehlt({"t": rest}); e["studentGrapheme"] = s; e["targetGrapheme"] = t
        e["reason"] = f"<{s}> für <{t}>: der Bestandteil <{rest}> fehlt."
        return e
    rest = s[len(t):] if s.startswith(t) else s[:len(s) - len(t)]
    e = graphem_zuviel({"s": rest}); e["studentGrapheme"] = s; e["targetGrapheme"] = t
    e["reason"] = f"<{s}> für <{t}>: der Bestandteil <{rest}> ist zu viel."
    return e


def klassifiziere_op(op: dict, t_seg: list[dict], ziel: str, lex: dict | None) -> dict:
    if op["op"] == "trans":
        e = ereignis(studentGrapheme="".join(op["s"]), targetGrapheme="".join(op["t"]), kategorie="35")
        e["reason"] = f"<{''.join(op['s'])}> für <{''.join(op['t'])}>: benachbarte Grapheme vertauscht – echte Transposition."
        _excl(e, "29+30", "Keine Auslassung plus Zufügung, sondern eine Umstellung (Manual §9.3).")
        return e
    if op["op"] == "del":
        return graphem_fehlt(op)
    if op["op"] == "ins":
        return graphem_zuviel(op)
    s, t = op["s"], op["t"]
    if t in VERDOPPELUNG and VERDOPPELUNG[t] == s:
        return verdoppelung_fehlt(op, t_seg, ziel, lex)
    if s in VERDOPPELUNG and VERDOPPELUNG[s] == t:
        return verdoppelung_zuviel(op, t_seg, ziel, lex)
    if t in VERDOPPELUNG and len(s) == 2 and s[0] == s[1] and VERDOPPELUNG[t] == s[0]:
        # «Kazze» für «Katze», «Zukker» für «Zucker»: Manual §6.1 führt das
        # unter 07 – die Schärfung ist erkannt, das Schärfungsgraphem (tz, ck)
        # nicht gewählt.
        e = ereignis(studentGrapheme=s, targetGrapheme=t, kategorie="07")
        e["reason"] = (f"<{s}> für <{t}>: Die Verdoppelung wurde erkannt, aber mit dem Buchstabenpaar statt "
                       f"dem Schärfungsgraphem <{t}> geschrieben (Manual §6.1: *Kazze → Katze).")
        _excl(e, "37", "Kein Sonstiges: Das Phänomen ist die Schärfung.")
        return e
    if s in FREMDGRAPHEME or t in FREMDGRAPHEME:
        return fremdgraphem(op)
    if t in LAENGENMARKER and LAENGENMARKER[t] == s:
        return markierung_fehlt(op)
    if s in LAENGENMARKER and LAENGENMARKER[s] == t:
        return markierung_zuviel(op, t_seg, lex)
    if ist_vokal_graphem(s) and ist_vokal_graphem(t):
        return vokalersatz(op, lex)
    if ist_konsonant_graphem(s) and ist_konsonant_graphem(t):
        if s != t and (s in t or t in s):
            return teilgraphem(op)
        return konsonantersatz(op, t_seg, lex)
    e = ereignis(studentGrapheme=s, targetGrapheme=t, kategorie="37")
    e["reason"] = f"<{s}> für <{t}>: Vokal und Konsonant vertauscht – kein spezifisches OLFA-Muster."
    return e


def gross_klein(schueler: str, ziel: str) -> list[dict]:
    aus: list[dict] = []
    s_g, z_g = schueler[:1].isupper(), ziel[:1].isupper()
    if z_g and not s_g:
        aus.append(ereignis(studentGrapheme=schueler[:1], targetGrapheme=ziel[:1], kategorie="01",
                            reason="Wortanfang kleingeschrieben, obwohl Grossschreibung gefordert ist."))
    if not z_g and s_g:
        aus.append(ereignis(studentGrapheme=schueler[:1], targetGrapheme=ziel[:1], kategorie="02",
                            reason="Wortanfang grossgeschrieben, obwohl Kleinschreibung gefordert ist."))
    innen_s = any(c.isupper() for c in schueler[1:])
    innen_z = any(c.isupper() for c in ziel[1:])
    if innen_s and not innen_z:
        aus.append(ereignis(studentGrapheme=next(c for c in schueler[1:] if c.isupper()), targetGrapheme="",
                            kategorie="03", reason="Grossbuchstabe innerhalb des Wortes."))
    return aus


def _vokalpaar_auftrennen(s_seg: list[dict], ziel: str) -> list[dict]:
    """«geen» für «gehen»: Das <ee> des Kindes ist keine Längenmarkierung,
    sondern zwei Silbenkerne, zwischen denen das silbentrennende h fehlt.
    Steht im Zielwort Vokal + h + Vokal, wird das doppelte Vokalzeichen des
    Kindes in zwei einfache zerlegt, damit das Alignment «h fehlt» erkennt."""
    z = ziel.lower()
    aus = []
    for x in s_seg:
        g = x["g"]
        if g in ("aa", "ee", "oo") and (g[0] + "h" + g[0]) in z and g not in z:
            aus.append({"g": g[0], "at": x["at"]}); aus.append({"g": g[0], "at": x["at"] + 1})
        else:
            aus.append(x)
    return aus


def klassifiziere_wort(schueler: str, ziel: str, lexikon: dict | None = None,
                       erzwingen: bool = False) -> dict[str, Any]:
    lexikon = lexikon or {}
    lex = lexikon.get(ziel.lower())
    aus = gross_klein(schueler, ziel)
    s_seg, t_seg = segmentiere(schueler), segmentiere(ziel)
    if schueler.lower() == ziel.lower():
        return {"ereignisse": aus, "ops": [], "distanz": 0, "wortersetzung": False}
    s_seg = _vokalpaar_auftrennen(s_seg, ziel)
    ops, distanz = align([x["g"] for x in s_seg], [x["g"] for x in t_seg])
    # Mehr als zwei Fünftel der Zielgrapheme abweichend: eher ein anderes Wort.
    grenze = max(1, math.ceil(0.4 * len(t_seg)))
    if distanz > grenze and not erzwingen:
        aus.append(ereignis(studentGrapheme=schueler.lower(), targetGrapheme=ziel.lower(), kategorie=None,
                            status="manual_review", kandidaten=[], featureSource="unbekannt",
                            reason=f"{distanz} Graphemabweichungen bei {len(t_seg)} Zielgraphemen – das ist eher ein anderes Wort als eine Schreibung mit Fehlern."))
        return {"ereignisse": aus, "ops": ops, "distanz": distanz, "wortersetzung": True}
    for op in ops:
        if op["op"] == "equal":
            continue
        e = klassifiziere_op(op, t_seg, ziel, lex)
        ti = op.get("ti")
        e["charOffsetImWort"] = t_seg[ti]["at"] if ti is not None and ti < len(t_seg) else (t_seg[-1]["at"] if t_seg else 0)
        aus.append(e)
    if {schueler.lower(), ziel.lower()} == {"das", "dass"}:
        for e in aus:
            e["possibleUnderlyingCause"] = "grammatisch: das/dass-Verwechslung (Konjunktion vs. Artikel/Pronomen)"
    return {"ereignisse": aus, "ops": ops, "distanz": distanz, "wortersetzung": False}


# --------------------------------------------------------------- Validator

def validiere(e: dict, kontext: dict | None = None) -> dict:
    kontext = kontext or {}
    protokoll: list[dict] = []

    def ablehnen(regel: str, neu: str | None) -> None:
        protokoll.append({"regel": regel, "ergebnis": f"reklassifiziert → {neu}" if neu else "manual_review"})
        if neu:
            _excl(e, e["kategorie"], f"Validator: {regel}"); e["kategorie"] = neu
        else:
            e["status"] = "manual_review"
            e["kandidaten"] = e["kandidaten"] or [k for k in [e["kategorie"]] if k]

    s, t = e.get("studentGrapheme") or "", e.get("targetGrapheme") or ""
    ist_verdoppelung = t in VERDOPPELUNG and VERDOPPELUNG[t] == s
    ist_marker = t in LAENGENMARKER and LAENGENMARKER[t] == s
    if e["kategorie"] and e["kategorie"] in NEVER_ASSIGN:
        ablehnen(f"Kategorie {e['kategorie']} wird für de-CH nie vergeben", None)
    if (e["kategorie"] == "29" and ist_verdoppelung
            and e["featureSource"] not in ("lexikon", "vorgabe", "heuristik", "schreibung")):
        ablehnen("29 bei Konsonantenverdoppelung ohne belegte Morphemgrenze", "07")
    if e["kategorie"] == "31" and ist_marker:
        ablehnen("31 bei reiner Längenmarkierung", "09")
    if e["kategorie"] == "08" and kontext.get("vokalDavor") == "lang":
        ablehnen("08 ohne Kurzvokal davor", "15" if t == "s" else "11")
    if e["kategorie"] == "07" and s == "s" and t == "ss" and kontext.get("vokalDavor") == "lang":
        ablehnen("07 bei s→ss nach Langvokal (A.5)", "13")
    if e["kategorie"] in ("08", "11") and s == "ss" and t == "s" and kontext.get("vokalDavor") == "lang":
        ablehnen("08/11 bei ss→s nach Langvokal (A.5)", "15")
    if "ß" in t or "ß" in (kontext.get("ziel") or ""):
        ablehnen("Zielschreibung enthält ß (de-CH)", None)
    if e["kategorie"] in ("13", "15"):
        e["definition"] = "de-CH"
    e["validator"] = protokoll
    return e


# ------------------------------------------------------- Konfidenz (C.2)

def konfidenz(e: dict, quellen: dict | None = None) -> dict:
    q = quellen or {}
    if e["status"] == "manual_review":
        k = 0.4
    elif e["status"] == "needs_context":
        k = 0.55
    else:
        k = 0.97
        if e["featureSource"] == "heuristik":
            k = 0.86
        if e["featureSource"] == "ki":
            k = 0.78
        if e["status"] == "resolved_by_area":
            k = min(k, 0.72)
        if e["status"] == "resolved_by_ki":
            k = 0.88 if q.get("zweitdurchgangEinig") else 0.80
        if q.get("eigeneZuordnung"):
            k = 0.95
    if q.get("zielwortSicherheit") is not None:
        k = min(k, q["zielwortSicherheit"])
    if q.get("quelle") == "import":
        k = min(k, 0.95)
    e["confidence"] = round(k, 2)
    e["band"] = band(e["confidence"])
    return e


def konsequenz_pruefen(e: dict) -> dict:
    """Ergänzung C.1: gleiche Förderbereiche → folgenlos."""
    if e["status"] != "needs_context" or not e["kandidaten"]:
        return e
    bereiche = {AREA_MAP.get(k, "F10") for k in e["kandidaten"]}
    if len(bereiche) == 1:
        e["status"] = "resolved_by_area"
        e["kategorie"] = e["kategorie"] if e["kategorie"] in e["kandidaten"] else e["kandidaten"][0]
        e["reason"] += (f" Alle Kandidaten ({'/'.join(e['kandidaten'])}) führen in {next(iter(bereiche))} – "
                        "die Unsicherheit ist für die Förderung folgenlos.")
    return e


def abschliessen(e: dict, kontext: dict | None = None, quellen: dict | None = None) -> dict:
    validiere(e, kontext)
    konsequenz_pruefen(e)
    e["foerderbereich"] = AREA_MAP.get(e["kategorie"]) if e["kategorie"] else None
    e["name"] = KURZNAME.get(e["kategorie"]) if e["kategorie"] else None
    e["locale"] = "de-CH"; e["area"] = "A"
    konfidenz(e, quellen)
    return e


def braucht_grenzfallpruefung(e: dict) -> bool:
    if e["status"] == "needs_context":
        return True
    if e["status"] != "resolved":
        return False
    if e["featureSource"] in ("lexikon", "vorgabe", "schreibung", "eigene"):
        return False
    return any(e["kategorie"] in paar for paar in KRITISCHE_PAARE)


def muster_schluessel(e: dict, ziel: str) -> str:
    t_seg = segmentiere(ziel or "")
    idx = next((i for i, x in enumerate(t_seg) if x["at"] == e.get("charOffsetImWort")), -1)
    davor = t_seg[idx - 1]["g"] if idx > 0 else "^"
    danach = t_seg[idx + 1]["g"] if 0 <= idx and idx + 1 < len(t_seg) else "$"
    return f"{e.get('studentGrapheme') or '∅'}>{e.get('targetGrapheme') or '∅'}|{davor}_{danach}"


# --------------------------------------------------- Text- und Satzstruktur

WORT_MUSTER = re.compile(r"[^\W\d_][\w]*(?:[-'’][\w]+)*|\d+", re.UNICODE)


def tokenisiere(text: str) -> list[dict[str, Any]]:
    t = str(text or "")
    aus: list[dict[str, Any]] = []
    satz, i = 0, 0
    for m in WORT_MUSTER.finditer(t):
        satz += len(re.findall(r"[.!?]+", t[i:m.start()]))
        aus.append({"wort": m.group(0), "at": m.start(), "satz": satz, "index": len(aus)})
        i = m.end()
    return aus


def saetze(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", str(text or "")) if s.strip()]


def normalisieren(wort: str) -> str:
    return re.sub(r"^[»«\"'’„“”.,;:!?()\[\]{}–—-]+|[»«\"'’„“”.,;:!?()\[\]{}–—-]+$", "", str(wort or "")).lower()


def opcodes(a: list, b: list) -> list[tuple]:
    from difflib import SequenceMatcher
    return [tuple(x) for x in SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes()]


def ist_selbststaendig(teil: str, lexikon: dict | None = None) -> bool:
    """Kann dieser abgetrennte Teil für sich ein Wort sein?

    Gebunden sind Präfixe und Suffixe («ver», «in», «ung»), alles unter drei
    Buchstaben, und Teile mit gebundener Endung, die nicht als Wort bekannt
    sind («sichtig»). Bekannt heisst: im Lexikon oder grossgeschrieben
    (ein Nomen wie «Arzt»)."""
    t = teil.lower()
    if len(t) < 3 or t in UNSELBSTSTAENDIG or t in SUFFIXE:
        return False
    if teil[:1].isupper() or (lexikon and t in lexikon):
        return True
    return not t.endswith(GEBUNDENE_ENDUNGEN)


def wortgrenzen_ereignis(teile: list[str], ziel: str, lexikon: dict | None = None) -> dict:
    e = ereignis(studentGrapheme=" ".join(teile), targetGrapheme=ziel)
    if all(ist_selbststaendig(t, lexikon) for t in teile):
        e["kategorie"] = "04"
        e["reason"] = f"«{' '.join(teile)}» statt «{ziel}»: Bestandteile getrennt, die zusammengeschrieben werden – beide könnten selbstständige Wörter sein."
        _excl(e, "06", "Alle Teile sind selbstständige Wörter (Manual §5.2).")
    else:
        e["kategorie"] = "06"
        e["reason"] = f"«{' '.join(teile)}» statt «{ziel}»: ein unselbstständiger Wortteil wurde abgetrennt."
        _excl(e, "04", "Mindestens ein Teil ist kein selbstständiges Wort.")
    e["featureSource"] = "heuristik"
    return e


def wortgrenzen_ergebnis(teile: list[str], ziel: str, lexikon: dict | None = None) -> list[dict]:
    """Getrennt geschrieben, wo zusammengehört (04/06) – samt dem Folgefehler
    aus Manual §5.1: «Zahn arzt» ist 04 PLUS 01, «Zahn Arzt» nur 04. Bei 06
    entfällt der Zusatz: Ein abgetrenntes Suffix («in») ist kein Nomen."""
    aus = [wortgrenzen_ereignis(teile, ziel, lexikon)]
    if ziel[:1].isupper() and aus[0]["kategorie"] == "04":
        for teil in teile[1:]:
            if teil[:1].islower():
                aus.append(ereignis(
                    studentGrapheme=teil[0], targetGrapheme=teil[0].upper(), kategorie="01",
                    reason=f"«{teil}» als abgetrennter Nomenbestandteil kleingeschrieben (Manual §5.1)."))
    return aus


def zusammenschreibung_ereignis(schuelerwort: str, ziel: str) -> dict:
    """Zusammengeschrieben, wo getrennt gehört (05)."""
    e = ereignis(studentGrapheme=schuelerwort, targetGrapheme=ziel, kategorie="05")
    e["reason"] = f"«{schuelerwort}» statt «{ziel}»: mehrere selbstständige Wörter zusammengeschrieben."
    _excl(e, "04", "Nicht getrennt statt zusammen, sondern umgekehrt.")
    e["featureSource"] = "heuristik"
    return e


# ------------------------------------- Deterministische Vorprüfungen -------
# Zwei Dinge lassen sich im Freitext ohne Modell sicher sagen. Sie laufen VOR
# dem Modell und gehen in dieselbe Liste – ein Modell, das sie übersieht, kann
# sie so nicht mehr verschlucken.

def eszett_screening(tokens: list[dict]) -> list[dict]:
    """In der Schweizer Zielnorm gibt es kein ß. Jedes ß ist objektiv falsch,
    die Zielform ergibt sich mechanisch."""
    return [{"tokenIndex": t["index"], "student": t["wort"],
             "target": t["wort"].replace("ß", "ss"), "sicherheit": 1, "herkunft": "regel"}
            for t in tokens if "ß" in t["wort"]]


def wiederholungs_screening(tokens: list[dict], bekannt: dict[str, str]) -> list[dict]:
    """Was dieses Kind schon einmal falsch geschrieben hat, wird beim erneuten
    Auftreten geprüft – gerade die wiederkehrenden Fehler tragen das
    Längsschnittprofil, und genau sie überliest ein Modell gern."""
    aus = []
    for t in tokens:
        ziel = bekannt.get(normalisieren(t["wort"]))
        if not ziel or normalisieren(ziel) == normalisieren(t["wort"]):
            continue
        aus.append({"tokenIndex": t["index"], "student": t["wort"], "target": ziel,
                    "sicherheit": 0.8, "herkunft": "wiederholung"})
    return aus


def align_woerter(referenz: str, schuelertext: str) -> dict[str, Any]:
    tok_r, tok_s = tokenisiere(referenz), tokenisiere(schuelertext)
    norm_r = [normalisieren(x["wort"]) for x in tok_r]
    norm_s = [normalisieren(x["wort"]) for x in tok_s]
    paare: list[dict] = []

    def push(art: str, r: dict | None, s: dict | None, **extra: Any) -> None:
        basis = s or r
        paare.append({"art": art, "ziel": r["wort"] if r else "", "schueler": s["wort"] if s else "",
                      "zielTok": r, "schuelerTok": s, "satz": basis["satz"] if basis else 0,
                      "at": s["at"] if s else (r["at"] if r else 0),
                      "tokenIndex": s["index"] if s else (r["index"] if r else -1), **extra})

    for tag, i1, i2, j1, j2 in opcodes(norm_r, norm_s):
        if tag == "equal":
            for v in range(i2 - i1):
                r, s = tok_r[i1 + v], tok_s[j1 + v]
                push("gleich" if r["wort"] == s["wort"] else "abweichung", r, s)
        elif tag == "replace":
            i, j = i1, j1
            while i < i2 and j < j2:
                getroffen = False
                k = 2
                while i + k <= i2:
                    if "".join(norm_r[i:i + k]) == norm_s[j]:
                        push("zusammen", tok_r[i], tok_s[j], zielWoerter=[x["wort"] for x in tok_r[i:i + k]])
                        i += k; j += 1; getroffen = True; break
                    k += 1
                if getroffen:
                    continue
                k = 2
                while j + k <= j2:
                    if "".join(norm_s[j:j + k]) == norm_r[i]:
                        push("getrennt", tok_r[i], tok_s[j], schuelerWoerter=[x["wort"] for x in tok_s[j:j + k]])
                        i += 1; j += k; getroffen = True; break
                    k += 1
                if getroffen:
                    continue
                push("abweichung", tok_r[i], tok_s[j]); i += 1; j += 1
            for v in range(i, i2):
                push("fehlt", tok_r[v], None)
            for v in range(j, j2):
                push("zusatz", None, tok_s[v])
        elif tag == "delete":
            for v in range(i1, i2):
                push("fehlt", tok_r[v], None)
        else:
            for v in range(j1, j2):
                push("zusatz", None, tok_s[v])
    return {"paare": paare, "tokR": tok_r, "tokS": tok_s}


def analysiere_diktat(referenz: str, schuelertext: str, lexikon: dict | None = None,
                      muster: dict | None = None) -> dict[str, Any]:
    muster = muster or {}
    al = align_woerter(referenz, schuelertext)
    paare, tok_r, tok_s = al["paare"], al["tokR"], al["tokS"]
    ereignisse: list[dict] = []
    abdeckung = [{"index": t["index"], "wort": t["wort"], "satz": t["satz"], "status": "offen"} for t in tok_s]
    ausgelassen: list[dict] = []; zusaetzlich: list[dict] = []; wortersetzungen: list[dict] = []

    def setze(tok: dict | None, st: str) -> None:
        if tok:
            abdeckung[tok["index"]]["status"] = st

    def fertig(e: dict, p: dict, ziel: str | None = None) -> None:
        e["studentForm"] = p["schueler"]; e["targetForm"] = ziel if ziel is not None else p["ziel"]
        e["sentenceIndex"] = p["satz"]; e["charOffset"] = p["at"] + (e.get("charOffsetImWort") or 0)
        e["tokenIndex"] = p["tokenIndex"]
        e["muster"] = muster_schluessel(e, e["targetForm"])
        frueher = muster.get(e["muster"])
        if frueher and e["status"] != "manual_review":
            if e["kategorie"] != frueher["kategorie"]:
                _excl(e, e["kategorie"], "Frühere eigene Zuordnung zu identischem Muster")
            e["kategorie"] = frueher["kategorie"]; e["status"] = "resolved"; e["featureSource"] = "eigene"; e["kandidaten"] = []
            e["reason"] += f" Nach eigener Zuordnung ({frueher.get('am', '')})."
        abschliessen(e, {"vokalDavor": None, "ziel": e["targetForm"]},
                     {"eigeneZuordnung": bool(frueher), "zielwortSicherheit": 1})
        ereignisse.append(e)

    for p in paare:
        art = p["art"]
        if art == "gleich":
            setze(p["schuelerTok"], "korrekt"); continue
        if art == "fehlt":
            ausgelassen.append({"wort": p["ziel"], "satz": p["satz"], "at": p["at"]}); continue
        if art == "zusatz":
            zusaetzlich.append({"wort": p["schueler"], "satz": p["satz"], "at": p["at"]}); setze(p["schuelerTok"], "zusatz"); continue
        if art == "zusammen":
            zw = " ".join(p["zielWoerter"])
            e = ereignis(studentGrapheme=p["schueler"], targetGrapheme=zw, kategorie="05",
                         reason=f"«{p['schueler']}» statt «{zw}»: mehrere Wörter zusammengeschrieben.")
            fertig(e, p, zw); setze(p["schuelerTok"], "fehler"); continue
        if art == "getrennt":
            for e in wortgrenzen_ergebnis(p["schuelerWoerter"], p["ziel"], lexikon):
                fertig(e, p, p["ziel"])
            start = p["schuelerTok"]["index"]
            for t in tok_s[start:start + len(p["schuelerWoerter"])]:
                setze(t, "fehler")
            continue
        r = klassifiziere_wort(p["schueler"], p["ziel"], lexikon)
        if r["wortersetzung"]:
            wortersetzungen.append({"schueler": p["schueler"], "ziel": p["ziel"], "satz": p["satz"]})
        for e in r["ereignisse"]:
            fertig(e, p)
        setze(p["schuelerTok"], "fehler" if r["ereignisse"] else "korrekt")
    return {"ereignisse": ereignisse, "abdeckung": abdeckung, "ausgelassen": ausgelassen,
            "zusaetzlich": zusaetzlich, "wortersetzungen": wortersetzungen,
            "kennzahlen": {"woerterReferenz": len(tok_r), "woerterSchueler": len(tok_s),
                           "fehler": sum(1 for e in ereignisse if e["kategorie"] or e["status"] == "manual_review"),
                           "saetze": len(saetze(schuelertext))}}


def analysiere_liste(liste: Iterable[dict], schuelertext: str, lexikon: dict | None = None,
                     muster: dict | None = None, quelle: str = "import") -> dict[str, Any]:
    """Import-/Freitextmodus: fertige Liste (Original, Ziel, Position) → Stufe 2.

    Kein Token gilt als geprüft, nur weil eine Liste vorliegt – wer die Liste
    erzeugt hat, setzt die Abdeckung (Bau-Prompt §5.1).
    """
    muster = muster or {}
    tok_s = tokenisiere(schuelertext)
    ereignisse: list[dict] = []
    verworfen: list[dict] = []
    abdeckung = [{"index": t["index"], "wort": t["wort"], "satz": t["satz"], "status": "offen"}
                 for t in tok_s]

    def finde(z: dict) -> dict | None:
        """Halluzinationsfilter (Bau-Prompt §5.2) mit Toleranz gegenüber
        verzählten Nummern: Ein Modell trifft die Wortnummer nicht immer, das
        Wort selbst aber schon. Erfunden ist ein Eintrag erst, wenn das Wort
        NIRGENDS steht."""
        gesucht = normalisieren(z.get("student", ""))
        if not gesucht:
            return None
        ti = z.get("tokenIndex")
        if isinstance(ti, int) and 0 <= ti < len(tok_s) and normalisieren(tok_s[ti]["wort"]) == gesucht:
            return tok_s[ti]
        treffer = [t for t in tok_s if normalisieren(t["wort"]) == gesucht
                   and (z.get("satz") is None or t["satz"] == z.get("satz"))]
        alle = treffer or [t for t in tok_s if normalisieren(t["wort"]) == gesucht]
        if not alle:
            return None
        if len(alle) == 1:
            return alle[0]
        if isinstance(ti, int):
            return min(alle, key=lambda t: abs(t["index"] - ti))
        return alle[0]

    def festhalten(e: dict, tok: dict, student_form: str, ziel: str, sicherheit: float) -> None:
        e["studentForm"] = student_form
        e["targetForm"] = ziel
        e["sentenceIndex"] = tok["satz"]
        e["charOffset"] = tok["at"] + (e.get("charOffsetImWort") or 0)
        e["tokenIndex"] = tok["index"]
        e["muster"] = muster_schluessel(e, ziel)
        frueher = muster.get(e["muster"])
        if frueher and e["status"] != "manual_review":
            e["kategorie"] = frueher["kategorie"]
            e["status"] = "resolved"
            e["featureSource"] = "eigene"
            e["kandidaten"] = []
            e["reason"] += f" Nach eigener Zuordnung ({frueher.get('am', '')})."
        if sicherheit < ZIELWORT_SCHWELLE:
            e["status"] = "manual_review"
            e["kandidaten"] = e["kandidaten"] or [k for k in [e["kategorie"]] if k]
            e["reason"] = (f"Zielwort «{ziel}» nur mit Sicherheit {sicherheit} bestimmt "
                           f"(Schwelle {ZIELWORT_SCHWELLE}) – eine unsichere Zielwortentscheidung darf "
                           "keine präzise Kategorie vortäuschen. ") + e["reason"]
        abschliessen(e, {"ziel": ziel},
                     {"eigeneZuordnung": bool(frueher), "zielwortSicherheit": sicherheit, "quelle": quelle})
        e["zielwortSicherheit"] = sicherheit
        ereignisse.append(e)

    for z in liste:
        ziel = str(z.get("target") or "").strip()
        if not ziel:
            verworfen.append({**z, "grund": "Keine Zielform angegeben"}); continue
        if "ß" in ziel:
            verworfen.append({**z, "grund": "Zielform enthält ß – in de-CH unzulässig"}); continue
        sicherheit = z.get("sicherheit") if isinstance(z.get("sicherheit"), (int, float)) else 1

        # Wortgrenzen: Das Kind hat EIN Zielwort auf mehrere Wörter verteilt.
        nummern = z.get("nummern")
        if isinstance(nummern, list) and len(nummern) > 1:
            toks = [tok_s[n] for n in nummern if isinstance(n, int) and 0 <= n < len(tok_s)]
            if (len(toks) != len(nummern)
                    or normalisieren("".join(t["wort"] for t in toks)) != normalisieren(ziel)):
                verworfen.append({**z, "grund": "Die genannten Wortnummern ergeben zusammen nicht die Zielform"})
                continue
            teile = [t["wort"] for t in toks]
            for e in wortgrenzen_ergebnis(teile, ziel, lexikon):
                festhalten(e, toks[0], " ".join(teile), ziel, sicherheit)
            for t in toks:
                abdeckung[t["index"]]["status"] = "fehler"
            continue

        tok = finde(z)
        if tok is None:
            verworfen.append({**z, "grund": "Originalform steht nicht im Text"}); continue

        # Umgekehrter Fall: mehrere Zielwörter zusammengezogen.
        if re.search(r"\s", ziel):
            if normalisieren(tok["wort"]) != normalisieren(re.sub(r"\s+", "", ziel)):
                verworfen.append({**z, "grund": "Zielform mit Leerzeichen passt nicht zum zusammengeschriebenen Wort"})
                continue
            festhalten(zusammenschreibung_ereignis(tok["wort"], ziel), tok, tok["wort"], ziel, sicherheit)
            abdeckung[tok["index"]]["status"] = "fehler"
            continue

        for e in klassifiziere_wort(tok["wort"], ziel, lexikon)["ereignisse"]:
            festhalten(e, tok, tok["wort"], ziel, sicherheit)
        abdeckung[tok["index"]]["status"] = "fehler"

    return {"ereignisse": ereignisse, "abdeckung": abdeckung, "verworfen": verworfen}


# ---------------------------------------------------- Goldstandard-Tests

GOLDSTANDARD: list[dict[str, Any]] = [
    {"s": "komen", "t": "kommen", "erwartet": ["07"], "quelle": "§19"},
    {"s": "Fahrad", "t": "Fahrrad", "erwartet": ["29"], "quelle": "§19"},
    {"s": "faren", "t": "fahren", "erwartet": ["09"], "quelle": "§19"},
    {"s": "habn", "t": "haben", "erwartet": ["31"], "quelle": "§19"},
    {"s": "kallt", "t": "kalt", "erwartet": ["08"], "quelle": "§19"},
    {"s": "Tall", "t": "Tal", "erwartet": ["11"], "quelle": "§19"},
    {"s": "frohr", "t": "fror", "erwartet": ["10"], "quelle": "§19"},
    {"s": "Wiend", "t": "Wind", "erwartet": ["12"], "quelle": "§19"},
    {"s": "Hende", "t": "Hände", "erwartet": ["17"], "quelle": "§19"},
    {"s": "jewals", "t": "jeweils", "erwartet": ["34"], "quelle": "§19"},
    {"s": "Korp", "t": "Korb", "erwartet": ["19"], "quelle": "§19"},
    {"s": "liede", "t": "liebe", "erwartet": ["33"], "quelle": "§19"},
    {"s": "Fogel", "t": "Vogel", "erwartet": ["23"], "quelle": "§19"},
    {"s": "Wase", "t": "Vase", "erwartet": ["25"], "quelle": "§19"},
    {"s": "lustich", "t": "lustig", "erwartet": ["27"], "quelle": "§19"},
    {"s": "Klatz", "t": "Platz", "erwartet": ["33"], "quelle": "§19"},
    {"s": "Graten", "t": "Garten", "erwartet": ["35"], "quelle": "§19"},
    {"s": "fuhrte", "t": "führte", "erwartet": ["36"], "quelle": "§19"},
    {"s": "Fus", "t": "Fuss", "erwartet": ["13"], "quelle": "A.1"},
    {"s": "Strase", "t": "Strasse", "erwartet": ["13"], "quelle": "A.1"},
    {"s": "heisen", "t": "heissen", "erwartet": ["13"], "quelle": "A.1"},
    {"s": "gros", "t": "gross", "erwartet": ["13"], "quelle": "A.1"},
    {"s": "Preisse", "t": "Preise", "erwartet": ["15"], "quelle": "A.1"},
    {"s": "Häusser", "t": "Häuser", "erwartet": ["15"], "quelle": "A.1"},
    {"s": "musen", "t": "müssen", "erwartet": ["36", "07"], "quelle": "A.4"},
    {"s": "Buss", "t": "Bus", "erwartet": ["08"], "quelle": "A.4"},
    {"s": "warscheinlich", "t": "wahrscheinlich", "erwartet": ["09"], "quelle": "Bau-Prompt §14"},
    {"s": "dan", "t": "dann", "erwartet": ["07"], "quelle": "Bau-Prompt §14"},
    {"s": "jetz", "t": "jetzt", "erwartet": ["29"], "quelle": "Bau-Prompt §14"},
    {"s": "zusamen", "t": "zusammen", "erwartet": ["07"], "quelle": "§1"},
    {"s": "libe", "t": "liebe", "erwartet": ["09"], "quelle": "§1"},
    {"s": "paken", "t": "packen", "erwartet": ["07"], "quelle": "§1"},
    {"s": "Kaze", "t": "Katze", "erwartet": ["07"], "quelle": "§1"},
    {"s": "sofor", "t": "sofort", "erwartet": ["29"], "quelle": "§1"},
    {"s": "haus", "t": "Haus", "erwartet": ["01"], "quelle": "§5"},
    {"s": "Kalt", "t": "kalt", "erwartet": ["02"], "quelle": "§5"},
    {"s": "HaUs", "t": "Haus", "erwartet": ["03"], "quelle": "§5"},
    {"s": "beckommen", "t": "bekommen", "erwartet": ["11"], "quelle": "§6"},
    {"s": "scharff", "t": "scharf", "erwartet": ["11"], "quelle": "§6"},
    {"s": "hatt", "t": "hat", "erwartet": ["08"], "quelle": "§6"},
    {"s": "Schu", "t": "Schuh", "erwartet": ["09"], "quelle": "§6"},
    {"s": "Schuhle", "t": "Schule", "erwartet": ["10"], "quelle": "§6"},
    {"s": "jätzt", "t": "jetzt", "erwartet": ["18"], "quelle": "§7"},
    {"s": "Läute", "t": "Leute", "erwartet": ["18"], "quelle": "§7"},
    {"s": "Beume", "t": "Bäume", "erwartet": ["17"], "quelle": "§7"},
    {"s": "Gescheft", "t": "Geschäft", "erwartet": ["17"], "quelle": "§7"},
    {"s": "balt", "t": "bald", "erwartet": ["19"], "quelle": "§7"},
    {"s": "wek", "t": "weg", "erwartet": ["19"], "quelle": "§7"},
    {"s": "Gesundheid", "t": "Gesundheit", "erwartet": ["20"], "quelle": "§7"},
    {"s": "Quarg", "t": "Quark", "erwartet": ["20"], "quelle": "§7"},
    {"s": "ferlieren", "t": "verlieren", "erwartet": ["23"], "quelle": "§8"},
    {"s": "vertig", "t": "fertig", "erwartet": ["24"], "quelle": "§8"},
    {"s": "vie", "t": "wie", "erwartet": ["26"], "quelle": "§8"},
    {"s": "schvierig", "t": "schwierig", "erwartet": ["26"], "quelle": "§8"},
    {"s": "Honich", "t": "Honig", "erwartet": ["27"], "quelle": "§8"},
    {"s": "Teppig", "t": "Teppich", "erwartet": ["28"], "quelle": "§8"},
    {"s": "fröhlig", "t": "fröhlich", "erwartet": ["28"], "quelle": "§8"},
    {"s": "nich", "t": "nicht", "erwartet": ["29"], "quelle": "§9"},
    {"s": "Geburstag", "t": "Geburtstag", "erwartet": ["29"], "quelle": "§9"},
    {"s": "Märdchen", "t": "Mädchen", "erwartet": ["30"], "quelle": "§9"},
    {"s": "artmen", "t": "atmen", "erwartet": ["30"], "quelle": "§9"},
    {"s": "schwierge", "t": "schwierige", "erwartet": ["31"], "quelle": "§9"},
    {"s": "weiel", "t": "weil", "erwartet": ["32"], "quelle": "§9"},
    {"s": "freundlech", "t": "freundlich", "erwartet": ["34"], "quelle": "§9"},
    {"s": "Gesundeiht", "t": "Gesundheit", "erwartet": ["35"], "quelle": "§9"},
    {"s": "gefahrlich", "t": "gefährlich", "erwartet": ["36"], "quelle": "§9"},
    {"s": "erkähltet", "t": "erkältet", "erwartet": ["12"], "quelle": "§6"},
    {"s": "Nus", "t": "Nuss", "erwartet": ["07"], "quelle": "Lexikon: u in Nuss ist kurz"},
    {"s": "Gose", "t": "Gosse", "erwartet": ["needs_context"], "quelle": "Bau-Prompt Stufe 2 (07/13 → F1/F3, Wort nicht im Lexikon)"},
    {"s": "gehrn", "t": "gern", "erwartet": ["resolved_by_area"], "quelle": "Ergänzung C.1 (10/12 → beide F2; vor r+Konsonant nicht ablesbar)"},
    # --- Grenzfallkorpus: je Fall die Regel, aus der die Erwartung folgt ------
    {"s": 'garten', "t": 'Garten', "erwartet": ['01'], "quelle": 'Korpus: Nomen klein: 01'},
    {"s": 'Schnell', "t": 'schnell', "erwartet": ['02'], "quelle": 'Korpus: Adjektiv gross: 02'},
    {"s": 'GArten', "t": 'Garten', "erwartet": ['03'], "quelle": 'Korpus: Grossbuchstabe im Wort: 03'},
    {"s": 'gARTEN', "t": 'Garten', "erwartet": ['01', '03'], "quelle": 'Korpus: Anfang klein und Binnenmajuskel: 01 + 03'},
    {"s": 'hunt', "t": 'Hund', "erwartet": ['01', '19'], "quelle": 'Korpus: zwei unabhängige Fehler'},
    {"s": 'man', "t": 'Mann', "erwartet": ['01', '07'], "quelle": 'Korpus: man/Mann: Grossschreibung und Schärfung'},
    {"s": 'Mann', "t": 'man', "erwartet": ['02', '08'], "quelle": 'Korpus: Mann/man: Kleinschreibung und Einfachschreibung'},
    {"s": 'hute', "t": 'Hüte', "erwartet": ['01', '36'], "quelle": 'Korpus: Grossschreibung und Umlautbezeichnung'},
    {"s": 'Sone', "t": 'Sonne', "erwartet": ['07'], "quelle": 'Korpus: Kurzvokal o'},
    {"s": 'Buter', "t": 'Butter', "erwartet": ['07'], "quelle": 'Korpus: Kurzvokal u'},
    {"s": 'Hamer', "t": 'Hammer', "erwartet": ['07'], "quelle": 'Korpus: Kurzvokal a'},
    {"s": 'Somer', "t": 'Sommer', "erwartet": ['07'], "quelle": 'Korpus: Kurzvokal o'},
    {"s": 'Kase', "t": 'Kasse', "erwartet": ['07'], "quelle": 'Korpus: Kurzvokal a – ss ist hier Schärfung, nicht 13'},
    {"s": 'Klase', "t": 'Klasse', "erwartet": ['07'], "quelle": 'Korpus: Kurzvokal a'},
    {"s": 'Tase', "t": 'Tasse', "erwartet": ['07'], "quelle": 'Korpus: Kurzvokal a'},
    {"s": 'Waser', "t": 'Wasser', "erwartet": ['07'], "quelle": 'Korpus: Kurzvokal a'},
    {"s": 'Meser', "t": 'Messer', "erwartet": ['07'], "quelle": 'Korpus: Kurzvokal e'},
    {"s": 'beser', "t": 'besser', "erwartet": ['07'], "quelle": 'Korpus: Kurzvokal e'},
    {"s": 'wisen', "t": 'wissen', "erwartet": ['07'], "quelle": 'Korpus: Kurzvokal i'},
    {"s": 'lasen', "t": 'lassen', "erwartet": ['07'], "quelle": 'Korpus: Kurzvokal a (lasen ist auch ein Wort – die Form entscheidet)'},
    {"s": 'nas', "t": 'nass', "erwartet": ['07'], "quelle": 'Korpus: Kurzvokal a'},
    {"s": 'Kus', "t": 'Kuss', "erwartet": ['07'], "quelle": 'Korpus: Kurzvokal u'},
    {"s": 'Flus', "t": 'Fluss', "erwartet": ['07'], "quelle": 'Korpus: Kurzvokal u – nicht 13'},
    {"s": 'Schlos', "t": 'Schloss', "erwartet": ['07'], "quelle": 'Korpus: Kurzvokal o'},
    {"s": 'gewis', "t": 'gewiss', "erwartet": ['07'], "quelle": 'Korpus: Kurzvokal i'},
    {"s": 'Kisen', "t": 'Kissen', "erwartet": ['07'], "quelle": 'Korpus: Kurzvokal i'},
    {"s": 'Schlüsel', "t": 'Schlüssel', "erwartet": ['07'], "quelle": 'Korpus: Kurzvokal ü'},
    {"s": 'esen', "t": 'essen', "erwartet": ['07'], "quelle": 'Korpus: Kurzvokal e'},
    {"s": 'müsen', "t": 'müssen', "erwartet": ['07'], "quelle": 'Korpus: Kurzvokal ü'},
    {"s": 'das', "t": 'dass', "erwartet": ['07'], "quelle": 'Korpus: Kurzvokal a; Ursache grammatisch'},
    {"s": 'Zuker', "t": 'Zucker', "erwartet": ['07'], "quelle": 'Korpus: Manual §6.1'},
    {"s": 'Bäker', "t": 'Bäcker', "erwartet": ['07'], "quelle": 'Korpus: Kurzvokal ä'},
    {"s": 'Blik', "t": 'Blick', "erwartet": ['07'], "quelle": 'Korpus: k für ck'},
    {"s": 'Haken', "t": 'Hacken', "erwartet": ['07'], "quelle": 'Korpus: Zielwort Hacken hat Kurzvokal (Haken ist ein anderes Wort)'},
    {"s": 'Kazze', "t": 'Katze', "erwartet": ['07'], "quelle": 'Korpus: Manual §6.1 nennt *Kazze → Katze unter 07: Schärfung erkannt, Zeichen falsch'},
    {"s": 'Zukker', "t": 'Zucker', "erwartet": ['07'], "quelle": 'Korpus: analog Kazze: Verdoppelung erkannt, ck nicht gewählt'},
    {"s": 'Karote', "t": 'Karotte', "erwartet": ['07'], "quelle": 'Korpus: Fremdwort mit Kurzvokal o vor tt'},
    {"s": 'Renrad', "t": 'Rennrad', "erwartet": ['07'], "quelle": 'Korpus: nn gehört zur Schärfung in renn-, keine Morphemfuge'},
    {"s": 'drausen', "t": 'draussen', "erwartet": ['13'], "quelle": 'Korpus: Diphthong au'},
    {"s": 'Spies', "t": 'Spiess', "erwartet": ['13'], "quelle": 'Korpus: Langvokal ie'},
    {"s": 'Grus', "t": 'Gruss', "erwartet": ['13'], "quelle": 'Korpus: Langvokal u'},
    {"s": 'weis', "t": 'weiss', "erwartet": ['13'], "quelle": 'Korpus: Diphthong ei'},
    {"s": 'Fleis', "t": 'Fleiss', "erwartet": ['13'], "quelle": 'Korpus: Diphthong ei'},
    {"s": 'reisen', "t": 'reissen', "erwartet": ['13'], "quelle": 'Korpus: Diphthong ei (reisen ist ein anderes Wort – die Form entscheidet)'},
    {"s": 'beisen', "t": 'beissen', "erwartet": ['13'], "quelle": 'Korpus: Diphthong ei'},
    {"s": 'schliesen', "t": 'schliessen', "erwartet": ['13'], "quelle": 'Korpus: Langvokal ie'},
    {"s": 'Schweis', "t": 'Schweiss', "erwartet": ['13'], "quelle": 'Korpus: Diphthong ei'},
    {"s": 'süs', "t": 'süss', "erwartet": ['13'], "quelle": 'Korpus: Langvokal ü'},
    {"s": 'Stos', "t": 'Stoss', "erwartet": ['13'], "quelle": 'Korpus: Langvokal o'},
    {"s": 'Mas', "t": 'Mass', "erwartet": ['13'], "quelle": 'Korpus: Langvokal a (das Mass)'},
    {"s": 'Spas', "t": 'Spass', "erwartet": ['13'], "quelle": 'Korpus: Langvokal a'},
    {"s": 'Fusbal', "t": 'Fussball', "erwartet": ['13', '07'], "quelle": 'Korpus: zwei Stellen: Langvokal u (13) und Kurzvokal a (07)'},
    {"s": 'Reiss', "t": 'Reis', "erwartet": ['15'], "quelle": 'Korpus: Diphthong ei'},
    {"s": 'Eiss', "t": 'Eis', "erwartet": ['15'], "quelle": 'Korpus: Diphthong ei'},
    {"s": 'Kreiss', "t": 'Kreis', "erwartet": ['15'], "quelle": 'Korpus: Diphthong ei'},
    {"s": 'Hasse', "t": 'Hase', "erwartet": ['15'], "quelle": 'Korpus: Langvokal a'},
    {"s": 'Nasse', "t": 'Nase', "erwartet": ['15'], "quelle": 'Korpus: Langvokal a'},
    {"s": 'Rosse', "t": 'Rose', "erwartet": ['15'], "quelle": 'Korpus: Langvokal o'},
    {"s": 'lessen', "t": 'lesen', "erwartet": ['15'], "quelle": 'Korpus: Langvokal e'},
    {"s": 'Glass', "t": 'Glas', "erwartet": ['15'], "quelle": 'Korpus: Langvokal a – nicht 08'},
    {"s": 'Grass', "t": 'Gras', "erwartet": ['15'], "quelle": 'Korpus: Langvokal a'},
    {"s": 'Riesse', "t": 'Riese', "erwartet": ['15'], "quelle": 'Korpus: Langvokal ie'},
    {"s": 'Hauss', "t": 'Haus', "erwartet": ['15'], "quelle": 'Korpus: Diphthong au'},
    {"s": 'Mauss', "t": 'Maus', "erwartet": ['15'], "quelle": 'Korpus: Diphthong au'},
    {"s": 'Gemüsse', "t": 'Gemüse', "erwartet": ['15'], "quelle": 'Korpus: Langvokal ü'},
    {"s": 'Kesse', "t": 'Käse', "erwartet": ['17', '15'], "quelle": 'Korpus: e für ä (17) und ss nach langem ä (15)'},
    {"s": 'mitt', "t": 'mit', "erwartet": ['08'], "quelle": 'Korpus: Kurzvokal i'},
    {"s": 'ann', "t": 'an', "erwartet": ['08'], "quelle": 'Korpus: Kurzvokal a'},
    {"s": 'umm', "t": 'um', "erwartet": ['08'], "quelle": 'Korpus: Kurzvokal u'},
    {"s": 'dass', "t": 'das', "erwartet": ['08'], "quelle": 'Korpus: Kurzvokal a; Ursache grammatisch'},
    {"s": 'Wurrst', "t": 'Wurst', "erwartet": ['08'], "quelle": 'Korpus: rr steht direkt nach dem Kurzvokal u – 08, nicht 11'},
    {"s": 'Hannd', "t": 'Hand', "erwartet": ['08'], "quelle": 'Korpus: nn direkt nach Kurzvokal'},
    {"s": 'Lammpe', "t": 'Lampe', "erwartet": ['08'], "quelle": 'Korpus: mm direkt nach Kurzvokal'},
    {"s": 'kamm', "t": 'kam', "erwartet": ['11'], "quelle": 'Korpus: Langvokal a'},
    {"s": 'Kartte', "t": 'Karte', "erwartet": ['11'], "quelle": 'Korpus: tt steht nach dem Konsonanten r'},
    {"s": 'Holtz', "t": 'Holz', "erwartet": ['11'], "quelle": 'Korpus: tz nach Konsonant l'},
    {"s": 'kranck', "t": 'krank', "erwartet": ['11'], "quelle": 'Korpus: ck nach Konsonant n'},
    {"s": 'Banck', "t": 'Bank', "erwartet": ['11'], "quelle": 'Korpus: ck nach Konsonant n'},
    {"s": 'Weitzen', "t": 'Weizen', "erwartet": ['11'], "quelle": 'Korpus: tz nach Diphthong ei'},
    {"s": 'Kreutz', "t": 'Kreuz', "erwartet": ['11'], "quelle": 'Korpus: tz nach Diphthong eu'},
    {"s": 'Schmertz', "t": 'Schmerz', "erwartet": ['11'], "quelle": 'Korpus: tz nach Konsonant r'},
    {"s": 'Hacken', "t": 'Haken', "erwartet": ['11'], "quelle": 'Korpus: ck nach Langvokal a'},
    {"s": 'Tommate', "t": 'Tomate', "erwartet": ['08'], "quelle": 'Korpus: das o vor mm ist unbetont und kurz – 08'},
    {"s": 'anehmen', "t": 'annehmen', "erwartet": ['29'], "quelle": 'Korpus: Präfix an|nehmen'},
    {"s": 'aufallen', "t": 'auffallen', "erwartet": ['29'], "quelle": 'Korpus: Präfix auf|fallen'},
    {"s": 'miteilen', "t": 'mitteilen', "erwartet": ['29'], "quelle": 'Korpus: Präfix mit|teilen'},
    {"s": 'verückt', "t": 'verrückt', "erwartet": ['29'], "quelle": 'Korpus: Präfix ver|rückt'},
    {"s": 'ereichen', "t": 'erreichen', "erwartet": ['29'], "quelle": 'Korpus: Präfix er|reichen'},
    {"s": 'Vorat', "t": 'Vorrat', "erwartet": ['29'], "quelle": 'Korpus: Präfix vor|rat'},
    {"s": 'Schiffahrt', "t": 'Schifffahrt', "erwartet": ['29'], "quelle": 'Korpus: Morphemfuge Schiff|fahrt'},
    {"s": 'Zan', "t": 'Zahn', "erwartet": ['09'], "quelle": 'Korpus: Dehnungs-h fehlt'},
    {"s": 'Bot', "t": 'Boot', "erwartet": ['09'], "quelle": 'Korpus: Vokalverdoppelung fehlt'},
    {"s": 'Wise', "t": 'Wiese', "erwartet": ['09'], "quelle": 'Korpus: ie fehlt'},
    {"s": 'Se', "t": 'See', "erwartet": ['09'], "quelle": 'Korpus: Vokalverdoppelung'},
    {"s": 'Sal', "t": 'Saal', "erwartet": ['09'], "quelle": 'Korpus: Vokalverdoppelung'},
    {"s": 'Ur', "t": 'Uhr', "erwartet": ['09'], "quelle": 'Korpus: Dehnungs-h'},
    {"s": 'Or', "t": 'Ohr', "erwartet": ['09'], "quelle": 'Korpus: Dehnungs-h'},
    {"s": 'Sig', "t": 'Sieg', "erwartet": ['09'], "quelle": 'Korpus: ie fehlt'},
    {"s": 'Spil', "t": 'Spiel', "erwartet": ['09'], "quelle": 'Korpus: ie fehlt'},
    {"s": 'Libe', "t": 'Liebe', "erwartet": ['09'], "quelle": 'Korpus: ie fehlt'},
    {"s": 'telefoniren', "t": 'telefonieren', "erwartet": ['09'], "quelle": 'Korpus: ie in -ieren'},
    {"s": 'Bine', "t": 'Biene', "erwartet": ['09'], "quelle": 'Korpus: ie fehlt'},
    {"s": 'Papir', "t": 'Papier', "erwartet": ['09'], "quelle": 'Korpus: ie fehlt'},
    {"s": 'wider', "t": 'wieder', "erwartet": ['09'], "quelle": 'Korpus: ie fehlt (wider ist ein anderes Wort)'},
    {"s": 'Zil', "t": 'Ziel', "erwartet": ['09'], "quelle": 'Korpus: ie fehlt'},
    {"s": 'geen', "t": 'gehen', "erwartet": ['09'], "quelle": 'Korpus: h als Längen-/Silbenzeichen fehlt'},
    {"s": 'Schue', "t": 'Schuhe', "erwartet": ['09'], "quelle": 'Korpus: Dehnungs-h in Schuh|e fehlt'},
    {"s": 'ruig', "t": 'ruhig', "erwartet": ['09'], "quelle": 'Korpus: Dehnungs-h fehlt'},
    {"s": 'Reie', "t": 'Reihe', "erwartet": ['29'], "quelle": 'Korpus: h nach Diphthong ist kein Längenzeichen, sondern ein Konsonantenzeichen'},
    {"s": 'Tuhr', "t": 'Tur', "erwartet": ['10'], "quelle": 'Korpus: Manual §19'},
    {"s": 'Tieger', "t": 'Tiger', "erwartet": ['10'], "quelle": 'Korpus: i ist lang, aber ohne ie geschrieben'},
    {"s": 'Maschiene', "t": 'Maschine', "erwartet": ['10'], "quelle": 'Korpus: i lang ohne ie – 10, nicht 12'},
    {"s": 'Kieno', "t": 'Kino', "erwartet": ['10'], "quelle": 'Korpus: i lang'},
    {"s": 'Musiek', "t": 'Musik', "erwartet": ['10'], "quelle": 'Korpus: i lang'},
    {"s": 'Biebel', "t": 'Bibel', "erwartet": ['10'], "quelle": 'Korpus: i lang'},
    {"s": 'nähmlich', "t": 'nämlich', "erwartet": ['10'], "quelle": 'Korpus: ä lang, h überflüssig'},
    {"s": 'Tohr', "t": 'Tor', "erwartet": ['10'], "quelle": 'Korpus: o lang'},
    {"s": 'Tühr', "t": 'Tür', "erwartet": ['10'], "quelle": 'Korpus: ü lang'},
    {"s": 'Nahme', "t": 'Name', "erwartet": ['10'], "quelle": 'Korpus: a lang'},
    {"s": 'Baahn', "t": 'Bahn', "erwartet": ['10'], "quelle": 'Korpus: Manual §6'},
    {"s": 'wieder', "t": 'wider', "erwartet": ['10'], "quelle": 'Korpus: i in wider ist lang, ie überflüssig'},
    {"s": 'Tiesch', "t": 'Tisch', "erwartet": ['12'], "quelle": 'Korpus: Manual §6'},
    {"s": 'Kiend', "t": 'Kind', "erwartet": ['12'], "quelle": 'Korpus: i kurz'},
    {"s": 'Fiesch', "t": 'Fisch', "erwartet": ['12'], "quelle": 'Korpus: i kurz'},
    {"s": 'Kahrte', "t": 'Karte', "erwartet": ['12'], "quelle": 'Korpus: a kurz'},
    {"s": 'Wahld', "t": 'Wald', "erwartet": ['12'], "quelle": 'Korpus: a kurz'},
    {"s": 'Sohne', "t": 'Sonne', "erwartet": ['12', '07'], "quelle": 'Korpus: h bei Kurzvokal (12) und fehlende Verdoppelung (07)'},
    {"s": 'Beren', "t": 'Bären', "erwartet": ['17'], "quelle": 'Korpus: Manual §7.2'},
    {"s": 'Heuser', "t": 'Häuser', "erwartet": ['17'], "quelle": 'Korpus: eu für äu'},
    {"s": 'Kese', "t": 'Käse', "erwartet": ['17'], "quelle": 'Korpus: e für ä – auch ohne Ableitungsbasis ist die Form 17'},
    {"s": 'Setze', "t": 'Sätze', "erwartet": ['17'], "quelle": 'Korpus: e für ä (Setze ist ein anderes Wort)'},
    {"s": 'spet', "t": 'spät', "erwartet": ['17'], "quelle": 'Korpus: e für ä, nicht ableitbar – trotzdem 17'},
    {"s": 'Ber', "t": 'Bär', "erwartet": ['17'], "quelle": 'Korpus: e für ä, nicht ableitbar – trotzdem 17'},
    {"s": 'Ältern', "t": 'Eltern', "erwartet": ['18'], "quelle": 'Korpus: ä für e – die Ableitung von alt führt in die Irre'},
    {"s": 'Bärg', "t": 'Berg', "erwartet": ['18'], "quelle": 'Korpus: ä für e'},
    {"s": 'Fräund', "t": 'Freund', "erwartet": ['18'], "quelle": 'Korpus: äu für eu'},
    {"s": 'Bucher', "t": 'Bücher', "erwartet": ['36'], "quelle": 'Korpus: Manual §19'},
    {"s": 'Hande', "t": 'Hände', "erwartet": ['36'], "quelle": 'Korpus: a für ä: Umlautbezeichnung fehlt'},
    {"s": 'schon', "t": 'schön', "erwartet": ['36'], "quelle": 'Korpus: o für ö (schon ist ein anderes Wort)'},
    {"s": 'Turen', "t": 'Türen', "erwartet": ['36'], "quelle": 'Korpus: u für ü'},
    {"s": 'Apfel', "t": 'Äpfel', "erwartet": ['36'], "quelle": 'Korpus: a für ä (Apfel ist ein anderes Wort)'},
    {"s": 'Mutter', "t": 'Mütter', "erwartet": ['36'], "quelle": 'Korpus: u für ü'},
    {"s": 'Baume', "t": 'Bäume', "erwartet": ['36'], "quelle": 'Korpus: au für äu'},
    {"s": 'Büch', "t": 'Buch', "erwartet": ['36'], "quelle": 'Korpus: ü für u: Umlautbezeichnung falsch gesetzt'},
    {"s": 'Finster', "t": 'Fenster', "erwartet": ['34'], "quelle": 'Korpus: Manual §9'},
    {"s": 'Vugel', "t": 'Vogel', "erwartet": ['34'], "quelle": 'Korpus: u für o'},
    {"s": 'Sunne', "t": 'Sonne', "erwartet": ['34'], "quelle": 'Korpus: u für o'},
    {"s": 'Kend', "t": 'Kind', "erwartet": ['34'], "quelle": 'Korpus: e für i'},
    {"s": 'Wold', "t": 'Wald', "erwartet": ['34'], "quelle": 'Korpus: o für a'},
    {"s": 'öber', "t": 'über', "erwartet": ['34'], "quelle": 'Korpus: ö für ü: kein Umlautpaar'},
    {"s": 'Loite', "t": 'Leute', "erwartet": ['34'], "quelle": 'Korpus: oi für eu: EIN Vokalgraphem ersetzt'},
    {"s": 'Hunt', "t": 'Hund', "erwartet": ['19'], "quelle": 'Korpus: Manual §7.3'},
    {"s": 'Walt', "t": 'Wald', "erwartet": ['19'], "quelle": 'Korpus: d im Auslaut'},
    {"s": 'Kint', "t": 'Kind', "erwartet": ['19'], "quelle": 'Korpus: d im Auslaut'},
    {"s": 'Berk', "t": 'Berg', "erwartet": ['19'], "quelle": 'Korpus: g im Auslaut'},
    {"s": 'Tak', "t": 'Tag', "erwartet": ['19'], "quelle": 'Korpus: g im Auslaut'},
    {"s": 'Rat', "t": 'Rad', "erwartet": ['19'], "quelle": 'Korpus: d im Auslaut (Rat ist ein anderes Wort)'},
    {"s": 'Zuk', "t": 'Zug', "erwartet": ['19'], "quelle": 'Korpus: g im Auslaut'},
    {"s": 'gelp', "t": 'gelb', "erwartet": ['19'], "quelle": 'Korpus: b im Auslaut'},
    {"s": 'Mätchen', "t": 'Mädchen', "erwartet": ['19'], "quelle": 'Korpus: d vor ch: Silbenrand'},
    {"s": 'unt', "t": 'und', "erwartet": ['19'], "quelle": 'Korpus: d im Auslaut'},
    {"s": 'sint', "t": 'sind', "erwartet": ['19'], "quelle": 'Korpus: d im Auslaut'},
    {"s": 'Gelt', "t": 'Geld', "erwartet": ['19'], "quelle": 'Korpus: d im Auslaut'},
    {"s": 'gipt', "t": 'gibt', "erwartet": ['19'], "quelle": 'Korpus: b vor t: Silbenrand'},
    {"s": 'lept', "t": 'lebt', "erwartet": ['19'], "quelle": 'Korpus: b vor t'},
    {"s": 'Herpst', "t": 'Herbst', "erwartet": ['19'], "quelle": 'Korpus: b vor s'},
    {"s": 'Opst', "t": 'Obst', "erwartet": ['19'], "quelle": 'Korpus: b vor s'},
    {"s": 'Fahrrat', "t": 'Fahrrad', "erwartet": ['19'], "quelle": 'Korpus: d im Auslaut'},
    {"s": 'Hunte', "t": 'Hunde', "erwartet": ['33'], "quelle": 'Korpus: d im Silbenanlaut – nicht am Silbenrand, daher 33 (Manual §7.3)'},
    {"s": 'Obsd', "t": 'Obst', "erwartet": ['20'], "quelle": 'Korpus: Manual §7'},
    {"s": 'Studend', "t": 'Student', "erwartet": ['20'], "quelle": 'Korpus: d für t im Auslaut'},
    {"s": 'Werg', "t": 'Werk', "erwartet": ['20'], "quelle": 'Korpus: g für k im Auslaut'},
    {"s": 'Bladd', "t": 'Blatt', "erwartet": ['20'], "quelle": 'Korpus: dd für tt im Auslaut: Verdoppelung bleibt, Konsonant falsch'},
    {"s": 'wenich', "t": 'wenig', "erwartet": ['27'], "quelle": 'Korpus: -ig → -ich'},
    {"s": 'Könich', "t": 'König', "erwartet": ['27'], "quelle": 'Korpus: -ig → -ich'},
    {"s": 'richtich', "t": 'richtig', "erwartet": ['27'], "quelle": 'Korpus: -ig → -ich'},
    {"s": 'Zuch', "t": 'Zug', "erwartet": ['27'], "quelle": 'Korpus: ch für g im Silbenende'},
    {"s": 'Berch', "t": 'Berg', "erwartet": ['27'], "quelle": 'Korpus: ch für g im Silbenende'},
    {"s": 'sachen', "t": 'sagen', "erwartet": ['33'], "quelle": 'Korpus: ch für g im Silbenanlaut – nicht Silbenende, daher 33'},
    {"s": 'endlig', "t": 'endlich', "erwartet": ['28'], "quelle": 'Korpus: -ich → -ig'},
    {"s": 'mig', "t": 'mich', "erwartet": ['28'], "quelle": 'Korpus: g für ch im Silbenende'},
    {"s": 'Fater', "t": 'Vater', "erwartet": ['23'], "quelle": 'Korpus: Manual §19'},
    {"s": 'fon', "t": 'von', "erwartet": ['23'], "quelle": 'Korpus: Merkwort'},
    {"s": 'for', "t": 'vor', "erwartet": ['23'], "quelle": 'Korpus: Merkwort'},
    {"s": 'fiel', "t": 'viel', "erwartet": ['23'], "quelle": 'Korpus: Merkwort (fiel ist ein anderes Wort)'},
    {"s": 'Wulkan', "t": 'Vulkan', "erwartet": ['25'], "quelle": 'Korpus: v = /v/'},
    {"s": 'Wideo', "t": 'Video', "erwartet": ['25'], "quelle": 'Korpus: v = /v/'},
    {"s": 'Willa', "t": 'Villa', "erwartet": ['25'], "quelle": 'Korpus: v = /v/'},
    {"s": 'Wogel', "t": 'Vogel', "erwartet": ['33'], "quelle": 'Korpus: w für v bei Lautwert /f/: 25 greift nicht, also 33'},
    {"s": 'Visch', "t": 'Fisch', "erwartet": ['24'], "quelle": 'Korpus: v für f'},
    {"s": 'vallen', "t": 'fallen', "erwartet": ['24'], "quelle": 'Korpus: v für f'},
    {"s": 'Vreund', "t": 'Freund', "erwartet": ['24'], "quelle": 'Korpus: v für f'},
    {"s": 'Vasser', "t": 'Wasser', "erwartet": ['26'], "quelle": 'Korpus: v für w'},
    {"s": 'vir', "t": 'wir', "erwartet": ['26'], "quelle": 'Korpus: v für w'},
    {"s": 'venn', "t": 'wenn', "erwartet": ['26'], "quelle": 'Korpus: v für w'},
    {"s": 'Vald', "t": 'Wald', "erwartet": ['26'], "quelle": 'Korpus: v für w'},
    {"s": 'Sule', "t": 'Schule', "erwartet": ['29'], "quelle": 'Korpus: Manual §9'},
    {"s": 'Blmen', "t": 'Blumen', "erwartet": ['31'], "quelle": 'Korpus: Manual §9'},
    {"s": 'komn', "t": 'kommen', "erwartet": ['07', '31'], "quelle": 'Korpus: m für mm (07) und e der Endung fehlt (31)'},
    {"s": 'Kinider', "t": 'Kinder', "erwartet": ['32'], "quelle": 'Korpus: Manual §9'},
    {"s": 'Hunrd', "t": 'Hund', "erwartet": ['30'], "quelle": 'Korpus: Manual §9'},
    {"s": 'gehe', "t": 'gehen', "erwartet": ['29'], "quelle": 'Korpus: n der Endung fehlt'},
    {"s": 'Fenser', "t": 'Fenster', "erwartet": ['29'], "quelle": 'Korpus: t fehlt'},
    {"s": 'Bort', "t": 'Brot', "erwartet": ['35'], "quelle": 'Korpus: Manual §9'},
    {"s": 'Wrot', "t": 'Wort', "erwartet": ['35'], "quelle": 'Korpus: Umstellung'},
    {"s": 'Apmel', "t": 'Ampel', "erwartet": ['35'], "quelle": 'Korpus: Umstellung'},
    {"s": 'Fahrat', "t": 'Fahrrad', "erwartet": ['29', '19'], "quelle": 'Korpus: Morphemfuge (29) und Auslaut (19)'},
    {"s": "Auto's", "t": 'Autos', "erwartet": ['37'], "quelle": 'Korpus: Apostroph: kein Graphem, Sonstiges'},
    {"s": 'Fysik', "t": 'Physik', "erwartet": ['37'], "quelle": 'Korpus: Fremdgraphem ph'},
    {"s": 'Teater', "t": 'Theater', "erwartet": ['37'], "quelle": 'Korpus: Fremdgraphem th'},
    {"s": 'Tema', "t": 'Thema', "erwartet": ['37'], "quelle": 'Korpus: Fremdgraphem th'},
    {"s": 'Apoteke', "t": 'Apotheke', "erwartet": ['37'], "quelle": 'Korpus: Fremdgraphem th'},
    {"s": 'Rytmus', "t": 'Rhythmus', "erwartet": ['37', '37'], "quelle": 'Korpus: rh und th: zwei Fremdgrapheme'},
    {"s": 'Sistem', "t": 'System', "erwartet": ['37'], "quelle": 'Korpus: Fremdgraphem y'},
    {"s": 'Tip', "t": 'Typ', "erwartet": ['37'], "quelle": 'Korpus: Fremdgraphem y'},
    {"s": 'Komputer', "t": 'Computer', "erwartet": ['37'], "quelle": 'Korpus: Fremdgraphem c'},
    {"s": 'Nazion', "t": 'Nation', "erwartet": ['37'], "quelle": 'Korpus: t = /ts/ in -tion'},
    {"s": 'Hekse', "t": 'Hexe', "erwartet": ['33'], "quelle": 'Korpus: ks für x: EIN Konsonantengraphem ersetzt'},
    {"s": 'Fuks', "t": 'Fuchs', "erwartet": ['33'], "quelle": 'Korpus: ks für chs: EIN Graphem ersetzt'},
    {"s": 'Fux', "t": 'Fuchs', "erwartet": ['33'], "quelle": 'Korpus: x für chs'},
    {"s": 'Sytem', "t": 'System', "erwartet": ['29'], "quelle": 'Korpus: s fehlt – kein Fremdgraphem betroffen, also gewöhnlich 29'},
]

GOLDSTANDARD_TEXT = [
    {"referenz": "Der Zahnarzt kam.", "schueler": "Der Zahn Arzt kam.", "erwartet": ["04"], "quelle": "§5.1"},
    {"referenz": "Der Zahnarzt kam.", "schueler": "Der Zahn arzt kam.", "erwartet": ["04", "01"], "quelle": "§5.1"},
    {"referenz": "Wir wollen weglaufen.", "schueler": "Wir wollen weg laufen.", "erwartet": ["04"], "quelle": "§5.2"},
    {"referenz": "Er will es vergraben.", "schueler": "Er will es ver graben.", "erwartet": ["06"], "quelle": "§5.2"},
    {"referenz": "Das ist zum Beispiel gut.", "schueler": "Das ist zumbeispiel gut.", "erwartet": ["05"], "quelle": "§5"},
    {"referenz": 'Wir müssen aufhören.', "schueler": 'Wir müssen auf hören.', "erwartet": ['04'], "quelle": 'Korpus: auf und hören beide selbstständig'},
    {"referenz": 'Das Schulhaus ist alt.', "schueler": 'Das Schul haus ist alt.', "erwartet": ['04', '01'], "quelle": 'Korpus: Kompositum'},
    {"referenz": 'Er ist gegangen.', "schueler": 'Er ist ge gangen.', "erwartet": ['06'], "quelle": 'Korpus: Präfix ge'},
    {"referenz": 'Das geht gar nicht.', "schueler": 'Das geht garnicht.', "erwartet": ['05'], "quelle": 'Korpus: zwei Wörter'},
    {"referenz": 'Das ist unmöglich.', "schueler": 'Das ist un möglich.', "erwartet": ['06'], "quelle": 'Korpus: Präfix un'},
    {"referenz": 'Meine Freundin kam.', "schueler": 'Meine Freund in kam.', "erwartet": ['06'], "quelle": 'Korpus: Suffix -in abgetrennt, obwohl «in» ein Wort ist'},
    {"referenz": 'Sei vorsichtig.', "schueler": 'Sei vor sichtig.', "erwartet": ['06'], "quelle": 'Korpus: «sichtig» ist unselbstständig'},
    {"referenz": 'Die Handschuhe sind neu.', "schueler": 'Die Hand schuhe sind neu.', "erwartet": ['04', '01'], "quelle": 'Korpus: Kompositum'},
]


def _erhalten(e: dict) -> str:
    return e["status"] if e["status"] in ("needs_context", "manual_review", "resolved_by_area") else (e["kategorie"] or e["status"])


def testlauf(lexikon: dict | None = None) -> list[dict]:
    lexikon = lexikon if lexikon is not None else VORGABE_LEXIKON
    aus = []
    for fall in GOLDSTANDARD:
        r = klassifiziere_wort(fall["s"], fall["t"], lexikon)
        for e in r["ereignisse"]:
            abschliessen(e, {"ziel": fall["t"]}, {"zielwortSicherheit": 1})
        erhalten = [_erhalten(e) for e in r["ereignisse"]]
        ok = len(fall["erwartet"]) == len(erhalten) and all(k in erhalten for k in fall["erwartet"])
        aus.append({**fall, "erhalten": erhalten, "ok": ok, "ereignisse": r["ereignisse"]})
    return aus


def testlauf_text(lexikon: dict | None = None) -> list[dict]:
    lexikon = lexikon if lexikon is not None else VORGABE_LEXIKON
    aus = []
    for fall in GOLDSTANDARD_TEXT:
        r = analysiere_diktat(fall["referenz"], fall["schueler"], lexikon)
        erhalten = [e["kategorie"] or e["status"] for e in r["ereignisse"]]
        ok = len(fall["erwartet"]) == len(erhalten) and all(k in erhalten for k in fall["erwartet"])
        aus.append({**fall, "erhalten": erhalten, "ok": ok})
    return aus
