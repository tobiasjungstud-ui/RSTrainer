"""Goldstandard-Tests der deterministischen OLFA-Engine.

Manual §19 verlangt die Minimalpaare als automatisierte Unit Tests, die
keine spätere Änderung verschlechtern darf. Die Liste selbst liegt in der
Engine (``GOLDSTANDARD``), damit Artefakt und Repo dieselben Fälle prüfen.
"""

from __future__ import annotations

import pytest

from rstrainer import olfa_engine as E


# --- Minimalpaare -----------------------------------------------------------

@pytest.mark.parametrize("fall", E.GOLDSTANDARD, ids=lambda f: f"{f['s']}→{f['t']}")
def test_goldstandard_minimalpaar(fall):
    r = E.klassifiziere_wort(fall["s"], fall["t"], E.VORGABE_LEXIKON)
    for e in r["ereignisse"]:
        E.abschliessen(e, {"ziel": fall["t"]}, {"zielwortSicherheit": 1})
    erhalten = [E._erhalten(e) for e in r["ereignisse"]]
    assert sorted(erhalten) == sorted(fall["erwartet"]), fall["quelle"]


@pytest.mark.parametrize("fall", E.GOLDSTANDARD_TEXT, ids=lambda f: f["schueler"])
def test_goldstandard_wortgrenzen(fall):
    r = E.analysiere_diktat(fall["referenz"], fall["schueler"], E.VORGABE_LEXIKON)
    erhalten = [e["kategorie"] or e["status"] for e in r["ereignisse"]]
    assert sorted(erhalten) == sorted(fall["erwartet"]), fall["quelle"]


def test_alle_goldstandardfaelle_gruen():
    assert all(f["ok"] for f in E.testlauf())
    assert all(f["ok"] for f in E.testlauf_text())


# --- Graphemsegmentierung (Manual §2) ---------------------------------------

@pytest.mark.parametrize("wort,erwartet", [
    ("fahren", ["f", "ah", "r", "e", "n"]),
    ("Fahrrad", ["f", "ah", "rr", "a", "d"]),
    ("Katze", ["k", "a", "tz", "e"]),
    ("packen", ["p", "a", "ck", "e", "n"]),
    ("Schule", ["sch", "u", "l", "e"]),
    ("Preisse", ["p", "r", "ei", "ss", "e"]),
    ("Gesundheit", ["g", "e", "s", "u", "n", "d", "h", "ei", "t"]),
    ("Quark", ["qu", "a", "r", "k"]),
])
def test_segmentierung_graphemorientiert(wort, erwartet):
    assert E.grapheme(wort) == erwartet


def test_transposition_wird_erkannt_nicht_zerlegt():
    """Manual §9.3: Graten → Garten ist EINE Umstellung, nicht Auslassung + Zufügung."""
    ops, distanz = E.align(E.grapheme("Graten"), E.grapheme("Garten"))
    assert distanz == 1
    assert [o["op"] for o in ops if o["op"] != "equal"] == ["trans"]


# --- Nie raten (Bau-Prompt Stufe 2) -----------------------------------------

def test_ohne_lexikon_kein_raten_bei_verschiedenen_foerderbereichen():
    r = E.klassifiziere_wort("Nus", "Nuss", {})
    e = r["ereignisse"][0]
    assert e["status"] == "needs_context"
    assert e["kandidaten"] == ["07", "13"]
    E.abschliessen(e, {"ziel": "Nuss"})
    assert e["status"] == "needs_context"          # F1 ≠ F3 → bleibt offen
    assert e["confidence"] < 0.65


def test_konsequenzpruefung_loest_gleichen_foerderbereich(monkeypatch):
    """Ergänzung C.1: 10/12 führen beide in F2 – folgenlos."""
    r = E.klassifiziere_wort("Bohl", "Bol", {})
    e = r["ereignisse"][0]
    assert e["kandidaten"] == ["10", "12"]
    E.abschliessen(e, {"ziel": "Bol"})
    assert e["status"] == "resolved_by_area"
    assert e["foerderbereich"] == "F2"


def test_lexikon_entscheidet_deterministisch():
    """Mit Lexikoneintrag wird derselbe Fall rein deterministisch."""
    kurz = E.klassifiziere_wort("Nus", "Nuss", {"nuss": {"vokale": ["kurz"], "quelle": "lexikon"}})["ereignisse"][0]
    lang = E.klassifiziere_wort("Nus", "Nuss", {"nuss": {"vokale": ["lang"], "quelle": "lexikon"}})["ereignisse"][0]
    assert (kurz["kategorie"], kurz["status"]) == ("07", "resolved")
    assert (lang["kategorie"], lang["status"], lang["definition"]) == ("13", "resolved", "de-CH")


def test_ganz_anderes_wort_wird_nicht_zerlegt():
    r = E.klassifiziere_wort("Hund", "Katze", E.VORGABE_LEXIKON)
    assert r["wortersetzung"] is True
    assert r["ereignisse"][0]["status"] == "manual_review"


# --- Validator (Manual §17, Ergänzung A.5) ----------------------------------

def test_validator_lehnt_never_assign_ab():
    e = E.ereignis(kategorie="14", studentGrapheme="ß", targetGrapheme="s")
    E.validiere(e)
    assert e["status"] == "manual_review"
    assert any("nie vergeben" in v["regel"] for v in e["validator"])


def test_validator_reklassifiziert_07_nach_langvokal_auf_13():
    e = E.ereignis(kategorie="07", studentGrapheme="s", targetGrapheme="ss")
    E.validiere(e, {"vokalDavor": "lang"})
    assert e["kategorie"] == "13" and e["definition"] == "de-CH"


def test_validator_lehnt_ss_zielform_mit_eszett_ab():
    e = E.ereignis(kategorie="07", studentGrapheme="s", targetGrapheme="ss")
    E.validiere(e, {"ziel": "Straße"})
    assert e["status"] == "manual_review"


# --- Förderbereiche (Ergänzung B.2) -----------------------------------------

def test_area_map_deckt_alle_vergebbaren_nummern():
    vergebbar = {f"{n:02d}" for n in range(1, 38)} - E.NEVER_ASSIGN
    assert set(E.AREA_MAP) == vergebbar


def test_never_assign_hat_keinen_foerderbereich():
    assert not any(nr in E.AREA_MAP for nr in E.NEVER_ASSIGN)


# --- Konfidenz (Ergänzung C.2) ----------------------------------------------

def test_konfidenz_wird_berechnet_und_gedeckelt():
    e = E.ereignis(kategorie="07", status="resolved", featureSource="schreibung")
    E.konfidenz(e)
    assert e["confidence"] == 0.97
    e2 = E.ereignis(kategorie="07", status="resolved", featureSource="ki")
    E.konfidenz(e2)
    assert e2["confidence"] == 0.78
    e3 = E.ereignis(kategorie="07", status="resolved", featureSource="schreibung")
    E.konfidenz(e3, {"zielwortSicherheit": 0.6})
    assert e3["confidence"] == 0.6                 # unsicheres Zielwort deckelt alles
    e4 = E.ereignis(kategorie="07", status="resolved", featureSource="ki")
    E.konfidenz(e4, {"eigeneZuordnung": True})
    assert e4["confidence"] == 0.95


# --- Mehrfachfehler, Positionen, Vollständigkeit (Manual §10, Bau-Prompt §5) --

def test_mehrfachfehler_werden_getrennt():
    r = E.klassifiziere_wort("musen", "müssen", E.VORGABE_LEXIKON)
    assert sorted(e["kategorie"] for e in r["ereignisse"]) == ["07", "36"]


def test_diktat_liefert_status_fuer_jedes_wort():
    r = E.analysiere_diktat("Der Hund lief über die Strasse.", "Der Hunt lief über die Strase.", E.VORGABE_LEXIKON)
    assert all(a["status"] != "offen" for a in r["abdeckung"])
    assert [e["kategorie"] for e in r["ereignisse"]] == ["19", "13"]
    assert r["ereignisse"][0]["charOffset"] == 7          # «Hunt» beginnt bei Zeichen 4, <t> ist drittes Graphem
    assert r["ereignisse"][1]["sentenceIndex"] == 0


def test_ausgelassene_und_zusaetzliche_woerter_sind_keine_kategorie():
    r = E.analysiere_diktat("Der Hund lief schnell weg.", "Der Hund lief weg nun.", E.VORGABE_LEXIKON)
    assert r["ereignisse"] == []
    assert [x["wort"] for x in r["ausgelassen"]] == ["schnell"]
    assert [x["wort"] for x in r["zusaetzlich"]] == ["nun"]


def test_das_dass_traegt_vermutete_ursache():
    r = E.klassifiziere_wort("das", "dass", E.VORGABE_LEXIKON)
    assert r["ereignisse"][0]["kategorie"] == "07"
    assert "das/dass" in r["ereignisse"][0]["possibleUnderlyingCause"]


# --- Halluzinationsfilter und Zielwortschwelle (Manual §12, Bau-Prompt §5.2) --

def test_importliste_verwirft_stellen_die_nicht_im_text_stehen():
    r = E.analysiere_liste([{"student": "Hunt", "target": "Hund"}, {"student": "Katze", "target": "Katze"}],
                           "Der Hunt bellt.", E.VORGABE_LEXIKON)
    assert [e["kategorie"] for e in r["ereignisse"]] == ["19"]
    assert r["verworfen"][0]["grund"].startswith("Originalform steht nicht")


def test_zielform_mit_eszett_wird_verworfen():
    r = E.analysiere_liste([{"student": "Strase", "target": "Straße"}], "Die Strase.", E.VORGABE_LEXIKON)
    assert r["ereignisse"] == [] and "ß" in r["verworfen"][0]["grund"]


def test_unsicheres_zielwort_wird_nicht_kaschiert():
    r = E.analysiere_liste([{"student": "wider", "target": "wieder", "sicherheit": 0.6}],
                           "Ich bin wider da.", E.VORGABE_LEXIKON, quelle="ki")
    e = r["ereignisse"][0]
    assert e["status"] == "manual_review"
    assert e["confidence"] <= 0.6


# --- Umstufungsmuster (Ergänzung C.3) ---------------------------------------

def test_eigene_zuordnung_wird_bei_gleichem_muster_vorgeschlagen():
    ohne = E.analysiere_diktat("Die Nuss.", "Die Nus.", {})["ereignisse"][0]
    schluessel = ohne["muster"]
    assert ohne["status"] == "needs_context"
    mit = E.analysiere_diktat("Die Nuss.", "Die Nus.", {}, {schluessel: {"kategorie": "13", "am": "2026-01-01"}})["ereignisse"][0]
    assert (mit["kategorie"], mit["status"], mit["featureSource"]) == ("13", "resolved", "eigene")
    assert mit["confidence"] == 0.95


# --- Die Beispieltabelle im README ------------------------------------------

README_TABELLE = [
    ("haus", "Haus", "01"), ("komen", "kommen", "07"), ("hatt", "hat", "08"),
    ("Zan", "Zahn", "09"), ("Fus", "Fuss", "13"), ("Preisse", "Preise", "15"),
    ("Beren", "Bären", "17"), ("Hunt", "Hund", "19"), ("Fater", "Vater", "23"),
    ("wenich", "wenig", "27"), ("Sule", "Schule", "29"),
    ("Straße", "Strasse", "33"), ("Graten", "Garten", "35"),
    ("Bucher", "Bücher", "36"),
]


@pytest.mark.parametrize("schueler,ziel,nummer", README_TABELLE,
                         ids=lambda x: str(x))
def test_readme_beispiele_stimmen_mit_der_engine_ueberein(schueler, ziel, nummer):
    """Die Tabelle im README ist eine Zusage – sie wird hier eingelöst."""
    r = E.klassifiziere_wort(schueler, ziel, E.VORGABE_LEXIKON)
    for e in r["ereignisse"]:
        E.abschliessen(e, {"ziel": ziel}, {"zielwortSicherheit": 1})
    assert [E._erhalten(e) for e in r["ereignisse"]] == [nummer]


def test_readme_tabelle_ist_vollstaendig_abgebildet():
    """Wer eine Zeile ergänzt, ergänzt auch den Test – und umgekehrt."""
    from pathlib import Path
    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
    fehlend = [(s, z) for s, z, _ in README_TABELLE if f"| {z} | {s} |" not in readme]
    assert not fehlend, f"Nicht im README: {fehlend}"
