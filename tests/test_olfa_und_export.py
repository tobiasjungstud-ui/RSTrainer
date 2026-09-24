"""Tests der Kategorienliste, des Testmodus und des Datenexports."""

from __future__ import annotations

import csv
import io
import json

from rstrainer import analysis, config, db, demo_data, export, olfa


# --- Kategorienliste --------------------------------------------------------

def test_mitgelieferte_liste_ist_lesbar(liste):
    assert len(liste) == 37
    assert liste.get("01").name == "Klein- für Grossschreibung"


def test_kategorienummern_sind_eindeutig(liste):
    nummern = [k.nr for k in liste]
    assert len(set(nummern)) == len(nummern)


def test_jede_kategorie_ist_vollstaendig(liste):
    for k in liste:
        assert k.nr and k.name, f"Kategorie {k.nr} unvollständig"
        assert k.kurzbeschreibung, f"Kategorie {k.nr} ohne Kurzbeschreibung"
        assert k.bereich, f"Kategorie {k.nr} ohne Bereich"


def test_liste_ist_als_geprueft_markiert(liste):
    """Die Liste stammt aus dem Fachmaterial der Lehrperson."""
    assert liste.alle_geprueft
    assert liste.anzahl_ungeprueft == 0


def test_herkunft_und_offene_punkte_sind_dokumentiert(liste):
    herkunft = " ".join(liste.meta.get("herkunft", []))
    assert "Lehrperson" in herkunft
    geklaert = " ".join(liste.meta.get("geklaert", []))
    assert "GRUPPENZUORDNUNG" in geklaert and "VERSION CH" in geklaert
    assert liste.meta.get("offene_punkte") == []


def test_gruppenzuordnung_folgt_der_kopiervorlage(liste):
    """Gruppen I/II/III aus Original S. 57; 21, 22, 36, 37 ohne Gruppe."""
    from rstrainer.olfa_engine import GRUPPEN
    for k in liste:
        assert k.gruppe == GRUPPEN.get(k.nr), k.nr
    assert all(liste.get(nr).gruppe is None for nr in ("21", "22", "36", "37"))


def test_unbesetzte_nummern_bleiben_erhalten(liste):
    """21 und 22 sind im Original unbesetzt – die Nummerierung muss
    trotzdem mit dem Auswertungsbogen übereinstimmen."""
    assert liste.get("21").name == "unbesetzt"
    assert liste.get("22").name == "unbesetzt"
    assert liste.get("21").heuristik == ()


def test_label_format(liste):
    assert liste.label("07") == "07 – Einfachschreibung für Konsonantenverdoppelung"


def test_label_fuer_unbekannte_nummer(liste):
    assert "unbekannte Kategorie" in liste.label("99")


def test_gruppierung_nach_bereich(liste):
    bereiche = liste.nach_bereich()
    assert "s-Schreibung" in bereiche
    assert sum(len(v) for v in bereiche.values()) == len(liste)


def test_jeder_diff_marker_findet_eine_kategorie(liste):
    """Jeder Marker, den der Abgleich erzeugen kann, muss mindestens eine
    Kategorie treffen – sonst bliebe die Abweichung ohne Vorschlag."""
    from rstrainer import diffing

    paare = [
        ("Haus", "haus"), ("kalt", "Kalt"), ("kommen", "komen"),
        ("Zucker", "Zuker"), ("Katze", "Kazze"), ("hat", "hatt"),
        ("Zahn", "Zan"), ("Boot", "Bot"), ("Wiese", "Wise"),
        ("Tur", "Tuhr"), ("Tisch", "Tiesch"),
        ("las", "laß"), ("dass", "daß"),
        ("Bären", "Beren"), ("Berg", "Bärg"), ("Hund", "Hunt"),
        ("Vater", "Fater"), ("Fisch", "Visch"), ("Vase", "Wase"),
        ("Wasser", "Vasser"), ("wenig", "wenich"), ("mich", "mig"),
        ("Schule", "Sule"), ("Blumen", "Blmen"), ("Kinder", "Kinider"),
        ("Ball", "Pall"), ("Fenster", "Finster"), ("Brot", "Bort"),
        ("Bücher", "Bucher"), ("Haus", ""),
    ]
    ohne = []
    for richtig, falsch in paare:
        marker = diffing.marker_bestimmen(richtig, falsch)
        for m in marker:
            if not liste.mit_heuristik(m):
                ohne.append((richtig, falsch, m))
    assert not ohne, f"Marker ohne Kategorie: {ohne}"


def test_speichern_und_wieder_laden(tmp_path, liste):
    pfad = tmp_path / "eigene.json"
    geaendert = olfa.Kategorienliste(
        kategorien=[olfa.Kategorie(nr="01", name="Eigene", geprueft=True)],
        meta={"status": "geprüft"},
    )
    olfa.speichern(geaendert, pfad)
    neu = olfa.laden(pfad)
    assert len(neu) == 1
    assert neu.get("01").name == "Eigene"
    assert neu.alle_geprueft


def test_gespeicherte_datei_ist_lesbares_json(tmp_path, liste):
    pfad = olfa.speichern(liste, tmp_path / "l.json")
    inhalt = json.loads(pfad.read_text(encoding="utf-8"))
    assert len(inhalt["kategorien"]) == 37
    assert "_meta" in inhalt


# --- Testmodus --------------------------------------------------------------

def test_demodaten_werden_angelegt(con):
    ids = demo_data.demodaten_anlegen(con)
    assert len(ids) == 3
    assert demo_data.demodaten_vorhanden(con)
    for sid in ids:
        assert db.schueler_holen(con, sid)["anzeigename"].startswith("DEMO – ")


def test_demodaten_sind_reproduzierbar():
    """Fester Zufallsstartwert: zwei Läufe ergeben dieselben Zahlen."""
    zahlen = []
    for _ in range(2):
        verbindung = db.verbinden(":memory:")
        demo_data.demodaten_anlegen(verbindung)
        zahlen.append([
            (f["kategorie_nr"], f["wort_schueler"])
            for f in db.fehler_liste(verbindung, 1)
        ])
        verbindung.close()
    assert zahlen[0] == zahlen[1]


def test_demodaten_zeigen_die_vorgesehenen_trends(con):
    """Der Testmodus taugt nur, wenn die eingebauten Entwicklungen auch so
    in der Auswertung ankommen."""
    ids = demo_data.demodaten_anlegen(con)
    for sid, name in zip(ids, demo_data.DEMO_PROFILE):
        diktate = db.diktat_liste(con, sid)
        punkte = [analysis.Diktatpunkt(d["id"], d["datum"], d["titel"], d["wortzahl"])
                  for d in diktate]
        fehler = [dict(f) for f in db.fehler_liste(con, sid)]
        soll = {nr: art for nr, (_, art) in demo_data.DEMO_PROFILE[name]["muster"].items()}
        for nr, trend in analysis.trends_bestimmen(punkte, fehler).items():
            assert trend.einstufung in (soll[nr], analysis.ZU_WENIG_DATEN), (
                f"{name}, Kategorie {nr}: erwartet {soll[nr]}, "
                f"gemessen {trend.einstufung}")


def test_demodaten_enthalten_schuelertexte_fuer_den_abgleich(con):
    demo_data.demodaten_anlegen(con)
    diktat = db.diktat_liste(con, 1)[0]
    assert diktat["schuelertext"]
    assert diktat["schuelertext"] != diktat["text_original"]


def test_demodaten_sind_freigegeben(con):
    demo_data.demodaten_anlegen(con)
    for diktat in db.diktat_liste(con, 1):
        assert diktat["freigegeben"] == 1


def test_demodaten_enthalten_freie_texte(con):
    """Ohne einen freien Text liesse sich der zweite Erfassungsweg im
    Testmodus nicht ansehen."""
    ids = demo_data.demodaten_anlegen(con)
    arten = {d["art"] for d in db.diktat_liste(con, ids[0])}
    assert arten == {"diktat", "freitext"}
    frei = [d for d in db.diktat_liste(con, ids[0]) if d["art"] == "freitext"]
    assert all(d["schuelertext"] and not d["text_original"] for d in frei)
    assert all(d["wortzahl"] > 0 for d in frei)


def test_demodaten_legen_keine_gelernten_arten_an(con, tmp_path, monkeypatch):
    """Die Sammlung liegt ausserhalb der Profile – erfundene Einträge blieben
    nach dem Entfernen der Demodaten stehen."""
    from rstrainer import config, taxonomie

    monkeypatch.setattr(config, "DATEN_DIR", tmp_path)
    demo_data.demodaten_anlegen(con)
    assert not taxonomie.dateipfad().exists()


def test_demodaten_entfernen_laesst_echte_profile_stehen(con):
    echt = db.schueler_anlegen(con, "Echtes Kind")
    demo_data.demodaten_anlegen(con)
    entfernt = demo_data.demodaten_entfernen(con)
    assert entfernt == 3
    assert not demo_data.demodaten_vorhanden(con)
    assert db.schueler_holen(con, echt) is not None


# --- Export -----------------------------------------------------------------

def test_fehler_csv_hat_kopfzeile_und_kategorienamen(con, schueler_id, register):
    did = db.diktat_anlegen(con, schueler_id, "Wald", "Text")
    db.fehler_anlegen(con, schueler_id, "07", did, "kommen", "komen", "Kontext")
    text = export.fehler_csv(con, schueler_id, register)
    zeilen = list(csv.DictReader(io.StringIO(text), delimiter=";"))
    assert len(zeilen) == 1
    assert zeilen[0]["kategorie_nr"] == "07"
    assert zeilen[0]["kategorie_name"] == "Einfachschreibung für Konsonantenverdoppelung"
    assert zeilen[0]["diktat_titel"] == "Wald"
    assert zeilen[0]["wort_schueler"] == "komen"


def test_csv_nutzt_semikolon(con, schueler_id, register):
    assert ";" in export.fehler_csv(con, schueler_id, register).splitlines()[0]


def test_diktate_csv(con, schueler_id):
    db.diktat_anlegen(con, schueler_id, "D", "Eins zwei drei",
                      ziel_kategorien=["07", "11"], freigegeben=True)
    zeile = list(csv.DictReader(
        io.StringIO(export.diktate_csv(con, schueler_id)), delimiter=";"))[0]
    assert zeile["titel"] == "D"
    assert zeile["wortzahl"] == "3"
    assert zeile["ziel_kategorien"] == "07, 11"
    assert zeile["freigegeben"] == "True"


def test_gesamt_json_enthaelt_alle_bereiche(con, schueler_id, register):
    did = db.diktat_anlegen(con, schueler_id, "D", "Text", freigegeben=True)
    db.fehler_anlegen(con, schueler_id, "07", did)
    db.blatt_anlegen(con, schueler_id, "B", ["07"], "u", "t")
    daten = json.loads(export.gesamt_json(con, schueler_id, register))
    assert daten["schueler"]["anzeigename"] == "Testkind"
    assert len(daten["diktate"]) == 1
    assert len(daten["fehler"]) == 1
    assert len(daten["blaetter"]) == 1
    assert "exportiert_am" in daten


def test_json_export_warnt_vor_personenbezug(con, schueler_id, register):
    daten = json.loads(export.gesamt_json(con, schueler_id, register))
    assert "personenbezogene Daten" in daten["hinweis"]


def test_json_export_ohne_texte(con, schueler_id, register):
    db.diktat_anlegen(con, schueler_id, "D", "Geheimer Text")
    daten = json.loads(export.gesamt_json(con, schueler_id, register, mit_texten=False))
    assert "text_original" not in daten["diktate"][0]


def test_export_meldet_unbekanntes_profil(con, register):
    import pytest
    with pytest.raises(ValueError):
        export.gesamt_json(con, 999, register)


def test_export_trennt_die_profile(con, register):
    a = db.schueler_anlegen(con, "A")
    b = db.schueler_anlegen(con, "B")
    did = db.diktat_anlegen(con, a, "Nur A", "Text")
    db.fehler_anlegen(con, a, "07", did)
    daten_b = json.loads(export.gesamt_json(con, b, register))
    assert daten_b["diktate"] == []
    assert daten_b["fehler"] == []


# --- Datenschutz ------------------------------------------------------------

def test_datenverzeichnis_ist_von_git_ausgeschlossen():
    gitignore = (config.PROJEKT_DIR / ".gitignore").read_text(encoding="utf-8")
    for muster in ["daten/", "*.sqlite3", "*.db", "export/"]:
        assert muster in gitignore, f"{muster} fehlt in .gitignore"
