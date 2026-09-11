"""Tests der Plausibilitätsprüfungen vor der Freigabe."""

from __future__ import annotations

from rstrainer import validation
from rstrainer.validation import HINWEIS, OK, WARNUNG

DIKTATTEXT = (
    "Am Morgen rannte der Hund über die nasse Wiese. Er sah den hohen Zaun und "
    "sprang darüber. Danach kam er zum Bach und trank. Die Sonne schien warm, "
    "und die Kinder kamen mit ihren Rädern angefahren."
)


def _finde(befunde, teil):
    return [b for b in befunde if teil in b.titel]


def test_passende_wortzahl_ist_ok(liste):
    befunde = validation.diktat_pruefen(DIKTATTEXT, 40, [], liste)
    wortzahl = _finde(befunde, "Wortanzahl")[0]
    assert wortzahl.stufe == OK


def test_abweichende_wortzahl_gibt_hinweis(liste):
    befunde = validation.diktat_pruefen(DIKTATTEXT, 200, [], liste)
    assert _finde(befunde, "Wortanzahl")[0].stufe == HINWEIS


def test_wortzahl_innerhalb_toleranz(liste):
    """Dokumentierte Annahme: bis 20 % Abweichung ohne Hinweis."""
    ist = len(DIKTATTEXT.split())
    assert validation.diktat_pruefen(
        DIKTATTEXT, int(ist * 1.15), [], liste)[0].stufe in (OK, HINWEIS)
    knapp = validation.diktat_pruefen(DIKTATTEXT, ist, [], liste)
    assert _finde(knapp, "Wortanzahl")[0].stufe == OK


def test_passende_kategorie_wird_bestaetigt(liste):
    befunde = validation.diktat_pruefen(DIKTATTEXT, 40, ["07"], liste)
    treffer = _finde(befunde, "Konsonantenverdoppelung")[0]
    assert treffer.stufe == OK
    assert "rannte" in treffer.text or "nasse" in treffer.text


def test_unpassende_kategorie_warnt(liste):
    """Ein Text ohne ß kann die Kategorie 15 (ss für ß) nicht üben."""
    text = "Am Morgen kam der Hund. Er lief davon."
    befunde = validation.diktat_pruefen(text, 9, ["15"], liste)
    assert _finde(befunde, "ss für ß")[0].stufe == WARNUNG


def test_leerer_text_warnt(liste):
    befunde = validation.diktat_pruefen("   ", 90, ["07"], liste)
    assert len(befunde) == 1 and befunde[0].stufe == WARNUNG


def test_korrekturlese_hinweis_erscheint_immer(liste):
    befunde = validation.diktat_pruefen(DIKTATTEXT, 40, [], liste)
    assert _finde(befunde, "Korrekturlesen")


def test_warnungen_stehen_oben(liste):
    text = "Am Morgen kam der Hund."
    befunde = validation.diktat_pruefen(text, 5, ["15", "07"], liste)
    stufen = [b.stufe for b in befunde]
    assert stufen == sorted(stufen, key=lambda s: {WARNUNG: 0, HINWEIS: 1, OK: 2}[s])


def test_pruefungen_blockieren_nie(liste):
    """Grundsatz: Prüfungen melden, sie verhindern nichts."""
    befunde = validation.diktat_pruefen("Kurz.", 500, ["15", "33"], liste)
    assert befunde  # es gibt Befunde …
    assert all(hasattr(b, "stufe") for b in befunde)  # … aber keine Ausnahme


def test_kategorie_treffer_sind_dublettenfrei(liste):
    treffer = validation.kategorie_treffer("Sonne Sonne Sonne", "07", liste)
    assert treffer == ["Sonne"]


def test_unbekannte_kategorie_liefert_keine_treffer(liste):
    assert validation.kategorie_treffer(DIKTATTEXT, "99", liste) == []


# --- Übungsblatt ------------------------------------------------------------

UEBUNG = "Aufgabe 1 (Kategorie 07): Ergänze ko___en, ren___en und So___e."
TEST = "Test 1 (Kategorie 07): Schreibe die Wörter mit doppeltem Konsonanten."


def test_genannte_kategorienummer_wird_bestaetigt(liste):
    befunde = validation.blatt_pruefen(UEBUNG, TEST, "1. kommen", ["07"], liste)
    assert _finde(befunde, "Zuordnung")[0].stufe == OK


def test_fehlende_kategoriezuordnung_warnt(liste):
    befunde = validation.blatt_pruefen(
        "Male ein Bild.", "Zeichne etwas.", "", ["15"], liste)
    assert _finde(befunde, "Zuordnung")[0].stufe == WARNUNG


def test_loesungsverdacht_auf_der_aufgabenseite(liste):
    befunde = validation.blatt_pruefen(
        "Aufgabe 1 (Kategorie 07): ko___en  Lösung: kommen", TEST, "", ["07"], liste)
    treffer = _finde(befunde, "Lösungen sichtbar")[0]
    assert treffer.stufe == WARNUNG


def test_klammerloesung_nach_luecke_wird_erkannt(liste):
    befunde = validation.blatt_pruefen(
        "Aufgabe 1 (Kategorie 07): ko____ (kommen)", TEST, "", ["07"], liste)
    assert _finde(befunde, "Lösungen sichtbar")[0].stufe == WARNUNG


def test_saubere_aufgabenseite_ist_ok(liste):
    befunde = validation.blatt_pruefen(UEBUNG, TEST, "1. kommen", ["07"], liste)
    assert _finde(befunde, "Lösungen sichtbar")[0].stufe == OK


def test_zu_grosse_ueberschneidung_gibt_hinweis(liste):
    gleich = "Ergänze kommen, rennen, Sonne (Kategorie 07)."
    befunde = validation.blatt_pruefen(gleich, gleich, "", ["07"], liste)
    assert _finde(befunde, "zu ähnlich")


def test_leerer_uebungsteil_warnt(liste):
    befunde = validation.blatt_pruefen("", TEST, "", ["07"], liste)
    assert _finde(befunde, "Übungsteil")[0].stufe == WARNUNG


def test_fehlende_loesungen_geben_hinweis(liste):
    befunde = validation.blatt_pruefen(UEBUNG, TEST, "", ["07"], liste)
    assert _finde(befunde, "Lösungsblatt")[0].stufe == HINWEIS


def test_niveaufrage_wird_immer_gestellt(liste):
    """Die App darf das Niveau nicht stillschweigend übernehmen."""
    befunde = validation.blatt_pruefen(UEBUNG, TEST, "1. kommen", ["07"], liste)
    assert _finde(befunde, "Schwierigkeitsgrad")


def test_jeder_befund_hat_ein_symbol(liste):
    for b in validation.blatt_pruefen(UEBUNG, TEST, "", ["07"], liste):
        assert b.symbol
