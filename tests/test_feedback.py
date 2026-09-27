"""Rückmeldung «was ist gut, was üben wir als Nächstes» – deterministisch aus
den Funden eines Analyse-Durchgangs, für alle drei Modi (Diktatmodus,
Freitextmodus, Freies Diktat)."""
from __future__ import annotations

from rstrainer import feedback
from rstrainer.ui import gemeinsam as g


def test_fehlerfreier_durchgang_ist_ausschliesslich_lob():
    gut, verbessern = feedback.feedback_erstellen(["A"], [], g.register())
    assert gut == ["Kein einziger Fehler in diesem Durchgang gefunden."]
    assert verbessern == []


def test_bereich_ohne_treffer_wird_gelobt_bereich_mit_treffern_zum_ueben():
    reg = g.register()
    funde = [
        feedback.Fund("07", "Fater", "Vater"),
        feedback.Fund("07", "Fogel", "Vogel"),
        feedback.Fund("11", "Strase", "Strasse"),
    ]
    gut, verbessern = feedback.feedback_erstellen(["A"], funde, reg)
    assert gut == []                                  # Bereich A hat Treffer – kein Lob dafür
    assert verbessern[0].startswith(f"{reg.label('07')}: 2×")
    assert "Fater" in verbessern[0] and "Vater" in verbessern[0]
    assert any(z.startswith(f"{reg.label('11')}: 1×") for z in verbessern)


def test_mehrere_geprueft_bereiche_ohne_treffer_werden_alle_gelobt():
    reg = g.register()
    funde = [feedback.Fund("B:Kasus", "ihn", "ihm")]
    gut, verbessern = feedback.feedback_erstellen(["B", "C", "D", "E"], funde, reg)
    assert "Keine Auffälligkeiten im Bereich Satzbau und Syntax." in gut
    assert "Keine Auffälligkeiten im Bereich Zeichensetzung." in gut
    assert "Keine Auffälligkeiten im Bereich Textebene." in gut
    assert not any("Grammatik" in z for z in gut)      # B hatte einen Treffer
    assert len(verbessern) == 1


def test_hoechstens_begrenzt_die_verbessern_liste():
    reg = g.register()
    funde = [feedback.Fund(nr) for nr in ["07", "08", "10", "20"] for _ in range(1)]
    gut, verbessern = feedback.feedback_erstellen(["A"], funde, reg, hoechstens=2)
    assert len(verbessern) == 2
