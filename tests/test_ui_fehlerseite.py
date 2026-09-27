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


def _radio(seite, label):
    return next(r for r in seite.radio if r.label == label)


def _neu_speichern(seite, titel, text):
    seite.text_input[0].set_value(titel)
    seite.text_area[0].set_value(text)
    seite.button[0].click().run()
    assert not seite.exception


def test_ohne_text_steht_die_erfassung_gleich_auf_der_seite(seite):
    """Keine Sackgasse: Ohne einen einzigen Text steht die Erfassung direkt da."""
    seite.run()
    assert not seite.exception
    assert _radio(seite, "Modus").value == "diktat"
    # Ohne Vorlage im Profil steht der Diktat-Umschalter auf «ohne Vorlage».
    assert _radio(seite, "Woher stammt der Diktattext?").value == "frei"
    assert [t.label for t in seite.text_area] == ["Text des Kindes *"]
    assert "Titel *" in [t.label for t in seite.text_input]
    assert "Bitte zuerst unter" not in " ".join(i.value for i in seite.info)


def test_es_gibt_genau_drei_modi_und_den_umschalter_nur_beim_diktat(seite):
    seite.run()
    modus = _radio(seite, "Modus")
    assert len(modus.options) == 3
    for wert in ("freitext", "diktiert"):
        modus.set_value(wert).run()
        assert not seite.exception
        assert not [r for r in seite.radio if r.label == "Woher stammt der Diktattext?"]
        modus = _radio(seite, "Modus")
    modus.set_value("diktat").run()
    assert _radio(seite, "Woher stammt der Diktattext?")


def test_hier_erfasster_text_ist_sofort_ausgewaehlt_und_im_freitextmodus(seite):
    seite.run()
    _radio(seite, "Modus").set_value("freitext").run()
    _neu_speichern(seite, "Aufsatz Herbstferien", "Ich ging zum Zahn arzt und die Straße war gros.")

    verbindung = db.verbinden(seite.pfad)
    texte = db.diktat_liste(verbindung, 1)
    verbindung.close()
    assert [(t["titel"], t["art"], t["wortzahl"]) for t in texte] == [
        ("Aufsatz Herbstferien", "freitext", 10)]
    assert seite.selectbox[0].value == texte[0]["id"]
    assert any(t.value.startswith("Ich ging zum Zahn arzt")
               for t in seite.text_area if t.label == "Text des Kindes")


def test_weitere_texte_lassen_sich_ohne_seitenwechsel_nachtragen(seite):
    seite.run()
    _radio(seite, "Modus").set_value("freitext").run()
    _neu_speichern(seite, "Aufsatz 1", "Ich ging zum Zahn arzt.")
    assert seite.selectbox[0].value != "__neu__"          # der neue Text ist ausgewählt
    assert "__neu__" in seite.selectbox[0].options or any(
        "Neuen Text" in seite.selectbox[0].format_func(o) for o in seite.selectbox[0].options)
    seite.selectbox[0].set_value("__neu__").run()
    assert not seite.exception
    assert "Titel *" in [t.label for t in seite.text_input]


def test_diktat_ohne_vorlage_zaehlt_zur_rechtschreibung(seite):
    """Diktat aus einem anderen Lehrmittel: Modus Diktat, Umschalter «ohne
    Vorlage». Gespeichert als Diktat ohne Vorlage, Wortzahl aus dem Text des
    Kindes, Zielwörter über das Sprachmodell – und es zählt normal."""
    seite.run()
    _neu_speichern(seite, "Diktat Lesebuch S. 42", "Der Fuchs und die Trauben waren reif.")
    verbindung = db.verbinden(seite.pfad)
    t = db.diktat_liste(verbindung, 1)[0]
    assert (t["art"], t["text_original"], t["wortzahl"]) == ("diktat", "", 7)
    assert not db.hat_vorlage(t)
    assert len(db.diktat_liste(verbindung, 1, textart="geschrieben")) == 1
    verbindung.close()
    assert "Diktat ohne Vorlage" in " ".join(c.value for c in seite.caption)


def test_diktat_mit_vorlage_aus_dem_tool(tmp_path, monkeypatch):
    monkeypatch.setenv("RSTRAINER_DATEN", str(tmp_path))
    pfad = tmp_path / "vorlage.sqlite3"
    con = db.verbinden(pfad)
    sid = db.schueler_anlegen(con, "Kind", "8a")
    vid = db.diktat_anlegen(con, sid, "Herbstdiktat", "Der Hund bellt laut.",
                            schuelertext="Der Hunt belt laut.")
    db.diktat_anlegen(con, sid, "Aufsatz", "", art="freitext", schuelertext="Ich schreibe.")
    con.close()
    datei = Path(tempfile.mkdtemp()) / "seite.py"
    datei.write_text(SEITE, encoding="utf-8")
    lauf = AppTest.from_file(str(datei), default_timeout=90)
    lauf.session_state["_pfad"] = pfad
    lauf.run()
    assert not lauf.exception
    # Mit Vorlagen im Profil steht der Umschalter auf «Vorlage aus dem Tool».
    assert _radio(lauf, "Woher stammt der Diktattext?").value == "tool"
    assert lauf.selectbox[0].label == "Vorlage"
    assert lauf.selectbox[0].options == [lauf.selectbox[0].format_func(vid)]  # nur Vorlagen, kein «neu»
    assert "exakter Abgleich" in " ".join(c.value for c in lauf.caption)
    # Umschalten auf «ohne Vorlage» zeigt die Vorlage nicht mehr, den Aufsatz auch nicht.
    _radio(lauf, "Woher stammt der Diktattext?").set_value("frei").run()
    assert not lauf.exception
    assert lauf.selectbox[0].options == ["✍️ Neuen Text eingeben"]


def test_ohne_vorlage_im_profil_zeigt_der_tool_weg_einen_hinweis(seite):
    seite.run()
    _radio(seite, "Woher stammt der Diktattext?").set_value("tool").run()
    assert not seite.exception
    assert "Noch keine Vorlage" in " ".join(i.value for i in seite.info)


def test_freies_diktat_wird_getrennt_gefuehrt(seite):
    """Freies Diktat (Diktierfunktion): Rechtschreibung wird geprüft, zählt
    aber zum eigenen Profil – nicht zur allgemeinen Auswertung."""
    seite.run()
    _radio(seite, "Modus").set_value("diktiert").run()
    _neu_speichern(seite, "Erzählung diktiert", "Ich habe gegangen zum Zoo weil es hat geregnet.")
    verbindung = db.verbinden(seite.pfad)
    texte = db.diktat_liste(verbindung, 1)
    assert [(t["titel"], t["art"], t["quelle"]) for t in texte] == [
        ("Erzählung diktiert", "diktiert", "diktiert")]
    assert db.diktat_liste(verbindung, 1, textart="geschrieben") == []
    verbindung.close()
    info = " ".join(i.value for i in seite.info)
    assert "Freies Diktat" in info and "eigenen Fehlerprofil" in info
    assert "abgeschaltet" not in info


def test_falsch_eingeordneter_text_laesst_sich_umstellen(seite):
    seite.run()
    _radio(seite, "Modus").set_value("freitext").run()
    _neu_speichern(seite, "Eigentlich diktiert", "Ich habe gegangen zum Zoo.")
    _radio(seite, "Richtiger Modus").set_value("diktiert")
    next(b for b in seite.button if b.label == "Umstellen").click().run()
    assert not seite.exception
    verbindung = db.verbinden(seite.pfad)
    assert db.diktat_liste(verbindung, 1)[0]["art"] == "diktiert"
    verbindung.close()
    assert _radio(seite, "Modus").value == "diktiert"
    assert "Eigentlich diktiert" in seite.selectbox[0].format_func(seite.selectbox[0].value)
