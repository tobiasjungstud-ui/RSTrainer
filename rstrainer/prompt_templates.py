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

#: Das Werkzeug ist ausschliesslich auf die Schweizer Rechtschreibung
#: ausgelegt. Es gibt keine Variantenumschaltung – ein ß darf nirgends
#: entstehen; die Kategorien 13–16 entfallen (Version CH der OLFA-Liste).
RECHTSCHREIBHINWEIS = (
    "Verwende durchgehend die Schweizer Rechtschreibung: KEIN ß, stattdessen "
    "immer ss (also «Strasse», «gross», «dass», «heisst»). Ein ß ist in keinem "
    "Wort zulässig."
)

#: Aus dem Schwierigkeitsgrad leitet sich die Zielstufe ab – ein Regler
#: weniger, und das Modell bekommt trotzdem eine konkrete Angabe.
STUFE = {
    "leicht": "7. Klasse Sekundarstufe I (ca. 13 Jahre)",
    "mittel": "8. Klasse Sekundarstufe I (ca. 14 Jahre)",
    "anspruchsvoll": "9. Klasse Sekundarstufe I (ca. 15 Jahre)",
}

# ---------------------------------------------------------------------------
# Anforderungsniveau
# ---------------------------------------------------------------------------
# Eine Klassenstufe allein macht kein Blatt schwer. «9. Klasse» erzeugte
# dieselben Lückenwörter wie «7. Klasse», nur mit anderem Wortmaterial – und
# selbst das nur zufällig. Der Schwierigkeitsgrad muss deshalb sagen, WAS die
# Aufgabe verlangt, nicht bloss, wie alt das Kind ist.
#
# Drei Hebel unterscheiden die Stufen, und zwar überprüfbar:
#   1. Wortmaterial   – Häufigkeit, Silbenzahl, Fremdwörter, Zweifelsfälle.
#   2. Stützung       – Ist der Suchort markiert? Steht der Buchstabe dabei?
#   3. Leistungsart   – Wiedererkennen, selbst finden, begründen, produzieren.
#
# Der schwerste Hebel ist der zweite: Solange jede Lücke mit «_____» markiert
# ist und der einzusetzende Buchstabe in Klammern danebensteht, bleibt die
# Aufgabe eine Ja/Nein-Entscheidung an bekannter Stelle. Wer den Fehler selbst
# finden muss, arbeitet um eine Stufe höher – auch bei gleichem Wortmaterial.

ANFORDERUNG = {
    "leicht": """\
- Wortmaterial: hochfrequenter Grundwortschatz, ein- bis zweisilbig. Keine \
Fremdwörter, keine mehrgliedrigen Zusammensetzungen.
- Stützung: Der Suchort darf markiert sein. Lücken mit Buchstabenvorgabe in \
Klammern, Ankreuzpaare und Sortieraufgaben sind erwünscht.
- Kontext: Einzelwörter und kurze, einfache Sätze.
- Leistungsart: Regel wiedererkennen und anwenden. Der Merksatz steht \
unmittelbar vor den Aufgaben und lässt sich direkt übertragen.""",

    "mittel": """\
- Wortmaterial: Grundwortschatz plus geläufige Ableitungen und \
Zusammensetzungen, einzelne geläufige Fremdwörter.
- Stützung: Höchstens die Hälfte der Aufgaben je Schwerpunkt darf den Suchort \
markieren. Mindestens EINE Aufgabe je Schwerpunkt ist ungestützt: ein Satz \
oder Kurztext, in dem die Fehler erst gefunden werden müssen.
- Kontext: Überwiegend ganze Sätze, dazu mindestens ein zusammenhängender \
Kurztext.
- Leistungsart: Anwenden und begründen. Bei einer Aufgabe je Schwerpunkt ist \
das Ableitungswort oder die Regel in Stichworten zu nennen.""",

    "anspruchsvoll": """\
Dies ist die höchste Stufe. Ein Blatt, das sich mit Schulwissen der \
Primarstufe lösen lässt, verfehlt sie. Die folgenden Punkte sind Vorgaben, \
keine Anregungen:

- Wortmaterial: mittlere bis geringe Häufigkeit, mehrsilbige Ableitungen und \
Zusammensetzungen, Fremd- und Lehnwörter, Fachwörter aus anderen Schulfächern. \
Helvetismen der Schweizer Standardsprache (parkieren, grillieren, Trottoir, \
Coiffeur, Velo, Peperoni) sind ausdrücklich erwünscht. VERBOTEN sind Wörter, \
die in der Primarschule geübt werden: Sonne, Blume, Hand, Baum, Haus, Wasser, \
Butter, Mutter, kommen, rennen und Vergleichbares.
- Stützung: Der einzusetzende Buchstabe wird NIE in Klammern mitgeliefert. \
Höchstens EINE Aufgabe je Schwerpunkt darf den Suchort markieren. Alle \
übrigen sind ungestützt.
- Mindestens die Hälfte der Aufgaben je Schwerpunkt ist eine Fehlersuche in \
einem zusammenhängenden Text. Nenne die Anzahl der Fehler, nie ihre Stelle.
- Distraktoren: In jedem Fehlersuchtext stehen mindestens drei Schreibungen, \
die KORREKT sind, aber ungewohnt aussehen – Stängel, aufwendig, Tollpatsch, \
nummerieren, platzieren, Känguru, rau, Zierrat, Ass, Tipp, selbstständig, \
Quäntchen, behände, Gämse, überschwänglich. Wer sie «verbessert», macht einen \
Fehler. Weise in der Aufgabenstellung darauf hin, dass nicht jede ungewohnte \
Schreibung falsch ist.
- Kontrastpaare, über die erst der Satz entscheidet: das/dass, wider/wieder, \
seit/seid, Stadt/statt, Lied/Lid, Waise/Weise, Leib/Laib, malen/mahlen, \
Saite/Seite, Rad/Rat, Mine/Miene, Gewähr/Gewehr, Ähre/Ehre. Ankreuzaufgaben \
sind NUR in dieser Form zulässig – beide Formen müssen für sich genommen \
existieren. Ein Paar wie «trefen / treffen», bei dem eine Form gar kein Wort \
ist, gehört nicht auf dieses Niveau.
- Begründungspflicht: Zu jeder Entscheidung gehört das Ableitungswort oder die \
Regel in Stichworten. Sag in der Aufgabenstellung, dass eine richtige \
Schreibung ohne Begründung nur halb zählt.
- Fälle, in denen das Hören versagt, gehören dazu: bei der Umlautableitung \
Wörter, deren ä/äu sich NICHT herleiten lässt (Eltern, fremd, Held, edel, \
Schwert, Segel) neben solchen, bei denen es geht (Stängel → Stange, \
überschwänglich → Überschwang, behände → Hand, Quäntchen → Quantum, \
aufwändig → Aufwand). Bei der Schärfung Wörter, die trotz kurzem Vokal NICHT \
verdoppeln, weil schon zwei Mitlaute folgen (Karte, Wurst, Lampe, Geduld), \
und Fremdwörter mit unerwarteter Schreibung (Karotte, Bagatelle, Gorilla, \
Marionette, Appartement).
- Weil es in de-CH kein ß gibt, fehlt die Längenmarkierung: Die Unterscheidung \
von ss nach kurzem Vokal (Fluss, müssen, Schloss) und ss nach langem Vokal \
oder Diphthong (Fuss, heissen, grüssen, draussen) ist ein eigener \
Schwerpunkt, sobald die Schärfung geübt wird.
- Bei der Gross- und Kleinschreibung reichen Satzanfang und Begleiter nicht. \
Verlangt sind Nominalisierungen ohne Artikel (etwas Schönes, nichts Besseres, \
im Allgemeinen, des Weiteren, aufs Neue, der Einzelne, im Folgenden), \
Tageszeiten nach Adverb (heute Abend, gestern Morgen – dagegen klein: abends, \
morgens) und feste Verbindungen (Rad fahren, recht haben, leid tun, Angst \
haben – dagegen gross: das Radfahren, sein Recht).
- Leistungsart: Mindestens eine Aufgabe je Schwerpunkt verlangt eigene \
Produktion unter Bedingung, z. B. «Schreibe einen Satz, in dem das und dass \
beide richtig vorkommen» oder «Schreibe zwei Sätze, in denen dasselbe Wort \
einmal gross und einmal klein geschrieben wird».
- Punkte: Vergib im Mini-Test Punkte je Teilleistung und rechne die Begründung \
mit. Die Punktzahl am Ende ist die Summe dieser Teilpunkte, nicht die Zahl der \
Aufgaben.""",
}

#: Für das Diktat greifen dieselben Hebel, aber an einem Fliesstext: Dort gibt
#: es keine Aufgabenformate, nur Wortwahl und Satzbau.
ANFORDERUNG_DIKTAT = {
    "leicht": """\
- Hochfrequenter Grundwortschatz, kurze Hauptsätze, höchstens ein Nebensatz \
pro Satz. Keine Fremdwörter, keine mehrgliedrigen Zusammensetzungen.""",

    "mittel": """\
- Grundwortschatz plus geläufige Ableitungen und Zusammensetzungen. \
Satzgefüge mit Nebensätzen, wörtliche Rede erlaubt. Einzelne geläufige \
Fremdwörter.""",

    "anspruchsvoll": """\
- Mittlere bis geringe Worthäufigkeit, mehrsilbige Ableitungen und \
Zusammensetzungen, Fremd- und Lehnwörter, Helvetismen der Schweizer \
Standardsprache. Keine Wörter aus dem Primarschul-Übungswortschatz (Sonne, \
Blume, Hand, Baum, Haus, Wasser).
- Mehrfach verschachtelte Satzgefüge, Einschübe zwischen Kommas, wörtliche \
Rede mit Redebegleitsatz in der Mitte.
- Baue bewusst Zweifelsfälle ein, die erst der Satz entscheidet: das/dass, \
wider/wieder, seit/seid, Getrennt- und Zusammenschreibung (Rad fahren gegen \
das Radfahren), Nominalisierungen ohne Artikel (etwas Wichtiges, im \
Allgemeinen), Tageszeiten nach Adverb (heute Abend).
- Da es in de-CH kein ß gibt, fehlt die Längenmarkierung: Nimm Wörter mit ss \
nach kurzem Vokal (Fluss, müssen) UND nach langem Vokal oder Diphthong (Fuss, \
heissen, draussen) in denselben Text.""",
}

#: Die oberste Ebene gelernter Fehlerarten, siehe rstrainer.taxonomie.
SCHWEIZ_REGEL = (
    "WICHTIG – Schweizer Rechtschreibung (de-CH): Es gibt kein ß. «Strasse», "
    "«gross», «heisst», «dass» sind KORREKT. Erzeuge nie eine Zielform mit ß. "
    "Die Nummern 13, 14, 15, 16, 21 und 22 werden NIE vergeben (Version CH der "
    "OLFA-Liste: 13–16 entfallen). Ein ß in der Schülerschreibung ist Kategorie 37. "
    "s für ss ist 07 (Fus → Fuss), ss für s ist 08 nach kurzem und 11 nach langem "
    "Vokal oder Diphthong (Preisse → Preise)."
)

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
- Zielgruppe: {stufe}
- Textsorte: {textsorte}
- Thema: {thema}
- Umfang: {wortzahl} Wörter (Toleranz ±10 %)
- Schwierigkeitsgrad: {schwierigkeit}

### Anforderungsniveau
Diese Vorgaben entscheiden über den Schwierigkeitsgrad. Halte sie ein, auch \
wenn der Text dadurch weniger glatt klingt.

{anforderung}

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
- Zielgruppe: {stufe}
- Bearbeitungszeit Übungsblatt: {bearbeitungszeit}
- Das Blatt wird beidseitig gedruckt: Vorderseite Übungsteil, Rückseite Mini-Test.
- Die Schülerin / der Schüler arbeitet selbstständig, ohne Lehrerhilfe.

### Anforderungsniveau
Diese Vorgaben entscheiden über den Schwierigkeitsgrad – nicht die \
Klassenstufe und nicht die Zahl der Aufgaben. Halte sie Punkt für Punkt ein \
und prüfe am Schluss jede Aufgabe gegen sie.

{anforderung}

### Förderschwerpunkte
Alle Aufgaben müssen erkennbar zu genau diesen Kategorien gehören. Ordne \
jeder Aufgabe im Aufgabentext sichtbar die Kategorienummer zu, damit die \
Lehrperson die Zuordnung prüfen kann.

{kategorienblock}

### Aufbau Übungsteil (Vorderseite)
Pro Förderschwerpunkt {aufgaben_pro_kategorie} Aufgaben, aufsteigend im \
Schwierigkeitsgrad. Die Formate wählst du nach dem Anforderungsniveau oben. \
Zur Auswahl stehen, von gestützt nach ungestützt:
- Lückenwörter ergänzen (Suchort markiert)
- richtige von falscher Schreibung unterscheiden und ankreuzen
- Wörter nach Regel sortieren
- Wortfamilie bilden / verlängern zur Ableitung
- Fehler in einem zusammenhängenden Text finden und berichtigen (Suchort \
nicht markiert)
- Entscheidung schriftlich begründen (Ableitungswort oder Regel nennen)
- eigene Sätze unter einer Bedingung schreiben

Die gestützten Formate ganz oben sind nur zulässig, soweit das \
Anforderungsniveau sie erlaubt.

Formuliere zu jedem Schwerpunkt EINEN kurzen Merksatz (höchstens zwei Zeilen, \
kindgerecht, ohne Fachjargon) vor den zugehörigen Aufgaben.

### Aufbau Mini-Test (Rückseite)
- Insgesamt {test_aufgaben} Aufgaben, alle Förderschwerpunkte abgedeckt.
- Andere Wörter als im Übungsteil, gleiches Anforderungsniveau. Der Test darf \
nicht leichter sein als der Übungsteil: Dieselben Formatvorgaben gelten hier \
unverändert.
- Am Ende eine Zeile «Erreichte Punkte: ____ von {test_aufgaben}».
- KEINE Merksätze und KEINE Lösungshinweise auf der Testseite.

### Prüfe dich selbst, bevor du antwortest
Geh jede Aufgabe einzeln durch und beantworte für dich: Erfüllt sie die \
Vorgaben unter «Anforderungsniveau»? Eine Aufgabe, die das nicht tut, \
ersetzt du – auch wenn sie inhaltlich schön ist. Prüfe besonders: Steht \
irgendwo ein einzusetzender Buchstabe in Klammern, obwohl das Niveau ihn \
verbietet? Ist eine Ankreuzform gar kein existierendes Wort? Stammt ein Wort \
aus dem Primarschul-Wortschatz?

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
- Zielgruppe: {stufe}
- Zweck: Überprüfung, ob die geübten Schwerpunkte sitzen.
- Umfang: {test_aufgaben} Aufgaben, in {bearbeitungszeit} lösbar.

### Anforderungsniveau
Diese Vorgaben entscheiden über den Schwierigkeitsgrad. Prüfe am Schluss jede \
Aufgabe gegen sie und ersetze, was nicht passt.

{anforderung}

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
    "diktat": {"auftrag_code", "kategorienblock", "wortzahl", "anforderung",
               "marke_anfang", "marke_ende"},
    "uebungsblatt": {"auftrag_code", "kategorienblock", "anforderung",
                     "marke_anfang", "marke_ende",
                     "marke_uebung", "marke_test", "marke_loesung"},
    "minitest": {"auftrag_code", "kategorienblock", "anforderung",
                 "marke_anfang", "marke_ende",
                 "marke_test", "marke_loesung"},
}


# ---------------------------------------------------------------------------
# Fehleranalyse durch das Sprachmodell
# ---------------------------------------------------------------------------
# Anders als der mechanische Abgleich ordnet das Modell die Kategorien
# inhaltlich zu und darf für alles, was die OLFA-Liste nicht abdeckt – vor
# allem Grammatik –, eigene Fehlerarten benennen und hierarchisch einordnen.

ANALYSE_KOPF = """\
Du bist eine erfahrene Lehrperson für Deutsch auf der Sekundarstufe I.

## Weg 1: die feste OLFA-Liste (Rechtschreibung)
Die Bezeichnungen folgen dem Muster «X für Y»: geschrieben wurde X, richtig wäre Y.

{olfa_liste}

{schweiz_regel}

## Weg 2: die feste Liste für Grammatik, Syntax, Zeichensetzung und Textebene
Für alles, was keine Rechtschreibung ist, gilt zuerst diese Liste. Verwende die \
Kennung (z. B. B:Kasus) als "kategorie" mit typ "bekannt". Helvetismen der \
Schweizer Standardsprache (das Tram, parkieren, grillieren) sind KEINE Fehler.

{grammatik_liste}

Dazu kommen bereits angelegte eigene Fehlerarten – auch sie mit typ "bekannt":

{bekannte_arten}

## Weg 3: eine neue Fehlerart benennen
Deckt weder die OLFA-Liste noch die feste Liste noch eine bestehende Art den \
Fehler ab, benennst du selbst eine neue Art mit hierarchischem Pfad, zum \
Beispiel ["Grammatik", "Kasus", "Dativ statt Akkusativ"]. Das soll die Ausnahme \
sein: Was in die feste Liste passt, gehört dorthin.

**Die oberste Stufe MUSS genau eines dieser Wörter sein** – andere werden verworfen:
{oberbegriffe}

Formuliere die unterste Stufe nach dem Muster «X statt Y» oder «X fehlt», damit \
gleichartige Fehler später gleich heissen. Lege keine neue Art an, wenn eine \
OLFA-Kategorie oder eine bestehende Art passt – die Sammlung wächst sonst mit \
Bedeutungsgleichem zu."""

ANALYSE_FORMAT = """\
## Ausgabe
Antworte ausschliesslich mit einem JSON-Array, ohne Vor- oder Nachtext und ohne \
Code-Zaun. Ein Objekt je Fehler, in der Reihenfolge des Textes:

[{{
  "richtig": "<die korrekte Form>",
  "geschrieben": "<was im Text steht>",
  "typ": "olfa" | "bekannt" | "neu",
  "kategorie": "<OLFA-Nummer bei typ olfa; Kennung wie B:Kasus oder X-abc12345 bei typ bekannt; sonst null>",
  "pfad": ["<Oberbegriff>", "<Untergruppe>", "<genaue Art>"],
  "beschreibung": "<bei typ neu: ein Satz, was diese Art bezeichnet>",
  "begruendung": "<höchstens 12 Wörter>"
}}]

Bei typ "olfa" und "bekannt" lässt du "pfad" und "beschreibung" weg."""

ANALYSE_DIKTAT = """\
{analyse_kopf}

## Allgemeine Regeln
- Beurteile ausschliesslich die Abweichungen vom Originaltext. Was mit dem Original \
übereinstimmt, ist richtig – auch wenn du es anders schreiben würdest.
- Ein Wort kann mehrere Fehler enthalten. Dann gib pro Fehler eine eigene Zeile an.
- Vergib die SPEZIFISCHSTE passende Kategorie. Nimm OLFA 37 nur, wenn wirklich \
nichts passt und auch keine eigene Art sinnvoll ist.
- Reine Satzzeichenunterschiede zählen NICHT als Fehler.
- Ist die Abschrift fehlerfrei, gib eine leere Liste zurück.

## Originaldiktat
{originaltext}

## Abschrift des Kindes
{schuelertext}

{analyse_format}
"""

ANALYSE_FREITEXT = """\
{analyse_kopf}

Du wertest einen **frei geschriebenen Text** aus. Es gibt keine Vorlage – du musst \
selbst beurteilen, was falsch ist, und die richtige Form angeben.

## Was KEIN Fehler ist – hier bitte streng mit dir sein
Ohne Vorlage ist die Versuchung gross, zu viel anzustreichen. Es zählt nur, was \
objektiv falsch ist:
- **Kein Stil.** Umständliche, einfache oder kindliche Formulierungen sind keine Fehler.
- **Keine Wortwahl**, solange das Wort existiert und passt.
- **Kein Satzbau**, solange der Satz grammatikalisch zulässig ist.
- **Keine Wiederholungen**, kein «besser wäre».
- Umgangssprache und Helvetismen sind zulässig, solange sie korrekt geschrieben sind.
- Im Zweifel: **nicht** als Fehler werten.

Ist der Text fehlerfrei, gib eine leere Liste zurück.

## Text des Kindes
{schuelertext}

{analyse_format}
"""

# ---------------------------------------------------------------------------
# Aufräumen der gelernten Fehlerarten
# ---------------------------------------------------------------------------

AUFRAEUMEN = """\
Du ordnest eine gewachsene Sammlung von Fehlerarten aus dem Deutschunterricht.

Die Sammlung ist im Lauf mehrerer Auswertungen entstanden. Dabei sind mutmasslich \
Einträge entstanden, die dasselbe meinen, aber verschieden heissen.

## Die Sammlung
{sammlung}

## Auftrag
Finde Einträge, die inhaltlich dasselbe bezeichnen, und schlage vor, sie \
zusammenzulegen. Schlage ausserdem einheitlichere Benennungen vor, wo sie sich anbieten.

Sei streng mit dir:
- Zusammenlegen NUR bei echter Bedeutungsgleichheit. «Dativ statt Akkusativ» und \
«Akkusativ statt Dativ» sind GEGENTEILE und dürfen niemals zusammengelegt werden.
- Ebenso wenig zusammenlegen: Ober- und Unterbegriff.
- Im Zweifel nichts vorschlagen. Eine zu Unrecht zusammengelegte Art zerstört die Statistik.
- Die oberste Ebene muss eines dieser Wörter bleiben: {oberbegriffe}.

## Ausgabe
Antworte ausschliesslich mit einem JSON-Objekt, ohne Vor- oder Nachtext und ohne Code-Zaun:

{{
  "zusammenlegen": [
    {{"von": "<Kennung, die verschwindet>", "nach": "<Kennung, die bleibt>", "warum": "<kurz>"}}
  ],
  "umbenennen": [
    {{"id": "<Kennung>", "pfad": ["<Oberbegriff>", "<Untergruppe>", "<genaue Art>"], "warum": "<kurz>"}}
  ]
}}

Ist nichts zu tun, gib leere Listen zurück.
"""

# ---------------------------------------------------------------------------
# Vierstufige Pipeline (Bau-Prompt): Stufe 1 Freitext und Stufe 3 Grenzfälle
# ---------------------------------------------------------------------------
# Die Klassifikation selbst übernimmt rstrainer.olfa_engine deterministisch.
# Das Sprachmodell wird nur gefragt, (1) welche Zielwörter im freien Text
# gemeint sind und (3) welches Merkmal einen Grenzfall entscheidet – nie,
# welche Kategorie es ist.

ZIELWOERTER = """\
Du bestimmst für einen Schülertext (Sekundarstufe I, Schweiz) die intendierte \
Zielschreibung jedes falsch geschriebenen Wortes. Du klassifizierst den Fehler NICHT – \
das macht ein Regelwerk. Deine einzige Aufgabe ist: Welches Wort war gemeint?

{schweiz_regel}

## Was zählt
Nur Orthografie: Buchstaben, Gross-/Kleinschreibung, Getrennt- und Zusammenschreibung.

## Was NICHT zählt
- Keine Grammatik (Fälle, Verbformen, Kongruenz), keine Zeichensetzung.
- Kein Stil, keine Wortwahl, kein Satzbau, keine Wiederholungen, kein «besser wäre».
- Umgangssprache und Helvetismen sind zulässig, solange sie korrekt geschrieben sind.
- Eigennamen und erfundene Namen sind nicht falsch.
- Im Zweifel NICHT als Fehler werten.

## Vollständigkeit
Geh die Wortliste von oben nach unten durch. Jedes falsch geschriebene Wort gehört in \
die Antwort, auch wenn derselbe Fehler mehrfach vorkommt – dann einmal pro Vorkommen \
mit der jeweiligen Nummer. Ein korrekt geschriebenes Wort kommt NICHT in die Liste.

## Zielwort aus dem Zusammenhang
Bei gleich klingenden Wörtern entscheidet der Satz, nicht die Häufigkeit: wider/wieder, \
das/dass, seid/seit, man/mann, wahr/war, mehr/Meer, Lied/Lid, Stadt/statt.
Bist du dir bei der gemeinten Zielform nicht sicher, nenne die wahrscheinlichere, setze \
«sicherheit» unter {schwelle} und trage die Alternative ein. Eine unsichere \
Zielwortentscheidung wird der Lehrperson vorgelegt – rate nicht.

## Wortgrenzen
- Zwei oder mehr Wörter zu einem verklebt: EIN Eintrag, «ziel» mit Leerzeichen \
(«zumbeispiel» → «zum Beispiel»).
- Ein Wort auf mehrere aufgeteilt: EIN Eintrag, alle beteiligten Nummern in «nummern», \
«ziel» zusammengeschrieben («Zahn» «arzt» → «Zahnarzt»).

## Textausschnitt
{text}

## Wörter (Nummer, Wort)
{woerter}

## Ausgabe
Antworte ausschliesslich mit einem JSON-Array, ohne Vor- oder Nachtext und ohne Code-Zaun:
[{{"nummer": 12, "wort": "wider", "ziel": "wieder", "sicherheit": 0.97, \
"alternative": null, "nummern": null}}]
Ein leeres Array, wenn in diesem Ausschnitt kein Wort falsch geschrieben ist.
"""

MERKMALE = """\
Du beantwortest für eine OLFA-Fehleranalyse präzise Fragen zu Merkmalen von Zielwörtern. \
Beurteilt wird NICHT der Fehler, sondern ein sprachliches Merkmal des Zielworts.

{schweiz_regel}

Für jeden Fall: Beantworte die Frage anhand des Zielworts. Nenne dann, welcher der genannten \
Kandidaten aus dem Merkmal folgt – nie eine Kategorie ausserhalb der Kandidatenliste. \
Bist du dir beim Merkmal nicht sicher, setze "sicher": false.

{faelle}

Antworte nur mit einem JSON-Array, ein Objekt je Fall in derselben Reihenfolge:
[{{"fall": 1, "vokallaenge": "kurz"|"lang"|null, "morphemgrenze": true|false|null, \
"v": "f"|"v"|null, "umlaut": true|false|null, "kategorie": "07", "sicher": true, \
"begruendung": "höchstens 15 Wörter"}}]
"""

VORLAGEN["zielwoerter"] = ZIELWOERTER
VORLAGEN["merkmale"] = MERKMALE
VORLAGEN["analyse_diktat"] = ANALYSE_DIKTAT
VORLAGEN["analyse_freitext"] = ANALYSE_FREITEXT
VORLAGEN["aufraeumen"] = AUFRAEUMEN

PFLICHTPLATZHALTER.update({
    "zielwoerter": {"schweiz_regel", "text", "woerter", "schwelle"},
    "merkmale": {"schweiz_regel", "faelle"},
    "analyse_diktat": {"analyse_kopf", "analyse_format", "originaltext", "schuelertext"},
    "analyse_freitext": {"analyse_kopf", "analyse_format", "schuelertext"},
    "aufraeumen": {"sammlung", "oberbegriffe"},
})

#: Auch der gemeinsame Kopf braucht seine Platzhalter – er wird von
#: :func:`rstrainer.auftraege.analyse_prompt_bauen` separat gefüllt.
KOPF_PLATZHALTER = {"olfa_liste", "schweiz_regel", "grammatik_liste", "bekannte_arten", "oberbegriffe"}
