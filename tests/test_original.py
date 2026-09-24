"""Jedes gedruckte Beispiel des Originals OLFA 3–9+ (2023) durch die Engine.

Quelle der Erwartungen: tests/original_korpus.py (mit Seitenzahl). Fälle mit
«unklar» in der Anmerkung sind im Original selbst nicht eindeutig (W4, W7 der
Spezifikation) und werden nur auf Plausibilität geprüft."""
import pytest

from rstrainer import olfa_engine as E
from original_korpus import B, T

LEX = {**E.VOKALLAENGEN, **E.VORGABE_LEXIKON}


def _lauf(s, t, anm):
    if " " in s:
        return E.wortgrenzen_ergebnis(s.split(" "), t, LEX)
    if " " in t:
        return E.zusammenschreibung_ergebnis(s, t, LEX)
    r = E.klassifiziere_wort(s, t, LEX, erzwingen=True, formfehler=(anm == "formfehler"))
    for e in r["ereignisse"]:
        E.abschliessen(e, {"ziel": t}, {"zielwortSicherheit": 1})
    return r["ereignisse"]


def _erhalten(evs):
    return sorted(E._erhalten(e) for e in evs)


@pytest.mark.parametrize("seite,s,t,erwartet,anm", B, ids=[f"S{x[0]}-{x[1]}" for x in B])
def test_beispiele_s16_bis_s28(seite, s, t, erwartet, anm):
    assert _erhalten(_lauf(s, t, anm)) == sorted(erwartet), f"S. {seite}: {s} → {t} ({anm})"


@pytest.mark.parametrize("seite,s,t,erwartet,anm", T, ids=[f"{x[4][:3]}-{x[1]}" for x in T])
def test_schuelertext_s48(seite, s, t, erwartet, anm):
    got = _erhalten(_lauf(s, t, anm))
    if "unklar" in anm:
        # Original selbst uneindeutig: Fehlerzahl darf abweichen, aber kein Raten und keine gesperrte Kategorie.
        assert got and not any(k in ("13", "14", "15", "16", "21", "22") for k in got)
        return
    assert got == sorted(erwartet), f"S. {seite}: {s} → {t} ({anm})"


def test_schuelertext_s48_summen_der_eindeutigen_faelle():
    """Die eindeutigen 48 Wörter des Schülertexts ergeben 74 Fehler; ihre
    Gruppenverteilung folgt S. 57."""
    from rstrainer import olfa_werte as W
    kats = [k for *_, erw, anm in T if "unklar" not in anm for k in erw]
    w = W.berechnen(kats, 188)
    assert w.gesamt == len(kats) == 74
    assert w.gruppen["I"] + w.gruppen["II"] + w.gruppen["III"] + w.ohne_gruppe["36"] + w.ohne_gruppe["37"] == 74


def test_korpus_ist_vollstaendig():
    assert len(B) == 181
    assert sum(len(x[3]) for x in T) == 92
    assert {x[0] for x in B} >= {16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28}


def test_original_widersprueche_sind_entschieden():
    """W1: *Könik → 19 (wie *stendik); W2/W3 betreffen nur die Werte."""
    r = E.klassifiziere_wort("Könik", "König", LEX)
    assert [e["kategorie"] for e in r["ereignisse"]] == ["19"]


@pytest.mark.parametrize("s,t,erwartet", [
    ("Zahn Artzt", "Zahnarzt", ["04", "11"]),          # innere Fehler der Teile (R19)
    ("weiter Reisen", "weiterreisen", ["02", "04"]),   # Verbkompositum, Teil gross (R18)
    ("Welt reise", "Weltreise", ["01", "04"]),
    ("garnich", "gar nicht", ["05", "29"]),
    ("kreisförmigergarten", "kreisförmiger Garten", ["05"]),
])
def test_wortgrenzen_mit_folgefehlern(s, t, erwartet):
    assert _erhalten(_lauf(s, t, "")) == sorted(erwartet)


@pytest.mark.parametrize("s,t,erwartet", [
    ("daß", "dass", ["37"]), ("Straße", "Strasse", ["37"]), ("mußten", "mussten", ["37"]),
    ("Fus", "Fuss", ["07"]), ("Strase", "Strasse", ["07"]), ("Preisse", "Preise", ["11"]), ("Kasse", "Kase", ["11"]),
])
def test_version_ch_s59(s, t, erwartet):
    evs = _lauf(s, t, "")
    assert _erhalten(evs) == sorted(erwartet)
    for e in evs:
        assert e["kategorie"] not in E.GESPERRT_CH


def test_f3_merkmal_nach_langvokal():
    fus = _lauf("Fus", "Fuss", "")[0]
    kas = _lauf("Kase", "Kasse", "")[0]
    assert (fus["kategorie"], fus["foerderbereich"]) == ("07", "F3")
    assert (kas["kategorie"], kas["foerderbereich"]) == ("07", "F1")


def test_out_of_the_box_grossschreibung_aendert_nichts_an_der_graphemzuordnung():
    """Jedes Beispiel auch mit vertauschter Gross-/Kleinschreibung: die
    Graphemkategorien bleiben, nur 01/02 kommt hinzu."""
    abweichungen = []
    for seite, s, t, erw, anm in B:
        if " " in s or " " in t or anm == "formfehler" or not s[:1].isalpha():
            continue
        s2 = s[0].swapcase() + s[1:]
        got = [k for k in _erhalten(_lauf(s2, t, anm)) if k not in ("01", "02")]
        soll = [k for k in sorted(erw) if k not in ("01", "02")]
        if got != soll:
            abweichungen.append((seite, s2, t, soll, got))
    assert abweichungen == []


def test_out_of_the_box_jedes_beispiel_im_traegersatz_diktatmodus():
    """Jedes Einzelwort-Beispiel als Diktat in einem Trägersatz: die Wortengine
    liefert dasselbe wie im Einzelwortaufruf."""
    abweichungen = []
    for seite, s, t, erw, anm in B:
        if " " in s or " " in t or anm == "formfehler":
            continue
        r = E.analysiere_diktat(f"Also {t} nie.", f"Also {s} nie.", LEX)
        got = sorted(e["kategorie"] or e["status"] for e in r["ereignisse"])
        # Im Diktatmodus greift die Wortersetzungsschwelle; solche Fälle gehen zur manuellen Kontrolle.
        if got == ["manual_review"]:
            continue
        if got != sorted(erw):
            abweichungen.append((seite, s, t, sorted(erw), got))
    assert abweichungen == []
