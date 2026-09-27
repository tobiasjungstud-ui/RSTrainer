"""Freitextmodus: zuverlässige Analyse ohne Vorlage.

Beim Diktat steht objektiv fest, was falsch ist – alles, was von der Vorlage
abweicht. Im frei geschriebenen Text fehlt dieser Massstab. Die Zuverlässigkeit
kommt deshalb aus vier Quellen, und genau die prüfen diese Tests:

1. Prüfungen ohne Modell (ß ist in de-CH immer falsch; frühere Fehlschreibungen
   dieses Kindes) – sie stehen fest, unabhängig von jeder Antwort.
2. Das Modell bestimmt nur das Zielwort, nie die Kategorie.
3. Ein blinder Zweitdurchgang deckelt die Sicherheit; Widerspruch führt zur
   Kontrolle statt zu einer erfundenen Genauigkeit.
4. Vollständigkeit wird ehrlich ausgewiesen: Ein Wort gilt nicht als geprüft,
   nur weil niemand es gemeldet hat.
"""

from __future__ import annotations

import json

import pytest

from rstrainer import auftraege, olfa_engine as E


# --- Stufe 0: was ohne Sprachmodell feststeht -------------------------------

def test_eszett_ist_in_de_ch_objektiv_falsch():
    funde = E.eszett_screening(E.tokenisiere("Die Straße war groß."))
    assert [(f["student"], f["target"], f["sicherheit"]) for f in funde] == [
        ("Straße", "Strasse", 1), ("groß", "gross", 1)]


def test_wiederholte_fehlschreibung_wird_ohne_modell_gefunden():
    funde = E.wiederholungs_screening(E.tokenisiere("Das war wider so."),
                                      {"wider": "wieder"})
    assert [(f["student"], f["target"], f["herkunft"]) for f in funde] == [
        ("wider", "wieder", "wiederholung")]
    assert funde[0]["sicherheit"] == 0.8


def test_wiederholungsliste_uebergeht_korrekte_schreibungen():
    assert E.wiederholungs_screening(E.tokenisiere("Haus"), {"haus": "Haus"}) == []


def test_bekannte_fehlschreibungen_aus_frueheren_fehlern():
    bekannt = auftraege.bekannte_fehlschreibungen([
        {"wort_schueler": "wider", "wort_original": "wieder"},
        {"wort_schueler": "Zahn arzt", "wort_original": "Zahnarzt"},   # mehrteilig
        {"wort_schueler": "", "wort_original": "Haus"},                # unvollständig
        {"wort_schueler": "Haus", "wort_original": "Haus"},            # kein Fehler
    ])
    assert bekannt == {"wider": "wieder"}


def test_regelfunde_verbinden_beide_pruefungen():
    funde = auftraege.regelfunde("Die Straße war wider da.", {"wider": "wieder"})
    assert {f["herkunft"] for f in funde} == {"regel", "wiederholung"}


# --- Stufe 1: der Prompt fragt nur nach dem Zielwort ------------------------

def test_zielwort_prompt_nennt_wortnummern_und_die_ch_regel():
    prompt = auftraege.zielwort_prompt_bauen("Die Straße war gros.")
    assert "0\tDie" in prompt and "3\tgros" in prompt
    assert "kein ß" in prompt
    assert "Du klassifizierst den Fehler NICHT" in prompt
    assert str(E.ZIELWORT_SCHWELLE) in prompt


def test_zweite_fassung_ist_anders_formuliert():
    eins = auftraege.zielwort_prompt_bauen("Die Straße war gros.", 1)
    zwei = auftraege.zielwort_prompt_bauen("Die Straße war gros.", 2)
    assert eins != zwei
    assert zwei.startswith("Du bist Korrektorin")


@pytest.mark.parametrize("roh", [
    '```json\n[{"nummer": 3, "wort": "gros", "ziel": "gross", "sicherheit": 0.9}]\n```',
    'Gerne! [{"nummer": 3, "wort": "gros", "ziel": "gross", "sicherheit": 0.9}] – viel Erfolg!',
])
def test_zielwoerter_lesen_vertraegt_begleittext_und_code_zaun(roh):
    assert auftraege.zielwoerter_lesen(roh) == [
        {"tokenIndex": 3, "student": "gros", "target": "gross", "sicherheit": 0.9,
         "alternative": None, "nummern": None, "herkunft": "ki"}]


def test_zielwoerter_lesen_meldet_unbrauchbare_antwort():
    with pytest.raises(ValueError):
        auftraege.zielwoerter_lesen("Ich habe keine Fehler gefunden.")


def test_zielwoerter_lesen_wirft_eintraege_ohne_zielform_weg():
    assert auftraege.zielwoerter_lesen('[{"nummer": 1, "wort": "x", "ziel": ""}]') == []


# --- Zusammenführen: Regel schlägt Modell, Zweifel bleibt Zweifel -----------

def _z(nummer, wort, ziel, sicherheit=0.95):
    return {"tokenIndex": nummer, "student": wort, "target": ziel,
            "sicherheit": sicherheit, "alternative": None, "nummern": None,
            "herkunft": "ki"}


def test_regelfund_schlaegt_modellaussage():
    regeln = [{"tokenIndex": 1, "student": "Straße", "target": "Strasse",
               "sicherheit": 1, "herkunft": "regel"}]
    vereint = auftraege.zielwoerter_vereinen(regeln, [_z(1, "Straße", "Strasze")])
    assert [(z["target"], z["sicherheit"]) for z in vereint] == [("Strasse", 1)]


def test_ein_durchgang_wird_gedeckelt():
    vereint = auftraege.zielwoerter_vereinen([], [_z(3, "gros", "gross", 0.99)])
    assert vereint[0]["sicherheit"] == 0.8
    assert vereint[0]["zweitdurchgang"] == "kein Zweitdurchgang"


def test_einigkeit_erhaelt_die_niedrigere_sicherheit():
    vereint = auftraege.zielwoerter_vereinen(
        [], [_z(3, "gros", "gross", 0.99)], [_z(3, "gros", "gross", 0.9)])
    assert vereint[0]["sicherheit"] == 0.9
    assert vereint[0]["zweitdurchgang"] == "beide Durchgänge einig"


def test_widerspruch_faellt_unter_die_zielwortschwelle():
    vereint = auftraege.zielwoerter_vereinen(
        [], [_z(3, "wider", "wieder")], [_z(3, "wider", "wider")])
    assert vereint[0]["sicherheit"] < E.ZIELWORT_SCHWELLE
    assert vereint[0]["alternative"] == "wider"


def test_fund_nur_im_zweiten_durchgang_geht_nicht_verloren():
    vereint = auftraege.zielwoerter_vereinen([], [], [_z(3, "gros", "gross")])
    assert [z["zweitdurchgang"] for z in vereint] == ["nur Durchgang 2"]
    assert vereint[0]["sicherheit"] == 0.7


def test_fund_nur_im_ersten_durchgang_wird_gekennzeichnet():
    vereint = auftraege.zielwoerter_vereinen([], [_z(3, "gros", "gross")], [])
    assert [z["zweitdurchgang"] for z in vereint] == ["nur Durchgang 1"]


# --- Stufe 2: klassifiziert wird deterministisch ----------------------------

def test_unsicheres_zielwort_geht_zur_kontrolle_statt_in_eine_kategorie():
    liste = auftraege.zielwoerter_vereinen(
        [], [_z(3, "wider", "wieder")], [_z(3, "wider", "wider")])
    r = E.analysiere_liste(liste, "Das war wider so.", E.VORGABE_LEXIKON, quelle="ki")
    e = r["ereignisse"][0]
    assert e["status"] == "manual_review"
    assert e["confidence"] <= 0.6


def test_verzaehlte_wortnummer_verwirft_den_fund_nicht():
    """Ein Modell trifft die Nummer nicht immer, das Wort selbst aber schon."""
    r = E.analysiere_liste([{"student": "Hunt", "target": "Hund", "tokenIndex": 99}],
                           "Der Hunt bellt.", E.VORGABE_LEXIKON)
    assert [e["kategorie"] for e in r["ereignisse"]] == ["19"]
    assert r["verworfen"] == []


def test_erfundenes_wort_wird_weiterhin_verworfen():
    r = E.analysiere_liste([{"student": "Pferd", "target": "Pferde", "tokenIndex": 1}],
                           "Der Hunt bellt.", E.VORGABE_LEXIKON)
    assert r["ereignisse"] == []
    assert r["verworfen"][0]["grund"].startswith("Originalform steht nicht")


def test_mehrdeutiges_wort_nimmt_das_naechstliegende_vorkommen():
    text = "Der Hunt bellt und der Hunt rennt."
    r = E.analysiere_liste([{"student": "Hunt", "target": "Hund", "tokenIndex": 6}],
                           text, E.VORGABE_LEXIKON)
    assert r["ereignisse"][0]["tokenIndex"] == 5


def test_getrennt_geschriebenes_wort_im_freitext():
    r = E.analysiere_liste(
        [{"student": "Zahn", "target": "Zahnarzt", "nummern": [1, 2], "tokenIndex": 1}],
        "Der Zahn arzt kam.", E.VORGABE_LEXIKON)
    assert sorted(e["kategorie"] for e in r["ereignisse"]) == ["01", "04"]
    assert [a["status"] for a in r["abdeckung"]][1:3] == ["fehler", "fehler"]


def test_zusammengeschriebenes_wort_im_freitext():
    r = E.analysiere_liste([{"student": "zumbeispiel", "target": "zum Beispiel"}],
                           "Das ist zumbeispiel gut.", E.VORGABE_LEXIKON)
    assert [e["kategorie"] for e in r["ereignisse"]] == ["05"]


def test_wortgrenzen_mit_unpassenden_nummern_werden_verworfen():
    r = E.analysiere_liste(
        [{"student": "Zahn", "target": "Zahnarzt", "nummern": [0, 1]}],
        "Der Zahn arzt kam.", E.VORGABE_LEXIKON)
    assert r["ereignisse"] == []
    assert "Wortnummern" in r["verworfen"][0]["grund"]


# --- Vollständigkeit wird nicht behauptet -----------------------------------

def test_ohne_vorlage_gilt_kein_wort_als_geprueft():
    r = E.analysiere_liste([{"student": "Hunt", "target": "Hund"}],
                           "Der Hunt bellt laut.", E.VORGABE_LEXIKON)
    status = [a["status"] for a in r["abdeckung"]]
    assert status.count("fehler") == 1
    assert status.count("offen") == 3
    assert "korrekt" not in status


def test_das_diktat_dagegen_kennt_den_status_jedes_wortes():
    r = E.analysiere_diktat("Der Hund bellt laut.", "Der Hunt bellt laut.",
                            E.VORGABE_LEXIKON)
    assert all(a["status"] != "offen" for a in r["abdeckung"])


# --- Modusauswahl -----------------------------------------------------------

@pytest.mark.parametrize("diktat,erwartet", [
    ({"art": "diktat", "text_original": "Der Hund bellt."}, True),
    ({"art": "diktat", "text_original": "   "}, False),
    ({"art": "freitext", "text_original": "Der Hund bellt."}, False),
])
def test_diktatmodus_nur_mit_vorlage(diktat, erwartet):
    from rstrainer.ui.seite_fehler import hat_vorlage
    assert hat_vorlage(diktat) is erwartet


# --- Durchgehender Ablauf ---------------------------------------------------

def test_freitext_ablauf_von_der_antwort_bis_zum_foerderbereich():
    text = "Ich ging zum Zahn arzt und die Straße war gros."
    regeln = auftraege.regelfunde(text, {"gros": "gross"})
    antwort = json.dumps([
        {"nummer": 3, "wort": "Zahn", "ziel": "Zahnarzt", "sicherheit": 0.95,
         "nummern": [3, 4]},
        {"nummer": 8, "wort": "Straße", "ziel": "Strasze", "sicherheit": 0.9},
    ])
    liste = auftraege.zielwoerter_vereinen(regeln, auftraege.zielwoerter_lesen(antwort))
    r = E.analysiere_liste(liste, text, E.VORGABE_LEXIKON, quelle="ki")

    gefunden = {(e["studentForm"], e["targetForm"], e["kategorie"]) for e in r["ereignisse"]}
    # Die beiden Regelfunde stehen fest, auch gegen eine falsche Modellantwort.
    # Original OLFA 3-9+, Version CH (S. 22, 59): ß-Fehler → 37; s für ss → 07 mit Merkmal F3.
    assert ("Straße", "Strasse", "37") in gefunden
    assert ("gros", "gross", "07") in gefunden
    assert ("Zahn arzt", "Zahnarzt", "04") in gefunden
    assert r["verworfen"] == []
    assert {e["foerderbereich"] for e in r["ereignisse"]} >= {"F10", "F3", "F7"}


# --- Kontextprüfung um das Wort --------------------------------------------
# Ein Modell meldet bei «Freitag Morgen» gern nur «Freitag» → «Freitagmorgen».
# Wortweise verglichen wäre das «ein anderes Wort»; der Satz zeigt aber, dass
# die Nachbarwörter zusammen genau das Zielwort ergeben.

SATZ_FREITAG = ("Am Freitag Morgen war das wichtigste bereits gepackt, so dass beim "
                "Aufbruch nichts unvorhergesehnes gescha.")


def test_teilwort_mit_kompositum_als_ziel_wird_zur_wortgrenze():
    r = E.analysiere_liste([{"tokenIndex": 1, "student": "Freitag", "target": "Freitagmorgen",
                             "sicherheit": 0.95}], SATZ_FREITAG, E.VORGABE_LEXIKON)
    assert [(e["studentForm"], e["kategorie"], e["status"]) for e in r["ereignisse"]] == [
        ("Freitag Morgen", "04", "resolved")]
    assert "Wortgrenze aus dem Satz" in r["ereignisse"][0]["reason"]
    assert [a["status"] for a in r["abdeckung"][1:3]] == ["fehler", "fehler"]


def test_auch_das_zweite_teilwort_wird_erkannt_und_nicht_doppelt_gezaehlt():
    liste = [{"tokenIndex": 1, "student": "Freitag", "target": "Freitagmorgen", "sicherheit": 0.95},
             {"tokenIndex": 2, "student": "Morgen", "target": "Freitagmorgen", "sicherheit": 0.9},
             {"tokenIndex": 2, "student": "Morgen", "target": "morgen", "sicherheit": 0.9}]
    repariert = E.wortgrenzen_reparieren(liste, SATZ_FREITAG)
    assert [(z["nummern"], z["sicherheit"]) for z in repariert] == [([1, 2], 0.95)]


def test_wortgrenze_mit_innerem_fehler():
    r = E.analysiere_liste([{"tokenIndex": 1, "student": "Zahn", "target": "Zahnarzt"}],
                           "Der Zahn artzt kam.", E.VORGABE_LEXIKON)
    kategorien = [e["kategorie"] for e in r["ereignisse"]]
    assert kategorien[:2] == ["04", "01"] and len(kategorien) == 3


def test_keine_wortgrenze_wo_das_einzelwort_schon_passt():
    liste = [{"tokenIndex": 2, "student": "das", "target": "dass"}]
    assert E.wortgrenzen_reparieren(liste, "Ich weiss, das Sie kommen.") == liste
    liste = [{"tokenIndex": 1, "student": "Hunt", "target": "Hund"}]
    assert E.wortgrenzen_reparieren(liste, "Der Hunt bellt.") == liste


def test_keine_wortgrenze_ueber_das_satzende():
    liste = [{"tokenIndex": 1, "student": "Haus", "target": "Haustür"}]
    assert E.wortgrenzen_reparieren(liste, "Das Haus. Tür zu.")[0].get("nummern") is None


def test_beide_durchgaenge_meinen_dieselbe_stelle_auch_bei_verschiedener_meldung():
    d1 = auftraege.zielwoerter_lesen([{"nummer": 1, "wort": "Freitag", "ziel": "Freitagmorgen",
                                       "sicherheit": 0.95}])
    d2 = auftraege.zielwoerter_lesen([{"nummer": 1, "wort": "Freitag Morgen", "ziel": "Freitagmorgen",
                                       "sicherheit": 0.9, "nummern": [1, 2]}])
    liste = auftraege.zielwoerter_vereinen([], d1, d2, SATZ_FREITAG)
    assert [(z["nummern"], z["zweitdurchgang"], z["sicherheit"]) for z in liste] == [
        ([1, 2], "beide Durchgänge einig", 0.9)]


def test_formgleiches_zielwort_braucht_keinen_zweitdurchgang():
    """Der Deckel von 0.8 gilt der Zielwort-Bestimmung. Bei «Freitag Morgen» →
    «Freitagmorgen» oder «wichtigste» → «Wichtigste» legt der Text selbst fest,
    welches Wort gemeint ist; bei «gescha» → «geschah» nicht."""
    d1 = auftraege.zielwoerter_lesen([
        {"nummer": 1, "wort": "Freitag", "ziel": "Freitagmorgen", "sicherheit": 0.95},
        {"nummer": 5, "wort": "wichtigste", "ziel": "Wichtigste", "sicherheit": 0.95},
        {"nummer": 14, "wort": "gescha", "ziel": "geschah", "sicherheit": 0.95}])
    liste = auftraege.zielwoerter_vereinen([], d1, None, SATZ_FREITAG)
    assert [(z["student"], z["sicherheit"]) for z in liste] == [
        ("Freitag Morgen", 0.95), ("wichtigste", 0.95), ("gescha", 0.8)]
    r = E.analysiere_liste(liste, SATZ_FREITAG, E.VORGABE_LEXIKON)
    assert [(e["kategorie"], e["status"]) for e in r["ereignisse"]] == [
        ("04", "resolved"), ("01", "resolved"), ("09", "manual_review")]


def test_der_ganze_satz_mit_zwei_durchgaengen():
    antwort = [{"nummer": 1, "wort": "Freitag Morgen", "ziel": "Freitagmorgen", "sicherheit": 0.95,
                "nummern": [1, 2]},
               {"nummer": 5, "wort": "wichtigste", "ziel": "Wichtigste", "sicherheit": 0.95},
               {"nummer": 13, "wort": "unvorhergesehnes", "ziel": "Unvorhergesehenes", "sicherheit": 0.95},
               {"nummer": 14, "wort": "gescha", "ziel": "geschah", "sicherheit": 0.95}]
    d = auftraege.zielwoerter_lesen(antwort)
    liste = auftraege.zielwoerter_vereinen([], d, d, SATZ_FREITAG)
    r = E.analysiere_liste(liste, SATZ_FREITAG, E.VORGABE_LEXIKON)
    assert [(e["studentForm"], e["kategorie"], e["status"]) for e in r["ereignisse"]] == [
        ("Freitag Morgen", "04", "resolved"), ("wichtigste", "01", "resolved"),
        ("unvorhergesehnes", "01", "resolved"), ("unvorhergesehnes", "31", "resolved"),
        ("gescha", "09", "resolved")]


def test_zielwort_prompt_verlangt_erst_den_satzsinn():
    p = auftraege.zielwort_prompt_bauen(SATZ_FREITAG)
    assert "erst der Satz, dann das Wort" in p
    assert "am Freitagmorgen" in p and "nichts Unvorhergesehenes" in p
    assert "sodass/so dass" in p
    assert "«Freitag» «Morgen» → «Freitagmorgen»" in p
