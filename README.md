# RSTrainer

Lokales Werkzeug für die Rechtschreibförderung im Deutschunterricht: Diktate
verwalten, Fehler systematisch nach OLFA-Kategorien erfassen, daraus
passgenaue Übungsblätter samt Mini-Test erzeugen und den Lernverlauf sichtbar
machen.

**Ohne Sprachmodell-Schnittstelle.** Die App enthält keinen API-Schlüssel und
ruft zur Laufzeit keinen externen Dienst auf. Die Texterzeugung passiert in
einem gewöhnlichen Claude-Chat; die App liefert dafür fertige Prompts und
nimmt das Ergebnis kontrolliert wieder entgegen.

---

## ⚠️ Zuerst lesen: die OLFA-Kategorienliste ist ein Platzhalter

Die Recherche ergab Folgendes:

* Die Oldenburger Fehleranalyse **OLFA 3–9** (Günther Thomé / Dorothea Thomé,
  isb-Verlag Oldenburg) arbeitet mit **37 Fehlerkategorien** – nicht mit rund
  30, wie ursprünglich angenommen.
* Jede Kategorie gehört zusätzlich zu einer von **drei entwicklungsbezogenen
  Gruppen (I / II / III)**.
* Online gesichert belegbar waren nur: diese Gesamtzahl, das Gruppenprinzip
  und die Kategorien **01** (Kleinbuchstabe statt Grossbuchstabe, `*haus` für
  *Haus*) und **02** (Grossbuchstabe statt Kleinbuchstabe, `*Kalt` für *kalt*).
* Die vollständige, wörtliche Kategorienliste steht ausschliesslich im
  kostenpflichtigen OLFA-Handbuch bzw. auf dem Auswertungsbogen und ist
  urheberrechtlich geschützt. Die Volltext-Quellen (isb-oldenburg.de,
  olfaonline.de, Universitätsserver) waren aus der Entwicklungsumgebung nicht
  abrufbar.

**Deshalb wurde nichts erfunden und nichts rekonstruiert.** Mitgeliefert ist
unter [`data/olfa_kategorien.json`](data/olfa_kategorien.json) eine fachlich
eigenständig formulierte **Arbeitsliste mit 37 Kategorien**, die sich an den
bei OLFA abgedeckten Rechtschreibbereichen orientiert. Jeder Eintrag trägt
`"geprueft": false`, und die App weist in der Seitenleiste dauerhaft darauf
hin, solange das so ist.

**Was Sie tun sollten:** Gleichen Sie die Liste einmal gegen Ihr Fachmaterial
ab (Einstellungen → OLFA-Kategorien), korrigieren Sie Nummern und
Bezeichnungen und setzen Sie die Häkchen. Die App funktioniert mit **jeder**
Kategorienliste – Anzahl, Nummern und Namen sind frei änderbar.

> Ein technisches Detail beim Bearbeiten: Die Spalte `heuristik` steuert die
> automatischen Kategorie-Vorschläge beim Textabgleich. Beim Umbenennen einer
> Kategorie bitte stehen lassen, beim Umnummerieren mitnehmen.

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

1. **Parameter wählen** – Länge, Zielkategorien, Klassenstufe, Thema.
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

### Korrekturlesen ist ein eigener Schritt

Beim Diktat ist das Korrekturlesen des Originaltexts **vom allgemeinen
Freigabehäkchen getrennt** und in der App eigens hervorgehoben. Der Grund:
Dieser Text ist später die **Referenzwahrheit** für den maschinellen Abgleich
mit dem Schülertext. Ein Tippfehler darin würde der Schülerin oder dem Schüler
als Fehler angerechnet.

Solange das Korrekturlesen nicht bestätigt ist, bleibt der diff-gestützte
Abgleich für dieses Diktat **gesperrt**. Nachholen lässt es sich jederzeit
unter *Diktate → Archiv*.

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

## Fehlererfassung mit Diff-Unterstützung

Statt jeden Fehler von Hand zu suchen: Schülertext abtippen, einfügen,
**Abgleich starten**. Die App richtet beide Texte wortweise aneinander aus und
schlägt Abweichungen samt passender OLFA-Kategorie vor. Sie bestätigen jede
Zeile einzeln und ändern die Kategorie, wo nötig – **vorgeschlagen wird, nie
automatisch übernommen**.

Beispiele für die Kategorie-Vorschläge:

| Original | Geschrieben | Vorschlag |
|---|---|---|
| Haus | haus | 01 – Kleinschreibung statt Grossschreibung |
| kommen | komen | 07 – Doppelkonsonant fehlt |
| Zahn | Zan | 11 – Dehnungs-h fehlt |
| Wiese | Wise | 13 – ie fehlt |
| Hund | Hunt | 27 – Auslautverhärtung |
| Brot | Bort | 29 – Buchstaben vertauscht |
| Mutter | Mutta | 34 – Wortendung falsch |

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

**Plausibilitätsprüfung** (`rstrainer/validation.py`)
* Wortzahl-Abweichungen bis **20 %** lösen keinen Hinweis aus (der Prompt
  fordert 10 %, gemessen wird grosszügiger).
* Ein Kategorie-«Treffer» heisst *könnte passen*, nicht *passt*. Die Prüfung
  arbeitet mit Wortmustern, nicht mit Wortbedeutungen.

**Rechtschreibvariante**
* Voreingestellt ist die **Schweizer Variante ohne ß** (ss durchgehend). Unter
  Einstellungen lässt sich auf die deutsch-österreichische Variante mit ß
  umstellen; die Einstellung fliesst in alle Chat-Prompts ein.

---

## Datenschutz

Es geht um Daten minderjähriger Schüler:innen.

* **Nichts Persönliches im Repository.** Die Datenbank liegt unter `daten/`,
  Exporte unter `daten/export/`. Beide Pfade stehen in `.gitignore`, zusammen
  mit `*.sqlite3`, `*.db` und `*.docx`. Ein Test wacht darüber.
* **Empfehlung: Kürzel statt Klarnamen.** Ein Übungsblatt landet schnell im
  Lehrerzimmer, im Drucker oder im Papierkorb. Mit einem Kürzel ist der Bezug
  zur Person nur für Sie herstellbar. Unter *Einstellungen → Namen auf
  Ausdrucken* lässt sich zwischen **Kürzel/Pseudonym** (Voreinstellung) und
  **Klarname** umschalten – für ein Elterngespräch etwa kurzzeitig.
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
Demoprofile mit Diktaten, Schülertexten und Fehlern an. Damit lassen sich
Abgleich, Empfehlungslogik, Trendanalyse und Word-Export ausprobieren, ohne
echte Schülerdaten anzufassen. Die Profile tragen das Präfix `DEMO – ` und
lassen sich in einem Zug wieder entfernen.

Die Demodaten sind mit festem Zufallsstartwert erzeugt und damit
reproduzierbar. Die eingebauten Entwicklungen (abnehmend / stagnierend /
zunehmend) sollen genau so in der Auswertung erscheinen – ein Test prüft das.

---

## Tests

```bash
python3 -m pytest tests/ -q
```

**Stand: 197 Tests, alle grün.** Abgedeckt sind:

| Datei | Prüft |
|---|---|
| `test_diffing.py` | Wort- und Buchstabenabgleich, Kategorie-Vorschläge, Kennzahlen |
| `test_analysis.py` | Trendeinstufung, Schwellen, Normierung, Empfehlungsreihenfolge |
| `test_docx_export.py` | Gültige .docx, Seitenumbruch Vorder-/Rückseite, keine Lösungen auf der Aufgabenseite |
| `test_auftraege.py` | Prompt-Aufbau, Auftragsnummern, Zerlegen der Chat-Antwort, Rückfall auf Fliesstext |
| `test_validation.py` | Plausibilitätsprüfungen für Diktat und Blatt |
| `test_db.py` | Datentrennung zwischen Profilen, Freigabe- und Korrekturlese-Nachweise |
| `test_olfa_und_export.py` | Kategorienliste, Testmodus, CSV/JSON-Export, `.gitignore` |
| `test_charts.py` | Diagramme, feste Farbreihenfolge, Serienbegrenzung |

Zusätzlich wurde die Oberfläche im Browser durchgespielt: alle sechs Bereiche
rendern fehlerfrei, und der komplette Diktat-Ablauf (Prompt erzeugen →
Ergebnis einfügen → Prüfung → Freigabe → Archiv) läuft durch. Dabei wurde
geprüft, dass der Speichern-Knopf ohne Freigabe tatsächlich gesperrt bleibt.

**Noch offen / bewusst nicht gebaut:**
* Die OLFA-Liste ist fachlich ungeprüft (siehe oben) – der wichtigste offene
  Punkt.
* Die Oberfläche selbst hat keine automatisierten Tests; geprüft wurde sie
  von Hand im Browser.
* Es gibt keine Mehrbenutzer-Funktion und keine Synchronisierung zwischen
  Geräten – bewusst, weil das den Datenschutzaufwand vervielfachen würde.

---

## Projektaufbau

```
app.py                        Einstiegspunkt (Streamlit)
data/olfa_kategorien.json     Referenzliste der Fehlerkategorien (editierbar)
daten/                        Lokale Daten – NICHT im Repository
rstrainer/
  config.py                   Pfade und fachliche Voreinstellungen
  db.py                       SQLite-Schema und Zugriffe
  olfa.py                     Kategorienliste laden, speichern, abfragen
  textwerkzeuge.py            Tokenisierung, Normalisierung, Kontext
  diffing.py                  Wort- und Buchstabenabgleich
  analysis.py                 Trendberechnung und Empfehlungslogik
  prompt_templates.py         >> Die Prompt-Vorlagen – zum Anpassen gedacht <<
  auftraege.py                Prompt bauen, Chat-Ergebnis zerlegen
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
