"""PDF-Ausgabe der Blätter.

Geprüft wird nicht das Aussehen, sondern was auf dem Papier ankommt: die
richtigen Seiten in der richtigen Reihenfolge, der Text vollständig und
lesbar, und keine Zeichen, die der PDF-Betrachter falsch darstellt.

Der letzte Punkt ist der wichtigste. Die eingebauten PDF-Schriften kennen
Umlaute und «Guillemets», aber keine Pfeile und keine Aufzählungspunkte. Ohne
Ersatz druckte ein «→» als «fi» – falsch, aber unauffällig. Genau so etwas
fällt im Klassensatz erst auf, wenn er kopiert ist.
"""

from __future__ import annotations

import pytest

from rstrainer import pdf_export

extract_text = pytest.importorskip("pdfminer.high_level").extract_text


UEBUNG = "Aufgabe 1 (F1)\nFinde die Fehler.\n\n  Unten am Flus stand der Stand.\n"
TEST = "Mini-Test\n\nAufgabe 1  ___ / 4"
LOESUNG = "Flus → Fluss · grilierte → grillierte"


@pytest.fixture
def blatt(tmp_path, register):
    def bauen(**abweichend):
        argumente = dict(
            pfad=tmp_path / "blatt.pdf", schuelername="Testkind",
            titel="Zweifelsfälle", kategorien=["07", "17", "01"],
            register=register, inhalt_uebung=UEBUNG, inhalt_test=TEST,
            loesungen=LOESUNG, datum="15.09.2026",
        )
        argumente.update(abweichend)
        return pdf_export.uebungsblatt_schreiben(**argumente)
    return bauen


# --- Grundlegendes ----------------------------------------------------------

def test_uebungsblatt_ist_eine_gueltige_pdf_datei(blatt):
    pfad = blatt()
    assert pfad.exists()
    assert pfad.read_bytes()[:5] == b"%PDF-"


def test_uebungsteil_und_minitest_stehen_auf_getrennten_seiten(blatt):
    seiten = extract_text(str(blatt())).split("\f")
    seiten = [s for s in seiten if s.strip()]
    assert len(seiten) == 2
    assert "Finde die Fehler" in seiten[0]
    assert "Mini-Test" in seiten[1]
    assert "Finde die Fehler" not in seiten[1]


def test_loesungen_fehlen_ohne_ausdrueckliche_anforderung(blatt):
    text = extract_text(str(blatt()))
    assert "Fluss" not in text
    assert "LÖSUNGSBLATT" not in text


def test_loesungsblatt_kommt_auf_wunsch_mit_warnung(blatt):
    seiten = [s for s in extract_text(str(blatt(loesungen_anhaengen=True))).split("\f") if s.strip()]
    assert len(seiten) == 3
    assert "LÖSUNGSBLATT – NICHT AUSTEILEN" in seiten[2]
    assert "Fluss" in seiten[2]


def test_leere_loesungen_erzeugen_keine_dritte_seite(blatt):
    seiten = [s for s in extract_text(str(blatt(loesungen="   ", loesungen_anhaengen=True))).split("\f") if s.strip()]
    assert len(seiten) == 2


# --- Zeichenvorrat ----------------------------------------------------------

@pytest.mark.parametrize("roh,erwartet", [
    ("Flus → Fluss", "Flus -> Fluss"),
    ("• Punkt", "· Punkt"),
    ("a … b", "a ... b"),
    ("a ⇒ b", "a => b"),
])
def test_unbekannte_zeichen_werden_lesbar_ersetzt(roh, erwartet):
    assert pdf_export._winansi(roh) == erwartet


@pytest.mark.parametrize("zeichen", ["ä", "ö", "ü", "Ä", "Ö", "Ü", "«", "»", "–", "—", "é"])
def test_bekannte_zeichen_bleiben_unveraendert(zeichen):
    assert pdf_export._winansi(zeichen) == zeichen


def test_pfeile_im_blatt_landen_lesbar_im_pdf(blatt):
    text = extract_text(str(blatt(loesungen_anhaengen=True)))
    assert "Flus -> Fluss" in text
    assert "→" not in text and "ﬁ" not in text


def test_umlaute_und_guillemets_ueberstehen_den_druck(blatt):
    text = extract_text(str(blatt(inhalt_uebung="Die «Strasse» war grösser als Bäche.")))
    assert "«Strasse»" in text and "grösser" in text and "Bäche" in text


def test_markup_im_schuelertext_wird_nicht_als_auszeichnung_gelesen(blatt):
    """Ein «<» im Text darf die PDF-Erzeugung nicht sprengen."""
    text = extract_text(str(blatt(inhalt_uebung="a < b & c > d <b>fett</b>")))
    assert "a < b & c > d <b>fett</b>" in text


def test_einrueckung_bleibt_erhalten(blatt):
    text = extract_text(str(blatt(inhalt_uebung="Aufgabe\n    Eingerückter Fehlersuchtext.")))
    assert "    Eingerückter" in text or "  Eingerückter" in text


# --- Kopfzeile und Förderschwerpunkte ---------------------------------------

def test_kopfzeile_traegt_name_datum_und_schwerpunkte(blatt):
    text = extract_text(str(blatt()))
    assert "Testkind" in text and "15.09.2026" in text
    assert "Förderschwerpunkte:" in text
    assert "Zweifelsfälle" in text


def test_ohne_kategorien_bleibt_der_untertitel_weg(blatt):
    text = extract_text(str(blatt(kategorien=[])))
    assert "Förderschwerpunkte:" not in text


# --- Informationsblatt und Verlaufsbericht ----------------------------------

def test_informationsblatt_zeigt_schwerpunkte_und_fehlerliste(tmp_path, register):
    fehler = [
        {"wort_original": "Fluss", "wort_schueler": "Flus", "kategorie_nr": "07",
         "kontext": "Unten am Flus"},
        {"wort_original": "Bäche", "wort_schueler": "Beche", "kategorie_nr": "17",
         "kontext": "die Beche"},
    ]
    pfad = pdf_export.informationsblatt_schreiben(
        tmp_path / "info.pdf", "Testkind", "Diktat A", "15.09.2026", fehler, register,
        kennzahlen={"wortzahl_original": 80, "fehlerquote_prozent": 2.5},
        kommentar="Die Schärfung sitzt besser.", diktattext="Unten am Fluss.",
    )
    seiten = [s for s in extract_text(str(pfad)).split("\f") if s.strip()]
    assert seiten[0].count("Flus") >= 1
    assert "Schwerpunkte" in seiten[0]
    assert "80 Wörter" in seiten[0] and "2.5" in seiten[0]
    assert "Die Schärfung sitzt besser." in seiten[0]
    assert "Unten am Fluss." in seiten[1]          # Text auf eigener Seite


def test_informationsblatt_ohne_fehler_sagt_das_auch(tmp_path, register):
    pfad = pdf_export.informationsblatt_schreiben(
        tmp_path / "leer.pdf", "Testkind", "Diktat A", "15.09.2026", [], register)
    assert "Keine Fehler erfasst." in extract_text(str(pfad))


def test_freier_text_wird_als_solcher_bezeichnet(tmp_path, register):
    pfad = pdf_export.informationsblatt_schreiben(
        tmp_path / "frei.pdf", "Testkind", "Aufsatz", "15.09.2026", [], register,
        diktattext="Ich ging zum Zahnarzt.", art="freitext")
    text = extract_text(str(pfad))
    assert "Freier Text" in text and "Text des Kindes" in text


def test_verlaufsbericht_enthaelt_die_trendtabelle(tmp_path, register):
    zeilen = [{"kategorie_nr": "07", "summe_gesamt": 12, "text": "↓ deutlich weniger",
               "rate_vorher": 3.1, "rate_aktuell": 1.2}]
    pfad = pdf_export.verlaufsbericht_schreiben(
        tmp_path / "verlauf.pdf", "Testkind", "Januar bis Juni", zeilen, register,
        kommentar="Fortschritt sichtbar.")
    text = extract_text(str(pfad))
    assert "Lernverlauf Rechtschreibung" in text
    assert "Januar bis Juni" in text
    assert "3.1 -> 1.2" in text                     # Pfeil ersetzt, Zahlen intakt
    assert "Fortschritt sichtbar." in text


def test_verlaufsbericht_ohne_daten_bleibt_ehrlich(tmp_path, register):
    pfad = pdf_export.verlaufsbericht_schreiben(
        tmp_path / "leer.pdf", "Testkind", "–", [], register)
    assert "Noch keine auswertbaren Daten vorhanden." in extract_text(str(pfad))


# --- Gleiche Aufrufe wie die Word-Fassung -----------------------------------

def test_beide_module_haben_dieselben_signaturen():
    """Die Oberfläche wählt nur das Modul – die Aufrufe bleiben gleich."""
    import inspect

    from rstrainer import docx_export

    for name in ("uebungsblatt_schreiben", "informationsblatt_schreiben",
                 "verlaufsbericht_schreiben"):
        a = inspect.signature(getattr(docx_export, name))
        b = inspect.signature(getattr(pdf_export, name))
        assert list(a.parameters) == list(b.parameters), name
