"""Feste Kategorienliste für Grammatik, Syntax, Zeichensetzung, Textebene."""

from __future__ import annotations

import pytest

from rstrainer import auftraege, grammatik, olfa, taxonomie
from rstrainer.kategorien import Register


@pytest.fixture
def reg():
    return Register(liste=olfa.laden(), sammlung=taxonomie.Sammlung())


def test_katalog_ist_vollstaendig_und_eindeutig():
    assert len(grammatik.KATALOG) >= 30
    for k in grammatik.KATALOG.values():
        assert k.bereich in "BCDE", k.id
        assert k.name and k.beschreibung and k.foerdern, k.id
        assert ":" in k.id and k.id.split(":")[1]


def test_jeder_bereich_hat_kategorien_und_foerderhinweis():
    for b in "BCDE":
        assert grammatik.nach_bereich(b), b
        assert grammatik.BEREICHE[b]["foerdern"]


def test_keine_deutschland_schreibung_im_katalog():
    """Ein Katalog für die Schweiz enthält kein ß in seiner eigenen Prosa."""
    for k in grammatik.KATALOG.values():
        for feld in (k.name, k.beschreibung, k.foerdern):
            assert "ß" not in feld, k.id


def test_helvetismen_sind_ausdruecklich_erlaubt():
    text = grammatik.prompt_zeilen()
    assert "das Tram" in text and "Helvetismen" in grammatik.KATALOG["B:Genus"].beschreibung


def test_bereich_von_folgt_der_kennung():
    assert grammatik.bereich_von("07") == "A"
    assert grammatik.bereich_von("B:Kasus") == "B"
    assert grammatik.bereich_von("D:Komma Nebensatz") == "D"
    assert grammatik.bereich_von("X-abc") == "A"


def test_label_auch_fuer_altbestand_ohne_katalogeintrag():
    assert grammatik.label("B:Kasus") == "Grammatik / Morphologie › Kasus"
    assert grammatik.label("B:Fall") == "Grammatik / Morphologie › Fall"


# --- Register -----------------------------------------------------------------

def test_register_beschriftet_katalogkennungen(reg):
    assert reg.label("B:Kasus").endswith("› Kasus")
    assert reg.name("D:Direkte Rede") == "Direkte Rede"
    assert reg.oberbegriff("C:Satzklammer") == "Syntax"
    assert reg.existiert("E:Wortwahl")
    assert reg.bereinigen("E:Wortwahl") == "E:Wortwahl"


def test_register_ordnet_jedem_eintrag_einen_bereich_zu(reg):
    assert reg.bereich("07") == "A"
    assert reg.bereich("B:Kasus") == "B"
    s = taxonomie.Sammlung()
    art = s.anlegen(["Zeichensetzung", "Komma", "vor aber fehlt"])
    reg2 = Register(liste=olfa.laden(), sammlung=s)
    assert reg2.bereich(art.id) == "D"


def test_katalog_ist_waehlbar(reg):
    kennungen = [nr for nr, _ in reg.waehlbar()]
    assert "B:Kasus" in kennungen and "07" in kennungen


# --- Analyse-Prompt und Rücklesen ---------------------------------------------

def test_analyse_prompt_nennt_den_katalog_vor_den_eigenen_arten():
    prompt = auftraege.analyse_prompt_bauen("Text", "", olfa.laden(), taxonomie.Sammlung())
    assert "B:Kasus" in prompt and "D:Komma Nebensatz" in prompt
    assert prompt.index("B:Kasus") < prompt.index("Weg 3")
    assert "Helvetismen" in prompt


def test_katalogkennung_wird_beim_lesen_uebernommen():
    roh = '[{"richtig": "ihm", "geschrieben": "ihn", "typ": "bekannt", "kategorie": "B:Kasus"}]'
    e = auftraege.analyse_lesen(roh, olfa.laden(), taxonomie.Sammlung())
    assert e.zeilen[0].kategorie_nr == "B:Kasus"
    assert e.neue_arten == []


def test_katalogkennung_zaehlt_auch_mit_falschem_typ():
    roh = '[{"richtig": "ihm", "geschrieben": "ihn", "typ": "neu", "kategorie": "D:Komma", "pfad": []}]'
    e = auftraege.analyse_lesen(roh, olfa.laden(), taxonomie.Sammlung())
    assert e.zeilen[0].kategorie_nr == "D:Komma"


def test_erfundene_katalogkennung_faellt_zurueck():
    roh = '[{"richtig": "a", "geschrieben": "b", "typ": "bekannt", "kategorie": "B:Erfunden"}]'
    e = auftraege.analyse_lesen(roh, olfa.laden(), taxonomie.Sammlung())
    assert e.zeilen[0].kategorie_nr == "37"
