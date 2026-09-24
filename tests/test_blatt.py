"""Übungsblätter als Aufgabenliste: Förderplan, Prüfung, Teilprompt."""
import json

from rstrainer import auftraege, blatt, olfa
from rstrainer import prompt_templates as pt


def _fehler(nr, orig, sch, n=1):
    return [{"kategorie_nr": nr, "wort_original": orig, "wort_schueler": sch, "diktat_id": 1} for _ in range(n)]


FEHLER = (_fehler("07", "kommen", "komen", 3) + _fehler("07", "Fuss", "Fus", 2) + _fehler("09", "Zahn", "Zan")
          + _fehler("29", "nicht", "nich", 4) + _fehler("31", "haben", "habn", 3) + _fehler("33", "Ball", "Pall"))


def test_ebene_nach_kompetenzwert_s36():
    assert blatt.ebene_bestimmen(30, 0.3) == "lautebene"
    assert blatt.ebene_bestimmen(60, 0.3) == "gemischt"
    assert blatt.ebene_bestimmen(80, 0.1) == "regelebene"
    assert blatt.ebene_bestimmen(80, 0.6) == "lautebene"      # Gruppe I dominant (S. 24, 49)
    assert blatt.ebene_bestimmen(None, None) == "gemischt"


def test_foerderplan_sammelt_lernwoerter_wiederholungen_zuerst():
    plan = blatt.foerderplan(["F1", "F2"], FEHLER, 200)
    assert plan.bereiche == ["F1", "F2"]
    f1 = plan.lernwoerter["F1"]
    assert [w.ziel for w in f1] == ["kommen", "Fuss"]
    assert f1[0].anzahl == 3 and f1[0].schueler == "komen"
    assert plan.lernwoerter["F2"][0].ziel == "Zahn"
    assert plan.kw is not None and plan.ebene == "lautebene"     # 8 von 14 Fehlern in Gruppe I


def test_foerderplan_override_und_umfang():
    plan = blatt.foerderplan(["07"], FEHLER, 200, anspruch="anspruchsvoll", umfang="lang", ebene="regelebene")
    assert plan.bereiche == ["F1"]
    assert plan.ebene == "regelebene" and "gewählt" in plan.ebene_grund
    assert (plan.aufgaben_je_bereich, plan.test_aufgaben) == (4, 8)
    assert "fehlersuche" in plan.formate and "gliedern" in plan.verboten


def test_foerderplan_block_im_prompt(liste):
    plan = blatt.foerderplan(["F1"], FEHLER, 200)
    block = blatt.foerderplan_block(plan)
    assert "Lautebene" in block and "kommen (3×, schrieb «komen»)" in block and "Verlängerungsprobe" in block
    _, prompt = auftraege.prompt_bauen("uebungsblatt", {
        "kategorien": ["07"], "schwierigkeit": "leicht", "bearbeitungszeit": "20 Minuten",
        "foerderplan_text": block}, liste)
    assert "### Förderplan" in prompt and pt.MARKE_JSON in prompt and '"strategie"' in prompt


ANTWORT = """Hier das Blatt:
===RSTRAINER-ANFANG===
AUFTRAG: RST-UEB-ABC123
TYP: uebungsblatt
TITEL: Schärfung üben
---JSON---
{"aufgaben": [
 {"nr": 1, "teil": "uebung", "bereich": "F1", "format": "luecke", "strategie": "Verlängern und hören", "merksatz": "Hör den kurzen Vokal – dann verdoppelt sich der Mitlaut.",
  "aufgabe": "Setze ein.", "material": "Wir ko___en morgen. Der Fu___ tut weh.", "loesung": "kommen, Fuss", "punkte": 2, "woerter": ["kommen", "Fuss"]},
 {"nr": 2, "teil": "uebung", "bereich": "F1", "format": "fehlersuche", "strategie": "Verlängern", "merksatz": "",
  "aufgabe": "Finde 2 Fehler.", "material": "Die Kater komen zur Hütte.", "loesung": "kommen, Katze", "punkte": 2, "woerter": ["kommen"],
  "fehler": [{"falsch": "komen", "richtig": "kommen"}, {"falsch": "Kater", "richtig": "Käter"}]},
 {"nr": 1, "teil": "test", "bereich": "F1", "format": "luecke", "strategie": "", "merksatz": "",
  "aufgabe": "Setze ein.", "material": "Die Kla___e ist gross.", "loesung": "Klasse", "punkte": 1, "woerter": ["Klasse"]}
]}
===RSTRAINER-ENDE==="""


def test_antwort_mit_json_wird_zu_aufgaben_und_text():
    e = auftraege.ergebnis_lesen(ANTWORT, "RST-UEB-ABC123", "uebungsblatt")
    assert e.titel == "Schärfung üben" and len(e.aufgaben) == 3
    assert "Merke (F1): Hör den kurzen Vokal" in e.uebungsteil
    assert "1. [F1] Setze ein." in e.testteil and "Erreichte Punkte: ____ von 1" in e.testteil
    assert "Übung 1: kommen, Fuss" in e.loesungen and "kommen" not in e.uebungsteil.replace("komen", "")


def test_pruefung_findet_fremden_fehler_und_verbotenes_format():
    e = auftraege.ergebnis_lesen(ANTWORT)
    plan = blatt.foerderplan(["F1"], FEHLER, 200, ebene="lautebene")
    befunde = blatt.aufgaben_pruefen(e.aufgaben, plan)
    texte = [b["text"] for b in befunde]
    assert any("Fehlersuche" in t and "nicht vorgesehen" in t for t in texte)          # Lautebene: keine Fehlersuche
    assert any("«Kater» → «Käter»" in t and "gehört also nicht zu F1" in t for t in texte)  # Engine: 36, nicht F1
    assert not any("komen" in t for t in texte)                                        # 07 gehört zu F1


def test_pruefung_lernwoerter_und_test_nicht_leichter():
    e = auftraege.ergebnis_lesen(ANTWORT)
    plan = blatt.foerderplan(["F1"], FEHLER, 200, ebene="gemischt")
    befunde = blatt.aufgaben_pruefen(e.aufgaben, plan)
    assert not any("Kein Lernwort" in b["text"] for b in befunde)      # kommen und Fuss kommen vor
    aufgaben = blatt.aufgabe_ersetzen(e.aufgaben, "uebung", 1, {**e.aufgaben[0], "woerter": ["Hütte"], "material": "Hü___e"})
    befunde = blatt.aufgaben_pruefen(aufgaben, plan)
    assert any("Lernwörter noch nicht geübt" in b["text"] or "Kein Lernwort" in b["text"] for b in befunde)
    assert any(b["teil"] == "test" and "gestützter" in b["text"] for b in befunde)


def test_eszett_wird_gemeldet():
    a = {"nr": 1, "teil": "uebung", "bereich": "F1", "format": "luecke", "strategie": "", "merksatz": "",
         "aufgabe": "Setze ein", "material": "Die Stra___e", "loesung": "Straße", "punkte": 1, "woerter": [], "fehler": []}
    plan = blatt.foerderplan(["F1"], [], 0)
    assert any("ß" in b["text"] for b in blatt.aufgaben_pruefen([a], plan))


def test_aufgaben_bearbeiten():
    e = auftraege.ergebnis_lesen(ANTWORT)
    a = blatt.aufgabe_entfernen(e.aufgaben, "uebung", 1)
    assert [x["nr"] for x in a if x["teil"] == "uebung"] == [1]
    b = blatt.aufgabe_verschieben(e.aufgaben, "uebung", 2, -1)
    assert b[0]["format"] == "fehlersuche" and b[0]["nr"] == 1


def test_teilprompt_und_antwort():
    e = auftraege.ergebnis_lesen(ANTWORT)
    plan = blatt.foerderplan(["F1"], FEHLER, 200)
    code, text = blatt.teilprompt_bauen(e.aufgaben[0], plan, "ueberarbeiten", chip="lernwoerter", hinweis="bitte mit Tieren")
    assert code.startswith("RST-AUF-") and "Lernwörter des Kindes" in text and "bitte mit Tieren" in text
    assert "kommen (schrieb «komen»)" in text and "TYP: aufgabe" in text
    neu, hinweise = blatt.aufgabe_lesen("===RSTRAINER-ANFANG===\nAUFTRAG: X\nTYP: aufgabe\n---JSON---\n"
                                        + json.dumps({**e.aufgaben[0], "material": "Neu ___"}) + "\n===RSTRAINER-ENDE===")
    assert hinweise == [] and neu["material"] == "Neu ___"
    ersetzt = blatt.aufgabe_ersetzen(e.aufgaben, "uebung", 1, neu)
    assert ersetzt[0]["material"] == "Neu ___" and ersetzt[0]["nr"] == 1
    _, text2 = blatt.teilprompt_bauen(e.aufgaben[0], plan, "austauschen")
    assert "NEUE Aufgabe" in text2


def test_chips_sind_wenige_und_benannt():
    assert 4 <= len(blatt.CHIPS) <= 8
    assert all(c["name"] and c["anweisung"] for c in blatt.CHIPS.values())


def test_alte_textantwort_bleibt_lesbar():
    alt = ("===RSTRAINER-ANFANG===\nAUFTRAG: RST-UEB-1\nTYP: uebungsblatt\nTITEL: Alt\n---UEBUNGSBLATT---\n1. A\n"
           "---MINITEST---\n1. B\n---LOESUNGEN---\n1. C\n===RSTRAINER-ENDE===")
    e = auftraege.ergebnis_lesen(alt)
    assert e.aufgaben == [] and e.uebungsteil == "1. A" and e.testteil == "1. B"


def test_blatt_mit_aufgaben_in_der_datenbank(con, schueler_id):
    from rstrainer import db
    aufgaben = auftraege.ergebnis_lesen(ANTWORT).aufgaben
    bid = db.blatt_anlegen(con, schueler_id, "T", ["07"], "u", "t", "l", aufgaben=aufgaben)
    row = db.blatt_holen(con, bid)
    assert len(json.loads(row["aufgaben"])) == 3
