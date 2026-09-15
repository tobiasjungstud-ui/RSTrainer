"""Tests des Prompt-/Ergebnis-Kreislaufs."""

from __future__ import annotations

import string

import pytest

from rstrainer import auftraege
from rstrainer import prompt_templates as pt


# --- Auftragsnummern --------------------------------------------------------

def test_auftragsnummer_hat_typpraefix():
    assert auftraege.auftrag_code("diktat").startswith("RST-DIK-")
    assert auftraege.auftrag_code("uebungsblatt").startswith("RST-UEB-")
    assert auftraege.auftrag_code("minitest").startswith("RST-TST-")


def test_auftragsnummern_sind_verschieden():
    codes = {auftraege.auftrag_code("diktat") for _ in range(200)}
    assert len(codes) > 190


# --- Vorlagen ---------------------------------------------------------------

@pytest.mark.parametrize("typ", sorted(pt.VORLAGEN))
def test_vorlage_hat_alle_pflichtplatzhalter(typ):
    felder = {f for _, f, _, _ in string.Formatter().parse(pt.VORLAGEN[typ]) if f}
    assert pt.PFLICHTPLATZHALTER[typ] <= felder


def test_analysekopf_hat_alle_pflichtplatzhalter():
    felder = {f for _, f, _, _ in string.Formatter().parse(pt.ANALYSE_KOPF) if f}
    assert pt.KOPF_PLATZHALTER <= felder


def test_kategorienblock_nennt_nummer_name_und_beschreibung(liste):
    block = auftraege.kategorienblock(["07", "19"], liste)
    assert "07 – Einfachschreibung für Konsonantenverdoppelung" in block
    assert "19 – p, t, k für b, d, g" in block
    assert "nicht verdoppelt" in block         # Kurzbeschreibung
    assert "*komen → kommen" in block          # Beispiel


def test_kategorienblock_meldet_unbekannte_nummer(liste):
    assert "nicht in der Liste" in auftraege.kategorienblock(["99"], liste)


def test_kategorienblock_ohne_auswahl(liste):
    assert "keine Kategorie" in auftraege.kategorienblock([], liste)


def test_diktatprompt_enthaelt_alle_parameter(liste):
    code, prompt = auftraege.prompt_bauen("diktat", {
        "kategorien": ["07"], "wortzahl": 95,
        "textsorte": "Erzählung", "thema": "Im Zirkus", "schwierigkeit": "mittel",
        "treffer_pro_kategorie": 4,
    }, liste)
    assert code in prompt
    assert "95 Wörter" in prompt
    assert "Im Zirkus" in prompt
    assert "07 – Einfachschreibung für Konsonantenverdoppelung" in prompt
    assert pt.MARKE_ANFANG in prompt and pt.MARKE_ENDE in prompt


@pytest.mark.parametrize("grad,stufe", [
    ("leicht", "7. Klasse"), ("mittel", "8. Klasse"), ("anspruchsvoll", "9. Klasse"),
])
def test_stufe_folgt_dem_schwierigkeitsgrad(liste, grad, stufe):
    """Es gibt kein eigenes Stufenfeld – die Stufe leitet sich ab."""
    parameter = _diktatparameter() | {"schwierigkeit": grad}
    _, prompt = auftraege.prompt_bauen("diktat", parameter, liste)
    assert stufe in prompt


def test_schweizer_rechtschreibung_ist_die_einzige(liste):
    """In der Schweiz gibt es kein ß – der Prompt muss das verlangen.

    Eine Variantenumschaltung gibt es nicht; ``prompt_bauen`` nimmt dafür auch
    keinen Parameter mehr entgegen.
    """
    _, prompt = auftraege.prompt_bauen("diktat", _diktatparameter(), liste)
    assert "KEIN ß" in prompt
    assert "Strasse" in prompt
    with pytest.raises(TypeError):
        auftraege.prompt_bauen("diktat", _diktatparameter(), liste,
                               rechtschreibvariante="deutschland_oesterreich")


def test_sondierungskategorien_sind_ausgewiesen(liste):
    """Sondierung und bekannter Schwerpunkt dürfen nicht gleich aussehen –
    sonst platziert das Modell überall gleich viele Zielwörter."""
    parameter = _diktatparameter() | {"kategorien": ["07", "19"],
                                      "sondierung": ["19"]}
    _, prompt = auftraege.prompt_bauen("diktat", parameter, liste)
    zeilen = [z for z in prompt.splitlines() if z.startswith("- **")]
    sieben = next(z for z in zeilen if "**07" in z)
    neunzehn = next(z for z in zeilen if "**19" in z)
    assert "bekannter Schwerpunkt" in sieben
    assert "Sondierung" in neunzehn


def test_gelernte_art_kommt_in_den_kategorienblock(liste):
    from rstrainer import taxonomie

    sammlung = taxonomie.Sammlung()
    art = sammlung.anlegen(["Grammatik", "Kasus", "Dativ statt Akkusativ"],
                           "Falscher Fall nach Präposition")
    parameter = _diktatparameter() | {"kategorien": ["07", art.id]}
    _, prompt = auftraege.prompt_bauen("diktat", parameter, liste,
                                       sammlung=sammlung)
    assert "Grammatik › Kasus › Dativ statt Akkusativ" in prompt
    assert "Falscher Fall nach Präposition" in prompt


def test_uebungsblattprompt_verbietet_loesungen_auf_der_aufgabenseite(liste):
    _, prompt = auftraege.prompt_bauen("uebungsblatt", {
        "kategorien": ["07", "11"], "schwierigkeit": "mittel",
        "bearbeitungszeit": "20 Minuten", "aufgaben_pro_kategorie": 3,
        "test_aufgaben": 6,
    }, liste)
    assert "KEINE Lösungen" in prompt or "KEINE Lösungen" in prompt.replace("\n", " ")
    assert pt.MARKE_UEBUNG in prompt
    assert pt.MARKE_TEST in prompt
    assert pt.MARKE_LOESUNG in prompt


def test_unbekannter_typ_wird_abgelehnt(liste):
    with pytest.raises(ValueError):
        auftraege.prompt_bauen("gibtsnicht", {}, liste)


def test_fehlender_platzhalter_liefert_klare_meldung(liste):
    with pytest.raises(KeyError, match="prompt_templates.py"):
        auftraege.prompt_bauen("diktat", {"kategorien": ["07"]}, liste)


def test_vorgegebener_code_wird_uebernommen(liste):
    code, prompt = auftraege.prompt_bauen(
        "diktat", _diktatparameter(), liste, code="RST-DIK-ABCDEF")
    assert code == "RST-DIK-ABCDEF"
    assert "RST-DIK-ABCDEF" in prompt


def _diktatparameter() -> dict:
    return {
        "kategorien": ["07"], "wortzahl": 90,
        "textsorte": "Erzählung", "thema": "Wald", "schwierigkeit": "mittel",
        "treffer_pro_kategorie": 4,
    }


# --- Ergebnis zurücklesen ---------------------------------------------------

DIKTAT_ANTWORT = """Gerne! Hier ist dein Diktat:

===RSTRAINER-ANFANG===
AUFTRAG: RST-DIK-ABC123
TYP: diktat
TITEL: Ein Tag im Wald
WOERTER: 64
ZIELWOERTER: 07: kommen, rennen
---
Am Morgen kommen die Kinder in den Wald und rennen über den Boden.
===RSTRAINER-ENDE===

Sag Bescheid, wenn du etwas ändern möchtest!"""


def test_diktatantwort_wird_zerlegt():
    e = auftraege.ergebnis_lesen(DIKTAT_ANTWORT, "RST-DIK-ABC123", "diktat")
    assert e.strukturiert
    assert e.auftrag_code == "RST-DIK-ABC123"
    assert e.typ == "diktat"
    assert e.titel == "Ein Tag im Wald"
    assert e.haupttext.startswith("Am Morgen kommen")
    assert "Gerne!" not in e.haupttext          # Geplauder bleibt draussen
    assert "Sag Bescheid" not in e.haupttext
    assert e.kopf["ZIELWOERTER"].startswith("07:")
    assert e.hinweise == []


def test_falsche_auftragsnummer_wird_gemeldet():
    e = auftraege.ergebnis_lesen(DIKTAT_ANTWORT, "RST-DIK-ANDERS", "diktat")
    assert any("RST-DIK-ABC123" in h for h in e.hinweise)
    assert e.haupttext                          # der Text geht trotzdem nicht verloren


def test_falscher_typ_wird_gemeldet():
    e = auftraege.ergebnis_lesen(DIKTAT_ANTWORT, "RST-DIK-ABC123", "uebungsblatt")
    assert any("diktat" in h for h in e.hinweise)


def test_fehlende_markierungen_fallen_auf_fliesstext_zurueck():
    """Wichtig: Auch ohne Markierungen darf nichts verloren gehen."""
    e = auftraege.ergebnis_lesen("Einfach nur ein Text ohne alles.")
    assert not e.strukturiert
    assert e.haupttext == "Einfach nur ein Text ohne alles."
    assert any("Markierungen" in h for h in e.hinweise)


def test_fehlende_auftragsnummer_wird_gemeldet():
    e = auftraege.ergebnis_lesen("Nur Text", erwarteter_code="RST-DIK-ABC123")
    assert any("keine Auftragsnummer" in h for h in e.hinweise)


def test_leere_eingabe():
    e = auftraege.ergebnis_lesen("")
    assert e.ist_leer
    assert e.hinweise


UEBUNGSBLATT_ANTWORT = """===RSTRAINER-ANFANG===
AUFTRAG: RST-UEB-ABC123
TYP: uebungsblatt
TITEL: Doppelkonsonanten üben
---UEBUNGSBLATT---
Aufgabe 1 (Kategorie 07): Ergänze ko___en.
---MINITEST---
Test 1: Schreibe die Wörter richtig.
---LOESUNGEN---
1. kommen
===RSTRAINER-ENDE==="""


def test_uebungsblattantwort_wird_in_drei_teile_zerlegt():
    e = auftraege.ergebnis_lesen(UEBUNGSBLATT_ANTWORT, "RST-UEB-ABC123", "uebungsblatt")
    assert e.titel == "Doppelkonsonanten üben"
    assert "Ergänze ko___en." in e.uebungsteil
    assert "Schreibe die Wörter richtig." in e.testteil
    assert "1. kommen" in e.loesungen
    assert e.hinweise == []


def test_loesungen_landen_nicht_im_uebungsteil():
    e = auftraege.ergebnis_lesen(UEBUNGSBLATT_ANTWORT)
    assert "kommen" not in e.uebungsteil
    assert "kommen" not in e.testteil


def test_fehlender_loesungsabschnitt_ist_kein_absturz():
    antwort = UEBUNGSBLATT_ANTWORT.split("---LOESUNGEN---")[0] + "===RSTRAINER-ENDE==="
    e = auftraege.ergebnis_lesen(antwort)
    assert e.uebungsteil and e.testteil
    assert e.loesungen == ""


def test_kopfzeilen_ohne_trenner_werden_erkannt():
    antwort = ("===RSTRAINER-ANFANG===\nAUFTRAG: RST-DIK-1\nTYP: diktat\n"
               "TITEL: Kurz\n\nDer eigentliche Text.\n===RSTRAINER-ENDE===")
    e = auftraege.ergebnis_lesen(antwort)
    assert e.titel == "Kurz"
    assert e.haupttext == "Der eigentliche Text."


# ---------------------------------------------------------------------------
# Anforderungsniveau (nicht nur Klassenstufe)
# ---------------------------------------------------------------------------
# Vorher übersetzte der Schwierigkeitsgrad nur in eine Klassenstufe. Das Modell
# baute daraufhin auf allen drei Stufen dasselbe Blatt: Lückenwörter mit
# vorgegebenem Buchstaben, Ankreuzpaare, Einzelwörter. «Anspruchsvoll» war
# mittelschwer. Diese Tests halten fest, dass die Stufen operativ verschieden
# sind – also sagen, WAS die Aufgabe verlangt.

STUFEN = ["leicht", "mittel", "anspruchsvoll"]


@pytest.mark.parametrize("grad", STUFEN)
def test_jede_stufe_hat_ein_eigenes_anforderungsniveau(grad):
    assert pt.ANFORDERUNG[grad].strip()
    assert pt.ANFORDERUNG_DIKTAT[grad].strip()


def test_die_stufen_unterscheiden_sich_wirklich():
    texte = [pt.ANFORDERUNG[g] for g in STUFEN]
    assert len(set(texte)) == 3
    diktat = [pt.ANFORDERUNG_DIKTAT[g] for g in STUFEN]
    assert len(set(diktat)) == 3


def test_anspruchsvoll_verbietet_die_gestuetzte_luecke():
    """Der Buchstabe in Klammern macht aus der Aufgabe eine Ja/Nein-Frage an
    bekannter Stelle – genau das war am hochgeladenen Blatt zu leicht."""
    text = pt.ANFORDERUNG["anspruchsvoll"]
    assert "NIE in Klammern mitgeliefert" in text
    assert "Höchstens EINE Aufgabe je Schwerpunkt darf den Suchort markieren" in text


def test_anspruchsvoll_verlangt_ungestuetzte_fehlersuche_mit_distraktoren():
    text = pt.ANFORDERUNG["anspruchsvoll"]
    assert "Mindestens die Hälfte der Aufgaben" in text
    assert "Nenne die Anzahl der Fehler, nie ihre Stelle" in text
    assert "Distraktoren" in text and "KORREKT sind, aber ungewohnt aussehen" in text


def test_anspruchsvoll_verlangt_begruendung_und_eigene_produktion():
    text = pt.ANFORDERUNG["anspruchsvoll"]
    assert "Begründungspflicht" in text
    assert "ohne Begründung nur halb zählt" in text
    assert "eigene Produktion unter Bedingung" in text.replace("\n", " ")


def test_anspruchsvoll_schliesst_den_primarschulwortschatz_aus():
    text = pt.ANFORDERUNG["anspruchsvoll"]
    assert "VERBOTEN" in text
    for wort in ("Sonne", "Blume", "Wasser"):
        assert wort in text


def test_anspruchsvoll_nennt_die_de_ch_luecke_ohne_eszett():
    """Ohne ß fehlt die Längenmarkierung – das ist hier der harte Fall."""
    for text in (pt.ANFORDERUNG["anspruchsvoll"], pt.ANFORDERUNG_DIKTAT["anspruchsvoll"]):
        assert "kein ß gibt" in text
        assert "Fuss" in text and "Fluss" in text     # lang gegen kurz, beide mit ss


def test_leichte_stufe_erlaubt_die_stuetzung_ausdruecklich():
    text = pt.ANFORDERUNG["leicht"]
    assert "Der Suchort darf markiert sein" in text
    assert "VERBOTEN" not in text


@pytest.mark.parametrize("typ,parameter", [
    ("uebungsblatt", {"aufgaben_pro_kategorie": 3, "test_aufgaben": 6,
                      "bearbeitungszeit": "20 Minuten"}),
    ("minitest", {"test_aufgaben": 6, "bearbeitungszeit": "10 Minuten",
                  "bekannte_woerter": "Sonne"}),
    ("diktat", {"textsorte": "Bericht", "thema": "Schulreise", "wortzahl": 110,
                "treffer_pro_kategorie": 3}),
])
@pytest.mark.parametrize("grad", STUFEN)
def test_das_niveau_steht_im_fertigen_prompt(typ, parameter, grad, liste):
    _, text = auftraege.prompt_bauen(
        typ, {**parameter, "kategorien": ["07", "17", "01"], "schwierigkeit": grad}, liste)
    assert "### Anforderungsniveau" in text
    erwartet = (pt.ANFORDERUNG_DIKTAT if typ == "diktat" else pt.ANFORDERUNG)[grad]
    assert erwartet.split("\n")[0][:40] in text


def test_anspruchsvoller_auftrag_ist_deutlich_fordernder_als_der_leichte(liste):
    parameter = {"kategorien": ["07", "17", "01"], "aufgaben_pro_kategorie": 3,
                 "test_aufgaben": 6, "bearbeitungszeit": "20 Minuten"}
    _, leicht = auftraege.prompt_bauen("uebungsblatt", {**parameter, "schwierigkeit": "leicht"}, liste)
    _, schwer = auftraege.prompt_bauen("uebungsblatt", {**parameter, "schwierigkeit": "anspruchsvoll"}, liste)
    assert len(schwer) > len(leicht) + 2000
    assert "Prüfe dich selbst" in schwer


def test_unbekannter_grad_faellt_auf_mittel_zurueck_je_typ():
    assert auftraege._anforderung("diktat", "sehr schwer") == pt.ANFORDERUNG_DIKTAT["mittel"]
    assert auftraege._anforderung("uebungsblatt", "sehr schwer") == pt.ANFORDERUNG["mittel"]
