"""Belastungskorpus: realistische Sek-I-Fehler (de-CH), die nicht im Goldstandard
des Originals stehen. Erwartet ist das geprüfte Verhalten der Engine; wo es von
der naiven Erwartung abweicht, folgt es dem Original:

* *seen → sehen, *geen → gehen, *Schue → Schuhe = 09, nicht 29 (S. 21: das
  silbentrennende h zählt zur Längenmarkierung).
* *durg → durch, *nog → noch = 33, nicht 28 (S. 25: *Bug für Buch = 33; 28
  gilt der Endung -ig/-ich).
* *Schtein → Stein, *schpielen → spielen = 37 (S. 25: lautgetreues <sch> im
  Anlaut-<st>/<sp>), Kirche/Kirsche = 33 (sch/ch ist eine Verwechslung, S. 25).
* *Werrk → Werk = 08 wie *kallt → kalt (§19) – kurzer Vokal davor.
* *Geburtstack → Geburtstag = 19 + 11: Umkehrung von *Sag für Sack (S. 21).
* Umschriften: *Schueler → Schüler = 36 (ein Fehler), *Kwelle → Quelle = 37.
* Fremdwörter mit Merkstelle: *Restorant → Restaurant = 37 (Lexikon).
"""

from __future__ import annotations

import pytest

from rstrainer import olfa_engine as E

KORPUS = [
    ("wichtigste", "Wichtigste", ['01']),
    ("schönes", "Schönes", ['01']),
    ("laufen", "Laufen", ['01']),
    ("Deutsche", "deutsche", ['02']),
    ("Gehe", "gehe", ['02']),
    ("ScHule", "Schule", ['03']),
    ("SChule", "Schule", ['03']),
    ("adresse", "Adresse", ['01']),
    ("komt", "kommt", ['07']),
    ("Sone", "Sonne", ['07']),
    ("wolte", "wollte", ['07']),
    ("dan", "dann", ['07']),
    ("wen", "wenn", ['07']),
    ("den", "denn", ['07']),
    ("das", "dass", ['07']),
    ("Zuker", "Zucker", ['07']),
    ("Zukker", "Zucker", ['07']),
    ("Glük", "Glück", ['07']),
    ("zurük", "zurück", ['07']),
    ("Kaze", "Katze", ['07']),
    ("jezt", "jetzt", ['07']),
    ("Plaz", "Platz", ['07']),
    ("plözlich", "plötzlich", ['07']),
    ("interesant", "interessant", ['07']),
    ("Tschüs", "Tschüss", ['07']),
    ("Brüke", "Brücke", ['07']),
    ("Ecke", "Ecke", []),
    ("hatt", "hat", ['08']),
    ("mitt", "mit", ['08']),
    ("Buss", "Bus", ['08']),
    ("dass", "das", ['08']),
    ("Addresse", "Adresse", ['08']),
    ("kamm", "kam", ['11']),
    ("schönn", "schön", ['11']),
    ("Tall", "Tal", ['11']),
    ("lieff", "lief", ['11']),
    ("Sportt", "Sport", ['11']),
    ("Werrk", "Werk", ['08']),
    ("Schulle", "Schule", ['11']),
    ("Kindt", "Kind", ['30']),
    ("undt", "und", ['30']),
    ("Zan", "Zahn", ['09']),
    ("nam", "nahm", ['09']),
    ("Jar", "Jahr", ['09']),
    ("ser", "sehr", ['09']),
    ("faren", "fahren", ['09']),
    ("wonen", "wohnen", ['09']),
    ("nemen", "nehmen", ['09']),
    ("Spil", "Spiel", ['09']),
    ("Tir", "Tier", ['09']),
    ("Bot", "Boot", ['09']),
    ("Mer", "Meer", ['09']),
    ("Har", "Haar", ['09']),
    ("par", "paar", ['09']),
    ("Te", "Tee", ['09']),
    ("Ide", "Idee", ['09']),
    ("Kuh", "Kuh", []),
    ("Ku", "Kuh", ['09']),
    ("fro", "froh", ['09']),
    ("zen", "zehn", ['09']),
    ("frölich", "fröhlich", ['09']),
    ("wider", "wieder", ['09']),
    ("Brif", "Brief", ['09']),
    ("Schuhle", "Schule", ['10']),
    ("viehl", "viel", ['10']),
    ("wahr", "war", ['10']),
    ("mahlen", "malen", ['10']),
    ("nähmlich", "nämlich", ['10']),
    ("geheen", "gehen", ['32']),
    ("Tiesch", "Tisch", ['12']),
    ("Kiend", "Kind", ['12']),
    ("Fiesch", "Fisch", ['12']),
    ("miet", "mit", ['12']),
    ("bien", "bin", ['12']),
    ("geen", "gehen", ['09']),
    ("seen", "sehen", ['09']),
    ("ruig", "ruhig", ['09']),
    ("Reie", "Reihe", ['29']),
    ("Schue", "Schuhe", ['09']),
    ("Hende", "Hände", ['17']),
    ("Menner", "Männer", ['17']),
    ("Heuser", "Häuser", ['17']),
    ("Beume", "Bäume", ['17']),
    ("Bleter", "Blätter", ['07', '17']),
    ("jätzt", "jetzt", ['18']),
    ("Läute", "Leute", ['18']),
    ("Bätt", "Bett", ['18']),
    ("Ältern", "Eltern", ['18']),
    ("Fräund", "Freund", ['18']),
    ("häute", "heute", ['18']),
    ("Medchen", "Mädchen", ['34']),
    ("Mähl", "Mehl", ['34']),
    ("Bucher", "Bücher", ['36']),
    ("schon", "schön", ['36']),
    ("Mutze", "Mütze", ['36']),
    ("Apfel", "Äpfel", ['36']),
    ("Mause", "Mäuse", ['36']),
    ("Kuche", "Küche", ['36']),
    ("Schueler", "Schüler", ['36']),
    ("Baume", "Bäume", ['36']),
    ("Sohne", "Söhne", ['36']),
    ("Hunt", "Hund", ['19']),
    ("Kint", "Kind", ['19']),
    ("Fahrrat", "Fahrrad", ['19']),
    ("abents", "abends", ['19']),
    ("unt", "und", ['19']),
    ("Wek", "Weg", ['19']),
    ("sint", "sind", ['19']),
    ("seit", "seid", ['19']),
    ("balt", "bald", ['19']),
    ("Ring", "Rink", ['20']),
    ("Quarg", "Quark", ['20']),
    ("Werg", "Werk", ['20']),
    ("Marg", "Mark", ['20']),
    ("seid", "seit", ['20']),
    ("Bang", "Bank", ['20']),
    ("Dang", "Dank", ['20']),
    ("singt", "sinkt", ['20']),
    ("Sag", "Sack", ['07', '20']),
    ("schmegt", "schmeckt", ['07', '20']),
    ("wirt", "wird", ['19']),
    ("fiel", "viel", ['23']),
    ("for", "vor", ['23']),
    ("fergessen", "vergessen", ['23']),
    ("Fogel", "Vogel", ['23']),
    ("vinden", "finden", ['24']),
    ("vertig", "fertig", ['24']),
    ("Vreund", "Freund", ['24']),
    ("Wideo", "Video", ['25']),
    ("Wulkan", "Vulkan", ['25']),
    ("vir", "wir", ['26']),
    ("Vald", "Wald", ['26']),
    ("Könich", "König", ['27']),
    ("fertich", "fertig", ['27']),
    ("ruhich", "ruhig", ['27']),
    ("zwanzich", "zwanzig", ['27']),
    ("fröhlig", "fröhlich", ['28']),
    ("durg", "durch", ['33']),
    ("ig", "ich", ['28']),
    ("nog", "noch", ['33']),
    ("aug", "auch", ['33']),
    ("mig", "mich", ['28']),
    ("nich", "nicht", ['29']),
    ("Fahrad", "Fahrrad", ['29']),
    ("vieleicht", "vielleicht", ['29']),
    ("Herbs", "Herbst", ['29']),
    ("Spot", "Sport", ['29']),
    ("un", "und", ['29']),
    ("Kuns", "Kunst", ['29']),
    ("Fahrat", "Fahrrad", ['19', '29']),
    ("Mutta", "Mutter", ['29', '34']),
    ("Hunrd", "Hund", ['30']),
    ("Turnm", "Turm", ['30']),
    ("jetztd", "jetzt", ['30']),
    ("Blmen", "Blumen", ['31']),
    ("gegangn", "gegangen", ['31']),
    ("habn", "haben", ['31']),
    ("Schwestr", "Schwester", ['31']),
    ("andre", "andere", ['31']),
    ("Kinider", "Kinder", ['32']),
    ("Bluemen", "Blumen", ['32']),
    ("Pall", "Ball", ['33']),
    ("Zonne", "Sonne", ['33']),
    ("Schtein", "Stein", ['37']),
    ("schpielen", "spielen", ['37']),
    ("chön", "schön", ['33']),
    ("gig", "ging", ['33']),
    ("Tinge", "Dinge", ['33']),
    ("Plume", "Blume", ['33']),
    ("Karten", "Garten", ['33']),
    ("Kirsche", "Kirche", ['33']),
    ("Kirche", "Kirsche", ['33']),
    ("Finster", "Fenster", ['34']),
    ("Sammer", "Sommer", ['34']),
    ("Geburtstog", "Geburtstag", ['34']),
    ("Huse", "Hose", ['34']),
    ("Brudar", "Bruder", ['34']),
    ("Mei", "Mai", ['34']),
    ("Keiser", "Kaiser", ['34']),
    ("Weise", "Waise", ['34']),
    ("Bort", "Brot", ['35']),
    ("Farbik", "Fabrik", ['35']),
    ("Kidner", "Kinder", ['35']),
    ("Fysik", "Physik", ['37']),
    ("Garasche", "Garage", ['37']),
    ("wier", "wir", ['37']),
    ("Handi", "Handy", ['37']),
    ("Tema", "Thema", ['37']),
    ("Teater", "Theater", ['37']),
    ("Apoteke", "Apotheke", ['37']),
    ("Bibliotek", "Bibliothek", ['37']),
    ("Rytmus", "Rhythmus", ['37', '37']),
    ("Straße", "Strasse", ['37']),
    ("groß", "gross", ['37']),
    ("daß", "dass", ['37']),
    ("heißt", "heisst", ['37']),
    ("Fux", "Fuchs", ['33']),
    ("sex", "sechs", ['33']),
    ("Kwelle", "Quelle", ['37']),
    ("Kompjuter", "Computer", ['30', '37']),
    ("Restorant", "Restaurant", ['37']),
    ("Schtrase", "Strasse", ['07', '37']),
    ("Kuhche", "Küche", ['12', '36']),
    ("Geburtstack", "Geburtstag", ['11', '19']),
    ("Fahrradt", "Fahrrad", ['30']),
    ("Stadt", "statt", ['02', '07', '30']),
    ("statt", "Stadt", ['01', '11', '29']),
]


@pytest.mark.parametrize("schueler,ziel,erwartet", KORPUS, ids=[f"{s}>{z}" for s, z, _ in KORPUS])
def test_sek1_korpus(schueler, ziel, erwartet):
    r = E.klassifiziere_wort(schueler, ziel, E.VORGABE_LEXIKON)
    for e in r["ereignisse"]:
        E.abschliessen(e, {"ziel": ziel})
    assert sorted(e["kategorie"] or e["status"] for e in r["ereignisse"]) == erwartet


def test_umschrift_ist_ein_umlautfehler():
    for s, z in [("Schueler", "Schüler"), ("Aerztin", "Ärztin"), ("Moebel", "Möbel")]:
        r = E.klassifiziere_wort(s, z, E.VORGABE_LEXIKON)
        assert [e["kategorie"] for e in r["ereignisse"]] == ["36"], (s, z)
    # Ohne Umlaut im Zielwort bleibt <ue> ein zugefügtes e.
    assert [e["kategorie"] for e in E.klassifiziere_wort("Bluemen", "Blumen")["ereignisse"]] == ["32"]


def test_ck_fuer_g_ist_zwei_fehler_wie_die_umkehrung():
    r = E.klassifiziere_wort("Geburtstack", "Geburtstag", E.VORGABE_LEXIKON)
    assert sorted(e["kategorie"] for e in r["ereignisse"]) == ["11", "19"]
    r = E.klassifiziere_wort("Sag", "Sack", E.VORGABE_LEXIKON)
    assert sorted(e["kategorie"] for e in r["ereignisse"]) == ["07", "20"]


def test_diktat_zeigt_beide_teile_einer_getrenntschreibung():
    r = E.analysiere_diktat("Am Freitagmorgen war es kalt.", "Am Freitag Morgen war es kalt.", E.VORGABE_LEXIKON)
    assert [(e["studentForm"], e["targetForm"], e["kategorie"]) for e in r["ereignisse"]] == [
        ("Freitag Morgen", "Freitagmorgen", "04")]
