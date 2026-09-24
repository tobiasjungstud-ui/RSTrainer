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
    assert len(modus.options) == 1            # ohne Vorlage kein Diktatmodus
    assert any(t.value.startswith("Ich ging zum Zahn arzt")
               for t in seite.text_area if t.label == "Text des Kindes")


def test_weitere_texte_lassen_sich_ohne_seitenwechsel_nachtragen(seite):
    seite.run()
    seite.text_input[0].set_value("Aufsatz 1")
    seite.text_area[0].set_value("Ich ging zum Zahn arzt.")
    seite.button[0].click().run()
    assert "📝 Weiteren freien Text erfassen" in [e.label for e in seite.get("expander")]


def test_diktierter_text_wird_getrennt_gefuehrt(seite):
    """Diktierte Texte (Sprachsoftware): markierbar, keine OLFA-Analyse, nur B–E."""
    seite.run()
    seite.text_input[0].set_value("Erzählung diktiert")
    art = next(r for r in seite.radio if r.label == "Art des Textes")
    art.set_value("diktiert")
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

    text = " ".join(i.value for i in seite.info) + " " + " ".join(w.value for w in seite.warning)
    assert "Diktierter Text" in text
    assert "Keine OLFA-Analyse" in text
    # Kein Analysemodus (Diktat/Freitext) mehr – die OLFA-Analyse ist abgeschaltet.
    assert not [r for r in seite.radio if r.label == "Modus der Fehleranalyse"]
    assert " · diktiert" in seite.selectbox[0].format_func(texte[0]["id"])
