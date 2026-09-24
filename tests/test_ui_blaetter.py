"""Die Blattseite durchgespielt: Regler → Prompt → JSON-Antwort → Aufgabenkarten → Chip-Prompt → Ersetzen → Speichern."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from rstrainer import db

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest

SEITE = '''
import streamlit as st
from rstrainer import db
from rstrainer.ui import seite_blaetter
con = db.verbinden(st.session_state["_pfad"])
seite_blaetter.zeichnen(con, db.schueler_liste(con)[0])
'''

ANTWORT = """===RSTRAINER-ANFANG===
AUFTRAG: {code}
TYP: uebungsblatt
TITEL: Schärfung üben
---JSON---
{{"aufgaben": [
 {{"nr": 1, "teil": "uebung", "bereich": "F1", "format": "luecke", "strategie": "Verlängern", "merksatz": "Kurzer Vokal, doppelter Mitlaut.",
  "aufgabe": "Setze ein.", "material": "Wir ko___en.", "loesung": "kommen", "punkte": 1, "woerter": ["kommen"]}},
 {{"nr": 2, "teil": "uebung", "bereich": "F1", "format": "sortieren", "strategie": "Hören", "merksatz": "",
  "aufgabe": "Sortiere nach kurzem und langem Vokal.", "material": "Fuss, Fluss, Hütte, Hüte", "loesung": "kurz: Fluss, Hütte; lang: Fuss, Hüte", "punkte": 2, "woerter": ["Fuss", "Fluss"]}},
 {{"nr": 1, "teil": "test", "bereich": "F1", "format": "luecke", "strategie": "", "merksatz": "",
  "aufgabe": "Setze ein.", "material": "Die Kla___e.", "loesung": "Klasse", "punkte": 1, "woerter": ["Klasse"]}}
]}}
===RSTRAINER-ENDE==="""


@pytest.fixture
def seite(tmp_path, monkeypatch):
    monkeypatch.setenv("RSTRAINER_DATEN", str(tmp_path))
    pfad = tmp_path / "test.sqlite3"
    con = db.verbinden(pfad)
    sid = db.schueler_anlegen(con, "Testkind", "8a")
    did = db.diktat_anlegen(con, sid, "Probe", "Wir kommen zum Fuss des Berges.", art="diktat",
                            schuelertext="Wir komen zum Fus des Berges.")
    db.fehler_mehrere_anlegen(con, sid, [
        {"diktat_id": did, "kategorie_nr": "07", "wort_original": "kommen", "wort_schueler": "komen", "kontext": "Wir [kommen]"},
        {"diktat_id": did, "kategorie_nr": "07", "wort_original": "Fuss", "wort_schueler": "Fus", "kontext": "zum [Fuss]"},
    ])
    con.close()
    datei = Path(tempfile.mkdtemp()) / "seite.py"
    datei.write_text(SEITE, encoding="utf-8")
    lauf = AppTest.from_file(str(datei), default_timeout=120)
    lauf.session_state["_pfad"] = pfad
    lauf.pfad = pfad
    return lauf


def _knopf(lauf, text):
    for b in lauf.button:
        if b.label == text:
            return b
    raise AssertionError(f"Knopf «{text}» nicht gefunden: {[b.label for b in lauf.button]}")


def test_blattseite_von_den_reglern_bis_zum_gespeicherten_blatt(seite):
    seite.run()
    assert not seite.exception
    labels = [s.label for s in seite.selectbox]
    assert "Niveau" in labels and "Umfang" in labels and "Übungsebene" in labels
    seite.multiselect[0].set_value(["07"])
    _knopf(seite, "Förderplan und Prompt erzeugen").click().run()
    assert not seite.exception
    md = " ".join(m.value for m in seite.markdown)
    assert "Übungsebene:" in md and "kommen (2" in md or "kommen (1" in md
    code = next(c.value for c in seite.code if "AUFTRAG" in c.value).split("Auftragsnummer: ")[1].split("\n")[0].strip()
    assert code.startswith("RST-UEB-")
    prompt = next(c.value for c in seite.code if "AUFTRAG" in c.value)
    assert "### Förderplan" in prompt and "---JSON---" in prompt and "Lernwörter des Kindes" in prompt

    seite.text_area(key="blatt_eingefuegt").set_value(ANTWORT.format(code=code))
    _knopf(seite, "Ergebnis auswerten").click().run()
    assert not seite.exception
    md = " ".join(m.value for m in seite.markdown)
    assert "1 · F1 · Lückenwörter" in md and "2 · F1 · Nach Regel sortieren" in md
    assert "Merke:" in md

    # Chip wählen und Teilprompt bauen
    _knopf(seite, "Lernwörter des Kindes").click().run()
    assert not seite.exception
    _knopf(seite, "Prompt: Überarbeiten").click().run()
    assert not seite.exception
    teil = [c.value for c in seite.code if "TYP: aufgabe" in c.value]
    assert teil and "Baue die unten genannten Lernwörter" in teil[0] and "RST-AUF-" in teil[0]

    # Antwort einfügen → Aufgabe ersetzt
    neu = {"nr": 1, "teil": "uebung", "bereich": "F1", "format": "luecke", "strategie": "Verlängern", "merksatz": "Neu!",
           "aufgabe": "Ergänze die Lernwörter.", "material": "Wir ko___en zum Fu___.", "loesung": "kommen, Fuss", "punkte": 2, "woerter": ["kommen", "Fuss"]}
    seite.text_area(key="tpa_uebung_1").set_value("---JSON---\n" + json.dumps(neu))
    _knopf(seite, "Aufgabe ersetzen").click().run()
    assert not seite.exception
    md = " ".join(m.value for m in seite.markdown)
    assert "Ergänze die Lernwörter." in md and "Neu!" in md

    # Entfernen der zweiten Übungsaufgabe
    seite.button(key="weg_uebung_2").click().run()
    assert not seite.exception
    md = " ".join(m.value for m in seite.markdown)
    assert "Nach Regel sortieren" not in md

    # Freigabe und Speichern
    for k in ("blatt_pruef_loesungen", "blatt_pruef_niveau", "blatt_freigabe"):
        seite.checkbox(key=k).check()
    seite.run()
    _knopf(seite, "Blatt speichern").click().run()
    assert not seite.exception
    con = db.verbinden(seite.pfad)
    blaetter = db.blatt_liste(con, 1)
    con.close()
    assert len(blaetter) == 1
    aufgaben = json.loads(blaetter[0]["aufgaben"])
    assert [a["teil"] for a in aufgaben] == ["uebung", "test"]
    assert "Merke (F1): Neu!" in blaetter[0]["inhalt_uebung"]
