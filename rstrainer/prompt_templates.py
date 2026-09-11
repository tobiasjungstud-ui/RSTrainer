"""Prompt-Vorlagen für die Texterzeugung im Chat.

DIESE DATEI DARF UND SOLL ANGEPASST WERDEN.

Hier stehen die Textbausteine, aus denen die App die fertigen Prompts baut.
Die App selbst ruft KEINE Sprachmodell-Schnittstelle auf – sie erzeugt nur
den Text, den die Lehrperson in einen beliebigen Claude-Chat kopiert.

Aufbau
------
Jede Vorlage ist ein ``str.format``-Muster. Geschweifte Klammern sind
Platzhalter und werden von :mod:`rstrainer.auftraege` gefüllt. Wer eine
Vorlage ändert, muss die vorhandenen Platzhalter beibehalten – sonst bricht
das Füllen mit einem ``KeyError`` ab (die App fängt das ab und zeigt einen
Hinweis).

Rückgabeformat
--------------
Alle Vorlagen verlangen vom Chat eine Antwort zwischen den Markierungen
``===RSTRAINER-ANFANG===`` und ``===RSTRAINER-ENDE===`` mit einem kurzen
Kopfbereich. Damit kann die App das Ergebnis beim Einfügen automatisch
zerlegen, die Auftragsnummer gegenprüfen und die Felder vorbelegen.
Fehlen die Markierungen, nimmt die App den eingefügten Text als reinen
Fliesstext an – es geht also nichts verloren.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Markierungen des Rückgabeformats (auch in auftraege.py verwendet)
# ---------------------------------------------------------------------------

MARKE_ANFANG = "===RSTRAINER-ANFANG==="
MARKE_ENDE = "===RSTRAINER-ENDE==="
MARKE_UEBUNG = "---UEBUNGSBLATT---"
MARKE_TEST = "---MINITEST---"
MARKE_LOESUNG = "---LOESUNGEN---"
KOPF_TRENNER = "---"


# ---------------------------------------------------------------------------
# Gemeinsame Bausteine
# ---------------------------------------------------------------------------

ROLLE = """\
Du unterstützt eine Lehrperson, die im Deutschunterricht einzelne \
Schülerinnen und Schüler in der Rechtschreibung fördert. Die Fehleranalyse \
folgt der Systematik der Oldenburger Fehleranalyse (OLFA): Fehler werden \
klar abgegrenzten Rechtschreibbereichen zugeordnet.

Arbeite präzise und zurückhaltend. Erfinde keine Zusatzaufgaben, die nicht \
verlangt sind, und liefere keine Erklärtexte ausserhalb des geforderten \
Rückgabeformats."""

RECHTSCHREIBHINWEIS = {
    "schweiz": (
        "Verwende durchgehend die Schweizer Rechtschreibung: KEIN ß, "
        "stattdessen immer ss (also «Strasse», «gross», "
        "«dass», «heisst»)."
    ),
    "deutschland_oesterreich": (
        "Verwende die in Deutschland und Österreich gültige "
        "Rechtschreibung mit ß nach langem Vokal und Diphthong "
        "(also «Straße», «groß», "
        "«heißt», aber «dass»)."
    ),
}

QUALITAETSREGELN = """\
Zwingende Vorgaben:
- Der Text muss orthografisch und grammatikalisch fehlerfrei sein. Er dient \
der Lehrperson anschliessend als Referenz für den maschinellen Abgleich mit \
dem Schülertext; jeder Tippfehler von dir würde dort als Schülerfehler gezählt.
- {rechtschreibhinweis}
- Keine Anführungszeichen-Spielereien, keine Emojis, keine Fussnoten, keine \
Markdown-Überschriften innerhalb des Textes.
- Keine Gewalt, keine Ängste auslösenden Inhalte, keine realen Personen des \
öffentlichen Lebens, keine Markennamen."""


# ---------------------------------------------------------------------------
# Vorlage 1: Diktat
# ---------------------------------------------------------------------------

DIKTAT = """\
{rolle}

## Auftrag: Übungsdiktat erstellen

Auftragsnummer: {auftrag_code}

### Rahmen
- Klassenstufe / Alter: {klassenstufe}
- Textsorte: {textsorte}
- Thema: {thema}
- Umfang: {wortzahl} Wörter (Toleranz ±10 %)
- Schwierigkeitsgrad: {schwierigkeit}

### Zielkategorien (OLFA)
Der Text muss gezielt Wörter enthalten, an denen sich genau diese \
Rechtschreibphänomene zeigen. Pro Kategorie brauche ich mindestens \
{treffer_pro_kategorie} passende Wörter, gut über den Text verteilt und in \
natürlichen Sätzen – keine Aufzählungen, keine erzwungene Häufung im selben Satz.

{kategorienblock}

### Was ich NICHT will
- Keine absichtlichen Rechtschreibfehler im Text. Die Zielkategorien \
bestimmen, welche *Wörter* vorkommen, nicht dass sie falsch geschrieben sind.
- Keine Wörter, die nur über Nebenbedeutungen zur Kategorie passen.
- Keine Fremdwörter, ausser sie sind ausdrücklich als Zielkategorie genannt.

{qualitaetsregeln}

### Rückgabeformat
Antworte ausschliesslich mit dem folgenden Block, ohne Vor- oder Nachtext:

{marke_anfang}
AUFTRAG: {auftrag_code}
TYP: diktat
TITEL: <kurzer Titel, höchstens 6 Wörter>
WOERTER: <tatsächlich gezählte Wortzahl deines Textes>
ZIELWOERTER: <je Kategorie die von dir platzierten Wörter, Format: 01: Haus, \
Wiese | 07: kommen, rennen>
{kopf_trenner}
<Hier der Diktattext als zusammenhängender Fliesstext, ohne Überschrift.>
{marke_ende}
"""


# ---------------------------------------------------------------------------
# Vorlage 2: Übungsblatt + Mini-Test
# ---------------------------------------------------------------------------

UEBUNGSBLATT = """\
{rolle}

## Auftrag: Übungsblatt mit Mini-Test erstellen

Auftragsnummer: {auftrag_code}

### Rahmen
- Klassenstufe / Alter: {klassenstufe}
- Bearbeitungszeit Übungsblatt: {bearbeitungszeit}
- Das Blatt wird beidseitig gedruckt: Vorderseite Übungsteil, Rückseite Mini-Test.
- Die Schülerin / der Schüler arbeitet selbstständig, ohne Lehrerhilfe.

### Förderschwerpunkte
Alle Aufgaben müssen erkennbar zu genau diesen Kategorien gehören. Ordne \
jeder Aufgabe im Aufgabentext sichtbar die Kategorienummer zu, damit die \
Lehrperson die Zuordnung prüfen kann.

{kategorienblock}

### Aufbau Übungsteil (Vorderseite)
Pro Förderschwerpunkt {aufgaben_pro_kategorie} Aufgaben, aufsteigend im \
Schwierigkeitsgrad. Nutze abwechslungsreiche Formate, zum Beispiel:
- Lückenwörter ergänzen
- richtige von falscher Schreibung unterscheiden und ankreuzen
- Wörter nach Regel sortieren
- Wortfamilie bilden / verlängern zur Ableitung
- eigene Sätze mit vorgegebenen Wörtern schreiben

Formuliere zu jedem Schwerpunkt EINEN kurzen Merksatz (höchstens zwei Zeilen, \
kindgerecht, ohne Fachjargon) vor den zugehörigen Aufgaben.

### Aufbau Mini-Test (Rückseite)
- Insgesamt {test_aufgaben} Aufgaben, alle Förderschwerpunkte abgedeckt.
- Andere Wörter als im Übungsteil, gleiches Anforderungsniveau.
- Am Ende eine Zeile «Erreichte Punkte: ____ von {test_aufgaben}».
- KEINE Merksätze und KEINE Lösungshinweise auf der Testseite.

### Sehr wichtig
Auf der Vorderseite und auf der Rückseite dürfen KEINE Lösungen stehen – \
weder in Klammern, noch als Beispiel mit ausgefüllter Lücke, noch als \
durchgestrichene Variante. Lösungen gehören ausschliesslich in den \
Lösungsabschnitt am Ende deiner Antwort.

{qualitaetsregeln}

### Rückgabeformat
Antworte ausschliesslich mit dem folgenden Block, ohne Vor- oder Nachtext:

{marke_anfang}
AUFTRAG: {auftrag_code}
TYP: uebungsblatt
TITEL: <kurzer Titel, höchstens 6 Wörter>
{marke_uebung}
<Übungsteil. Reiner Text. Aufgaben nummeriert. Lücken als _______ .>
{marke_test}
<Mini-Test. Reiner Text. Aufgaben nummeriert.>
{marke_loesung}
<Lösungen zu Übungsteil und Mini-Test, nach Aufgabennummer geordnet.>
{marke_ende}
"""


# ---------------------------------------------------------------------------
# Vorlage 3: nur Mini-Test (Nachtest zu einem bestehenden Übungsblatt)
# ---------------------------------------------------------------------------

MINITEST = """\
{rolle}

## Auftrag: Mini-Test (Nachtest) erstellen

Auftragsnummer: {auftrag_code}

### Rahmen
- Klassenstufe / Alter: {klassenstufe}
- Zweck: Überprüfung, ob die geübten Schwerpunkte sitzen.
- Umfang: {test_aufgaben} Aufgaben, in {bearbeitungszeit} lösbar.

### Förderschwerpunkte
{kategorienblock}

### Vorgaben
- Verwende andere Wörter als in der folgenden Liste bereits geübter Wörter:
{bekannte_woerter}
- Keine Merksätze, keine Regelerklärungen, keine Lösungshinweise im Test.
- Am Ende eine Zeile «Erreichte Punkte: ____ von {test_aufgaben}».

{qualitaetsregeln}

### Rückgabeformat
Antworte ausschliesslich mit dem folgenden Block, ohne Vor- oder Nachtext:

{marke_anfang}
AUFTRAG: {auftrag_code}
TYP: minitest
TITEL: <kurzer Titel, höchstens 6 Wörter>
{marke_test}
<Mini-Test. Reiner Text. Aufgaben nummeriert.>
{marke_loesung}
<Lösungen, nach Aufgabennummer geordnet.>
{marke_ende}
"""


VORLAGEN = {
    "diktat": DIKTAT,
    "uebungsblatt": UEBUNGSBLATT,
    "minitest": MINITEST,
}

#: Welche Platzhalter jede Vorlage mindestens braucht – für den Selbsttest.
PFLICHTPLATZHALTER = {
    "diktat": {"auftrag_code", "kategorienblock", "wortzahl", "marke_anfang", "marke_ende"},
    "uebungsblatt": {"auftrag_code", "kategorienblock", "marke_anfang", "marke_ende",
                     "marke_uebung", "marke_test", "marke_loesung"},
    "minitest": {"auftrag_code", "kategorienblock", "marke_anfang", "marke_ende",
                 "marke_test", "marke_loesung"},
}
