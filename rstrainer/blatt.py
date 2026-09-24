"""Übungsblätter als Aufgabenliste: Förderplan, Formate, Prüfung, Teilprompts.

Fachliche Grundlage ist das Original OLFA 3–9+ (Thomé/Thomé 2023):

* **Übungsebene nach Kompetenzwert** (S. 36): unter 50 Lautebene
  (Lautgliederung, Vokalquantität), 50–70 Regelbereiche plus phonologische
  Bewusstheit, über 70 orthographische Themen. Überwiegt Gruppe I, gilt die
  Lautebene (S. 24, 49).
* **Lernwörter des Kindes** (S. 19, 27–28): Wiederholungsfehler werden als
  Lernwörter geübt; aus der ausgefüllten Liste lassen sich wortspezifische
  Förderinhalte direkt ableiten, denn «viele Fehler treten an wenigen, fast
  immer denselben Wörtern auf».
* **Basiskonzept** (S. 8–10, 39–47): Grapheme statt Buchstaben; die Übungen
  8.1–8.3 des Originals (Graphemgrenzen, Orthographeme, Basisgrapheme) sind
  als Schülerformate übernommen. Das Igelsyndrom (S. 21) verlangt den
  Kontrast ie gegen Merkwörter mit einfachem i.
* **Nichts Falsches zeigen** auf der Lautebene: Wer die Lautstruktur noch
  nicht sicher hat, soll keine Fehlschreibungen zum Ankreuzen sehen
  (Übergeneralisierung, S. 38). Fehlersuche gibt es erst auf der Regelebene.
* **Strategie statt Regeltext**: Jeder Förderbereich hat sein Verfahren
  (Ergänzung B.2): Verlängern, Ableiten, Nomenprobe, Abhören. Der Merksatz
  nennt das Verfahren, nicht die Regel.

Das Blatt ist eine Liste von Aufgaben (JSON), damit jede Aufgabe einzeln
angezeigt, geprüft, überarbeitet oder ausgetauscht werden kann.
"""

from __future__ import annotations

import json
import re
import secrets
from dataclasses import dataclass, field
from typing import Any, Iterable

from .olfa_engine import FOERDERBEREICHE, AREA_MAP, GRUPPEN, VORGABE_LEXIKON, klassifiziere_wort
from . import olfa_werte

MARKE_JSON = "---JSON---"

# ---------------------------------------------------------------- Formate

#: Aufgabenformate. «stufe» ordnet von gestützt (0) nach ungestützt (4);
#: «ebene» sagt, ob das Format Laute/Grapheme oder Regeln übt.
FORMATE: dict[str, dict[str, Any]] = {
    "lernwoerter": {"name": "Lernwörter des Kindes", "stufe": 0, "ebene": "laut",
                    "was": "Die eigenen Fehlwörter richtig geschrieben: lesen, die schwierige Stelle markieren, "
                           "abdecken, aus dem Gedächtnis schreiben, vergleichen. Nie die Fehlschreibung zeigen."},
    "gliedern": {"name": "In Grapheme gliedern", "stufe": 0, "ebene": "laut",
                 "was": "Wörter mit Strichen in Grapheme zerlegen (sch, ch, ei, ie, ck, tz, ss, äu = je ein Zeichen), "
                        "wie Übung 8.1 des Originals: S-t-r-ei-ch-h-ö-l-z-ch-e-n."},
    "hoeren": {"name": "Vokallänge hören", "stufe": 0, "ebene": "laut",
               "was": "Wörter nach langem und kurzem Vokal sortieren, Minimalpaare (Hüte/Hütte, Miete/Mitte) sprechen und zuordnen."},
    "orthographeme": {"name": "Orthographeme markieren", "stufe": 1, "ebene": "laut",
                      "was": "In einem kurzen Text die seltenen Schreibungen unterstreichen (ll, tt, ss, tz, ck, Dehnungs-h, ie, v, ä), "
                             "wie Übung 8.2 des Originals; die Anzahl wird genannt."},
    "luecke": {"name": "Lückenwörter", "stufe": 1, "ebene": "regel",
               "was": "Lücke an der Regelstelle ergänzen; die Lösung darf nicht in Klammern stehen, sofern das Niveau das verbietet."},
    "sortieren": {"name": "Nach Regel sortieren", "stufe": 1, "ebene": "regel",
                  "was": "Wörter in zwei oder drei Spalten nach der Regel ordnen (z. B. ss nach kurzem / nach langem Vokal)."},
    "ableiten": {"name": "Verlängern und ableiten", "stufe": 2, "ebene": "regel",
                 "was": "Wortfamilie bilden, verlängern (Korb → Körbe), Grundwort finden (Hände ← Hand) und die Schreibung daraus begründen."},
    "ankreuzen": {"name": "Kontrastpaar ankreuzen", "stufe": 2, "ebene": "regel",
                  "was": "Nur echte Kontrastpaare, über die der Satz entscheidet (das/dass, wider/wieder); beide Formen müssen existieren."},
    "fehlersuche": {"name": "Fehlersuche im Text", "stufe": 3, "ebene": "regel",
                    "was": "Fehler in einem zusammenhängenden Text finden und berichtigen; Anzahl genannt, Stelle nicht; mit Distraktoren."},
    "begruenden": {"name": "Schreibung begründen", "stufe": 3, "ebene": "regel",
                   "was": "Zu jeder Entscheidung das Ableitungswort oder die Strategie in Stichworten nennen."},
    "produktion": {"name": "Eigene Sätze unter Bedingung", "stufe": 4, "ebene": "regel",
                   "was": "Eigene Sätze schreiben, in denen die Regelstelle mehrfach vorkommt."},
}

#: Übungsebene nach Kompetenzwert (S. 36) und Gruppe-I-Anteil (S. 24, 49).
EBENEN: dict[str, dict[str, Any]] = {
    "lautebene": {
        "name": "Lautebene", "formate": ["lernwoerter", "gliedern", "hoeren", "orthographeme", "luecke", "sortieren"],
        "verboten": ["fehlersuche", "ankreuzen"],
        "grund": "Kompetenzwert unter 50 oder überwiegend Gruppe-I-Fehler: zuerst Lautgliederung, Vokalquantität und die "
                 "eigenen Lernwörter (Original S. 36, 24, 49). Dem Kind werden keine Fehlschreibungen gezeigt.",
    },
    "gemischt": {
        "name": "Laut- und Regelebene", "formate": ["lernwoerter", "gliedern", "hoeren", "luecke", "sortieren", "ableiten", "begruenden", "fehlersuche"],
        "verboten": [],
        "grund": "Kompetenzwert 50–70: Regelbereiche üben, dazu Übungen zur phonologischen Bewusstheit (Original S. 36).",
    },
    "regelebene": {
        "name": "Regelebene", "formate": ["luecke", "sortieren", "ableiten", "ankreuzen", "fehlersuche", "begruenden", "produktion"],
        "verboten": ["gliedern", "hoeren"],
        "grund": "Kompetenzwert über 70: Das lautliche Fundament trägt, es wird fast ausschliesslich orthographisch gearbeitet (Original S. 36).",
    },
}

#: Umfang statt zweier Zahlenfelder: Aufgaben je Bereich / Aufgaben im Test.
UMFANG = {"kurz": (2, 4), "normal": (3, 6), "lang": (4, 8)}

#: Was je Förderbereich als Kontrast geübt werden muss (Original mit Seite).
KONTRASTE = {
    "F1": "Schärfung: ss/ll/tt nach kurzem Vokal gegen Einfachschreibung nach langem Vokal (Kasse/Käse, Hütte/Hüte); "
          "keine Verdoppelung, wenn schon zwei Mitlaute folgen (Karte, Wald). *das für dass = 07 (S. 21).",
    "F2": "Längenmarkierung: ie gegen Merkwörter mit einfachem i für /iː/ (Tiger, Biber, mir, dir, wir, Maschine – Igelsyndrom, S. 21); "
          "Dehnungs-h gegen unmarkierte Länge (Zahn/Tal).",
    "F3": "ss nach langem Vokal oder Diphthong (Fuss, Strasse, heissen, draussen) gegen ss nach kurzem Vokal (Fluss, müssen) – "
          "in de-CH nur als Merkwortschatz lernbar (13–16 entfallen, S. 59).",
    "F4": "ä/äu ableitbar (Hände ← Hand, Bäume ← Baum) gegen nicht ableitbar (Käse, Bär, Eltern); e/ä nur bei kurzem /ɛ/ (S. 22–23).",
    "F5": "Auslautverhärtung: Verlängerungsprobe (Korb → Körbe, Hund → Hunde); -ig gegen -ich (König/fröhlich, S. 24).",
    "F6": "Nomenprobe: Artikel/Begleiter, Nominalisierung (das Lesen, etwas Schönes) gegen Verb/Adjektiv; Satzanfang.",
    "F7": "Wortbausteine: Zusammensetzung (Zahnarzt) gegen Wortgruppe (zum Beispiel); unselbstständige Teile (ver-, -ung).",
    "F8": "v als /f/ (Vogel, Vater, viel) gegen w/f; Merkwörter mit v für /v/ (Vase, Vulkan, Provinz).",
    "F9": "Vollständiges Abhören: jeder Laut ein Zeichen (nicht → *nich, Kräuter → *Käuter); Silben klatschen, Wortgrenzen.",
    "F10": "Keine Regel – Einzelwörter als Lernwörter; Fremdwörter mit ihrer Merkstelle (Garage, Maschine).",
}

#: Wenige Chips, die den Teilprompt steuern (so wenig wie möglich).
CHIPS: dict[str, dict[str, str]] = {
    "leichter": {"name": "Leichter", "anweisung": "Mache die Aufgabe eine Stufe leichter: kürzeres Material, häufigere Wörter, Suchort markiert. Format und Bereich bleiben."},
    "schwerer": {"name": "Schwerer", "anweisung": "Mache die Aufgabe eine Stufe schwerer: ungestützt, längeres oder selteneres Wortmaterial, Begründung verlangt. Bereich bleibt."},
    "woerter": {"name": "Andere Wörter", "anweisung": "Behalte Format, Bereich und Schwierigkeit, nimm aber vollständig anderes Wortmaterial derselben Regelstelle."},
    "lernwoerter": {"name": "Lernwörter des Kindes", "anweisung": "Baue die unten genannten Lernwörter des Kindes in die Aufgabe ein (richtig geschrieben, die Fehlschreibung nicht zeigen)."},
    "begruendung": {"name": "Begründung verlangen", "anweisung": "Verlange zu jeder Entscheidung die Strategie oder das Ableitungswort in Stichworten; passe Lösung und Punkte an."},
    "format": {"name": "Anderes Format", "anweisung": "Wechsle in ein anderes erlaubtes Format derselben Übungsebene, gleicher Bereich, gleiche Schwierigkeit."},
}

AUFGABENSCHEMA = (
    '{"nr": 1, "teil": "uebung" | "test", "bereich": "F1", "format": "luecke", '
    '"strategie": "Verlängern: Hund → Hunde", "merksatz": "nur im Übungsteil, nur bei der ersten Aufgabe eines Bereichs, sonst \\"\\"", '
    '"aufgabe": "Anweisung an das Kind", "material": "Wörter, Sätze oder Text; Lücken als _______", '
    '"loesung": "vollständige Lösung", "punkte": 1, "woerter": ["Zielwörter dieser Aufgabe, richtig geschrieben"], '
    '"fehler": [{"falsch": "nur bei fehlersuche", "richtig": "…"}]}'
)


# ------------------------------------------------------------ Förderplan

@dataclass
class Lernwort:
    ziel: str
    schueler: str
    anzahl: int
    bereich: str


@dataclass
class Foerderplan:
    bereiche: list[str]
    ebene: str
    ebene_grund: str
    kw: float | None
    gruppe_i_anteil: float | None
    lernwoerter: dict[str, list[Lernwort]] = field(default_factory=dict)
    anspruch: str = "mittel"
    umfang: str = "normal"

    @property
    def formate(self) -> list[str]:
        return list(EBENEN[self.ebene]["formate"])

    @property
    def verboten(self) -> list[str]:
        return list(EBENEN[self.ebene]["verboten"])

    @property
    def aufgaben_je_bereich(self) -> int:
        return UMFANG.get(self.umfang, UMFANG["normal"])[0]

    @property
    def test_aufgaben(self) -> int:
        return UMFANG.get(self.umfang, UMFANG["normal"])[1]

    def als_dict(self) -> dict[str, Any]:
        return {"bereiche": self.bereiche, "ebene": self.ebene, "ebene_grund": self.ebene_grund, "kw": self.kw,
                "gruppe_i_anteil": self.gruppe_i_anteil, "anspruch": self.anspruch, "umfang": self.umfang,
                "lernwoerter": {b: [w.__dict__ for w in ws] for b, ws in self.lernwoerter.items()}}


def ebene_bestimmen(kw: float | None, gruppe_i_anteil: float | None) -> str:
    """Original S. 36 (KW-Bänder) und S. 24/49 (Gruppe I dominant)."""
    if gruppe_i_anteil is not None and gruppe_i_anteil > 0.5:
        return "lautebene"
    if kw is None:
        return "gemischt"
    if kw < 50:
        return "lautebene"
    if kw > 70:
        return "regelebene"
    return "gemischt"


def bereich_von(kategorie_nr: str) -> str | None:
    nr = str(kategorie_nr)
    if nr in FOERDERBEREICHE:
        return nr
    return AREA_MAP.get(nr)


def lernwoerter_sammeln(fehler: Iterable[dict], bereiche: Iterable[str], hoechstens: int = 8) -> dict[str, list[Lernwort]]:
    """Fehlwörter des Kindes je Förderbereich: Wiederholungen zuerst (S. 19),
    dann die jüngsten; höchstens ``hoechstens`` je Bereich."""
    gewuenscht = set(bereiche)
    zaehler: dict[tuple[str, str], dict[str, Any]] = {}
    for reihe, f in enumerate(fehler):
        d = dict(f) if not isinstance(f, dict) else f
        b = bereich_von(str(d.get("kategorie_nr", "")))
        ziel = str(d.get("wort_original") or "").strip()
        if not b or b not in gewuenscht or not ziel or "ß" in ziel:
            continue
        schluessel = (b, ziel.lower())
        e = zaehler.setdefault(schluessel, {"ziel": ziel, "schueler": str(d.get("wort_schueler") or "").strip(), "anzahl": 0, "zuletzt": reihe, "bereich": b})
        e["anzahl"] += 1
        e["zuletzt"] = reihe
        if d.get("wort_schueler"):
            e["schueler"] = str(d["wort_schueler"]).strip()
    aus: dict[str, list[Lernwort]] = {}
    for b in gewuenscht:
        eintraege = [e for (bb, _), e in zaehler.items() if bb == b]
        eintraege.sort(key=lambda e: (-e["anzahl"], -e["zuletzt"]))
        aus[b] = [Lernwort(e["ziel"], e["schueler"], e["anzahl"], b) for e in eintraege[:hoechstens]]
    return aus


def foerderplan(bereiche: Iterable[str], fehler: Iterable[dict], woerter: int,
                anspruch: str = "mittel", umfang: str = "normal", ebene: str | None = None) -> Foerderplan:
    """Förderplan aus den Daten des Kindes. ``ebene`` überschreibt die Automatik."""
    fehler = [dict(f) if not isinstance(f, dict) else f for f in fehler]
    bereiche = [bereich_von(b) or b for b in bereiche]
    kats = [str(f.get("kategorie_nr", "")) for f in fehler if str(f.get("kategorie_nr", "")) in GRUPPEN
            or str(f.get("kategorie_nr", "")) in ("36", "37")]
    w = olfa_werte.berechnen(kats, max(woerter, 1)) if kats else None
    kw = w.kw if w else None
    summe = sum(w.gruppen.values()) if w else 0
    anteil = (w.gruppen["I"] / summe) if w and summe >= 10 else None
    auto = ebene_bestimmen(kw, anteil)
    gewaehlt = ebene if ebene in EBENEN else auto
    grund = EBENEN[gewaehlt]["grund"] if gewaehlt == auto else f"Von der Lehrperson gewählt (Automatik hätte «{EBENEN[auto]['name']}» ergeben)."
    return Foerderplan(bereiche=bereiche, ebene=gewaehlt, ebene_grund=grund, kw=kw, gruppe_i_anteil=anteil,
                       lernwoerter=lernwoerter_sammeln(fehler, bereiche), anspruch=anspruch, umfang=umfang)


def foerderplan_block(plan: Foerderplan) -> str:
    """Der Förderplan als Prompt-Abschnitt."""
    z = ["### Förderplan (aus der OLFA-Auswertung des Kindes)"]
    kw = "unbekannt" if plan.kw is None else f"{plan.kw:g}"
    z.append(f"- Kompetenzwert des Kindes: {kw}. Übungsebene: **{EBENEN[plan.ebene]['name']}** – {plan.ebene_grund}")
    erlaubt = ", ".join(f"«{FORMATE[f]['name']}» ({f}: {FORMATE[f]['was']})" for f in plan.formate)
    z.append(f"- Erlaubte Aufgabenformate (Feld «format»): {erlaubt}")
    if plan.verboten:
        z.append("- NICHT erlaubt auf dieser Ebene: " + ", ".join(FORMATE[f]["name"] for f in plan.verboten)
                 + ". Dem Kind werden keine Fehlschreibungen vorgelegt.")
    z.append("- Strategie je Förderbereich (der Merksatz nennt das Verfahren, nicht die Regel) und der Kontrast, der geübt werden muss:")
    for b in plan.bereiche:
        fb = FOERDERBEREICHE.get(b)
        if fb:
            z.append(f"  - {b} – {fb['name']}: {fb['foerdern']}. Kontrast: {KONTRASTE.get(b, '')}")
    lw = [(b, ws) for b, ws in plan.lernwoerter.items() if ws]
    if lw:
        z.append("- Lernwörter des Kindes (richtig geschrieben; die Fehlschreibung dem Kind NICHT zeigen; jedes Lernwort muss "
                 "im Übungsteil in mindestens einer Aufgabe vorkommen; im Mini-Test andere Wörter derselben Regelstelle):")
        for b, ws in lw:
            z.append(f"  - {b}: " + ", ".join(f"{w.ziel} ({w.anzahl}×, schrieb «{w.schueler}»)" if w.schueler else f"{w.ziel} ({w.anzahl}×)" for w in ws))
    else:
        z.append("- Lernwörter des Kindes: noch keine erfasst – nimm typische Wörter der Regelstelle.")
    z.append(f"- Umfang: {plan.aufgaben_je_bereich} Aufgaben je Förderbereich im Übungsteil, {plan.test_aufgaben} Aufgaben im Mini-Test.")
    return "\n".join(z)


# ----------------------------------------------------- Aufgaben lesen/schreiben

def _json_ausschneiden(roh: str) -> str | None:
    text = str(roh or "")
    if MARKE_JSON in text:
        text = text.split(MARKE_JSON, 1)[1]
    text = text.replace("===RSTRAINER-ENDE===", "")
    text = re.sub(r"^```(?:json)?\s*|\s*```\s*$", "", text.strip(), flags=re.M)
    a, b = text.find("{"), text.rfind("}")
    if a == -1 or b == -1 or b <= a:
        return None
    return text[a:b + 1]


def _aufgabe_normalisieren(a: dict, nr: int) -> dict:
    d = {
        "nr": int(a.get("nr") or nr),
        "teil": "test" if str(a.get("teil", "uebung")).lower().startswith("t") else "uebung",
        "bereich": str(a.get("bereich") or "").strip().upper(),
        "format": str(a.get("format") or "luecke").strip().lower(),
        "strategie": str(a.get("strategie") or "").strip(),
        "merksatz": str(a.get("merksatz") or "").strip(),
        "aufgabe": str(a.get("aufgabe") or "").strip(),
        "material": str(a.get("material") or "").strip(),
        "loesung": str(a.get("loesung") or "").strip(),
        "punkte": int(a.get("punkte") or 1),
        "woerter": [str(w).strip() for w in (a.get("woerter") or []) if str(w).strip()],
        "fehler": [{"falsch": str(x.get("falsch", "")).strip(), "richtig": str(x.get("richtig", "")).strip()}
                   for x in (a.get("fehler") or []) if isinstance(x, dict)],
    }
    if d["format"] not in FORMATE:
        d["format"] = "luecke"
    return d


def aufgaben_lesen(roh: str) -> tuple[list[dict], list[str]]:
    """JSON-Aufgabenliste aus der Antwort; Rückgabe (aufgaben, hinweise)."""
    text = _json_ausschneiden(roh)
    if text is None:
        return [], ["Kein JSON-Block gefunden."]
    try:
        daten = json.loads(text)
    except json.JSONDecodeError as f:
        return [], [f"Der JSON-Block liess sich nicht lesen: {f.msg} (Zeile {f.lineno})."]
    liste = daten.get("aufgaben") if isinstance(daten, dict) else daten
    if not isinstance(liste, list):
        return [], ["Im JSON fehlt die Liste «aufgaben»."]
    aufgaben = [_aufgabe_normalisieren(a, i + 1) for i, a in enumerate(liste) if isinstance(a, dict)]
    return neu_nummerieren(aufgaben), []


def aufgabe_lesen(roh: str) -> tuple[dict | None, list[str]]:
    """Eine einzelne Aufgabe (Antwort auf einen Teilprompt)."""
    text = _json_ausschneiden(roh)
    if text is None:
        return None, ["Kein JSON gefunden."]
    try:
        daten = json.loads(text)
    except json.JSONDecodeError as f:
        return None, [f"Das JSON liess sich nicht lesen: {f.msg}."]
    if isinstance(daten, dict) and isinstance(daten.get("aufgaben"), list) and daten["aufgaben"]:
        daten = daten["aufgaben"][0]
    if not isinstance(daten, dict):
        return None, ["Die Antwort enthält keine Aufgabe."]
    return _aufgabe_normalisieren(daten, 0), []


def neu_nummerieren(aufgaben: list[dict]) -> list[dict]:
    """Nummeriert je Teil neu – auf Kopien, damit die Eingabe unverändert bleibt."""
    aufgaben = [dict(a) for a in aufgaben]
    n_u = n_t = 0
    for a in aufgaben:
        if a["teil"] == "test":
            n_t += 1; a["nr"] = n_t
        else:
            n_u += 1; a["nr"] = n_u
    return aufgaben


def aufgabe_ersetzen(aufgaben: list[dict], teil: str, nr: int, neue: dict) -> list[dict]:
    aus = []
    for a in aufgaben:
        if a["teil"] == teil and a["nr"] == nr:
            b = dict(neue); b["teil"] = teil; aus.append(b)
        else:
            aus.append(a)
    return neu_nummerieren(aus)


def aufgabe_entfernen(aufgaben: list[dict], teil: str, nr: int) -> list[dict]:
    return neu_nummerieren([a for a in aufgaben if not (a["teil"] == teil and a["nr"] == nr)])


def aufgabe_verschieben(aufgaben: list[dict], teil: str, nr: int, richtung: int) -> list[dict]:
    idx = [i for i, a in enumerate(aufgaben) if a["teil"] == teil]
    pos = next((k for k, i in enumerate(idx) if aufgaben[i]["nr"] == nr), None)
    if pos is None or not (0 <= pos + richtung < len(idx)):
        return aufgaben
    i, j = idx[pos], idx[pos + richtung]
    aufgaben = list(aufgaben)
    aufgaben[i], aufgaben[j] = aufgaben[j], aufgaben[i]
    return neu_nummerieren(aufgaben)


def aufgaben_zu_text(aufgaben: list[dict]) -> tuple[str, str, str]:
    """Übungsteil, Mini-Test und Lösungen als Text (für Druck und Export)."""
    uebung, test, loesungen = [], [], []
    gesehen: set[str] = set()
    punkte = 0
    for a in aufgaben:
        kopf = f"{a['nr']}. [{a['bereich']}] {a['aufgabe']}".rstrip()
        block = kopf + (f"\n{a['material']}" if a["material"] else "")
        if a["teil"] == "test":
            if a["punkte"] > 1:
                block += f"\n({a['punkte']} Punkte)"
            punkte += a["punkte"]
            test.append(block)
            loesungen.append(f"Test {a['nr']}: {a['loesung']}")
        else:
            if a["merksatz"] and a["bereich"] not in gesehen:
                gesehen.add(a["bereich"])
                block = f"Merke ({a['bereich']}): {a['merksatz']}\n\n" + block
            uebung.append(block)
            loesungen.append(f"Übung {a['nr']}: {a['loesung']}")
    if test:
        test.append(f"Erreichte Punkte: ____ von {punkte}")
    return "\n\n".join(uebung), "\n\n".join(test), "\n".join(loesungen)


# ------------------------------------------------------------ Prüfung

def _woerter(text: str) -> list[str]:
    return re.findall(r"[^\W\d_][\w]*", text or "")


def aufgaben_pruefen(aufgaben: list[dict], plan: Foerderplan, lexikon: dict | None = None) -> list[dict]:
    """Prüft jede Aufgabe: Rückgabe je Befund {nr, teil, stufe, text}.

    stufe: «warnung» (muss angeschaut werden), «hinweis», «ok»."""
    lexikon = lexikon if lexikon is not None else VORGABE_LEXIKON
    befunde: list[dict] = []
    erlaubt = set(plan.formate)
    olfa_von = {b: set(FOERDERBEREICHE[b]["olfa"]) for b in FOERDERBEREICHE}

    def melde(a: dict, stufe: str, text: str) -> None:
        befunde.append({"nr": a["nr"], "teil": a["teil"], "stufe": stufe, "text": text})

    uebung_woerter: dict[str, set[str]] = {}
    for a in aufgaben:
        alles = " ".join([a["aufgabe"], a["material"], a["loesung"], " ".join(a["woerter"])])
        if "ß" in alles:
            melde(a, "warnung", "Enthält ein ß – in der Schweizer Rechtschreibung gibt es keines.")
        if a["bereich"] and a["bereich"] not in plan.bereiche:
            melde(a, "warnung", f"Bereich {a['bereich']} gehört nicht zu den gewählten Förderbereichen ({', '.join(plan.bereiche)}).")
        if a["format"] not in erlaubt:
            melde(a, "warnung", f"Format «{FORMATE[a['format']]['name']}» ist auf der Ebene «{EBENEN[plan.ebene]['name']}» nicht vorgesehen.")
        if not a["loesung"] and a["format"] not in ("lernwoerter", "gliedern"):
            melde(a, "warnung", "Keine Lösung angegeben.")
        if not a["aufgabe"]:
            melde(a, "warnung", "Aufgabenstellung fehlt.")
        if a["format"] == "luecke" and a["material"]:
            loes = {w.lower() for w in _woerter(a["loesung"])} - {w.lower() for w in _woerter(a["aufgabe"])}
            mat = {w.lower() for w in _woerter(a["material"])}
            treffer = [w for w in loes if w in mat and len(w) > 3]
            if treffer and "_" in a["material"]:
                melde(a, "hinweis", f"Lösungswort steht schon im Material: {', '.join(sorted(treffer)[:3])}.")
            if plan.anspruch == "anspruchsvoll" and re.search(r"\(\s*[a-zäöü]{1,3}\s*\)", a["material"]):
                melde(a, "warnung", "Buchstabenvorgabe in Klammern – auf Stufe «anspruchsvoll» nicht erlaubt.")
        if a["format"] == "fehlersuche":
            if not a["fehler"]:
                melde(a, "hinweis", "Fehlersuche ohne Liste der eingebauten Fehler (Feld «fehler») – die Zuordnung kann nicht geprüft werden.")
            for x in a["fehler"]:
                if not x["falsch"] or not x["richtig"]:
                    continue
                r = klassifiziere_wort(x["falsch"], x["richtig"], lexikon, erzwingen=True)
                kats = [e["kategorie"] for e in r["ereignisse"] if e.get("kategorie")]
                gehoert = olfa_von.get(a["bereich"], set())
                if kats and not any(k in gehoert for k in kats):
                    melde(a, "warnung", f"Eingebauter Fehler «{x['falsch']}» → «{x['richtig']}» ist OLFA {'/'.join(kats)}, "
                                        f"gehört also nicht zu {a['bereich']}.")
        if a["teil"] == "uebung":
            uebung_woerter.setdefault(a["bereich"], set()).update(w.lower() for w in a["woerter"])
    # Lernwörter im Übungsteil?
    for b, ws in plan.lernwoerter.items():
        if not ws:
            continue
        drin = uebung_woerter.get(b, set())
        text_gesamt = " ".join(a["material"] + " " + a["aufgabe"] for a in aufgaben if a["teil"] == "uebung" and a["bereich"] == b).lower()
        fehlend = [w.ziel for w in ws if w.ziel.lower() not in drin and w.ziel.lower() not in text_gesamt]
        if fehlend and len(fehlend) == len(ws):
            befunde.append({"nr": 0, "teil": "uebung", "stufe": "warnung",
                            "text": f"{b}: Kein Lernwort des Kindes kommt im Übungsteil vor ({', '.join(fehlend[:4])})."})
        elif fehlend:
            befunde.append({"nr": 0, "teil": "uebung", "stufe": "hinweis",
                            "text": f"{b}: Lernwörter noch nicht geübt: {', '.join(fehlend[:4])}."})
    # Test nicht leichter als Übung, andere Wörter
    stufen_u = {a["bereich"]: max(FORMATE[x["format"]]["stufe"] for x in aufgaben if x["teil"] == "uebung" and x["bereich"] == a["bereich"])
                for a in aufgaben if a["teil"] == "uebung"}
    for a in aufgaben:
        if a["teil"] != "test":
            continue
        if a["bereich"] in stufen_u and FORMATE[a["format"]]["stufe"] < stufen_u[a["bereich"]] - 1:
            melde(a, "hinweis", "Deutlich gestützter als der Übungsteil – der Test darf nicht leichter sein.")
        doppelt = {w.lower() for w in a["woerter"]} & uebung_woerter.get(a["bereich"], set())
        if doppelt:
            melde(a, "hinweis", f"Wörter schon im Übungsteil: {', '.join(sorted(doppelt)[:3])}.")
    if not any(a["teil"] == "test" for a in aufgaben):
        befunde.append({"nr": 0, "teil": "test", "stufe": "warnung", "text": "Kein Mini-Test enthalten."})
    if not any(a["teil"] == "uebung" for a in aufgaben):
        befunde.append({"nr": 0, "teil": "uebung", "stufe": "warnung", "text": "Kein Übungsteil enthalten."})
    return befunde


# ------------------------------------------------------------ Teilprompt

def teilprompt_bauen(aufgabe: dict, plan: Foerderplan, aktion: str, chip: str | None = None,
                     hinweis: str = "", anforderung: str = "", code: str | None = None) -> tuple[str, str]:
    """Prompt für eine einzelne Aufgabe: «ueberarbeiten» oder «austauschen»."""
    code = code or f"RST-AUF-{secrets.token_hex(3).upper()}"
    fb = FOERDERBEREICHE.get(aufgabe.get("bereich", ""), {})
    lw = plan.lernwoerter.get(aufgabe.get("bereich", ""), [])
    anweisung = []
    if aktion == "austauschen":
        anweisung.append("Ersetze die Aufgabe durch eine NEUE Aufgabe an derselben Stelle: gleicher Bereich, gleicher Teil, "
                         "gleiche Schwierigkeit, aber anderes Wortmaterial und – wenn möglich – ein anderes erlaubtes Format.")
    else:
        anweisung.append("Überarbeite die Aufgabe. Behalte Bereich und Teil bei.")
    if chip in CHIPS:
        anweisung.append(CHIPS[chip]["anweisung"])
    if hinweis.strip():
        anweisung.append("Wunsch der Lehrperson: " + hinweis.strip())
    text = f"""Du unterstützt eine Lehrperson bei der Rechtschreibförderung (OLFA 3–9, Schweizer Rechtschreibung: kein ß, immer ss).

## Auftrag: eine einzelne Aufgabe eines Übungsblatts {"austauschen" if aktion == "austauschen" else "überarbeiten"}

Auftragsnummer: {code}

### Die bisherige Aufgabe
```json
{json.dumps(aufgabe, ensure_ascii=False, indent=1)}
```

### Was zu tun ist
{chr(10).join('- ' + a for a in anweisung)}

### Rahmen, der weiter gilt
- Förderbereich {aufgabe.get('bereich', '')}: {fb.get('name', '')} – Strategie: {fb.get('foerdern', '')}. Kontrast: {KONTRASTE.get(aufgabe.get('bereich', ''), '')}
- Übungsebene «{EBENEN[plan.ebene]['name']}»: erlaubte Formate {', '.join(plan.formate)}{'; nicht erlaubt: ' + ', '.join(plan.verboten) if plan.verboten else ''}.
- Anforderungsniveau «{plan.anspruch}»: {anforderung.strip() or 'wie im ursprünglichen Auftrag'}
- Lernwörter des Kindes für diesen Bereich: {', '.join(f'{w.ziel} (schrieb «{w.schueler}»)' if w.schueler else w.ziel for w in lw) or 'keine erfasst'}
- Im Feld «teil» = «test»: keine Merksätze, keine Hilfen. Lösungen nur im Feld «loesung», nie in «material».
- Bei «fehlersuche» jeden eingebauten Fehler unter «fehler» als Paar falsch/richtig aufführen; jeder Fehler muss zum Bereich gehören.

### Rückgabeformat
Antworte ausschliesslich mit diesem Block:

===RSTRAINER-ANFANG===
AUFTRAG: {code}
TYP: aufgabe
{MARKE_JSON}
{AUFGABENSCHEMA}
===RSTRAINER-ENDE===
"""
    return code, text
