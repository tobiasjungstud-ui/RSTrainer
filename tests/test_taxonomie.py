"""Tests der gelernten Fehlerarten.

Der Schwerpunkt liegt auf dem, was schiefgehen kann, wenn Einträge ohne
Rückfrage angelegt werden: eine Sammlung, die mit Bedeutungsgleichem
zuwächst – und, schlimmer, eine, die Gegenteiliges zusammenlegt.
"""

from __future__ import annotations

import json

from rstrainer import taxonomie
from rstrainer.kategorien import Register, schwerpunkte


# --- Pfade begradigen -------------------------------------------------------

def test_oberbegriff_wird_auf_die_feste_liste_gezwungen():
    """Sonst stünden nach zwanzig Texten «Grammatik», «Grammatikalisch» und
    «Sprachrichtigkeit» nebeneinander."""
    assert taxonomie.pfad_normalisieren(["grammatik", "kasus"])[0] == "Grammatik"
    assert taxonomie.pfad_normalisieren(["Sprachrichtigkeit", "x"])[0] == "Sonstiges"


def test_pfad_wird_gekuerzt_und_bereinigt():
    pfad = taxonomie.pfad_normalisieren(
        ["  grammatik ", "kasus", "dativ  statt akkusativ", "zuviel"])
    assert pfad == ("Grammatik", "Kasus", "Dativ statt akkusativ")


def test_leerer_pfad_landet_unter_sonstiges():
    assert taxonomie.pfad_normalisieren([]) == ("Sonstiges", "Unbenannt")
    assert taxonomie.pfad_normalisieren(["", "   "]) == ("Sonstiges", "Unbenannt")


# --- Anlegen ----------------------------------------------------------------

def test_gleicher_pfad_wird_nicht_doppelt_angelegt():
    s = taxonomie.Sammlung()
    a = s.anlegen(["Grammatik", "Kasus", "Dativ statt Akkusativ"])
    b = s.anlegen(["grammatik", "KASUS", "dativ statt akkusativ"])
    assert a.id == b.id and len(s) == 1


def test_kennung_ist_als_gelernt_erkennbar():
    """Eine gelernte Art und eine OLFA-Nummer müssen sich unterscheiden lassen,
    ohne dass die Auswertung zwei Datenwege braucht."""
    s = taxonomie.Sammlung()
    art = s.anlegen(["Grammatik", "Kasus"])
    assert taxonomie.ist_gelernt(art.id)
    assert not taxonomie.ist_gelernt("07")


def test_neue_arten_sind_als_ungesehen_markiert():
    s = taxonomie.Sammlung()
    s.anlegen(["Grammatik", "Kasus"])
    assert len(s.ungesehen) == 1


# --- Ähnlichkeit ------------------------------------------------------------

def test_gegenteile_werden_gemeldet_aber_nie_zusammengelegt():
    """«Dativ statt Akkusativ» und «Akkusativ statt Dativ» teilen alle Wörter
    und meinen das Gegenteil. Deshalb ist die Ähnlichkeit ein Hinweis an die
    Lehrperson, nie ein Automatismus."""
    s = taxonomie.Sammlung()
    s.anlegen(["Grammatik", "Kasus", "Dativ statt Akkusativ"])
    s.anlegen(["Grammatik", "Kasus", "Akkusativ statt Dativ"])
    paare = s.aehnliche_paare()
    assert len(paare) == 1 and paare[0][2] == 100
    assert len(s) == 2


def test_verschiedene_oberbegriffe_werden_nicht_verglichen():
    s = taxonomie.Sammlung()
    s.anlegen(["Grammatik", "Komma", "Komma fehlt"])
    s.anlegen(["Zeichensetzung", "Komma", "Komma fehlt"])
    assert s.aehnliche_paare() == []


# --- Speichern --------------------------------------------------------------

def test_speichern_und_laden_erhaelt_alles(tmp_path):
    s = taxonomie.Sammlung()
    art = s.anlegen(["Grammatik", "Kasus", "Dativ statt Akkusativ"], "Erklärung")
    pfad = taxonomie.speichern(s, tmp_path / "arten.json")
    geladen = taxonomie.laden(pfad)
    assert len(geladen) == 1
    zurueck = geladen.get(art.id)
    assert zurueck.pfad == art.pfad
    assert zurueck.beschreibung == "Erklärung"
    assert zurueck.neu is True


def test_gespeicherte_datei_warnt_vor_rueckschluessen(tmp_path):
    s = taxonomie.Sammlung()
    s.anlegen(["Grammatik", "Kasus"])
    pfad = taxonomie.speichern(s, tmp_path / "arten.json")
    inhalt = json.loads(pfad.read_text(encoding="utf-8"))
    assert "hinweis" in inhalt


def test_fehlende_datei_ist_kein_fehler(tmp_path):
    assert len(taxonomie.laden(tmp_path / "gibtsnicht.json")) == 0


# --- Register ---------------------------------------------------------------

def test_register_beschriftet_beide_systeme(liste):
    s = taxonomie.Sammlung()
    art = s.anlegen(["Grammatik", "Kasus", "Dativ statt Akkusativ"])
    reg = Register(liste=liste, sammlung=s)
    assert reg.label("07").startswith("07 – ")
    assert reg.label(art.id) == "Grammatik › Kasus › Dativ statt Akkusativ"
    assert reg.label("gibtsnicht") == "gibtsnicht – (unbekannt)"


def test_register_kuerzt_lange_pfade(liste):
    s = taxonomie.Sammlung()
    art = s.anlegen(["Grammatik", "Verbform", "Falsches Partizip bei starken Verben"])
    reg = Register(liste=liste, sammlung=s)
    assert len(reg.kurz(art.id, 20)) == 20
    assert reg.kurz(art.id, 20).endswith("…")


def test_register_spaltet_name_und_nummer(register):
    """Im CSV steht die Nummer schon in einer eigenen Spalte."""
    assert register.name("07") == "Einfachschreibung für Konsonantenverdoppelung"


def test_gesperrte_kategorien_sind_nicht_waehlbar(register):
    waehlbar = {nr for nr, _ in register.waehlbar()}
    assert "13" not in waehlbar and "15" not in waehlbar
    assert "14" in waehlbar and "16" in waehlbar


def test_bereinigen_lenkt_verschwundene_kennungen_auf_37(register):
    assert register.bereinigen("07") == "07"
    assert register.bereinigen("15") == "37"      # gesperrt
    assert register.bereinigen("X-gibtsnicht") == "37"


# --- Schwerpunkte -----------------------------------------------------------

def _fehler(*paare) -> list[dict]:
    return [{"kategorie_nr": nr} for nr, menge in paare for _ in range(menge)]


def test_schwerpunkte_lassen_den_langen_schwanz_weg():
    punkte = schwerpunkte(_fehler(("07", 10), ("09", 4), ("01", 1), ("19", 1)))
    assert [nr for nr, _ in punkte.liste] == ["07", "09"]
    assert punkte.rest == 2
    assert punkte.gesamt == 16


def test_schwerpunkte_zeigen_notfalls_auch_einzelfaelle():
    """Bei lauter Einzelvorkommen stünde sonst gar nichts da."""
    punkte = schwerpunkte(_fehler(("07", 1), ("09", 1)))
    assert len(punkte.liste) == 2


def test_schwerpunkte_ohne_fehler():
    punkte = schwerpunkte([])
    assert punkte.liste == [] and punkte.gesamt == 0
