"""Gemeinsame Testvorrichtungen."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rstrainer import db, olfa  # noqa: E402
from rstrainer.analysis import Diktatpunkt  # noqa: E402


@pytest.fixture
def liste() -> olfa.Kategorienliste:
    """Die mitgelieferte Kategorienliste."""
    return olfa.laden(Path(__file__).resolve().parent.parent / "data" / "olfa_kategorien.json")


@pytest.fixture
def con():
    """Frische Datenbank im Arbeitsspeicher."""
    verbindung = db.verbinden(":memory:")
    yield verbindung
    verbindung.close()


@pytest.fixture
def schueler_id(con) -> int:
    return db.schueler_anlegen(con, "Testkind", kuerzel="TK", klasse="5a")


def diktatpunkte(anzahl: int, wortzahl: int = 100) -> list[Diktatpunkt]:
    """Gleichmässige Reihe von Diktaten für Trendtests."""
    return [
        Diktatpunkt(i + 1, f"2026-01-{i + 1:02d}", f"Diktat {i + 1}", wortzahl)
        for i in range(anzahl)
    ]


def fehlerreihe(kategorie_nr: str, mengen: list[int]) -> list[dict]:
    """Baut Fehlereinträge aus einer Mengenreihe je Diktat."""
    eintraege = []
    for i, menge in enumerate(mengen):
        eintraege.extend(
            {"kategorie_nr": kategorie_nr, "diktat_id": i + 1} for _ in range(menge)
        )
    return eintraege
