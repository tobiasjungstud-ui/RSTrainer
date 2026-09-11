"""Tests der Trendberechnung und der Empfehlungslogik."""

from __future__ import annotations

import pytest

from conftest import diktatpunkte, fehlerreihe
from rstrainer import analysis
from rstrainer.analysis import ABNEHMEND, NEU, STAGNIEREND, ZU_WENIG_DATEN, ZUNEHMEND


# --- Zeitreihe --------------------------------------------------------------

def test_zeitreihe_zaehlt_je_diktat():
    diktate = diktatpunkte(3)
    fehler = fehlerreihe("07", [2, 0, 5])
    assert analysis.zeitreihe(diktate, fehler) == {"07": [2, 0, 5]}


def test_fehler_ohne_diktat_werden_ignoriert():
    """Ein Fehler ohne Diktatbezug hat keinen Zeitpunkt und darf den
    Verlauf nicht verfälschen."""
    diktate = diktatpunkte(2)
    fehler = [{"kategorie_nr": "07", "diktat_id": None},
              {"kategorie_nr": "07", "diktat_id": 999},
              {"kategorie_nr": "07", "diktat_id": 1}]
    assert analysis.zeitreihe(diktate, fehler) == {"07": [1, 0]}


# --- Trend ------------------------------------------------------------------

def test_zu_wenig_daten_unterhalb_von_fenster_plus_eins():
    diktate = diktatpunkte(3)
    trend = analysis.trend_bestimmen([1, 1, 1], diktate, fenster=3)
    assert trend.einstufung == ZU_WENIG_DATEN


def test_abnehmender_trend():
    diktate = diktatpunkte(6)
    trend = analysis.trend_bestimmen([6, 6, 6, 1, 1, 0], diktate, fenster=3)
    assert trend.einstufung == ABNEHMEND
    assert trend.rate_vorher > trend.rate_aktuell


def test_zunehmender_trend():
    diktate = diktatpunkte(6)
    trend = analysis.trend_bestimmen([0, 1, 1, 4, 5, 6], diktate, fenster=3)
    assert trend.einstufung == ZUNEHMEND


def test_gleichbleibend_ist_stagnierend():
    diktate = diktatpunkte(6)
    trend = analysis.trend_bestimmen([4, 4, 4, 4, 4, 4], diktate, fenster=3)
    assert trend.einstufung == STAGNIEREND
    assert trend.veraenderung == 0.0


def test_kleine_schwankung_bleibt_stagnierend():
    """Dokumentierte Annahme: unter 20 % Veränderung ist es Rauschen."""
    diktate = diktatpunkte(6)
    trend = analysis.trend_bestimmen([10, 10, 10, 9, 10, 10], diktate, fenster=3)
    assert trend.einstufung == STAGNIEREND


def test_mindestdifferenz_verhindert_scheintrend():
    """2 statt 1 Fehler sind +100 %, aber keine belastbare Verschlechterung."""
    diktate = diktatpunkte(6)
    trend = analysis.trend_bestimmen([1, 0, 0, 0, 1, 1], diktate, fenster=3)
    assert trend.einstufung == STAGNIEREND


def test_neu_aufgetretene_kategorie():
    diktate = diktatpunkte(6)
    trend = analysis.trend_bestimmen([0, 0, 0, 3, 4, 3], diktate, fenster=3)
    assert trend.einstufung == NEU


def test_durchgehend_null_ist_stagnierend():
    diktate = diktatpunkte(6)
    trend = analysis.trend_bestimmen([0, 0, 0, 0, 0, 0], diktate, fenster=3)
    assert trend.einstufung == STAGNIEREND


def test_normierung_auf_hundert_woerter():
    """Gleich viele Fehler in einem doppelt so langen Diktat sind eine
    Verbesserung, keine Stagnation."""
    diktate = [
        analysis.Diktatpunkt(i + 1, f"2026-01-{i + 1:02d}", "D", wortzahl)
        for i, wortzahl in enumerate([50, 50, 50, 200, 200, 200])
    ]
    trend = analysis.trend_bestimmen([5, 5, 5, 5, 5, 5], diktate, fenster=3)
    assert trend.einstufung == ABNEHMEND
    assert trend.rate_vorher == 10.0
    assert trend.rate_aktuell == 2.5


def test_diktat_ohne_wortzahl_zaehlt_als_null_rate():
    diktate = [analysis.Diktatpunkt(1, "2026-01-01", "D", 0)]
    trend = analysis.trend_bestimmen([5], diktate)
    assert trend.rate_aktuell == 0.0
    assert trend.summe_gesamt == 5


def test_raten_werden_auf_zwei_stellen_gerundet():
    diktate = diktatpunkte(6, wortzahl=90)
    trend = analysis.trend_bestimmen([1, 2, 3, 4, 5, 6], diktate, fenster=3)
    assert trend.rate_aktuell == round(trend.rate_aktuell, 2)


def test_trends_bestimmen_deckt_alle_kategorien_ab():
    diktate = diktatpunkte(6)
    fehler = fehlerreihe("07", [3] * 6) + fehlerreihe("11", [6, 6, 6, 1, 1, 0])
    trends = analysis.trends_bestimmen(diktate, fehler)
    assert set(trends) == {"07", "11"}
    assert trends["07"].einstufung == STAGNIEREND
    assert trends["11"].einstufung == ABNEHMEND


# --- Empfehlung -------------------------------------------------------------

def test_stagnierendes_schlaegt_sich_besserndes():
    """Kernanforderung: Fehler, die sich bereits bessern, haben niedrigere
    Priorität als stagnierende – auch bei mehr Gesamtfehlern."""
    diktate = diktatpunkte(6)
    fehler = (fehlerreihe("07", [4, 4, 4, 4, 4, 4])       # stagnierend, 24 gesamt
              + fehlerreihe("11", [8, 8, 8, 1, 0, 0]))    # abnehmend, 25 gesamt
    empfehlungen = analysis.empfehlungen(diktate, fehler)
    assert [e.kategorie_nr for e in empfehlungen][0] == "07"


def test_zunehmendes_steht_ganz_oben():
    diktate = diktatpunkte(6)
    fehler = (fehlerreihe("07", [3, 3, 3, 3, 3, 3])
              + fehlerreihe("01", [0, 1, 1, 5, 6, 7]))
    empfehlungen = analysis.empfehlungen(diktate, fehler)
    assert empfehlungen[0].kategorie_nr == "01"
    assert empfehlungen[0].trend.einstufung == ZUNEHMEND


def test_hoechstens_drei_vorschlaege():
    diktate = diktatpunkte(6)
    fehler = []
    for nr in ["01", "02", "07", "11", "13", "22"]:
        fehler += fehlerreihe(nr, [2] * 6)
    assert len(analysis.empfehlungen(diktate, fehler)) == 3


def test_anzahl_ist_einstellbar():
    diktate = diktatpunkte(6)
    fehler = fehlerreihe("01", [2] * 6) + fehlerreihe("07", [3] * 6)
    assert len(analysis.empfehlungen(diktate, fehler, anzahl=1)) == 1


def test_blockierte_kategorien_werden_uebersprungen():
    diktate = diktatpunkte(6)
    fehler = fehlerreihe("01", [9] * 6) + fehlerreihe("07", [2] * 6)
    empfehlungen = analysis.empfehlungen(diktate, fehler, blockieren=["01"])
    assert [e.kategorie_nr for e in empfehlungen] == ["07"]


def test_juengere_diktate_wiegen_schwerer():
    """Zeitgewichtung: dieselbe Gesamtzahl, aber zuletzt aufgetreten."""
    diktate = diktatpunkte(6)
    frueh = fehlerreihe("01", [6, 6, 0, 0, 0, 0])
    spaet = fehlerreihe("07", [0, 0, 0, 0, 6, 6])
    empfehlungen = analysis.empfehlungen(diktate, frueh + spaet)
    assert empfehlungen[0].kategorie_nr == "07"


def test_begruendung_nennt_zahlen_und_trend():
    diktate = diktatpunkte(6)
    fehler = fehlerreihe("12", [3, 0, 3, 3, 0, 3])
    begruendung = analysis.empfehlungen(diktate, fehler)[0].begruendung
    assert "Kategorie 12" in begruendung
    assert "von" in begruendung
    assert begruendung.endswith(".")


def test_begruendung_erwaehnt_besserung_bei_abnehmendem_trend():
    diktate = diktatpunkte(6)
    fehler = fehlerreihe("11", [8, 8, 8, 1, 1, 0])
    begruendung = analysis.empfehlungen(diktate, fehler)[0].begruendung
    assert "Besserung" in begruendung


def test_ohne_fehler_keine_empfehlung():
    assert analysis.empfehlungen(diktatpunkte(6), []) == []


def test_ohne_diktate_keine_empfehlung():
    assert analysis.empfehlungen([], []) == []


def test_punktzahl_ist_absteigend_sortiert():
    diktate = diktatpunkte(6)
    fehler = (fehlerreihe("01", [5] * 6) + fehlerreihe("07", [3] * 6)
              + fehlerreihe("11", [1] * 6))
    punkte = [e.punktzahl for e in analysis.empfehlungen(diktate, fehler)]
    assert punkte == sorted(punkte, reverse=True)


def test_details_enthalten_nachvollziehbare_faktoren():
    diktate = diktatpunkte(6)
    fehler = fehlerreihe("07", [4] * 6)
    details = analysis.empfehlungen(diktate, fehler)[0].details
    assert set(details) >= {"gewichtete_rate", "verbreitung", "trendfaktor",
                            "fehler_gesamt", "reihe"}
    assert details["fehler_gesamt"] == 24


@pytest.mark.parametrize("einstufung", [ABNEHMEND, STAGNIEREND, ZUNEHMEND, NEU,
                                        ZU_WENIG_DATEN])
def test_jede_einstufung_hat_symbol_und_text(einstufung):
    assert analysis.TREND_SYMBOL[einstufung]
    assert analysis.TREND_TEXT[einstufung]
    assert analysis.TREND_FAKTOR[einstufung] > 0


def test_abnehmend_wird_abgewertet_zunehmend_aufgewertet():
    assert analysis.TREND_FAKTOR[ABNEHMEND] < analysis.TREND_FAKTOR[STAGNIEREND]
    assert analysis.TREND_FAKTOR[ZUNEHMEND] > analysis.TREND_FAKTOR[STAGNIEREND]
