"""Tests der Diff- und Abgleichslogik."""

from __future__ import annotations

import pytest

from rstrainer import diffing
from rstrainer.diffing import ERSETZT, FEHLT, ZUSAETZLICH


# --- Marker auf Wortebene ---------------------------------------------------

@pytest.mark.parametrize("original,schueler,erwartet", [
    ("Haus", "haus", "klein_statt_gross"),
    ("kalt", "Kalt", "gross_statt_klein"),
    ("kommen", "komen", "doppelkonsonant_fehlt"),
    ("hat", "hatt", "doppelkonsonant_zuviel"),
    ("Zucker", "Zuker", "ck"),
    ("Katze", "Kazze", "tz"),
    ("Zahn", "Zan", "dehnungs_h_fehlt"),
    ("Tor", "Tohr", "dehnungs_h_zuviel"),
    ("Wiese", "Wise", "ie_fehlt"),
    ("Boot", "Bot", "doppelvokal_fehlt"),
    ("Hund", "Hunt", "auslautverhaertung"),
    ("Korb", "Korp", "auslautverhaertung"),
    ("Fuß", "Fus", "s_statt_sz"),
    ("las", "laß", "sz_statt_s"),
    ("dass", "daß", "sz_statt_ss"),
    ("Vater", "Fater", "f_statt_v"),
    ("Fisch", "Visch", "v_statt_f"),
    ("Vase", "Wase", "w_statt_v"),
    ("Wasser", "Vasser", "v_statt_w"),
    ("mich", "mig", "g_statt_ch"),
    ("Bücher", "Bucher", "umlaut_fehlt"),
    ("Bären", "Beren", "e_statt_ae"),
    ("Berg", "Bärg", "ae_statt_e"),
    ("Brot", "Bort", "dreher"),
    ("Schule", "Sule", "konsonant_fehlt"),
    ("wenig", "wenich", "ch_statt_g"),
])
def test_marker_wird_erkannt(original, schueler, erwartet):
    assert erwartet in diffing.marker_bestimmen(original, schueler)


def test_ss_wird_nicht_als_grossschreibfehler_verbucht():
    """casefold() bildet ß auf ss ab – das darf den ß-Fehler nicht verdecken."""
    marker = diffing.marker_bestimmen("Straße", "Strasse")
    assert "ss_statt_sz" in marker
    assert "gross_statt_klein" not in marker
    assert "klein_statt_gross" not in marker


def test_gleiches_wort_hat_keine_marker():
    assert diffing.marker_bestimmen("Haus", "Haus") == ()


def test_fehlendes_wort():
    assert diffing.marker_bestimmen("Haus", "") == ("wort_fehlt",)


def test_dreher_erzeugt_keine_zusatzmarker():
    """Ein Dreher erklärt das Wort vollständig – alles Weitere wäre Rauschen."""
    assert diffing.marker_bestimmen("Brot", "Bort") == ("dreher",)


def test_marker_sind_dublettenfrei():
    marker = diffing.marker_bestimmen("Wassermann", "Wasermann")
    assert len(marker) == len(set(marker))


# --- Ausrichtung auf Textebene ----------------------------------------------

def test_gleiche_texte_ohne_abweichung():
    text = "Der Hund läuft über die Wiese."
    assert diffing.vergleiche(text, text) == []


def test_grossschreibfehler_zerstoert_ausrichtung_nicht():
    """Kernfall: 'haus' statt 'Haus' muss als Ersetzung erkannt werden,
    nicht als Löschung plus Einfügung."""
    abw = diffing.vergleiche("Wir gehen zum Haus", "Wir gehen zum haus")
    assert len(abw) == 1
    assert abw[0].art == ERSETZT
    assert (abw[0].wort_original, abw[0].wort_schueler) == ("Haus", "haus")


def test_fehlendes_wort_wird_erkannt():
    abw = diffing.vergleiche("Der kleine Hund bellt", "Der Hund bellt")
    assert [a.art for a in abw] == [FEHLT]
    assert abw[0].wort_original == "kleine"


def test_zusaetzliches_wort_wird_erkannt():
    abw = diffing.vergleiche("Der Hund bellt", "Der kleine Hund bellt")
    assert [a.art for a in abw] == [ZUSAETZLICH]
    assert abw[0].wort_schueler == "kleine"


def test_satzzeichen_erzeugen_keine_abweichung():
    """Dokumentierte Annahme: Satzzeichen werden nicht verglichen."""
    assert diffing.vergleiche("Hallo, Welt!", "Hallo Welt") == []


def test_mehrere_fehler_in_reihenfolge():
    original = "Der Hund lief schnell über die Wiese zum Haus"
    schueler = "Der Hunt lief schnel über die Wise zum haus"
    abw = diffing.vergleiche(original, schueler)
    assert [a.wort_original for a in abw] == ["Hund", "schnell", "Wiese", "Haus"]
    assert all(a.art == ERSETZT for a in abw)


def test_kontext_markiert_das_betroffene_wort():
    abw = diffing.vergleiche("Der Hund lief davon", "Der Hunt lief davon")
    assert "[Hund]" in abw[0].kontext


def test_leerer_schuelertext_meldet_alle_woerter_als_fehlend():
    abw = diffing.vergleiche("Ein kurzer Satz", "")
    assert len(abw) == 3
    assert all(a.art == FEHLT for a in abw)


# --- Kategorie-Vorschläge ---------------------------------------------------

def test_vorschlaege_verweisen_auf_die_liste(liste):
    abw = diffing.vergleiche("Der Hund kommt", "Der Hunt komt", liste)
    nach_wort = {a.wort_original: a for a in abw}
    assert nach_wort["Hund"].vorschlaege[0].nr == "19"
    assert nach_wort["kommt"].vorschlaege[0].nr == "07"


def test_faelschlich_gesetztes_sz_wird_erkannt(liste):
    """Schweizer Fall: Im Originaltext kommt nie ein ß vor, ein Kind kann aber
    trotzdem eines setzen. Kategorie 14 und 16 müssen das auffangen."""
    assert diffing.kategorie_vorschlaege(
        diffing.marker_bestimmen("dass", "daß"), liste)[0].nr == "16"
    assert diffing.kategorie_vorschlaege(
        diffing.marker_bestimmen("las", "laß"), liste)[0].nr == "14"


def test_ein_marker_darf_mehrere_kategorien_vorschlagen(liste):
    """08 und 11 unterscheiden sich durch die Vokallänge, die das Werkzeug
    nicht kennt – dann werden beide vorgeschlagen."""
    vorschlaege = diffing.kategorie_vorschlaege(("doppelkonsonant_zuviel",), liste)
    assert [k.nr for k in vorschlaege] == ["08", "11"]


def test_ohne_liste_keine_vorschlaege():
    abw = diffing.vergleiche("Der Hund", "Der Hunt")
    assert abw[0].vorschlaege == []
    assert abw[0].marker  # Marker gibt es trotzdem


def test_unbekannter_marker_liefert_leere_liste(liste):
    assert diffing.kategorie_vorschlaege(("gibt_es_nicht",), liste) == []


# --- Kennzahlen -------------------------------------------------------------

def test_kennzahlen():
    k = diffing.kennzahlen("Der Hund lief schnell", "Der Hunt lief schnell")
    assert k["wortzahl_original"] == 4
    assert k["abweichungen"] == 1
    assert k["richtig_geschrieben"] == 3
    assert k["fehlerquote_prozent"] == 25.0


def test_kennzahlen_bei_leerem_original():
    k = diffing.kennzahlen("", "irgendwas")
    assert k["fehlerquote_prozent"] == 0.0
