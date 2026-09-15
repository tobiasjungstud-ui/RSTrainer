# RSTrainer

Lokales Werkzeug für die Rechtschreibförderung im Deutschunterricht: Diktate
und frei geschriebene Texte verwalten, Fehler systematisch erfassen, daraus
passgenaue Übungsblätter samt Mini-Test erzeugen und den Lernverlauf sichtbar
machen.

Ausgelegt auf die **Sekundarstufe I** (7.–9. Klasse) und ausschliesslich auf
die **Schweizer Rechtschreibung**: kein ß, durchgehend ss. Eine
Variantenumschaltung gibt es nicht.

**Ohne Sprachmodell-Schnittstelle.** Die App enthält keinen API-Schlüssel und
ruft zur Laufzeit keinen externen Dienst auf. Texterzeugung *und*
Fehleranalyse passieren in einem gewöhnlichen Claude-Chat; die App liefert
dafür fertige Prompts und nimmt das Ergebnis kontrolliert wieder entgegen.

> **Hinweis:** Es gibt daneben eine Fassung als Claude-Artefakt, in der das
> Sprachmodell direkt in der Seite arbeitet und die Daten bei Claude liegen.
> Die beiden Fassungen sind fachlich deckungsgleich – dieselbe Kategorienliste,
> dieselbe Trend- und Empfehlungsrechnung, dieselben Prompts. Der Unterschied
> ist, wo die Daten liegen und wer das Modell aufruft. Diese hier bleibt
> vollständig lokal.

---

## Die OLFA-Kategorienliste

Unter [`data/olfa_kategorien.json`](data/olfa_kategorien.json) liegen die **37
Fehlerkategorien der Oldenburger Fehleranalyse**, wie sie die Lehrperson aus
ihrem Fachmaterial übernommen hat. Alle Einträge sind als `"geprueft": true`
markiert.

Die Bezeichnungen folgen dem Muster **«X für Y»**: geschrieben wurde X, richtig
wäre Y. «Klein- für Großschreibung» heißt also *kleingeschrieben, obwohl groß
richtig wäre*.

Die Nummern **21 und 22 sind im Original unbesetzt** und bleiben es auch hier,
damit die Nummerierung mit dem Auswertungsbogen übereinstimmt.

### Zwei offene Punkte

**1. Die Gruppenzuordnung I / II / III fehlt.** OLFA ordnet jede Kategorie
zusätzlich einer von drei entwicklungsbezogenen Gruppen zu, erkennbar an der
roten, gelben bzw. grünen Markierung der Kategorienummer auf dem
Auswertungsbogen. Diese Angabe war in der übermittelten Tabelle nicht
enthalten und wurde **nicht erraten** – das Feld `gruppe` ist überall `null`.
Nachtragen lässt sie sich unter *Einstellungen → OLFA-Kategorien*. Die App
funktioniert auch ohne; es fehlt lediglich die Gruppierung nach
Entwicklungsphase.

**2. Zwei der vier ß-Kategorien sind gesperrt.** Die App kennt nur die
Schweizer Rechtschreibung – in den Prompts entsteht nie ein ß. Damit gilt für
die Kategorien 13–16:

| Nr. | Kategorie | In der Schweiz |
|---|---|---|
| 13 | s für ß | **gesperrt** – die Schreibung ohne ß ist hier richtig |
| 14 | ß für s | **relevant** – erfasst ein fälschlich gesetztes ß |
| 15 | ss für ß | **gesperrt** – ss ist hier die korrekte Schreibung |
| 16 | ß für ss | **relevant** – etwa `*daß` statt `dass` |

«Gesperrt» heisst: nicht auswählbar, und der Analyse-Prompt untersagt dem
Modell diese beiden Nummern ausdrücklich. Die Nummern bleiben trotzdem
erhalten, damit die Zählung mit dem Auswertungsbogen übereinstimmt – ebenso
wie die unbesetzten 21 und 22.

### Eigene Änderungen

Die Liste ist frei editierbar – Nummern, Namen und Anzahl. Ein technisches
Detail: Die Spalte `heuristik` steuert die automatischen Kategorie-Vorschläge
beim Textabgleich. Beim Umbenennen einer Kategorie bitte stehen lassen, beim
Umnummerieren mitnehmen. Ein Marker darf auf **mehrere** Kategorien zeigen;
dann schlägt die App beide vor – so geschieht es bei `doppelkonsonant_zuviel`,
das zu Kategorie 08 *und* 11 passt, weil das Werkzeug die Vokallänge nicht
kennt.

---

## Installation

```bash
git clone https://github.com/tobiasjungstud-ui/RSTrainer.git
cd RSTrainer
python3 -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Die App öffnet sich im Browser unter `http://localhost:8501`. Ausser beim
Erzeugen der Texte im Chat wird keine Internetverbindung gebraucht.

---

## Der Arbeitsablauf

### Warum der Umweg über den Chat?

Die App soll keine laufenden Kosten verursachen und von keinem externen Dienst
abhängen. Statt eines API-Aufrufs erzeugt sie deshalb einen **fertig
formulierten Prompt**, den Sie in einen beliebigen Claude-Chat kopieren. Das
Ergebnis kopieren Sie zurück.

### Der Auftragsnummern-Kreislauf

Damit dabei nichts durcheinandergerät, bekommt jeder Auftrag eine
**Auftragsnummer** wie `RST-DIK-4F7A2B`:

```
 App                          Chat                         App
  │                            │                            │
  │  Prompt mit Nummer ───────►│                            │
  │                            │  Antwort in Markierungen   │
  │                            │  + Nummer wiederholt ─────►│
  │                            │                            │  prüft Nummer,
  │                            │                            │  zerlegt Kopf
  │                            │                            │  und Abschnitte
```

Die Antwort steht zwischen `===RSTRAINER-ANFANG===` und `===RSTRAINER-ENDE===`
und hat einen kleinen Kopfbereich (`AUFTRAG:`, `TYP:`, `TITEL:`, `WOERTER:`).
Beim Einfügen kann die App dadurch

* einleitendes Geplauder des Chats abschneiden («Gerne! Hier ist dein Diktat:»),
* prüfen, ob der Text zum richtigen Auftrag gehört, und warnen, wenn nicht,
* Übungsteil, Mini-Test und Lösungen automatisch voneinander trennen,
* die Formularfelder vorbelegen.

**Fehlen die Markierungen, geht nichts verloren**: Der Text wird dann
unverändert als Fliesstext übernommen, mit einem entsprechenden Hinweis.

### Die vier Schritte

1. **Parameter wählen** – Länge, Zielkategorien, Schwierigkeitsgrad, Thema.
2. **Prompt kopieren** – ein Klick aufs Kopier-Symbol, ab in den Chat.
3. **Ergebnis einfügen** – die App zeigt eine Vorschau und prüft automatisch.
4. **Freigeben** – erst jetzt wird gespeichert.

---

## Die Kontrollpunkte vor der Freigabe

Nichts aus dem Chat gelangt ungeprüft in die Datenbank.

### Kein Speichern ohne Freigabe

Nach dem Einfügen steht der Text **nur zur Ansicht** auf dem Bildschirm. Der
Speichern-Knopf bleibt gesperrt, bis Sie «Geprüft und freigegeben» ankreuzen.
Das Freigabedatum wird mitgespeichert, sodass im Archiv nachvollziehbar bleibt,
dass nichts durchgerutscht ist.

### Korrekturlesen: Hinweis statt Sperre

Der Diktattext ist später die **Referenzwahrheit** für den maschinellen
Abgleich; ein Tippfehler darin würde der Schülerin oder dem Schüler als Fehler
angerechnet. Die Plausibilitätsprüfung weist bei jedem Diktat darauf hin.

Ein **eigenes Häkchen mit Sperre** gab es in einer früheren Fassung; es ist
bewusst wieder entfernt worden. Zwei Bestätigungen für denselben Blick aufs
Blatt werden zur Formalie, und eine gesperrte Funktion, die man mit einem
zweiten Klick aufschliesst, schützt niemanden.

### Plausibilitätsprüfungen (Hinweise, keine Sperren)

Beim **Diktat**:
* Stimmt die Wortanzahl ungefähr mit der Vorgabe überein?
* Enthält der Text überhaupt Wörter, an denen die gewünschten Kategorien
  sichtbar werden können? Die App zeigt die gefundenen Kandidaten an.

Beim **Übungsblatt**:
* Sind die Aufgaben erkennbar den gewählten Kategorien zugeordnet?
* Stehen versehentlich Lösungen auf der Aufgabenseite? Erkannt werden
  Formulierungen wie `Lösung:`, `→ Wort` oder `_____ (kommen)`.
* Überschneiden sich Übungs- und Testwörter zu stark? Dann misst der Test eher
  das Merken als das Können.

Vor dem Speichern eines Blattes verlangt die App **zwei ausdrückliche
Antworten**, die sie selbst nicht geben kann:
* «Keine Lösungen auf den Aufgabenseiten» – Sie haben beide Seiten angeschaut.
* «Schwierigkeitsgrad passt zur Altersstufe» – das kann nur die Lehrperson
  beurteilen.

Beide Antworten werden mit dem Freigabedatum in der Datenbank festgehalten.

---

## Zwei Arten von Texten

**Diktat** – die Lehrperson gibt eine fehlerfreie Vorlage vor, das Kind
schreibt sie ab. Was von der Vorlage abweicht, ist objektiv ein Fehler.

**Freier Text** – alles, was im Unterricht sonst entsteht: Aufsatz, Bericht,
Antwort auf eine Frage. Es gibt keine Vorlage; die Beurteilung übernimmt das
Sprachmodell. Die Wortzahl richtet sich hier nach dem Text des Kindes, denn
etwas anderes gibt es nicht zu zählen.

Beide landen in derselben Auswertung und im selben Lernverlauf.

---

## Fehlererfassung: drei Wege, eine Bestätigungsliste

### 1. Analyse durch das Sprachmodell

Die App erzeugt einen Analyse-Prompt mit dem Text, der vollständigen
OLFA-Liste und allen bereits gelernten Fehlerarten. Im Chat ausgewertet,
kommt ein JSON-Array zurück, das die App einliest – auch wenn ein Code-Zaun
oder einleitendes Geplauder mitkommt.

Das Modell leistet zweierlei, was der mechanische Abgleich nicht kann: Es
ordnet die Kategorien **inhaltlich** zu statt nach dem Buchstabenbild, und es
darf für alles, was die OLFA-Liste nicht abdeckt – vor allem **Grammatik** –
eigene Fehlerarten benennen (siehe unten). Für freie Texte ist es der einzige
Weg.

Bei freien Texten warnt der Prompt ausdrücklich vor Stilkritik: Ohne Vorlage
ist die Versuchung gross, zu viel anzustreichen. Umständliche Formulierungen,
Wortwahl, Wiederholungen und Umgangssprache sind **keine** Fehler.

### 2. Mechanischer Abgleich (nur Diktat)

Schülertext abtippen, einfügen, **Abgleich starten**. Die App richtet beide
Texte wortweise aneinander aus und schlägt Abweichungen samt Kategorie vor.
Sie sieht nur das Buchstabenbild – die Kategorie ist geraten, nicht
verstanden.

### 3. Von Hand

Für alles, was beide nicht sehen: Satzzeichen, Silbentrennung am Zeilenende,
unleserliche Stellen.

---

Alle drei Wege enden in **derselben Bestätigungsliste**: Sie bestätigen jede
Zeile einzeln und ändern die Kategorie, wo nötig – **vorgeschlagen wird, nie
automatisch übernommen**.

Beispiele für die Kategorie-Vorschläge des mechanischen Abgleichs:

| Original | Geschrieben | Vorschlag |
|---|---|---|
| Haus | haus | 01 – Klein- für Großschreibung |
| kommen | komen | 07 – Einfachschreibung für Konsonantenverdoppelung |
| hat | hatt | 08 / 11 – Verdoppelung an falscher Stelle |
| Zahn | Zan | 09 – markierte Länge fehlt |
| dass | daß | 16 – ß für ss |
| Bären | Beren | 17 – e für ä |
| Hund | Hunt | 19 – p, t, k für b, d, g |
| Vater | Fater | 23 – f für v |
| wenig | wenich | 27 – ch für g im Silbenende |
| Schule | Sule | 29 – Konsonantenzeichen fehlt |
| Brot | Bort | 35 – Zeichenumstellung |
| Bücher | Bucher | 36 – Umlautbezeichnung |

Ein Test prüft jedes dieser Paare gegen die Kategorienliste.

---

## Gelernte Fehlerarten

Die OLFA-Liste deckt die Rechtschreibung ab. Für alles andere – vor allem
Grammatik – benennt das Sprachmodell die Fehlerart selbst und ordnet sie
hierarchisch ein:

```
Grammatik › Kasus › Dativ statt Akkusativ
Zeichensetzung › Komma › Komma vor Nebensatz fehlt
```

Sie werden **ohne Rückfrage angelegt** (mit dem Übernehmen der Fehlerzeilen,
die sie tragen) und liegen in `daten/fehlerarten.json`. Das war ausdrücklich
so gewollt; der Preis dafür ist eine Sammlung, die wächst. Vier Vorkehrungen
halten sie in Form:

1. **Die oberste Ebene ist nicht frei**, sondern auf fünf Oberbegriffe
   beschränkt: Grammatik, Zeichensetzung, Wortschatz, Formales, Sonstiges.
   Sonst stünden nach zwanzig Texten «Grammatik», «Grammatikalisch» und
   «Sprachrichtigkeit» nebeneinander.
2. **Pfade werden begradigt**, bevor sie verglichen werden – Leerraum weg,
   erster Buchstabe gross. Exakt gleiche werden zusammengelegt.
3. **Ähnliche Paare werden gemeldet, nie automatisch verschmolzen.**
   «Dativ statt Akkusativ» und «Akkusativ statt Dativ» teilen alle Wörter und
   meinen das Gegenteil. Der Wortvergleich ist ein Hinweis an die Lehrperson,
   kein Automatismus.
4. **Aufräumen lassen.** Unter *Einstellungen → Gelernte Fehlerarten* erzeugt
   die App einen Prompt, mit dem das Modell seine eigene Sammlung ordnet.
   Angewendet wird erst nach Bestätigung, Zeile für Zeile und nichts
   vorausgewählt: Anders als beim Anlegen ist ein Fehlgriff hier teuer, weil
   er bestehende Fehlerdaten umhängt.

Zusammenlegen und Löschen wirken **über alle Profile hinweg** – sonst zeigten
die Einträge fremder Kinder ins Leere. Eine gelöschte Art fällt auf die
Auffangkategorie 37 zurück; zusammenlegen erhält die Information, löschen
nicht.

---

## Klassiker oder Sondierung?

Beim Erzeugen eines Diktats steht ein Regler zwischen zwei Polen:

* **Alte Klassiker** – gezielt üben, was nicht sitzt. Die Kategorien kommen
  aus der Empfehlungslogik unten.
* **Neues prüfen** – schauen, wo es sonst noch hakt. Die Kategorien kommen aus
  dem Sondierungsvorrat: alles, wozu dieses Kind noch keinen Fehler hat.

Der Vorrat ist breit über die Rechtschreibbereiche gestreut, stellt nie
geprüfte Kategorien nach vorn, und das Fenster wandert mit der Zahl der Texte
weiter – sonst kämen immer dieselben Kandidaten. Fehlt eine der beiden Seiten
(ein neues Profil hat noch keine Klassiker), füllt die andere auf.

Der Regler **setzt** die Auswahl, er erzwingt sie nicht: Darunter steht die
Kategorienliste zum Anpassen von Hand. Im Prompt sind Sondierungskategorien
als solche ausgewiesen, damit das Modell dort nicht ebenso viele Zielwörter
platziert wie bei den bekannten Schwerpunkten.

---

## Empfehlungslogik: welche Kategorie fördern?

Die Priorität einer Kategorie berechnet sich als

```
Punktzahl = zeitgewichtete Fehlerrate × Trendfaktor × Verbreitungsfaktor
```

* **Zeitgewichtete Fehlerrate** – Fehler pro 100 Wörter, wobei jüngere Diktate
  exponentiell stärker zählen (Halbwertszeit 3 Diktate).
* **Trendfaktor** – bessert sich eine Kategorie bereits, wird sie mit **0,6**
  abgewertet; nimmt sie zu, mit **1,35** aufgewertet; stagnierend **1,0**, neu
  aufgetreten **1,1**. Genau das setzt den Wunsch um, stagnierende und
  zunehmende Fehler zu bevorzugen.
* **Verbreitungsfaktor** – `0,5 + 0,5 × (Diktate mit Fehler / betrachtete
  Diktate)`. Ein einmaliger Ausreisser zählt weniger als ein durchgehendes
  Muster.

Zu jedem Vorschlag zeigt die App die Begründung, zum Beispiel:

> Kategorie 11 in 6 von 6 betrachteten Diktaten; 30 Fehler insgesamt; keine
> Besserung erkennbar.

---

## Getroffene Annahmen – bitte fachlich gegenprüfen

Diese Entscheidungen sind im Code dokumentiert und hier zusammengefasst,
damit sie nicht stillschweigend gelten:

**Trendberechnung** (`rstrainer/analysis.py`)
* Verglichen werden **Fehler pro 100 Wörter**, nicht absolute Zahlen. Sonst
  wäre ein langes Diktat automatisch «schlechter» als ein kurzes.
* Das Trendfenster umfasst die **letzten 3 Diktate gegen die 3 davor**. Es
  braucht also mindestens **4 Diktate**, bevor überhaupt ein Trend ausgewiesen
  wird; vorher lautet die Einstufung *zu wenig Daten*.
* Eine Veränderung gilt erst ab **20 % relativer Abweichung** als Trend, und
  zusätzlich muss die absolute Differenz mindestens **0,5 Fehler pro 100
  Wörter** betragen. Sonst wären 2 statt 1 Fehler bereits «+100 %».
* Angezeigte Raten sind auf **2 Nachkommastellen** gerundet; gerechnet wird
  mit den ungerundeten Werten.

**Textabgleich** (`rstrainer/diffing.py`)
* Für die **Ausrichtung** der beiden Texte wird die Gross-/Kleinschreibung
  ignoriert, damit ein reiner Grossschreibfehler nicht als «Wort gelöscht plus
  Wort eingefügt» erscheint. Die **Abweichung** selbst wird anschliessend auf
  den Originalformen bestimmt.
* Verglichen wird mit `.lower()` statt `.casefold()`, weil `casefold()` das ß
  auf ss abbildet und damit genau den ß/ss-Fehler verdecken würde.
* **Satzzeichen werden nicht verglichen** – sie werden beim Abtippen
  erfahrungsgemäss unzuverlässig übertragen. Satzzeichenfehler bitte von Hand
  erfassen.
* Die Kategorie-Vorschläge sind **Heuristik, keine linguistische Analyse**.
  Sie sind nach Plausibilität sortiert; die Entscheidung trifft die Lehrperson.
* Ein erkannter Buchstabendreher erklärt das ganze Wort; weitere Marker werden
  dann unterdrückt, weil sie nur Rauschen wären.
* OLFA spricht bei den Kategorien 19/20 und 27/28 vom **Silbenrand bzw.
  Silbenende**. Ohne Silbentrennung prüft das Werkzeug ersatzweise das
  **Wortende** – den häufigsten Fall. Fehler im Silbenrand wortintern muss die
  Lehrperson selbst zuordnen.
* **Ohne automatische Erkennung** bleiben die Kategorien 03, 04, 05, 06 und 12
  sowie Fremdwortfehler: Sie hängen an Wortbedeutung, Silbenstruktur oder
  Vokallänge, nicht am Buchstabenvergleich. Diese Fehler werden wie bisher von
  Hand erfasst.

**Plausibilitätsprüfung** (`rstrainer/validation.py`)
* Wortzahl-Abweichungen bis **20 %** lösen keinen Hinweis aus (der Prompt
  fordert 10 %, gemessen wird grosszügiger).
* Ein Kategorie-«Treffer» heisst *könnte passen*, nicht *passt*. Die Prüfung
  arbeitet mit Wortmustern, nicht mit Wortbedeutungen.

**Gelernte Fehlerarten** (`rstrainer/taxonomie.py`)
* Die oberste Ebene ist auf fünf feste Oberbegriffe beschränkt. Alles, was das
  Modell darüber hinaus vorschlägt, landet unter *Sonstiges*.
* Ein Pfad hat **zwei oder drei Stufen**; ein einstufiger ist keine Fehlerart,
  sondern ein Oberbegriff, und wird verworfen.
* Die Ähnlichkeit zweier Arten wird als **Anteil gemeinsamer Wörter** gemessen.
  Das ist grob und dient allein der Anzeige – zusammengelegt wird nie
  automatisch.
* Eine Kennung, die es nicht mehr gibt, lenkt die Auswertung auf die
  **Auffangkategorie 37**. Nichts verschwindet stillschweigend aus der Statistik.

**Modell-Analyse** (`rstrainer/auftraege.py`)
* Eine Antwort, die kein verwertbares JSON enthält, führt zu einer **Meldung**,
  nie zu geratenen Fehlern. Code-Zaun und Begleittext werden abgeschnitten.
* Eine OLFA-Nummer, die es nicht gibt oder die gesperrt ist, fällt auf **37**
  zurück. Ebenso eine erfundene Kennung einer gelernten Art.
* Neue Fehlerarten werden erst mit dem **Übernehmen der Fehlerzeilen** angelegt,
  die sie tragen. Ein verworfener Abgleich hinterlässt nichts.
* Beim Diktat wird die Fundstelle im **Original** gesucht, beim freien Text im
  **Text des Kindes** – dort steht die falsche Form. Die App versucht beides.

**Schweizer Rechtschreibung**
* Es gibt **keine Variantenumschaltung**. Alle Prompts verlangen durchgehend
  ss; die Kategorien 13 und 15 sind gesperrt.

---

## Datenschutz

Es geht um Daten minderjähriger Schüler:innen.

* **Nichts Persönliches im Repository.** Die Datenbank liegt unter `daten/`,
  Exporte unter `daten/export/`. Beide Pfade stehen in `.gitignore`, zusammen
  mit `*.sqlite3`, `*.db` und `*.docx`. Ein Test wacht darüber.
* **Empfehlung: Pseudonym als Anzeigename.** Ein Übungsblatt landet schnell im
  Lehrerzimmer, im Drucker oder im Papierkorb. Der Anzeigename ist zugleich
  das, was auf Ausdrucken erscheint – wer dort keinen Klarnamen haben will,
  trägt schon im Profil ein Pseudonym ein. Dann gibt es gar keine Datei mit dem
  Klarnamen darin.
* **Ein Profil trägt nur Anzeigename und Notiz.** Kürzel, Klasse und
  Klassenstufe gab es in einer früheren Fassung und sind bewusst entfernt
  worden: drei personenbezogene Felder ohne Nutzen für eine Lehrperson, die
  die wenigen Kinder kennt, die sie einzeln fördert.
* **`daten/fehlerarten.json` enthält keine Namen**, lässt aber Rückschlüsse auf
  den Unterricht zu. Die Datei liegt deshalb ebenfalls unter `daten/`.
* **Der Code darf öffentlich sein, die Daten nie.** Exportdateien enthalten
  Klartext und gehören weder in einen Cloud-Ordner noch unverschlüsselt in
  einen E-Mail-Anhang.
* Ein anderer Speicherort lässt sich über Umgebungsvariablen setzen:
  ```bash
  RSTRAINER_DATEN_DIR=/pfad/zu/verschluesseltem/ordner streamlit run app.py
  ```

---

## Testmodus

Unter *Einstellungen → Testmodus* legen Sie drei **frei erfundene**
Demoprofile mit Diktaten, freien Texten, Schülertexten und Fehlern an. Damit
lassen sich Abgleich, Empfehlungslogik, Trendanalyse und Word-Export
ausprobieren, ohne echte Schülerdaten anzufassen. Die Profile tragen das
Präfix `DEMO – ` und lassen sich in einem Zug wieder entfernen.

Die Demodaten sind mit festem Zufallsstartwert erzeugt und damit
reproduzierbar. Die eingebauten Entwicklungen (abnehmend / stagnierend /
zunehmend) sollen genau so in der Auswertung erscheinen – ein Test prüft das.
Deshalb schreibt auch der freie Text, als jüngster Eintrag, die Entwicklung
auf dem Stand des letzten Diktats fort: Ein Fixwert am Ende machte aus jedem
«abnehmend» ein «stagnierend», und der Testmodus prüfte dann seine eigene
Verzerrung.

**Gelernte Fehlerarten legt der Testmodus keine an.** Die stehen ausserhalb
der Profile und blieben nach dem Entfernen der Demodaten stehen. Sie entstehen
erst, wenn das Sprachmodell einen Text auswertet.

---

## Tests

```bash
python3 -m pytest tests/ -q
```

**Stand: 287 Tests, alle grün.** Abgedeckt sind:

| Datei | Prüft |
|---|---|
| `test_diffing.py` | Wort- und Buchstabenabgleich, Kategorie-Vorschläge, Kennzahlen |
| `test_analysis.py` | Trendeinstufung, Schwellen, Normierung, Empfehlungsreihenfolge |
| `test_docx_export.py` | Gültige .docx, Seitenumbruch Vorder-/Rückseite, keine Lösungen auf der Aufgabenseite |
| `test_auftraege.py` | Prompt-Aufbau, Auftragsnummern, Zerlegen der Chat-Antwort, Rückfall auf Fliesstext |
| `test_validation.py` | Plausibilitätsprüfungen für Diktat und Blatt |
| `test_db.py` | Datentrennung zwischen Profilen, Freigabe, freie Texte, Umhängen über Profile hinweg |
| `test_olfa_und_export.py` | Kategorienliste, unbesetzte Nummern 21/22, Testmodus, CSV/JSON-Export, `.gitignore` |
| `test_charts.py` | Diagramme, feste Farbreihenfolge, Serienbegrenzung |
| `test_taxonomie.py` | Pfade begradigen, Dubletten, Gegenteile nicht verschmelzen, Register, Schwerpunkte |
| `test_analyse.py` | Analyse-Prompts, JSON zurücklesen, neue Fehlerarten, Aufräumplan, Regler Klassiker/Sondierung |

Zusätzlich wurde die Oberfläche durchgespielt – von Hand im Browser und
kopfrechnend über `streamlit.testing`: Alle sechs Bereiche rendern
fehlerfrei, der komplette Diktat-Ablauf (Prompt erzeugen → Ergebnis einfügen
→ Prüfung → Freigabe → Archiv) läuft durch, und ebenso der Analyse-Ablauf für
einen freien Text (Prompt → JSON einfügen → Bestätigungsliste → Übernehmen),
inklusive Anlegen einer neuen Fehlerart und Wiederverwenden einer bestehenden.

**Noch offen / bewusst nicht gebaut:**
* Die Gruppenzuordnung I / II / III der Kategorien fehlt noch (siehe oben).
* Die Oberfläche hat keine automatisierten Tests in der Suite; geprüft wurde
  sie von Hand und mit einem Skript ausserhalb des Repositorys.
* Es gibt keine Mehrbenutzer-Funktion und keine Synchronisierung zwischen
  Geräten – bewusst, weil das den Datenschutzaufwand vervielfachen würde.

---

## Projektaufbau

```
app.py                        Einstiegspunkt (Streamlit)
data/olfa_kategorien.json     Die 37 OLFA-Fehlerkategorien (editierbar)
daten/                        Lokale Daten – NICHT im Repository
  rstrainer.sqlite3           Profile, Texte, Fehler, Blätter, Aufträge
  fehlerarten.json            Vom Modell gelernte Fehlerarten
  export/                     CSV, JSON, .docx, Diagramme
rstrainer/
  config.py                   Pfade und fachliche Voreinstellungen
  db.py                       SQLite-Schema und Zugriffe
  olfa.py                     Kategorienliste laden, speichern, abfragen
  taxonomie.py                Gelernte Fehlerarten: anlegen, begradigen, ordnen
  kategorien.py               Gemeinsame Sicht auf beide Kategoriensysteme
  textwerkzeuge.py            Tokenisierung, Normalisierung, Kontext
  diffing.py                  Wort- und Buchstabenabgleich
  analysis.py                 Trendberechnung und Empfehlungslogik
  prompt_templates.py         >> Die Prompt-Vorlagen – zum Anpassen gedacht <<
  auftraege.py                Prompts bauen, Chat-Ergebnis und Analyse zerlegen
  validation.py               Plausibilitätsprüfungen vor der Freigabe
  docx_export.py              Übungsblatt, Informationsblatt, Verlaufsbericht
  charts.py                   Diagramme
  export.py                   CSV-/JSON-Export
  demo_data.py                Testmodus mit erfundenen Beispieldaten
  ui/                         Die sechs Bereiche der Oberfläche
tests/                        pytest-Suite
```

### Warum Python + Streamlit + SQLite?

Die vorgeschlagene Kombination wurde übernommen und ist für diesen Zweck
tatsächlich passend: Streamlit braucht kaum Gerüstcode, läuft rein lokal im
Browser und kommt ohne Web-Kenntnisse aus; SQLite ist eine einzelne Datei,
die sich sichern, verschlüsseln und löschen lässt, ohne dass ein Serverdienst
laufen muss. Für ein Werkzeug, das eine einzelne Lehrperson auf einem einzigen
Rechner benutzt, wäre alles Grössere Mehraufwand ohne Gegenwert.

### Die Prompt-Vorlagen anpassen

Die Textbausteine stehen in
[`rstrainer/prompt_templates.py`](rstrainer/prompt_templates.py) und sind zum
Ändern gedacht. Die Platzhalter in geschweiften Klammern müssen erhalten
bleiben; fehlt einer, zeigt die App einen verständlichen Hinweis statt
abzustürzen.
