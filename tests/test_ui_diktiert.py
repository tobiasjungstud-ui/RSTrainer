"""Diktierte Texte (Sprachsoftware) bleiben in der Auswertung getrennt: Kennwerte,
Förderbereiche und Lernwörter nur aus geschriebenen Texten, Satzbau und Grammatik
der diktierten Texte in einem eigenen Abschnitt."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from rstrainer import auftraege, db, docx_export, pdf_export, prompt_templates as pt
from rstrainer.ui import gemeinsam as g

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest

SEITE = '''
import streamlit as st
from rstrainer import db
from rstrainer.ui import seite_auswertung
con = db.verbinden(st.session_state["_pfad"])
seite_auswertung.zeichnen(con, db.schueler_liste(con)[0])
'''


def _daten(pfad):
    con = db.verbinden(pfad)
    sid = db.schueler_anlegen(con, "Testkind", "8a")
    d1 = db.diktat_anlegen(con, sid, "Diktat", "Der Hund bellt laut.", datum="2026-01-10",
                           schuelertext="Der Hunt belt laut.", freigegeben=True)
    d2 = db.diktat_anlegen(con, sid, "Erzählung diktiert", "", datum="2026-02-10", art="diktiert",
                           schuelertext="Ich habe gegangen zum Zoo weil es hat geregnet.", freigegeben=True)
    db.fehler_anlegen(con, sid, "08", d1, "Hund", "Hunt", kontext="Der Hunt belt")
    db.fehler_anlegen(con, sid, "10", d1, "bellt", "belt", kontext="Der Hunt belt")
    db.fehler_anlegen(con, sid, "B_ZEITFORM", d2, "bin gegangen", "habe gegangen",
                      kontext="Ich habe gegangen zum Zoo")
    db.fehler_anlegen(con, sid, "B_SATZBAU", d2, "weil es geregnet hat", "weil es hat geregnet",
                      kontext="weil es hat geregnet")
    con.close()
    return sid, d1, d2


@pytest.fixture
def seite(tmp_path, monkeypatch):
    monkeypatch.setenv("RSTRAINER_DATEN", str(tmp_path))
    pfad = tmp_path / "test.sqlite3"
    _daten(pfad)
    datei = Path(tempfile.mkdtemp()) / "seite.py"
    datei.write_text(SEITE, encoding="utf-8")
    lauf = AppTest.from_file(str(datei), default_timeout=90)
    lauf.session_state["_pfad"] = pfad
    lauf.pfad = pfad
    return lauf


def test_auswertung_trennt_diktierte_texte(seite):
    seite.run()
    assert not seite.exception
    metriken = {m.label: m.value for m in seite.metric}
    assert metriken["Geschriebene Texte"] == "1"
    assert metriken["Erfasste Fehler"] == "2"            # nur 08 und 10
    assert metriken["Diktierte Texte"] == "1"
    assert metriken["Befunde B–E"] == "2"
    ueberschriften = " ".join(s.value for s in seite.subheader)
    assert "Diktierte Texte (Sprachsoftware)" in ueberschriften
    # Kennwerte nur aus dem geschriebenen Text: 4 Wörter, 2 Fehler → F/100 = 50
    text = " ".join(m.value for m in seite.markdown)
    assert "50" in text
    quelle = next(r for r in seite.radio if r.label == "Textquelle")
    assert quelle.value == "geschrieben"


def test_auswertung_nur_mit_diktierten_texten(tmp_path, monkeypatch):
    monkeypatch.setenv("RSTRAINER_DATEN", str(tmp_path))
    pfad = tmp_path / "nur.sqlite3"
    con = db.verbinden(pfad)
    sid = db.schueler_anlegen(con, "Kind", "7b")
    d = db.diktat_anlegen(con, sid, "Diktiert", "", art="diktiert", schuelertext="Er gehen heim.")
    db.fehler_anlegen(con, sid, "B_KONGRUENZ", d, "geht", "gehen")
    con.close()
    datei = Path(tempfile.mkdtemp()) / "seite.py"
    datei.write_text(SEITE, encoding="utf-8")
    lauf = AppTest.from_file(str(datei), default_timeout=90)
    lauf.session_state["_pfad"] = pfad
    lauf.run()
    assert not lauf.exception
    assert "geschriebenen" in " ".join(i.value for i in lauf.info)
    assert "Diktierte Texte (Sprachsoftware)" in " ".join(s.value for s in lauf.subheader)


def test_prompt_fuer_diktierte_texte_verbietet_rechtschreibkategorien():
    reg = g.register()
    prompt = auftraege.analyse_prompt_bauen("Ich habe gegangen zum Zoo.", "", reg.liste, reg.sammlung,
                                            ohne_rechtschreibung=True)
    assert "Rechtschreibung wird NICHT bewertet" in prompt
    assert "Keine OLFA-Kategorien" in prompt
    assert "Ich habe gegangen zum Zoo." in prompt
    normal = auftraege.analyse_prompt_bauen("Ich habe gegangen zum Zoo.", "", reg.liste, reg.sammlung)
    assert "NICHT bewertet" not in normal
    assert pt.ANALYSE_DIKTIERT.count("{") == pt.ANALYSE_DIKTIERT.count("}")


@pytest.mark.parametrize("modul, endung", [(docx_export, "docx"), (pdf_export, "pdf")])
def test_infoblatt_bezeichnet_diktierte_texte(tmp_path, modul, endung):
    fehler = [{"kategorie_nr": "B_KONGRUENZ", "wort_original": "geht", "wort_schueler": "gehen",
               "kontext": "Er gehen heim.", "datum": "2026-02-10", "notiz": ""}]
    pfad = modul.informationsblatt_schreiben(
        tmp_path / f"ib.{endung}", "Kind", "Diktiert", "2026-02-10", fehler, g.register(),
        None, "", "Er gehen heim.", art="diktiert")
    assert pfad.exists() and pfad.stat().st_size > 0
    if endung == "docx":
        from docx import Document
        text = "\n".join(a.text for a in Document(pfad).paragraphs)
        assert "Diktierter Text (Sprachsoftware)" in text
        assert "Text des Kindes" in text
