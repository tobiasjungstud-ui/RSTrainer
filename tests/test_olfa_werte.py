"""Rechenproben aus dem Original OLFA 3–9+ (S. 30, 33–35, 49) und Zählregeln (S. 16, 47)."""
from rstrainer import olfa_werte as W
from rstrainer import olfa_engine as E


def test_gruppen_der_kopiervorlage_s57():
    assert {nr for nr, g in E.GRUPPEN.items() if g == "I"} == {"03", "06", "11", "12", "29", "30", "31", "32", "33", "34", "35"}
    assert {nr for nr, g in E.GRUPPEN.items() if g == "II"} == {"01", "04", "07", "09", "13", "17", "19", "23", "25", "27"}
    assert {nr for nr, g in E.GRUPPEN.items() if g == "III"} == {"02", "05", "08", "10", "14", "15", "16", "18", "20", "24", "26", "28"}
    assert "36" not in E.GRUPPEN and "37" not in E.GRUPPEN


def test_abbildung_7_s49_fuenftklaessler():
    """188 Wörter, 92 Fehler; Gruppen 55/22/6; 36: 5, 37: 4; F/100 48,9; KW −32."""
    zaehlung = {"01": 6, "02": 2, "04": 3, "05": 1, "07": 3, "09": 7, "10": 1, "20": 1, "23": 2, "24": 1,
                "27": 1, "29": 24, "30": 8, "31": 14, "32": 2, "33": 2, "34": 4, "35": 1, "36": 5, "37": 4}
    kats = [nr for nr, n in zaehlung.items() for _ in range(n)]
    w = W.berechnen(kats, 188, "5 Mitte", "gymnasium")
    assert w.gesamt == 92
    assert (w.gruppen["I"], w.gruppen["II"], w.gruppen["III"]) == (55, 22, 6)
    # Original druckt 66,2 / 26,5 / 7,3 und KW −32 (W8: 55/83 = 66,27 wird dort abgerundet).
    # Nach S. 32 (eine Nachkommastelle, Summe 100) ergibt sich 66,3 / 26,5 / 7,2 und KW −33.
    assert w.prozent == {"I": 66.3, "II": 26.5, "III": 7.2}
    assert w.f100 == 48.9
    assert w.kw == -33
    assert w.tf == 7.2
    # Original druckt LW −443 (RF = TF eingesetzt, W3); nach der Formel S. 35: RF = 48,9/7,2 = 6,8 → −416.
    assert w.rf == 6.8
    assert w.lw == -417
    assert any("Textmenge" in s for s in w.warnungen)
    assert any("Gruppe I" in s for s in w.warnungen)


def test_beispiel_olaf_s33_bis_s35():
    """125 Fehler / 523 Wörter → F/100 23,9; 23/59/18 % → KW 54; TF 7,2 → RF 3,3; LW 1,1 → gerundet 1."""
    w = W.Werte(woerter=523, gesamt=125, gruppen={"I": 23, "II": 59, "III": 18}, ohne_gruppe={"36": 0, "37": 0},
                prozent={"I": 23.0, "II": 59.0, "III": 18.0}, f100=23.9, kw=54.0)
    assert W._runde(100 * 125 / 523) == 23.9
    assert (59 + 18) - 23 == 54
    rf = W._runde(23.9 / 7.2)
    assert rf == 3.3
    assert W._runde(77 - 23 * rf) == 1.1


def test_tf_tabelle_5_und_formeln_s29():
    assert W.tf("5 Mitte", "gymnasium") == 7.2
    assert W.tf("9 Mitte", "hauptschule") == 11.2
    assert W.tf("3 Mitte", "realschule") == 21.5
    assert W.tf("Unbekannt") is None
    assert round(W.tf_formel(5), 1) == 7.2
    assert round(W.tf_formel(6, "realschule"), 1) == 8.0
    assert round(W.tf_formel(6, "hauptschule"), 1) == 11.0


def test_zaehlregel_s16_und_s47():
    assert W.woerter_zaehlen("Ich gehe in die Klas se 9a der IGS.") == 8   # Klas + se getrennt: hier 8 Tokens, Kompositum-Regel greift in der Ausrichtung
    assert W.woerter_zaehlen("bekam es koste ca 100000000000000") == 4
    assert W.woerter_zaehlen("13 Tagen wusste er wie man den Mond in") == 8
    assert W.woerter_zaehlen("") == 0


def test_warnung_37_ueber_drei_prozent():
    kats = ["07"] * 60 + ["37"] * 3
    w = W.berechnen(kats, 400)
    assert any("37" in s for s in w.warnungen)


def test_deutung_kw_baender_s36():
    assert "über 70" in W.deutung_kw(80)
    assert "50–70" in W.deutung_kw(60)
    assert "0–50" in W.deutung_kw(30)
    assert "ärztliche" in W.deutung_kw(-5)
