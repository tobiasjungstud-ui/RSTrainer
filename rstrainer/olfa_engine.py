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

MEHRGRAPHEME = ["sch", "ch", "ck", "tz", "ie", "ah", "eh", "ih", "oh", "uh", "äh", "öh", "üh",
                "aa", "ee", "oo", "ei", "ai", "au", "eu", "äu", "pf", "qu", "ng", "nk", "ss"]
VOKALBUCHSTABEN = "aeiouäöüy"
DIPHTHONGE = {"ei", "ai", "au", "eu", "äu"}
LAENGENMARKER = {"ah": "a", "eh": "e", "ih": "i", "oh": "o", "uh": "u", "äh": "ä", "öh": "ö", "üh": "ü",
                 "aa": "a", "ee": "e", "oo": "o", "ie": "i"}
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
        if (letzt and len(letzt["g"]) == 1 and letzt["g"] == e["g"]
                and ist_konsonant_graphem(e["g"]) and (letzt["g"] + e["g"]) in VERDOPPELUNG):
            letzt["g"] = letzt["g"] + e["g"]
        else:
            verschmolzen.append({"g": e["g"], "at": e["at"]})
    return verschmolzen


def grapheme(wort: str) -> list[str]:
    return [x["g"] for x in segmentiere(wort)]


# ----------------------------------------- Damerau-Levenshtein-Alignment

def align(s: list[str], t: list[str]) -> tuple[list[dict[str, Any]], int]:
    n, m = len(s), len(t)
    D = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        D[i][0] = i
    for j in range(m + 1):
        D[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            kosten = 0 if s[i - 1] == t[j - 1] else 1
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
        elif i > 0 and j > 0 and s[i - 1] == t[j - 1] and D[i][j] == D[i - 1][j - 1]:
            ops.append({"op": "equal", "si": i - 1, "ti": j - 1, "s": s[i - 1], "t": t[j - 1]}); i -= 1; j -= 1
        elif i > 0 and j > 0 and D[i][j] == D[i - 1][j - 1] + 1:
            ops.append({"op": "sub", "si": i - 1, "ti": j - 1, "s": s[i - 1], "t": t[j - 1]}); i -= 1; j -= 1
        elif i > 0 and D[i][j] == D[i - 1][j] + 1:
            ops.append({"op": "ins", "si": i - 1, "ti": j, "s": s[i - 1], "t": None}); i -= 1
        else:
            ops.append({"op": "del", "si": i, "ti": j - 1, "s": None, "t": t[j - 1]}); j -= 1
    ops.reverse()
    return ops, D[n][m]


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


def vokalersatz(op: dict, lex: dict | None) -> dict:
    s, t = op["s"], op["t"]
    e = ereignis(studentGrapheme=s, targetGrapheme=t)
    grund_s, grund_t = LAENGENMARKER.get(s, s), LAENGENMARKER.get(t, t)
    if grund_s == grund_t:
        if t in LAENGENMARKER and s not in LAENGENMARKER:
            return markierung_fehlt(op)
        e["status"] = "needs_context"; e["kandidaten"] = ["34", "37"]; e["featureSource"] = "schreibung"
        e["reason"] = f"<{s}> statt <{t}>: gleicher Grundvokal, andere Längenmarkierung – weder 09 noch 10/12 sauber zuordenbar."
        return e
    um = umlaut_merkmal(lex)
    if (s, t) in {("e", "ä"), ("eu", "äu"), ("eh", "äh"), ("ee", "äh")}:
        e["kategorie"] = "17"; e["featureSource"] = um["quelle"]
        e["reason"] = f"<{s}> für <{t}>: Umlautschreibung nicht realisiert{' (Lexikon: Umlautwort)' if um['wert'] is True else ''}."
        _excl(e, "34", "e ↔ ä ist die spezifische Opposition 17 (Manual §7.2).")
        if um["wert"] is not True:
            e["status"] = "needs_context"; e["kandidaten"] = ["17", "34"]
            e["entscheidend"] = "Ist <ä/äu> im Zielwort eine Umlautschreibung (z. B. ableitbar: Hände ← Hand)?"
        return e
    if (s, t) in {("ä", "e"), ("äu", "eu"), ("äh", "eh")}:
        e["kategorie"] = "18"; e["featureSource"] = um["quelle"]
        e["reason"] = f"<{s}> für <{t}>: Umlautschreibung gesetzt, wo das Zielwort keinen Umlaut hat{' (Lexikon)' if um['wert'] is False else ''}."
        _excl(e, "34", "ä ↔ e ist die spezifische Opposition 18 (Manual §7.2).")
        if um["wert"] is not False:
            e["status"] = "needs_context"; e["kandidaten"] = ["18", "34"]
            e["entscheidend"] = "Hat das Zielwort an dieser Stelle tatsächlich ein e ohne Umlautbezug?"
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
    e = ereignis(studentGrapheme="", targetGrapheme=op["t"])
    if ist_vokal_graphem(op["t"]):
        e["kategorie"] = "31"; e["reason"] = f"Vokalgraphem <{op['t']}> fehlt – eine vokalische Einheit wurde ausgelassen."
        _excl(e, "09", "Es fehlt nicht nur eine Markierung, sondern der Vokal selbst.")
    else:
        e["kategorie"] = "29"; e["reason"] = f"Konsonantengraphem <{op['t']}> fehlt."
        _excl(e, "07", "Keine fehlende Verdoppelung, ein eigenständiges Graphem fehlt.")
    return e


def graphem_zuviel(op: dict) -> dict:
    e = ereignis(studentGrapheme=op["s"], targetGrapheme="")
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
        e = ereignis(studentGrapheme=s, targetGrapheme=t, kategorie="37")
        e["reason"] = f"<{s}> für <{t}>: Verdoppelung erkannt, aber mit falschem Zeichen."
        return e
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


def klassifiziere_wort(schueler: str, ziel: str, lexikon: dict | None = None,
                       erzwingen: bool = False) -> dict[str, Any]:
    lexikon = lexikon or {}
    lex = lexikon.get(ziel.lower())
    aus = gross_klein(schueler, ziel)
    s_seg, t_seg = segmentiere(schueler), segmentiere(ziel)
    if schueler.lower() == ziel.lower():
        return {"ereignisse": aus, "ops": [], "distanz": 0, "wortersetzung": False}
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


def ist_selbststaendig(teil: str) -> bool:
    return len(teil) >= 3 and teil.lower() not in UNSELBSTSTAENDIG


def wortgrenzen_ereignis(teile: list[str], ziel: str) -> dict:
    e = ereignis(studentGrapheme=" ".join(teile), targetGrapheme=ziel)
    if all(ist_selbststaendig(t) for t in teile):
        e["kategorie"] = "04"
        e["reason"] = f"«{' '.join(teile)}» statt «{ziel}»: Bestandteile getrennt, die zusammengeschrieben werden – beide könnten selbstständige Wörter sein."
        _excl(e, "06", "Alle Teile sind selbstständige Wörter (Manual §5.2).")
    else:
        e["kategorie"] = "06"
        e["reason"] = f"«{' '.join(teile)}» statt «{ziel}»: ein unselbstständiger Wortteil wurde abgetrennt."
        _excl(e, "04", "Mindestens ein Teil ist kein selbstständiges Wort.")
    e["featureSource"] = "heuristik"
    return e


def wortgrenzen_ergebnis(teile: list[str], ziel: str) -> list[dict]:
    """Getrennt geschrieben, wo zusammengehört (04/06) – samt dem Folgefehler
    aus Manual §5.1: «Zahn arzt» ist 04 PLUS 01, «Zahn Arzt» nur 04."""
    aus = [wortgrenzen_ereignis(teile, ziel)]
    if ziel[:1].isupper():
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
            for e in wortgrenzen_ergebnis(p["schuelerWoerter"], p["ziel"]):
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
            for e in wortgrenzen_ergebnis(teile, ziel):
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
    {"s": "Nus", "t": "Nuss", "erwartet": ["needs_context"], "quelle": "Bau-Prompt Stufe 2 (07/13 → F1/F3)"},
    {"s": "Bohl", "t": "Bol", "erwartet": ["resolved_by_area"], "quelle": "Ergänzung C.1 (10/12 → beide F2)"},
]

GOLDSTANDARD_TEXT = [
    {"referenz": "Der Zahnarzt kam.", "schueler": "Der Zahn Arzt kam.", "erwartet": ["04"], "quelle": "§5.1"},
    {"referenz": "Der Zahnarzt kam.", "schueler": "Der Zahn arzt kam.", "erwartet": ["04", "01"], "quelle": "§5.1"},
    {"referenz": "Wir wollen weglaufen.", "schueler": "Wir wollen weg laufen.", "erwartet": ["04"], "quelle": "§5.2"},
    {"referenz": "Er will es vergraben.", "schueler": "Er will es ver graben.", "erwartet": ["06"], "quelle": "§5.2"},
    {"referenz": "Das ist zum Beispiel gut.", "schueler": "Das ist zumbeispiel gut.", "erwartet": ["05"], "quelle": "§5"},
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
