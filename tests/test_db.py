"""Tests der Datenhaltung, Profiltrennung und Freigabe-Nachweise."""

from __future__ import annotations

import json

import pytest

from rstrainer import db


# --- Profile ----------------------------------------------------------------

def test_profil_anlegen_und_holen(con):
    sid = db.schueler_anlegen(con, "Testkind", "Notiz")
    schueler = db.schueler_holen(con, sid)
    assert schueler["anzeigename"] == "Testkind"
    assert schueler["notiz"] == "Notiz"
    assert schueler["aktiv"] == 1


def test_profil_hat_kein_kuerzel_und_keine_klasse(con, schueler_id):
    """Beides wurde bewusst entfernt: zwei personenbezogene Felder weniger."""
    schueler = db.schueler_holen(con, schueler_id)
    assert set(schueler.keys()) == {"id", "anzeigename", "notiz", "angelegt_am",
                                    "aktiv"}


def test_leerer_name_wird_abgelehnt(con):
    with pytest.raises(ValueError):
        db.schueler_anlegen(con, "   ")


def test_profile_werden_alphabetisch_sortiert(con):
    for name in ["Zoe", "anna", "Max"]:
        db.schueler_anlegen(con, name)
    assert [s["anzeigename"] for s in db.schueler_liste(con)] == ["anna", "Max", "Zoe"]


def test_profil_aktualisieren(con, schueler_id):
    db.schueler_aktualisieren(con, schueler_id, anzeigename="Neu", notiz="neu")
    schueler = db.schueler_holen(con, schueler_id)
    assert schueler["anzeigename"] == "Neu" and schueler["notiz"] == "neu"


def test_unbekannte_felder_werden_ignoriert(con, schueler_id):
    db.schueler_aktualisieren(con, schueler_id, gibtsnicht="x")
    assert db.schueler_holen(con, schueler_id) is not None


# --- Datentrennung zwischen Profilen ---------------------------------------

def test_profile_sehen_die_daten_des_anderen_nicht(con):
    """Kernanforderung: jedes Profil hat eine eigene, isolierte Datengrundlage."""
    a = db.schueler_anlegen(con, "Kind A")
    b = db.schueler_anlegen(con, "Kind B")
    diktat_a = db.diktat_anlegen(con, a, "Diktat A", "Text A")
    db.diktat_anlegen(con, b, "Diktat B", "Text B")
    db.fehler_anlegen(con, a, "07", diktat_a, "kommen", "komen")

    assert [d["titel"] for d in db.diktat_liste(con, a)] == ["Diktat A"]
    assert [d["titel"] for d in db.diktat_liste(con, b)] == ["Diktat B"]
    assert len(db.fehler_liste(con, a)) == 1
    assert db.fehler_liste(con, b) == []


def test_loeschen_raeumt_alle_zugehoerigen_daten_ab(con):
    a = db.schueler_anlegen(con, "Kind A")
    b = db.schueler_anlegen(con, "Kind B")
    diktat_a = db.diktat_anlegen(con, a, "D", "T")
    db.fehler_anlegen(con, a, "07", diktat_a)
    db.blatt_anlegen(con, a, "Blatt", ["07"], "u", "t")
    diktat_b = db.diktat_anlegen(con, b, "D", "T")
    db.fehler_anlegen(con, b, "07", diktat_b)

    db.schueler_loeschen(con, a)

    assert db.schueler_holen(con, a) is None
    assert db.diktat_liste(con, a) == []
    assert db.fehler_liste(con, a) == []
    assert db.blatt_liste(con, a) == []
    # Das andere Profil bleibt unangetastet
    assert len(db.diktat_liste(con, b)) == 1
    assert len(db.fehler_liste(con, b)) == 1


# --- Diktate und Freigaben --------------------------------------------------

def test_diktat_ist_ohne_freigabe_angelegt(con, schueler_id):
    """Grundsatz: nichts gelangt ungeprüft in den Verlauf."""
    did = db.diktat_anlegen(con, schueler_id, "D", "Ein kurzer Text")
    diktat = db.diktat_holen(con, did)
    assert diktat["freigegeben"] == 0
    assert diktat["freigegeben_am"] is None


def test_wortzahl_wird_automatisch_berechnet(con, schueler_id):
    did = db.diktat_anlegen(con, schueler_id, "D", "Eins zwei drei vier.")
    assert db.diktat_holen(con, did)["wortzahl"] == 4


def test_freigabe_wird_mit_zeitstempel_festgehalten(con, schueler_id):
    did = db.diktat_anlegen(con, schueler_id, "D", "Text")
    db.diktat_freigeben(con, did)
    diktat = db.diktat_holen(con, did)
    assert diktat["freigegeben"] == 1
    assert diktat["freigegeben_am"]


def test_korrekturlesen_ist_kein_eigener_schritt_mehr(con, schueler_id):
    """Die Sperre wurde entfernt – die Freigabe ist der einzige Nachweis."""
    did = db.diktat_anlegen(con, schueler_id, "D", "Text")
    assert "korrektur_gelesen" not in db.diktat_holen(con, did).keys()
    assert not hasattr(db, "diktat_korrektur_bestaetigen")


# --- Freie Texte ------------------------------------------------------------

def test_freitext_zaehlt_die_woerter_des_kindes(con, schueler_id):
    """Ohne Vorlage gibt es nichts anderes zu zählen als den Text selbst."""
    did = db.diktat_anlegen(con, schueler_id, "Aufsatz", "",
                            art="freitext", schuelertext="Eins zwei drei.")
    diktat = db.diktat_holen(con, did)
    assert diktat["art"] == "freitext"
    assert diktat["wortzahl"] == 3
    assert diktat["text_original"] == ""


def test_freitext_fuehrt_die_wortzahl_nach(con, schueler_id):
    did = db.diktat_anlegen(con, schueler_id, "Aufsatz", "",
                            art="freitext", schuelertext="Eins zwei.")
    db.diktat_aktualisieren(con, did, schuelertext="Eins zwei drei vier fünf.")
    assert db.diktat_holen(con, did)["wortzahl"] == 5


def test_diktat_zaehlt_die_vorlage_nicht_die_abschrift(con, schueler_id):
    did = db.diktat_anlegen(con, schueler_id, "D", "Eins zwei drei vier.")
    db.diktat_aktualisieren(con, did, schuelertext="Eins zwei.")
    assert db.diktat_holen(con, did)["wortzahl"] == 4


def test_fehler_umhaengen_greift_ueber_alle_profile(con, schueler_id):
    """Beim Zusammenlegen gelernter Arten zeigten sonst die Einträge fremder
    Profile ins Leere."""
    anderes = db.schueler_anlegen(con, "Zweites Kind")
    db.fehler_anlegen(con, schueler_id, "X-alt")
    db.fehler_anlegen(con, anderes, "X-alt")
    db.fehler_anlegen(con, anderes, "07")

    assert db.fehler_umhaengen(con, "X-alt", "X-neu") == 2
    assert {f["kategorie_nr"] for f in db.fehler_liste(con, schueler_id)} == {"X-neu"}
    assert {f["kategorie_nr"] for f in db.fehler_liste(con, anderes)} == {"X-neu", "07"}


def test_freigabe_kann_zurueckgenommen_werden(con, schueler_id):
    did = db.diktat_anlegen(con, schueler_id, "D", "Text", freigegeben=True)
    db.diktat_freigeben(con, did, freigegeben=False)
    diktat = db.diktat_holen(con, did)
    assert diktat["freigegeben"] == 0 and diktat["freigegeben_am"] is None


def test_wortzahl_wird_bei_textaenderung_nachgefuehrt(con, schueler_id):
    did = db.diktat_anlegen(con, schueler_id, "D", "Eins zwei")
    db.diktat_aktualisieren(con, did, text_original="Eins zwei drei vier fünf")
    assert db.diktat_holen(con, did)["wortzahl"] == 5


def test_zielkategorien_ueberleben_die_speicherung(con, schueler_id):
    did = db.diktat_anlegen(con, schueler_id, "D", "T", ziel_kategorien=["07", "11"])
    assert json.loads(db.diktat_holen(con, did)["ziel_kategorien"]) == ["07", "11"]


def test_diktate_sind_chronologisch(con, schueler_id):
    for datum in ["2026-03-01", "2026-01-01", "2026-02-01"]:
        db.diktat_anlegen(con, schueler_id, datum, "T", datum=datum)
    assert [d["datum"] for d in db.diktat_liste(con, schueler_id)] == [
        "2026-01-01", "2026-02-01", "2026-03-01"]


def test_nur_freigegebene_filtern(con, schueler_id):
    db.diktat_anlegen(con, schueler_id, "offen", "T")
    db.diktat_anlegen(con, schueler_id, "frei", "T", freigegeben=True)
    assert [d["titel"] for d in db.diktat_liste(con, schueler_id, True)] == ["frei"]


def test_diktat_loeschen_entfernt_seine_fehler(con, schueler_id):
    did = db.diktat_anlegen(con, schueler_id, "D", "T")
    db.fehler_anlegen(con, schueler_id, "07", did)
    db.diktat_loeschen(con, did)
    assert db.fehler_liste(con, schueler_id) == []


# --- Fehler -----------------------------------------------------------------

def test_mehrere_fehler_auf_einmal(con, schueler_id):
    did = db.diktat_anlegen(con, schueler_id, "D", "T")
    anzahl = db.fehler_mehrere_anlegen(con, schueler_id, [
        {"diktat_id": did, "kategorie_nr": "07", "wort_original": "kommen"},
        {"diktat_id": did, "kategorie_nr": "11", "wort_original": "Zahn"},
    ])
    assert anzahl == 2
    assert len(db.fehler_liste(con, schueler_id)) == 2


def test_leere_fehlerliste_ist_kein_fehler(con, schueler_id):
    assert db.fehler_mehrere_anlegen(con, schueler_id, []) == 0


def test_haeufigkeit_absteigend(con, schueler_id):
    did = db.diktat_anlegen(con, schueler_id, "D", "T")
    for nr, menge in [("07", 3), ("11", 5), ("01", 1)]:
        for _ in range(menge):
            db.fehler_anlegen(con, schueler_id, nr, did)
    ergebnis = [(z["kategorie_nr"], z["anzahl"])
                for z in db.fehler_haeufigkeit(con, schueler_id)]
    assert ergebnis == [("11", 5), ("07", 3), ("01", 1)]


# --- Übungsblätter ----------------------------------------------------------

def test_blatt_ist_ohne_freigabe_angelegt(con, schueler_id):
    bid = db.blatt_anlegen(con, schueler_id, "B", ["07"], "u", "t")
    assert db.blatt_holen(con, bid)["freigegeben"] == 0


def test_blattfreigabe_haelt_beide_pruefungen_fest(con, schueler_id):
    bid = db.blatt_anlegen(con, schueler_id, "B", ["07"], "u", "t")
    db.blatt_freigeben(con, bid, pruef_loesungen=True, pruef_niveau=True)
    blatt = db.blatt_holen(con, bid)
    assert blatt["freigegeben"] == 1
    assert blatt["freigegeben_am"]
    assert blatt["pruef_loesungen"] == 1
    assert blatt["pruef_niveau"] == 1


# --- Aufträge ---------------------------------------------------------------

def test_auftrag_durchlaeuft_die_zustaende(con, schueler_id):
    db.auftrag_anlegen(con, schueler_id, "RST-DIK-1", "diktat", {"a": 1}, "Prompt")
    assert db.auftrag_holen(con, "RST-DIK-1")["status"] == "offen"
    db.auftrag_status_setzen(con, "RST-DIK-1", "freigegeben", "Ergebnis")
    auftrag = db.auftrag_holen(con, "RST-DIK-1")
    assert auftrag["status"] == "freigegeben"
    assert auftrag["ergebnis_roh"] == "Ergebnis"
    assert auftrag["eingefuegt_am"]


def test_auftragsnummer_ist_eindeutig(con, schueler_id):
    import sqlite3
    db.auftrag_anlegen(con, schueler_id, "RST-DIK-1", "diktat", {}, "P")
    with pytest.raises(sqlite3.IntegrityError):
        db.auftrag_anlegen(con, schueler_id, "RST-DIK-1", "diktat", {}, "P")


def test_auftraege_nach_typ_filtern(con, schueler_id):
    db.auftrag_anlegen(con, schueler_id, "A1", "diktat", {}, "P")
    db.auftrag_anlegen(con, schueler_id, "A2", "uebungsblatt", {}, "P")
    assert len(db.auftrag_liste(con, schueler_id, typ="diktat")) == 1


# --- Einstellungen ----------------------------------------------------------

def test_einstellungen_lesen_und_schreiben(con):
    assert db.einstellung_holen(con, "fehlt", "standard") == "standard"
    db.einstellung_setzen(con, "namensmodus", "kuerzel")
    assert db.einstellung_holen(con, "namensmodus") == "kuerzel"
    db.einstellung_setzen(con, "namensmodus", "klarname")
    assert db.einstellung_holen(con, "namensmodus") == "klarname"


def test_einstellungen_koennen_strukturen_speichern(con):
    db.einstellung_setzen(con, "liste", ["a", "b"])
    assert db.einstellung_holen(con, "liste") == ["a", "b"]


# --- Übersicht --------------------------------------------------------------

def test_uebersicht_fuer_leeres_profil(con, schueler_id):
    u = db.schueler_uebersicht(con, schueler_id)
    assert u["anzahl_diktate"] == 0
    assert u["letztes_diktat_datum"] is None


def test_uebersicht_zeigt_letztes_diktat_und_offene_freigaben(con, schueler_id):
    db.diktat_anlegen(con, schueler_id, "Alt", "T", datum="2026-01-01",
                      freigegeben=True)
    db.diktat_anlegen(con, schueler_id, "Neu", "T", datum="2026-05-01")
    u = db.schueler_uebersicht(con, schueler_id)
    assert u["anzahl_diktate"] == 2
    assert u["letztes_diktat_datum"] == "2026-05-01"
    assert u["letztes_diktat_titel"] == "Neu"
    assert u["diktate_ohne_freigabe"] == 1
