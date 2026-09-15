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
#: entstehen, und die Kategorien 13 und 15 sind entsprechend gesperrt.
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

#: Die oberste Ebene gelernter Fehlerarten, siehe rstrainer.taxonomie.
SCHWEIZ_REGEL = (
    "WICHTIG – Schweizer Rechtschreibung (de-CH): Es gibt kein ß. «Strasse», "
    "«gross», «heisst», «dass» sind KORREKT. Erzeuge nie eine Zielform mit ß. "
    "Die Nummern 14 und 16 werden NIE vergeben. 13 = «s für ss» und 15 = «ss für s» "
    "gelten nur nach langem Vokal oder Diphthong (Fus → Fuss, Preisse → Preise); "
    "nach kurzem Vokal ist es Schärfung (07/08). Ein fälschlich gesetztes ß ist "
    "ein Konsonantenersatz (33)."
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
- Zielgruppe: {stufe}
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

## Weg 2: bereits angelegte eigene Fehlerarten
Verwende sie bevorzugt weiter, statt gleichbedeutende neue anzulegen:

{bekannte_arten}

## Weg 3: eine neue Fehlerart benennen
Deckt weder die OLFA-Liste noch eine bestehende Art den Fehler ab – insbesondere \
bei **Grammatik** –, benennst du selbst eine neue Art mit hierarchischem Pfad, \
zum Beispiel ["Grammatik", "Kasus", "Dativ statt Akkusativ"].

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
  "kategorie": "<OLFA-Nummer bei typ olfa, Kennung wie X-abc12345 bei typ bekannt, sonst null>",
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
Zielschreibung jedes falsch geschriebenen Wortes.

{schweiz_regel}

Regeln:
- Nur Rechtschreibung (Buchstaben, Gross-/Kleinschreibung, Getrennt-/Zusammenschreibung). \
Keine Grammatik, kein Stil, keine Zeichensetzung.
- Homophone aus dem Satzzusammenhang entscheiden (wider/wieder, das/dass, seid/seit).
- Ein Wort, das korrekt ist, kommt NICHT in die Liste.
- «sicherheit» ist deine Sicherheit (0–1), dass genau diese Zielform gemeint ist. Bei Zweifel: \
die wahrscheinlichere nennen, Sicherheit unter {schwelle} setzen, Alternative angeben.

Text:
{text}

Wörter (Nummer, Wort):
{woerter}

Antworte nur mit einem JSON-Array, ohne Vor- oder Nachtext:
[{{"nummer": 12, "wort": "wider", "ziel": "wieder", "sicherheit": 0.97, "alternative": null}}]
Leeres Array, wenn kein Wort falsch ist.
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
KOPF_PLATZHALTER = {"olfa_liste", "schweiz_regel", "bekannte_arten", "oberbegriffe"}
