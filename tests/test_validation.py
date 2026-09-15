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


def test_passende_wortzahl_ist_ok(register):
    befunde = validation.diktat_pruefen(DIKTATTEXT, 40, [], register)
    wortzahl = _finde(befunde, "Wortanzahl")[0]
    assert wortzahl.stufe == OK


def test_abweichende_wortzahl_gibt_hinweis(register):
    befunde = validation.diktat_pruefen(DIKTATTEXT, 200, [], register)
    assert _finde(befunde, "Wortanzahl")[0].stufe == HINWEIS


def test_wortzahl_innerhalb_toleranz(register):
    """Dokumentierte Annahme: bis 20 % Abweichung ohne Hinweis."""
    ist = len(DIKTATTEXT.split())
    assert validation.diktat_pruefen(
        DIKTATTEXT, int(ist * 1.15), [], register)[0].stufe in (OK, HINWEIS)
    knapp = validation.diktat_pruefen(DIKTATTEXT, ist, [], register)
    assert _finde(knapp, "Wortanzahl")[0].stufe == OK


def test_passende_kategorie_wird_bestaetigt(register):
    befunde = validation.diktat_pruefen(DIKTATTEXT, 40, ["07"], register)
    treffer = _finde(befunde, "Konsonantenverdoppelung")[0]
    assert treffer.stufe == OK
    assert "rannte" in treffer.text or "nasse" in treffer.text


def test_unpassende_kategorie_warnt(register):
    """Ein Text ohne ß kann die Kategorie 15 (ss für ß) nicht üben."""
    text = "Am Morgen kam der Hund. Er lief davon."
    befunde = validation.diktat_pruefen(text, 9, ["15"], register)
    assert _finde(befunde, "ss für s")[0].stufe == WARNUNG


def test_leerer_text_warnt(register):
    befunde = validation.diktat_pruefen("   ", 90, ["07"], register)
    assert len(befunde) == 1 and befunde[0].stufe == WARNUNG


def test_korrekturlese_hinweis_erscheint_immer(register):
    befunde = validation.diktat_pruefen(DIKTATTEXT, 40, [], register)
    assert _finde(befunde, "Korrekturlesen")


def test_warnungen_stehen_oben(register):
    text = "Am Morgen kam der Hund."
    befunde = validation.diktat_pruefen(text, 5, ["15", "07"], register)
    stufen = [b.stufe for b in befunde]
    assert stufen == sorted(stufen, key=lambda s: {WARNUNG: 0, HINWEIS: 1, OK: 2}[s])


def test_pruefungen_blockieren_nie(register):
    """Grundsatz: Prüfungen melden, sie verhindern nichts."""
    befunde = validation.diktat_pruefen("Kurz.", 500, ["15", "33"], register)
    assert befunde  # es gibt Befunde …
    assert all(hasattr(b, "stufe") for b in befunde)  # … aber keine Ausnahme


def test_kategorie_treffer_sind_dublettenfrei(register):
    treffer = validation.kategorie_treffer("Sonne Sonne Sonne", "07", register.liste)
    assert treffer == ["Sonne"]


def test_unbekannte_kategorie_liefert_keine_treffer(register):
    assert validation.kategorie_treffer(DIKTATTEXT, "99", register.liste) == []


# --- Übungsblatt ------------------------------------------------------------

UEBUNG = "Aufgabe 1 (Kategorie 07): Ergänze ko___en, ren___en und So___e."
TEST = "Test 1 (Kategorie 07): Schreibe die Wörter mit doppeltem Konsonanten."


def test_genannte_kategorienummer_wird_bestaetigt(register):
    befunde = validation.blatt_pruefen(UEBUNG, TEST, "1. kommen", ["07"], register)
    assert _finde(befunde, "Zuordnung")[0].stufe == OK


def test_fehlende_kategoriezuordnung_warnt(register):
    befunde = validation.blatt_pruefen(
        "Male ein Bild.", "Zeichne etwas.", "", ["15"], register)
    assert _finde(befunde, "Zuordnung")[0].stufe == WARNUNG


def test_loesungsverdacht_auf_der_aufgabenseite(register):
    befunde = validation.blatt_pruefen(
        "Aufgabe 1 (Kategorie 07): ko___en  Lösung: kommen", TEST, "", ["07"], register)
    treffer = _finde(befunde, "Lösungen sichtbar")[0]
    assert treffer.stufe == WARNUNG


def test_klammerloesung_nach_luecke_wird_erkannt(register):
    befunde = validation.blatt_pruefen(
        "Aufgabe 1 (Kategorie 07): ko____ (kommen)", TEST, "", ["07"], register)
    assert _finde(befunde, "Lösungen sichtbar")[0].stufe == WARNUNG


def test_saubere_aufgabenseite_ist_ok(register):
    befunde = validation.blatt_pruefen(UEBUNG, TEST, "1. kommen", ["07"], register)
    assert _finde(befunde, "Lösungen sichtbar")[0].stufe == OK


def test_zu_grosse_ueberschneidung_gibt_hinweis(register):
    gleich = "Ergänze kommen, rennen, Sonne (Kategorie 07)."
    befunde = validation.blatt_pruefen(gleich, gleich, "", ["07"], register)
    assert _finde(befunde, "zu ähnlich")


def test_leerer_uebungsteil_warnt(register):
    befunde = validation.blatt_pruefen("", TEST, "", ["07"], register)
    assert _finde(befunde, "Übungsteil")[0].stufe == WARNUNG


def test_fehlende_loesungen_geben_hinweis(register):
    befunde = validation.blatt_pruefen(UEBUNG, TEST, "", ["07"], register)
    assert _finde(befunde, "Lösungsblatt")[0].stufe == HINWEIS


def test_niveaufrage_wird_immer_gestellt(register):
    """Die App darf das Niveau nicht stillschweigend übernehmen."""
    befunde = validation.blatt_pruefen(UEBUNG, TEST, "1. kommen", ["07"], register)
    assert _finde(befunde, "Schwierigkeitsgrad")


def test_jeder_befund_hat_ein_symbol(register):
    for b in validation.blatt_pruefen(UEBUNG, TEST, "", ["07"], register):
        assert b.symbol
