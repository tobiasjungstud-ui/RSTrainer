"""Die Fehleranalyse-Seite darf keine Sackgasse sein.

Wer einen frei geschriebenen Schülertext auswerten will, soll ihn dort eingeben
können, wo er ihn auswertet. Vorher stand auf der leeren Seite nur «Bitte zuerst
unter Texte … erfassen» – ein Verweis auf eine andere Seite statt eines Wegs.

Diese Tests fahren die Seite mit ``streamlit.testing`` durch. Sie sind die
einzigen Oberflächentests der Suite und decken bewusst nur diesen einen Weg ab:
Er ist derjenige, an dem die Benutzung tatsächlich hängen geblieben ist.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from rstrainer import db

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest

SEITE = '''
import streamlit as st
from rstrainer import db
from rstrainer.ui import seite_fehler
con = db.verbinden(st.session_state["_pfad"])
seite_fehler.zeichnen(con, db.schueler_liste(con)[0])
'''


@pytest.fixture
def seite(tmp_path, monkeypatch):
    """Eine Datenbank mit genau einem Profil und ohne Text."""
    monkeypatch.setenv("RSTRAINER_DATEN", str(tmp_path))
    pfad = tmp_path / "test.sqlite3"
    verbindung = db.verbinden(pfad)
    db.schueler_anlegen(verbindung, "Testkind", "8a")
    verbindung.close()

    datei = Path(tempfile.mkdtemp()) / "seite.py"
    datei.write_text(SEITE, encoding="utf-8")
    lauf = AppTest.from_file(str(datei), default_timeout=90)
    lauf.session_state["_pfad"] = pfad
    lauf.pfad = pfad
    return lauf


def test_ohne_text_steht_die_erfassung_gleich_auf_der_seite(seite):
    seite.run()
    assert not seite.exception
    assert [t.label for t in seite.text_area] == ["Text des Kindes *"]
    assert "Titel *" in [t.label for t in seite.text_input]
    hinweis = " ".join(i.value for i in seite.info)
    assert "noch kein Text erfasst" in hinweis
    assert "Bitte zuerst unter" not in hinweis


def test_hier_erfasster_text_ist_sofort_ausgewaehlt_und_im_freitextmodus(seite):
    seite.run()
    seite.text_input[0].set_value("Aufsatz Herbstferien")
    seite.text_area[0].set_value("Ich ging zum Zahn arzt und die Straße war gros.")
    seite.button[0].click().run()
    assert not seite.exception

    verbindung = db.verbinden(seite.pfad)
    texte = db.diktat_liste(verbindung, 1)
    verbindung.close()
    assert [(t["titel"], t["art"], t["wortzahl"]) for t in texte] == [
        ("Aufsatz Herbstferien", "freitext", 10)]

    assert seite.selectbox[0].value == texte[0]["id"]
    modus = next(r for r in seite.radio if r.label == "Modus der Fehleranalyse")
    assert modus.value == "freitext"
    assert len(modus.options) == 2            # ohne Vorlage: Freitextmodus oder Sprachdiktat
    assert any(t.value.startswith("Ich ging zum Zahn arzt")
               for t in seite.text_area if t.label == "Text des Kindes")


def test_weitere_texte_lassen_sich_ohne_seitenwechsel_nachtragen(seite):
    """Die Textwahl oben bietet «Freier Text – neu» dauerhaft an – auch wenn
    schon Texte da sind, ohne Seitenwechsel."""
    seite.run()
    seite.text_input[0].set_value("Aufsatz 1")
    seite.text_area[0].set_value("Ich ging zum Zahn arzt.")
    seite.button[0].click().run()
    assert seite.selectbox[0].value != "__neu__"          # der neue Text ist ausgewählt
    assert "__neu__" in seite.selectbox[0].options or any(
        "Freier Text – neu" in seite.selectbox[0].format_func(o) for o in seite.selectbox[0].options)
    seite.selectbox[0].set_value("__neu__").run()
    assert not seite.exception
    assert "Titel *" in [t.label for t in seite.text_input]
    modus = next(r for r in seite.radio if r.label == "Modus der Fehleranalyse")
    assert modus.value == "freitext" and len(modus.options) == 2   # frei: Freitextmodus oder Sprachdiktat, kein Diktatmodus


def test_diktierter_text_wird_getrennt_gefuehrt(seite):
    """Sprachdiktat: «Freier Text – neu» wählen, Modus Sprachdiktat, speichern.
    Kein Vorab-Markieren, keine OLFA-Analyse, nur B–E – und jederzeit wieder
    auf Freitextmodus umstellbar."""
    seite.run()
    seite.text_input[0].set_value("Erzählung diktiert")
    modus_neu = next(r for r in seite.radio if r.label == "Modus der Fehleranalyse")
    assert modus_neu.value == "freitext" and len(modus_neu.options) == 2   # kein Diktatmodus für freien Text
    modus_neu.set_value("sprachdiktat")
    seite.text_area[0].set_value("Ich habe gegangen zum Zoo weil es hat geregnet.")
    seite.button[0].click().run()
    assert not seite.exception

    verbindung = db.verbinden(seite.pfad)
    texte = db.diktat_liste(verbindung, 1)
    assert [(t["titel"], t["art"], t["quelle"]) for t in texte] == [
        ("Erzählung diktiert", "diktiert", "diktiert")]
    assert db.diktat_liste(verbindung, 1, textart="geschrieben") == []
    assert len(db.diktat_liste(verbindung, 1, textart="diktiert")) == 1
    verbindung.close()

    text = " ".join(i.value for i in seite.info)
    assert "Sprachdiktat" in text and "OLFA-Analyse würde das Bild verfälschen" in text
    modus2 = next(r for r in seite.radio if r.label == "Modus der Fehleranalyse")
    assert modus2.value == "sprachdiktat"
    assert " · Sprachdiktat" in seite.selectbox[0].format_func(texte[0]["id"])

    # Und zurück: einfach wieder Freitextmodus anklicken.
    modus2.set_value("freitext").run()
    assert not seite.exception
    verbindung2 = db.verbinden(seite.pfad)
    assert db.diktat_liste(verbindung2, 1, textart="diktiert") == []
    verbindung2.close()
