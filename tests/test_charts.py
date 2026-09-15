"""Tests der Diagrammerzeugung."""

from __future__ import annotations

from conftest import diktatpunkte
from rstrainer import charts


def test_balkendiagramm_entsteht(tmp_path, register):
    figur = charts.balken_kategorien({"07": 12, "11": 5}, register)
    pfad = charts.speichern(figur, tmp_path / "balken.png")
    assert pfad.exists() and pfad.stat().st_size > 1000


def test_balkendiagramm_ohne_daten_stuerzt_nicht_ab(tmp_path, register):
    figur = charts.balken_kategorien({}, register)
    assert charts.speichern(figur, tmp_path / "leer.png").exists()


def test_balkendiagramm_begrenzt_die_zeilen(register):
    haeufigkeit = {f"{i:02d}": 40 - i for i in range(1, 30)}
    figur = charts.balken_kategorien(haeufigkeit, register, hoechstens=5)
    achse = figur.axes[0]
    assert len(achse.get_yticklabels()) == 5


def test_verlauf_zeichnet_hoechstens_fuenf_linien(register):
    diktate = diktatpunkte(6)
    reihen = {f"{i:02d}": [i] * 6 for i in range(1, 10)}
    figur, gezeigt = charts.verlauf_linien(diktate, reihen, register)
    assert len(gezeigt) == charts.MAX_SERIEN
    assert len(figur.axes[0].lines) == charts.MAX_SERIEN


def test_haeufigste_kategorien_werden_gezeigt(register):
    diktate = diktatpunkte(3)
    reihen = {"01": [1, 1, 1], "07": [9, 9, 9], "11": [5, 5, 5]}
    _, gezeigt = charts.verlauf_linien(diktate, reihen, register, hoechstens=2)
    assert gezeigt == ["07", "11"]


def test_verlauf_hat_immer_eine_legende(register):
    diktate = diktatpunkte(3)
    figur, _ = charts.verlauf_linien(diktate, {"07": [1, 2, 3], "11": [3, 2, 1]}, register)
    assert figur.axes[0].get_legend() is not None


def test_farben_werden_in_fester_reihenfolge_vergeben(register):
    """Kategorie-Farben dürfen nicht davon abhängen, wie viele Linien
    gerade sichtbar sind."""
    diktate = diktatpunkte(3)
    reihen = {"07": [9, 9, 9], "11": [5, 5, 5], "01": [1, 1, 1]}
    figur, gezeigt = charts.verlauf_linien(diktate, reihen, register)
    farben = [linie.get_color() for linie in figur.axes[0].lines]
    assert farben == charts.SERIENFARBEN[:len(gezeigt)]


def test_verlauf_ohne_daten_stuerzt_nicht_ab(tmp_path, register):
    figur, gezeigt = charts.verlauf_linien([], {}, register)
    assert gezeigt == []
    assert charts.speichern(figur, tmp_path / "leer.png").exists()


def test_y_achse_beginnt_bei_null(register):
    diktate = diktatpunkte(3)
    figur, _ = charts.verlauf_linien(diktate, {"07": [4, 5, 6]}, register)
    assert figur.axes[0].get_ylim()[0] == 0


def test_raten_statt_absoluter_zahlen(register):
    """Bei 200 Wörtern sind 10 Fehler 5 pro 100 Wörter."""
    diktate = [charts.Diktatpunkt(1, "2026-01-01", "D", 200)]
    figur, _ = charts.verlauf_linien(diktate, {"07": [10]}, register)
    assert figur.axes[0].lines[0].get_ydata()[0] == 5.0


def test_diktat_ohne_wortzahl_fuehrt_nicht_zur_division_durch_null(register):
    diktate = [charts.Diktatpunkt(1, "2026-01-01", "D", 0)]
    figur, _ = charts.verlauf_linien(diktate, {"07": [3]}, register)
    assert figur.axes[0].lines[0].get_ydata()[0] == 0.0
