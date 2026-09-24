"""Tests der Modell-Analyse und des Kategorienmischers.

Das Sprachmodell antwortet in JSON. Zwei Dinge müssen sicher sein: Die
Antwort wird auch dann verwertet, wenn Begleittext oder ein Code-Zaun
mitkommt – und eine unbrauchbare Antwort führt zu einer Meldung, nicht zu
einem Absturz oder zu erfundenen Fehlern.
"""

from __future__ import annotations

import json

import pytest

from rstrainer import analysis, auftraege, taxonomie
from rstrainer.kategorien import Register

from conftest import diktatpunkte


def _antwort(*eintraege) -> str:
    return json.dumps(list(eintraege), ensure_ascii=False)


OLFA_ZEILE = {"richtig": "kommen", "geschrieben": "komen", "typ": "olfa",
              "kategorie": "07", "begruendung": "Doppelkonsonant fehlt"}


# --- Prompt -----------------------------------------------------------------

def test_diktatprompt_nennt_die_vorlage(liste, sammlung):
    prompt = auftraege.analyse_prompt_bauen("Abschrift", "Originaltext", liste, sammlung)
    assert "## Originaldiktat" in prompt
    assert "Originaltext" in prompt and "Abschrift" in prompt


def test_freitextprompt_hat_keine_vorlage_und_warnt_vor_stilkritik(liste, sammlung):
    """Ohne Vorlage ist die Versuchung gross, zu viel anzustreichen."""
    prompt = auftraege.analyse_prompt_bauen("Text des Kindes", "", liste, sammlung)
    assert "## Originaldiktat" not in prompt
    assert "Kein Stil" in prompt


def test_prompt_verbietet_die_gesperrten_kategorien(liste, sammlung):
    prompt = auftraege.analyse_prompt_bauen("Text", "", liste, sammlung)
    for nr in ("13", "14", "15", "16"):
        assert f"\n{nr} = " not in prompt
    assert "\n07 = " in prompt and "\n11 = " in prompt
    assert "13, 14, 15, 16, 21 und 22 werden NIE vergeben" in prompt


def test_prompt_zaehlt_bereits_angelegte_arten_auf(liste):
    """Sonst legt das Modell für denselben Fehler jedes Mal eine neue an."""
    s = taxonomie.Sammlung()
    art = s.anlegen(["Grammatik", "Kasus", "Dativ statt Akkusativ"], "Erklärung")
    prompt = auftraege.analyse_prompt_bauen("Text", "", liste, s)
    assert art.id in prompt
    assert "Grammatik › Kasus › Dativ statt Akkusativ" in prompt
    assert "Erklärung" in prompt


def test_prompt_ohne_gelernte_arten_sagt_das(liste, sammlung):
    assert "noch keine" in auftraege.analyse_prompt_bauen("Text", "", liste, sammlung)


# --- Antwort lesen ----------------------------------------------------------

def test_olfa_zeile_wird_uebernommen(liste, sammlung):
    e = auftraege.analyse_lesen(_antwort(OLFA_ZEILE), liste, sammlung)
    assert e.fehler is None and len(e.zeilen) == 1
    zeile = e.zeilen[0]
    assert zeile.kategorie_nr == "07"
    assert zeile.wort_original == "kommen" and zeile.wort_schueler == "komen"
    assert zeile.begruendung == "Doppelkonsonant fehlt"


def test_einstellige_nummer_wird_aufgefuellt(liste, sammlung):
    e = auftraege.analyse_lesen(_antwort(OLFA_ZEILE | {"kategorie": "7"}),
                                liste, sammlung)
    assert e.zeilen[0].kategorie_nr == "07"


@pytest.mark.parametrize("nr", ["14", "16", "21", "99", "", None])
def test_unbrauchbare_nummern_landen_auf_der_auffangkategorie(liste, sammlung, nr):
    """14, 16, 21, 22 werden in de-CH nie vergeben, 99 gibt es nicht."""
    e = auftraege.analyse_lesen(_antwort(OLFA_ZEILE | {"kategorie": nr}),
                                liste, sammlung)
    assert e.zeilen[0].kategorie_nr == "37"


def test_code_zaun_und_begleittext_stoeren_nicht(liste, sammlung):
    roh = "Gerne! Hier ist die Analyse:\n```json\n" + _antwort(OLFA_ZEILE) + "\n```\nViel Erfolg!"
    e = auftraege.analyse_lesen(roh, liste, sammlung)
    assert e.fehler is None and len(e.zeilen) == 1


def test_leere_liste_ist_kein_fehler(liste, sammlung):
    e = auftraege.analyse_lesen("[]", liste, sammlung)
    assert e.fehler is None and e.zeilen == []


@pytest.mark.parametrize("roh", ["", "Ich habe keine Fehler gefunden.", "{kaputt"])
def test_unlesbare_antwort_meldet_statt_zu_raten(liste, sammlung, roh):
    e = auftraege.analyse_lesen(roh, liste, sammlung)
    assert e.fehler and e.zeilen == []


def test_kaputtes_json_wird_gemeldet(liste, sammlung):
    e = auftraege.analyse_lesen('[{"richtig": }]', liste, sammlung)
    assert e.fehler == "Die Antwort war kein gültiges JSON."


def test_fehlende_klammer_wird_gemeldet(liste, sammlung):
    e = auftraege.analyse_lesen('[{"richtig": "a"', liste, sammlung)
    assert e.fehler == "Die Antwort enthielt keine Fehlerliste."


# --- Neue Fehlerarten -------------------------------------------------------

NEUE_ZEILE = {"richtig": "dem Hund", "geschrieben": "den Hund", "typ": "neu",
              "pfad": ["grammatik", "kasus", "Akkusativ statt Dativ"],
              "beschreibung": "Falscher Fall", "begruendung": "Dativ verlangt"}


def test_gleiche_neue_art_wird_nur_einmal_vorgeschlagen(liste, sammlung):
    e = auftraege.analyse_lesen(
        _antwort(NEUE_ZEILE, NEUE_ZEILE | {"pfad": ["Grammatik", "Kasus",
                                                    "Akkusativ statt Dativ"]}),
        liste, sammlung)
    assert len(e.neue_arten) == 1
    assert e.neue_arten[0].anzahl == 2
    assert e.zeilen[0].kategorie_nr == e.zeilen[1].kategorie_nr


def test_bestehende_art_gewinnt_vor_einer_neuen(liste):
    """Sonst wüchse die Sammlung bei jedem Text um dieselben Einträge."""
    s = taxonomie.Sammlung()
    art = s.anlegen(["Grammatik", "Kasus", "Akkusativ statt Dativ"])
    e = auftraege.analyse_lesen(_antwort(NEUE_ZEILE), liste, s)
    assert e.neue_arten == []
    assert e.zeilen[0].kategorie_nr == art.id


def test_bekannte_kennung_wird_weiterverwendet(liste):
    s = taxonomie.Sammlung()
    art = s.anlegen(["Grammatik", "Kasus", "Dativ statt Akkusativ"])
    e = auftraege.analyse_lesen(
        _antwort({"richtig": "a", "geschrieben": "b", "typ": "bekannt",
                  "kategorie": art.id}), liste, s)
    assert e.zeilen[0].kategorie_nr == art.id
    assert e.neue_arten == []


def test_erfundene_kennung_faellt_auf_37_zurueck(liste, sammlung):
    e = auftraege.analyse_lesen(
        _antwort({"richtig": "a", "geschrieben": "b", "typ": "bekannt",
                  "kategorie": "X-erfunden"}), liste, sammlung)
    assert e.zeilen[0].kategorie_nr == "37"


def test_einstufiger_pfad_reicht_nicht(liste, sammlung):
    """«Grammatik» allein ist keine Fehlerart, sondern ein Oberbegriff."""
    e = auftraege.analyse_lesen(_antwort(NEUE_ZEILE | {"pfad": ["Grammatik"]}),
                                liste, sammlung)
    assert e.neue_arten == []
    assert e.zeilen[0].kategorie_nr == "37"


def test_uebernehmen_behaelt_die_kennung_der_zeilen(liste, sammlung):
    """Die Zeilen tragen die Kennung des Vorschlags schon – legte das Anlegen
    eine neue an, zeigten sie ins Leere."""
    e = auftraege.analyse_lesen(_antwort(NEUE_ZEILE), liste, sammlung)
    vorschlag = e.neue_arten[0].id
    angelegt = auftraege.analyse_uebernehmen(e, sammlung)
    assert len(angelegt) == 1
    assert angelegt[0].id == vorschlag == e.zeilen[0].kategorie_nr
    assert sammlung.get(vorschlag) is not None


def test_uebernehmen_haengt_auf_eine_zwischenzeitlich_angelegte_art_um(liste, sammlung):
    e = auftraege.analyse_lesen(_antwort(NEUE_ZEILE), liste, sammlung)
    bestehend = sammlung.anlegen(["Grammatik", "Kasus", "Akkusativ statt Dativ"])
    angelegt = auftraege.analyse_uebernehmen(e, sammlung)
    assert angelegt == []
    assert e.zeilen[0].kategorie_nr == bestehend.id
    assert e.zeilen[0].neue_art is None


# --- Abweichungen -----------------------------------------------------------

def test_zeilen_werden_zur_bestaetigungsliste(liste, sammlung):
    e = auftraege.analyse_lesen(_antwort(OLFA_ZEILE), liste, sammlung)
    abweichungen = auftraege.analyse_zu_abweichungen(
        e.zeilen, "Sie wollten gestern komen aber es regnete", liste)
    a = abweichungen[0]
    assert a["darstellung"] == "kommen → komen"
    assert a["quelle"] == "modell"
    assert a["vorgabe"] == "07"
    assert "komen" in a["kontext"]
    assert "doppelkonsonant_fehlt" in a["marker"]


def test_fehlendes_wort_wird_als_solches_dargestellt(liste, sammlung):
    e = auftraege.analyse_lesen(
        _antwort({"richtig": "Haus", "geschrieben": "", "typ": "olfa",
                  "kategorie": "37"}), liste, sammlung)
    a = auftraege.analyse_zu_abweichungen(e.zeilen, "Das Haus ist gross", liste)[0]
    assert a["art"] == "fehlt"
    assert a["darstellung"] == "Haus → (fehlt)"


def test_nicht_auffindbares_wort_bleibt_ohne_kontext(liste, sammlung):
    e = auftraege.analyse_lesen(_antwort(OLFA_ZEILE), liste, sammlung)
    a = auftraege.analyse_zu_abweichungen(e.zeilen, "Ein ganz anderer Text", liste)[0]
    assert a["position"] == -1 and a["kontext"] == ""


# --- Aufräumen --------------------------------------------------------------

def test_aufraeumen_verwirft_unbekannte_kennungen():
    s = taxonomie.Sammlung()
    a = s.anlegen(["Grammatik", "Kasus", "Dativ statt Akkusativ"])
    b = s.anlegen(["Grammatik", "Kasus", "Kasusfehler"])
    plan = auftraege.aufraeum_lesen(json.dumps({
        "zusammenlegen": [{"von": b.id, "nach": a.id, "warum": "gleich"},
                          {"von": "X-gibtsnicht", "nach": a.id},
                          {"von": a.id, "nach": a.id}],
        "umbenennen": [],
    }), s)
    assert len(plan.zusammenlegen) == 1
    assert plan.zusammenlegen[0]["von"] == b.id


def test_aufraeumen_verwirft_umbenennungen_ohne_wirkung():
    s = taxonomie.Sammlung()
    a = s.anlegen(["Grammatik", "Kasus", "Dativ statt Akkusativ"])
    plan = auftraege.aufraeum_lesen(json.dumps({
        "zusammenlegen": [],
        "umbenennen": [{"id": a.id, "pfad": ["grammatik", "kasus",
                                             "Dativ statt Akkusativ"]},
                       {"id": a.id, "pfad": ["Grammatik", "Kasus", "Falscher Fall"]}],
    }), s)
    assert len(plan.umbenennen) == 1
    assert plan.umbenennen[0]["pfad"][2] == "Falscher Fall"


def test_aufraeumplan_ist_nie_vorausgewaehlt_falsch():
    """Angewendet wird nichts ohne Bestätigung, aber der Vorschlag selbst
    kommt angehakt – die Oberfläche entscheidet."""
    s = taxonomie.Sammlung()
    a = s.anlegen(["Grammatik", "Kasus", "A"])
    b = s.anlegen(["Grammatik", "Kasus", "B"])
    plan = auftraege.aufraeum_lesen(
        json.dumps({"zusammenlegen": [{"von": b.id, "nach": a.id}]}), s)
    assert plan.zusammenlegen[0]["anwenden"] is True
    assert not plan.ist_leer


def test_leerer_aufraeumplan():
    plan = auftraege.aufraeum_lesen('{"zusammenlegen": [], "umbenennen": []}',
                                    taxonomie.Sammlung())
    assert plan.ist_leer and plan.fehler is None


def test_unlesbarer_aufraeumplan_meldet():
    plan = auftraege.aufraeum_lesen("Ich habe nichts gefunden.", taxonomie.Sammlung())
    assert plan.fehler


# --- Kategorien mischen -----------------------------------------------------

def _mischung(register, anteil: float, anzahl: int = 4):
    punkte = diktatpunkte(4)
    fehler = [{"kategorie_nr": nr, "diktat_id": i + 1}
              for nr in ("07", "09", "01") for i in range(4)]
    return analysis.kategorien_mischen(punkte, fehler, register, anzahl, anteil)


def test_regler_ganz_links_liefert_nur_klassiker(register):
    m = _mischung(register, 0.0, anzahl=3)
    assert m.sondierung == [] and len(m.klassiker) == 3
    assert set(m.klassiker) == {"07", "09", "01"}


def test_fehlende_klassiker_werden_mit_sondierung_aufgefuellt(register):
    """Drei bekannte Schwerpunkte, vier gewünschte Kategorien: Die vierte
    Stelle bleibt nicht leer, sie geht an die Sondierung."""
    m = _mischung(register, 0.0, anzahl=4)
    assert len(m.klassiker) == 3 and len(m.sondierung) == 1


def test_regler_ganz_rechts_liefert_nur_sondierung(register):
    m = _mischung(register, 1.0)
    assert m.klassiker == [] and len(m.sondierung) == 4


def test_regler_in_der_mitte_mischt(register):
    m = _mischung(register, 0.5)
    assert len(m.klassiker) == 2 and len(m.sondierung) == 2
    assert not set(m.klassiker) & set(m.sondierung)


def test_ohne_daten_bleibt_nur_sondierung(register):
    m = analysis.kategorien_mischen([], [], register, 4, 0.0)
    assert m.klassiker == [] and len(m.sondierung) == 4


def test_sondierung_enthaelt_keine_gesehenen_kategorien(register):
    m = _mischung(register, 1.0)
    assert not set(m.sondierung) & {"07", "09", "01"}


def test_sondierung_ueberspringt_gesperrte_kategorien(register):
    vorrat = analysis.sondierungsvorrat(diktatpunkte(2), [], register)
    assert not {"14", "16", "21", "22"} & set(vorrat)


def test_sondierung_bezieht_gelernte_arten_ein(liste):
    s = taxonomie.Sammlung()
    art = s.anlegen(["Grammatik", "Kasus", "Dativ statt Akkusativ"])
    vorrat = analysis.sondierungsvorrat(diktatpunkte(2), [],
                                        Register(liste=liste, sammlung=s))
    assert art.id in vorrat


def test_fenster_wandert_mit_der_zahl_der_texte(register):
    """Sonst würden immer dieselben Kandidaten geprüft."""
    a = analysis.sondierungsvorrat(diktatpunkte(1), [], register)
    b = analysis.sondierungsvorrat(diktatpunkte(2), [], register)
    assert a[0] != b[0]
    assert sorted(a) == sorted(b)


def test_bereits_geprueft_ohne_fehler_kommt_spaeter(register):
    """Eine Kategorie, die schon Ziel war und trotzdem nichts brachte, ist
    weniger unerforscht als eine nie geprüfte."""
    def unrotiert(punkte):
        # Das Fenster wandert mit der Zahl der Texte. Beide Aufrufe haben
        # gleich viele, also dieselbe Drehung – die lässt sich zurückdrehen,
        # sonst misst der Test die Drehung statt der Reihenfolge.
        vorrat = analysis.sondierungsvorrat(punkte, [], register)
        versatz = len(punkte) % len(vorrat)
        return vorrat[-versatz:] + vorrat[:-versatz] if versatz else vorrat

    punkte = diktatpunkte(1)
    punkte[0].ziel_kategorien = ("01",)
    mit_ziel = unrotiert(punkte)
    ohne_ziel = unrotiert(diktatpunkte(1))
    assert mit_ziel.index("01") > ohne_ziel.index("01")
    # Die Geschwister im selben Bereich rücken entsprechend vor.
    assert mit_ziel.index("02") < mit_ziel.index("01")
