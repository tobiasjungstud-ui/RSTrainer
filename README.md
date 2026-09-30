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
wäre Y. «Klein- für Grossschreibung» heisst also *kleingeschrieben, obwohl gross
richtig wäre*.

Die Nummern **21 und 22 sind im Original unbesetzt** und bleiben es auch hier,
damit die Nummerierung mit dem Auswertungsbogen übereinstimmt.

### Zwei geklärte Punkte (Original OLFA 3–9+, 7. Aufl. 2023)

Beide Punkte waren in früheren Fassungen offen und sind nach vollständiger
Lektüre des Originalhefts (`docs/olfa_original/`) verbindlich geklärt.

**1. Die Gruppenzuordnung I / II / III** stammt aus der Kopiervorlage (S. 57)
und ist mit der ausgefüllten Beispielliste (Abb. 7, S. 49) kreuzgerechnet:
Gruppe I (protoalphabetisch, rot) 03, 06, 11, 12, 29–35; Gruppe II
(alphabetisch, gelb) 01, 04, 07, 09, 17, 19, 23, 25, 27; Gruppe III
(orthographisch, grün) 02, 05, 08, 10, 18, 20, 24, 26, 28. 36 und 37 gehören
keiner Gruppe an und zählen nicht zum Kompetenzwert (S. 31).

**2. Die Kategorien 13–16 entfallen in der Schweizer Version** (S. 22, S. 59:
«entfällt für die Schweiz, sonst Nr. 37»). Das Tool folgt dem Original:

| Nr. | de-DE (Original) | Version CH (Tool) |
|---|---|---|
| 13–16 | s/ss/ß-Oppositionen | **gesperrt** – ein ß in der Schülerschreibung ist ein Fehler der Kategorie **37** (`*daß → dass`, `*Straße → Strasse`) |
| 07 | Einfachschreibung für Verdoppelung | `*Fus → Fuss`, `*Strase → Strasse` – auch nach Langvokal; die Stelle trägt dann das Fördermerkmal **F3** (lexikalische ss-Schreibung) |
| 08 / 11 | Verdoppelung für Einfachschreibung | `*Preisse → Preise` ist 11 (nach Diphthong, F3), `*Hasse → Hase` 11, `*Kasse → Kase`-Fälle nach Kurzvokal 08 |

Die frühere Neubelegung 13 = «s für ss», 15 = «ss für s» (Ergänzung A.3) ist
damit zurückgenommen; die Unterscheidung Schärfung (F1) gegen Merkwortschatz
(F3) lebt als Fördermerkmal weiter, nicht als Kategorie. 13, 14, 15, 16, 21,
22 stehen auf `NEVER_ASSIGN`.

### Was die Engine über das Original hinaus regelt

Fälle, die im Original nicht ausbuchstabiert sind, sind so entschieden – und
im Belastungskorpus (`tests/test_stress_sek1.py`) festgehalten:

* **Umschriften** eines Graphems zählen als *ein* Fehler: `*Schueler → Schüler`
  ist 36 (Umlautbezeichnung; Schweizer Tastatur), nicht 36 + 32; `*Kwelle →
  Quelle` ist 37 (lautgetreu, wie `*Schtein` auf S. 25), nicht 33 + 30.
* **ck für g** (`*Geburtstack → Geburtstag`) ist die Umkehrung von `*Sag für
  Sack` (S. 21) und zählt wie diese zwei Fehler: 19 und 08/11.
* Das **silbentrennende h** (`*seen → sehen`, `*ruig → ruhig`) bleibt 09 –
  so das Original auf S. 21, obwohl man 29 erwarten könnte.
* **Fremdwörter mit Merkstelle** stehen im Lexikon (`Restaurant`, `Computer`,
  `Trottoir`, `Chauffeur`, `Portemonnaie` …): Die Abweichung an dieser
  Stelle ist 37, nicht Vokal- oder Konsonantenersatz (S. 25–26).
* `*Werrk → Werk` ist 08 wie `*kallt → kalt` (§19): Verdoppelung nach kurzem
  Vokal, auch wenn ein Konsonant folgt.

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

## Übungsblätter: aus der Analyse abgeleitet, Aufgabe für Aufgabe steuerbar

Ein Blatt ist keine Textwand mehr, sondern eine **Liste von Aufgaben** (JSON
aus dem Chat, gleiches Schema in beiden Fassungen). Drei Regler genügen:

| Regler | Stufen | Was er steuert |
|---|---|---|
| **Niveau** | leicht · mittel · anspruchsvoll | was die Aufgabe verlangt: Wortmaterial, Stützung, Leistungsart (unverändert) |
| **Umfang** | kurz · normal · lang | 2/3/4 Aufgaben je Bereich, 4/6/8 im Mini-Test, Bearbeitungszeit |
| **Übungsebene** | automatisch · Lautebene · gemischt · Regelebene | welche Aufgabenformate überhaupt in Frage kommen |

Die Übungsebene folgt dem Original (S. 36, 24, 49): Kompetenzwert unter 50
oder überwiegend Gruppe-I-Fehler heisst **Lautebene** – Wörter in Grapheme
gliedern (Übung 8.1), Orthographeme markieren (8.2), Vokallänge hören, die
eigenen Lernwörter; dem Kind werden keine Fehlschreibungen vorgelegt (keine
Fehlersuche, kein Ankreuzen). 50–70 mischt Regel- und Lautebene, über 70
gibt es nur noch Regelarbeit: Sortieren, Ableiten, Fehlersuche mit
Distraktoren, Begründen, eigene Produktion.

Der **Förderplan** geht in den Prompt: je Bereich die Strategie
(Verlängern, Ableiten, Nomenprobe, Abhören) statt der Regel, der Kontrast,
der geübt werden muss (ss nach kurzem gegen langem Vokal, ie gegen Merkwörter
mit i, ableitbares gegen nicht ableitbares ä), und die **Lernwörter des
Kindes** – Wiederholungsfehler zuerst (S. 19, 27–28), richtig geschrieben,
mit dem Hinweis, was das Kind geschrieben hat. Jedes Lernwort muss im
Übungsteil vorkommen; der Mini-Test nimmt andere Wörter derselben Stelle.

**Auch Grammatik, Satzbau, Zeichensetzung und Textebene.** Als
Förderschwerpunkt lässt sich neben den OLFA-Kategorien jede Kategorie des
festen Katalogs B–E wählen (`B:Kasus`, `D:Komma Nebensatz` …). Die Befunde
dafür kommen aus **allen** Texten – auch aus dem Freien Diktat, dessen
Rechtschreibung sonst getrennt bleibt. Für diese Bereiche gelten eigene
Formate (Lückenwörter, Sortieren, **Sätze umformen**, Ankreuzen, Fehlersuche,
Begründen, eigene Produktion); die Übungsebene nach Kompetenzwert betrifft
nur die Rechtschreibung. Statt Lernwörtern gehen die **Lernstellen des
Kindes** in den Prompt – seine eigenen Sätze, falsch → richtig –, und die
richtige Form muss im Übungsteil vorkommen. Rechtschreibung und Grammatik
lassen sich auf einem Blatt mischen; das Tool schlägt die häufigsten
Katalogkategorien vor (`blatt.bereich_von`, `GRAMMATIK_FORMATE`, im Artefakt
`Blatt.istGrammatik`).

**Prüfung mit der Engine:** Jede Aufgabe wird geprüft – ß, Format auf der
Ebene erlaubt, Lösung vorhanden, Lösungswort nicht schon im Material,
Buchstabenvorgabe auf «anspruchsvoll» verboten, Lernwörter geübt, Test nicht
leichter als die Übung. Bei einer Fehlersuche läuft jeder eingebaute Fehler
durch die Engine: Gehört «Kater → Käter» nicht zu F1, steht das an der
Aufgabe (36 ist Umlautbezeichnung, nicht Schärfung).

**Im Tool sichtbar und steuerbar:** Vorder- und Rückseite werden als Blatt
gezeigt. Mit der Maus über eine Aufgabe fahren (Tastatur: Fokus; Touch:
immer sichtbar) bringt die Werkzeuge: **Bearbeiten** (Aufgabe, Material,
Lösung, Merksatz von Hand), **Austauschen**, nach oben, nach unten,
**Entfernen**. Im Editor liegen sechs **Chips**, die den Prompt für diese
eine Aufgabe steuern: Leichter · Schwerer · Andere Wörter · Lernwörter des
Kindes · Begründung verlangen · Anderes Format, dazu ein freies Wunschfeld.
«Prompt: Überarbeiten» oder «Prompt: Austauschen» erzeugt einen kurzen
Auftrag (RST-AUF-…) mit der Aufgabe als JSON und dem Rahmen des Blattes; die
Antwort wird eingefügt und ersetzt genau diese Aufgabe. Wo das Sprachmodell
direkt erreichbar ist, geht das mit einem Klick. Gespeicherte Blätter lassen
sich aus dem Archiv wieder in den Editor öffnen. In der Streamlit-Fassung
liegen dieselben Werkzeuge in einem Aufklapper unter jeder Aufgabe.

## Blätter als PDF oder als Word-Datei

Jedes druckbare Dokument – Übungsblatt mit Mini-Test, Informationsblatt zu
einem Text, Verlaufsbericht fürs Elterngespräch – lässt sich in beiden
Formaten erzeugen. Die Auswahl steht direkt neben dem Knopf, vorbelegt ist
PDF.

| | PDF | Word |
|---|---|---|
| **Wofür** | drucken, kopieren, verschicken | vorher noch ändern |
| **Sieht überall gleich aus** | ja | nein |
| **Aufgabe streichen, Zeile zufügen** | nein | ja |

`pdf_export.py` und `docx_export.py` haben absichtlich **dieselben
Signaturen**. Die Oberfläche wählt nur das Modul und ruft unverändert dieselbe
Funktion auf; ein Test hält das fest. Gesetzt wird mit reportlab, einem reinen
Python-Paket ohne Systemabhängigkeiten – es lässt sich auf einem Lehrerlaptop
ohne Administratorrechte installieren.

Im Artefakt entsteht das PDF ohne fremde Bibliothek: Ein Übungsblatt ist
reiner Text in einer Schrift, die jeder PDF-Betrachter mitbringt. Eine
Bibliothek aus einem fremden Netz nachzuladen hiesse, dass ohne Internet kein
Blatt entsteht und bei jedem Druck ein Zugriff nach draussen geht – in einem
Werkzeug, das ausdrücklich lokal bleiben soll. Die Zeichenbreiten für den
Zeilenumbruch stehen deshalb als Tabelle in `pdfdruck.js`; es ist dieselbe
Metrik, die reportlab benutzt, damit beide Fassungen dasselbe Blatt gleich
setzen.

**Eine Fussangel, die beide Fassungen teilen:** Die eingebauten PDF-Schriften
kennen Umlaute, «Guillemets» und Gedankenstriche, aber keine Pfeile und keine
Aufzählungspunkte. Der Blatttext kommt aus einem Sprachmodell und enthält gern
beides. Ohne Ersatz druckte ein `→` als `fi` – falsch, aber unauffällig, und
im Klassensatz erst nach dem Kopieren zu sehen. Beide Fassungen führen darum
dieselbe Ersetzungstabelle: `→` wird zu `->`, `•` zu `·`, und was danach noch
fehlt, wird zu `?`. Sichtbar falsch ist besser als unsichtbar falsch.

---

## Was «anspruchsvoll» bedeutet

Der Schwierigkeitsgrad hiess früher nur eine Klassenstufe: «7. Klasse»,
«8. Klasse», «9. Klasse». Das reichte nicht. Das Modell baute auf allen drei
Stufen dasselbe Blatt – Lückenwörter mit vorgegebenem Buchstaben, Ankreuzpaare,
Einzelwörter – und tauschte höchstens das Wortmaterial. «Anspruchsvoll» kam als
mittelschwer heraus.

Der Grad sagt jetzt, **was die Aufgabe verlangt**. Drei Hebel unterscheiden die
Stufen, und zwar überprüfbar:

| Hebel | leicht | mittel | anspruchsvoll |
|---|---|---|---|
| **Wortmaterial** | hochfrequenter Grundwortschatz | dazu geläufige Ableitungen und Fremdwörter | mittlere bis geringe Häufigkeit, Fremd- und Lehnwörter, Helvetismen; Primarschulwortschatz verboten |
| **Stützung** | Suchort markiert, Buchstabe in Klammern | höchstens die Hälfte gestützt | Buchstabe nie vorgegeben, höchstens eine markierte Aufgabe je Schwerpunkt |
| **Leistungsart** | wiedererkennen und anwenden | anwenden und begründen | selbst finden, begründen, unter Bedingung produzieren |

Der wirksamste Hebel ist die Stützung. Solange jede Lücke mit `_____` markiert
ist und der einzusetzende Buchstabe daneben steht, bleibt die Aufgabe eine
Ja/Nein-Entscheidung an bekannter Stelle. Wer den Fehler selbst finden muss,
arbeitet eine Stufe höher – bei gleichem Wortmaterial.

Auf der höchsten Stufe kommen vier Vorgaben dazu, die den Unterschied
ausmachen:

* **Fehlersuche statt Lücke.** Mindestens die Hälfte der Aufgaben ist ein
  zusammenhängender Text mit einer genannten Zahl von Fehlern an ungenannter
  Stelle.
* **Distraktoren.** In jedem Fehlersuchtext stehen mindestens drei korrekte,
  aber ungewohnt aussehende Schreibungen (Stängel, aufwendig, Tollpatsch,
  nummerieren, Zierrat, Ass, Tipp). Wer sie «verbessert», macht einen Fehler.
  Das trennt Regelwissen von Rechtschreib-Misstrauen.
* **Begründungspflicht.** Zu jeder Entscheidung gehört das Ableitungswort oder
  die Regel. Eine richtige Schreibung ohne Begründung zählt halb.
* **Fälle, in denen das Hören versagt.** Umlaute, die sich nicht ableiten
  lassen (Eltern, fremd, Held), neben solchen, die es tun (Stängel → Stange).
  Kurze Vokale ohne Verdoppelung, weil schon zwei Mitlaute folgen (Karte,
  Wurst). Und – weil in de-CH die Längenmarkierung fehlt – ss nach kurzem
  Vokal (Fluss, müssen) gegen ss nach langem Vokal oder Diphthong (Fuss,
  heissen) – in der OLFA-Liste beides 07/08/11, in der Förderung F1 gegen F3.

Ankreuzaufgaben sind auf dieser Stufe nur noch als echte Kontrastpaare
zulässig, über die der Satz entscheidet (das/dass, Stadt/statt, Saite/Seite).
Ein Paar wie «trefen / treffen», bei dem eine Form gar kein Wort ist, prüft
nichts.

Für das Diktat greifen dieselben Hebel an einem Fliesstext: Wortwahl,
Satzverschachtelung und eingebaute Zweifelsfälle statt Aufgabenformaten.

---

## Die vierstufige Pipeline (Bereich A)

Die Fehleranalyse folgt dem «Technischen Manual zur algorithmischen
Erkennung» und seiner Ergänzung. Leitsatz: **so viel wie möglich
deterministisch im Code, so wenig wie nötig per Sprachmodell.** Eine
Zuordnung, die bei zwei Durchläufen desselben Textes verschieden ausfällt,
macht das Längsschnittprofil wertlos.

| Stufe | Was passiert | Wer |
|---|---|---|
| 1 | Fehler lokalisieren, Zielform bestimmen. Diktat: Alignment gegen den Referenztext. Freitext: erst Regelprüfungen ohne Modell (ß, frühere Fehlschreibungen), dann Zielwörter aus dem Kontext, Schwelle 0,85, sonst manuelle Kontrolle | Code / Modell (nur Freitext) |
| 2 | Graphemsegmentierung (`sch, ch, ck, tz, ie, ah … ss` als Einheiten), Transposition zuerst, Entscheidungsbaum nach Manual §11 mit CH-Abzweigung A.4, spezifische Kategorien vor generischen, Mehrfachfehler getrennt | Code |
| 3 | Nur Grenzfälle (`needs_context` und die kritischen Paare aus §20): Frage nach dem **entscheidenden Merkmal**, nicht nach der Kategorie; Antwort ausserhalb der Kandidatenliste wird verworfen; blinder Zweitdurchgang ohne Kenntnis des ersten | Modell |
| 4 | Kandidaten, berechnete Konfidenz (nie geschätzt), Status. Führen alle Kandidaten in denselben Förderbereich → `resolved_by_area`, sonst `manual_review` | Code |

Fehlt dem Baum ein Merkmal (Vokallänge eines unmarkierten Wortes, Morphemgrenze,
Lautwert eines v), rät er nicht: Er gibt `needs_context` mit den verbliebenen
Kandidaten aus. Das **Zielwort-Lexikon** liefert diese Merkmale; beim ersten
Auftreten schlägt das Modell den Eintrag vor, die Lehrperson bestätigt – ab
dann ist die Klassifikation für dieses Wort rein deterministisch.

Kontrollen, die keine Rückfrage an das Modell sind: Vollständigkeit (jedes
Wort, jeder Satz hat einen Status – im Code), Halluzinationsfilter (steht die
Originalform wirklich an der Stelle?), Validator nach §17 und A.5, und jede
Zuordnung trägt Begründung, verworfene Alternativen und Merkmalherkunft mit.

`rstrainer/olfa_engine.py` ist der Port der Engine des Artefakts; beide
bestehen dieselben Goldstandard-Tests (Manual §19, Ergänzung A.1, Bau-Prompt
§14 sowie die Beispiele aus §1–§9 und §5.1/5.2 für Wortgrenzen).

### Wie verlässlich ist die Zuordnung?

Massstab ist das **Originalheft OLFA 3–9+** (Thomé/Thomé, 7. Aufl. 2023).
Es wurde vollständig gelesen und in `docs/olfa_original/` protokolliert
(Seitenprotokoll, Spezifikation mit Seitenverweisen, Abgleich, Messwerte,
Abschlussbericht). Alle **181 gedruckten Beispiele** der Seiten 16–28 und
die **92 klassifizierten Fehler des Schülertexts** (S. 48) sind als
Prüfkorpus im Repository (`tests/original_korpus.py`, ohne Volltext). Vor
der Präzisierung stimmten 81 % bzw. 77 %, danach **181/181** und alle 48 Wörter,
die das Original eindeutig entscheidet; die vier übrigen sind im Original
selbst uneindeutig (dokumentiert als W4 und W7 der Spezifikation).

Was sich dabei gegenüber dem technischen Manual geändert hat, mit Seitenzahl:
17/18 nur bei kurzem /ɛ/, langes ä → 34 (S. 22–23); Konsonantersatz am
Wortanfang ist 33, nie 19/20 (S. 18); g für ck sind zwei Fehler 20 + 07
(S. 21, 23); ie für einfaches i bei /iː/ ist 37 (S. 21, 25); g für ng und
ch für sch sind 33 (S. 25); 27/28 nur in -ig/-ich (S. 24–25); vokalisiertes
r nur 29 (S. 24); ß in der Schweiz → 37, 13–16 entfallen (S. 22, 59).

Dazu kommt der frühere Korpus von **289 Grenzfällen** (08/11, 09/10/12,
Silbenrand, Morphemfuge, Fremdwörter, Mehrfachfehler, Wortgrenzen); der
Goldstandard umfasst **291 Wortpaare und 13 Satzpaare**, in Python und im
Artefakt wortgleich, beide 100 %.

Woher die Engine ihre Merkmale nimmt, in dieser Reihenfolge:

| Quelle | Konfidenz | Beispiel |
|---|---|---|
| **Schreibung** – Verdoppelung, Längenzeichen, Diphthong im Zielwort | 0,97 | `komen → kommen`: vor `mm` ist der Vokal kurz |
| **Lexikon** – 560 Wörter, deren Vokallänge, Morphemgrenze, v-Lautwert, Umlautbezug oder Fremdwortstelle nicht in der Schreibung steht | 0,97 | `Kase → Kasse` (kurz, 07/F1) gegen `Fus → Fuss` (lang, 07/F3); `Medchen → Mädchen` (langes ä: 34, nicht 17) |
| **Heuristik** – zwei Faustregeln der deutschen Orthografie | 0,86 | vor `ng` und vor zwei verschiedenen Konsonanten kurz (Hand, Wald); vor einfachem Konsonanten mit folgendem Vokal lang (Name, Tiger) |
| **Keine** – dann `needs_context`, nie geraten | 0,55 | `Tiesch → Tisch`: vor sch ist die Länge nicht lesbar – 37 (Merkwort) oder 12 (kurzes i) bleibt offen |

Die Heuristik gilt ausdrücklich nicht vor r + Konsonant (Karte kurz, Erde
lang), nicht vor ch/sch/x (Fisch kurz, Buch lang) und nicht für die gelisteten
Dehnungen (Obst, Mond, Trost). Dort entscheidet allein das Lexikon, und die
Grenzfallprüfung darf bei Heuristik-Entscheidungen nachfragen.

Drei Festlegungen, die man kennen sollte, weil sie von naiven Lesarten
abweichen:

* **17/18 sind graphemisch definiert.** `Kese → Käse` ist 17, obwohl das ä
  nicht ableitbar ist. Das Lexikon liefert nur die Erklärung («Merkwort»),
  nicht die Entscheidung.
* **Fremdgrapheme sind 37.** Ein Fehler genau an ph, th, rh, y, c oder in der
  Endung -tion (`Fysik`, `Teater`, `Nazion`) ist ein Fremdwortfehler, keine
  Auslassung oder Ersetzung.
* **`Kazze → Katze` ist 07** (Manual §6.1): Die Schärfung ist erkannt, nur das
  Schärfungsgraphem nicht gewählt.

---

## OLFA-Kennwerte: Gruppen, Kompetenz- und Leistungswert

Die Auswertung rechnet die Kennwerte des Originals (S. 29–37) und weist
jeden Schritt mit Seitenzahl aus:

* **Gruppen I / II / III** je Fehler (Kopiervorlage S. 57); 36 und 37 zählen
  nur zur Gesamtfehlerzahl.
* **Fehler auf 100 Wörter** (F/100), **Kompetenzwert** KW = (II % + III %) −
  I %, **tolerierte Fehlerzahl** TF nach Tabelle 5 (Klassenstufe, Zeitpunkt,
  Schulform), **relativer Fehlerwert** RF = F/100 : TF und **Leistungswert**
  LW = (II % + III %) − I % · RF.
* **Deutung** nach den KW-Bändern (über 70, 50–70, 0–50, unter 0; S. 36).
* **Wächter:** unter 350 Wörtern oder 50 Fehlern «vorläufig» (S. 15, 49);
  mehr als 3 % in 37 → Zuordnung prüfen (S. 26); Gruppe I über 50 % →
  lautlicher Grundlagenbereich, ggf. OLFA 1–2 (S. 28, 49); F/100 unter dem
  Zweifachen von TF → OLFA nicht mehr nötig (S. 6, 15).

Klassenstufe und Schulform werden nur für die Rechnung gewählt und nicht
gespeichert. Zwei Rechenfehler des Originals sind dokumentiert und werden
nicht nachgebaut: Der Leistungswert −443 in Abb. 7 setzt TF statt F/100 : TF
ein (nach S. 35 wären es −417), und die dort gedruckten Anteile 66,2 / 7,3 %
sind gegen S. 32 gerundet (Spezifikation W3, W8).

## Förderbereiche F1–F10

Die OLFA-Nummer beantwortet «welche Struktur wurde verletzt», die
Unterrichtsfrage lautet «was üben wir als Nächstes». Dazwischen liegt die
Aggregation auf zehn **Förderbereiche** (Ergänzung B.2) – die eigentliche
Ausgabe. Übersicht, Trend und Übungsblätter arbeiten auf dieser Ebene; die
Nummern bleiben aufklappbar. F9 (Sorgfalt) ist anders zu lesen als F1–F8
(Regelwissen); wächst F10 (Rest), ist das ein Hinweis auf den Classifier,
nicht auf das Kind.

---

## Drei Modi – und ein Umschalter

Es gibt genau drei Modi. Der Modus ist zugleich die Art des gespeicherten
Textes (`diktate.art`):

| Modus | Wer schreibt | Vorlage | Wer bestimmt das Zielwort | Zählt für |
|---|---|---|---|---|
| 📄 **Diktat** (`diktat`) | die Lehrperson diktiert, das Kind schreibt mit der Tastatur | **Umschalter:** *Vorlage aus dem Tool* (auswählbar) **oder** *ohne Vorlage* (anderes Lehrmittel) | mit Vorlage: der Referenztext, per Alignment – ohne Vorlage: Regelprüfungen und das Sprachmodell | Reiter «Geschrieben» |
| 📝 **Freitextmodus** (`freitext`) | das Kind schreibt selbst einen Text mit der Tastatur (Aufsatz, Bericht …) | keine | Regelprüfungen und das Sprachmodell | Reiter «Geschrieben» |
| 🎙️ **Freies Diktat** (`diktiert`) | das Kind diktiert einen eigenen Text mit der Diktierfunktion | keine | Regelprüfungen und das Sprachmodell | Reiter «Diktieren» (eigenes Profil) |

**Der Umschalter beim Diktat.** Ein Diktat *kann* auf einer Vorlage aus dem
Tool beruhen, muss aber nicht – der Text kann aus einem anderen Lehrmittel
stammen, das nicht abgetippt werden soll. Deshalb gibt es beim Diktat genau
eine zusätzliche Frage: *Woher stammt der Diktattext?*

* **Vorlage aus dem Tool** – eine unter *Texte* erstellte Vorlage wird
  ausgewählt. Abgleich exakt und wiederholbar, kein Sprachmodell in Stufe 1.
* **Ohne Vorlage (anderes Lehrmittel)** – nur der Text des Kindes wird
  eingegeben. Objektiv falsch ist trotzdem, was von der – nur nicht
  erfassten – Vorlage abweicht; technisch läuft die Analyse deshalb wie im
  Freitextmodus. Die Wortzahl richtet sich nach dem Text des Kindes. Ein
  solches Diktat zählt ganz normal zur Rechtschreibauswertung.

Ob ein Text eine Vorlage hat, sagt `db.hat_vorlage(...)` (Artefakt:
`hatVorlage`): Art `diktat` und ein nicht leerer Referenztext.

**Warum das Freie Diktat ein eigenes Fehlerprofil hat, aber nicht weniger
geprüft wird.** Mit der Diktierfunktion schreibt das Programm lautgetreu –
klassische Verschreibungen entstehen darüber kaum. Aber Gross-/
Kleinschreibung, Wortgrenzen und Zusammenschreibung bleiben Sache des Kindes
(Autokorrektur, manuelle Korrektur). Die **Rechtschreibprüfung bleibt
deshalb eingeschaltet**, mit demselben Regelwerk wie im Freitextmodus – nur
zählen ihre Ergebnisse nie zu den Kennwerten, Förderbereichen oder
Rechtschreib-Übungsblättern des Reiters «Geschrieben», sondern zum eigenen
Reiter **Diktieren**. Was dort an Grammatik, Satzbau, Zeichensetzung und
Textebene anfällt, wird geübt: Diese Befunde stehen unter *Übungsblätter*
zur Wahl. Die Trennung zieht sich durch:

| Ebene | geschriebene Texte (Diktat, Freitextmodus) | Freies Diktat |
|---|---|---|
| Eingabe | Fehleranalyse → Modus Diktat oder Freitextmodus | Fehleranalyse → Modus Freies Diktat, mit 🎙️ markiert |
| OLFA-Analyse (Bereich A) | ja, Regelwerk | ja, dasselbe Regelwerk – zählt aber zum eigenen Profil |
| Satzbau, Grammatik, Zeichensetzung, Textebene (B–E) | ja | ja |
| Fehler von Hand | alle Bereiche | alle Bereiche |
| OLFA-Kennwerte, Förderbereiche, Verlauf, Trends | nur aus geschriebenen Texten | nie |
| Lernwörter, Empfehlungen, Mischung, Übungsblätter für Rechtschreibung (F1–F10) | nur aus geschriebenen Texten | nie |
| Übungsblätter für Grammatik, Satzbau, Zeichensetzung, Textebene (B–E) | aus allen Texten | ja – die Befunde des Reiters «Diktieren» werden zu Lernstellen |
| Auswertung | Reiter «Geschrieben»: Förderprofil wie bisher | Reiter «Diktieren»: eigenes Fehlerprofil – je Bereich A–E, je Text, nach Kategorie mit Fördern-Hinweisen und jedem Befund im Satz |
| Übersicht je Bereich | Quelle «geschriebene Texte» (Vorgabe) | Quelle «Freie Diktate» oder «beide» – jede Quelle trägt ihre eigenen Bereich-A-Befunde |
| Informationsblatt | «Diktat», «Diktat (ohne Vorlage)» oder «Freitextmodus» | «Freies Diktat (Diktierfunktion)» |

Die Trennung liegt in der Datenschicht: `db.diktat_liste(...,
textart="geschrieben" | "diktiert")` und `db.fehler_liste(..., textart=...)`
liefern die jeweilige Sicht; jede Rechtschreibauswertung fragt ausschliesslich
die geschriebene Sicht ab. Fehler ohne zugeordneten Text zählen als
geschrieben. Im Artefakt übernehmen `texteGeschrieben()`, `fehlerGeschrieben()`
und `fehlerDiktiert()` dieselbe Rolle.

Ältere Datenbestände mit der Zwischen-Textart `freies_diktat` werden beim
Öffnen (Python) bzw. Laden und Importieren (Artefakt) automatisch zu
*Diktat ohne Vorlage* umgeschrieben.

---

## Fehlererfassung

Die Seite *Fehleranalyse* beginnt mit dem **Modus** (drei Karten). Beim
Diktat folgt der Umschalter *Woher stammt der Diktattext?*. Darunter steht
die Textwahl – sie zeigt nur, was zur Wahl passt:

* **Diktat · Vorlage aus dem Tool** – nur die Vorlagen dieses Profils. Neue
  Vorlagen entstehen unter *Texte*; gibt es noch keine, steht ein Hinweis da.
* **Diktat · ohne Vorlage**, **Freitextmodus**, **Freies Diktat** –
  *Neuen Text eingeben* sowie die schon gespeicherten Texte genau dieser Art.
  Ein neuer Text braucht Titel und Text des Kindes; gespeichert wird er mit
  dem gewählten Modus als Textart und ist danach sofort ausgewählt.

Wird ein bestehender Text gewählt, bestimmt er Modus und Umschalter selbst.
Ist ein Text ohne Vorlage im falschen Modus gelandet, lässt er sich unter
*Falsch eingeordnet? Modus dieses Textes ändern* umstellen
(`rstrainer.db.diktat_art_setzen`); ein Diktat mit Vorlage bleibt ein Diktat.

Die Seite *Texte* ist nur noch für **Diktatvorlagen** da (über den
Chat-Prompt oder von Hand) sowie für das Archiv aller Texte.

### Rückmeldung zu jedem Durchgang

Nach jedem Analyse-Durchgang – in allen drei Modi – steht eine kurze,
deterministisch abgeleitete Rückmeldung: **Das ist gut** (Bereiche, die
dieser Durchgang geprüft hat und in denen nichts auffiel) und **Das üben wir
als Nächstes** (die häufigsten Funde dieses Durchgangs, mit Beispiel und der
**Strategie**, mit der das Kind sich selbst kontrollieren kann – bei
Rechtschreibung die des Förderbereichs F1–F10, etwa «Kurzvokal hören,
Verdoppelungsregel anwenden, Verlängerungsprobe», bei B–E der
Fördern-Hinweis des Katalogs, etwa die Frageprobe für den Kasus). Sie
kommt ohne zusätzlichen Aufruf des Sprachmodells aus, weil sie ausschliesslich
auf den bereits klassifizierten Funden dieses einen Durchgangs beruht
(`rstrainer/feedback.py`, im Artefakt `feedbackErstellen`/`feedbackHtml`).

**Klassifiziert wird immer identisch** – von `olfa_engine`, nie vom
Sprachmodell. Ob es eine Vorlage aus dem Tool gibt, entscheidet nur, woher
die Zielform kommt: mit Vorlage aus dem Abgleich, sonst (Diktat ohne
Vorlage, Freitextmodus, Freies Diktat) über den Freitext-Ablauf.

### Diktat mit Vorlage (exakter Abgleich)

Schülertext abtippen, **Abgleich starten**. Die App richtet beide Texte
wortweise aneinander aus, segmentiert graphemorientiert und klassifiziert über
den Entscheidungsbaum: reproduzierbar, mit Begründung und verworfenen
Alternativen je Fehler. Jedes Wort bekommt einen Status (korrekt, Fehler,
ausgelassen, zusätzlich); kein Sprachmodell ist beteiligt.

### Ohne Vorlage: Freitextmodus, Diktat ohne Vorlage, Freies Diktat

Ohne Vorlage muss zuerst feststehen, welches Wort gemeint war. Das ist die
einzige Frage, die das Modell beantwortet – die Kategorie bestimmt es nie.
Fünf Vorkehrungen tragen die Zuverlässigkeit:

**1. Was ohne Modell feststeht, wird ohne Modell gefunden.** In der Schweizer
Zielnorm gibt es kein ß: Jedes ß ist objektiv falsch, die Zielform ergibt sich
mechanisch (`Straße → Strasse`). Und was dieses Kind schon einmal falsch
geschrieben hat, wird beim erneuten Auftreten geprüft – gerade die
wiederkehrenden Fehler tragen das Längsschnittprofil, und genau sie überliest
ein Modell gern, weil sie im Satz unauffällig sind. Diese Funde gelten auch
dann, wenn das Modell gar nicht oder falsch antwortet; ein Regelfund schlägt
jede Modellaussage.

**2. Der Prompt fragt nur nach dem Zielwort – aber erst nach dem Satzsinn.**
Er nennt jedes Wort mit einer Nummer, verbietet Grammatik-, Stil- und
Zeichensetzungskritik ausdrücklich (ohne Vorlage ist die Versuchung gross, zu
viel anzustreichen) und gibt ein festes Vorgehen vor: erst jeden Satz ganz
lesen und seinen Sinn klären, dann Wort für Wort mit Blick auf die
Nachbarwörter prüfen. Er erklärt die Homophone aus dem Satzzusammenhang,
nennt die Stolperstellen, die nur der Satz entscheidet (Nominalisierungen wie
*das Wichtigste*, *nichts Unvorhergesehenes*; Tageszeiten wie *am
Freitagmorgen*, *heute Morgen*, *morgens*; zulässige Doppelschreibungen wie
*sodass/so dass*, die kein Fehler sind) und regelt die Wortgrenzen in beide
Richtungen: `Zahn` + `arzt` → `Zahnarzt` über die Nummernliste, `zumbeispiel`
→ `zum Beispiel` über die Zielform mit Leerzeichen.

**3. Eine Kontextprüfung um das Wort fängt halbe Wortgrenzen ab.** Ein Modell
meldet bei «Am Freitag Morgen» gern nur `Freitag` → `Freitagmorgen`.
Wortweise verglichen sähe das nach einem ganz anderen Wort aus. Ohne Modell
prüft die Engine deshalb, ob benachbarte Wörter desselben Satzes (bis zu drei)
zusammen das Zielwort ergeben – exakt oder mit inneren Fehlern wie `Zahn
artzt` → `Zahnarzt`. Dann wird daraus ein Wortgrenzen-Eintrag über alle
beteiligten Wörter (hier: Getrenntschreibung 04), Teilmeldungen zum selben
Wort fallen weg, und beide Durchgänge meinen dieselbe Stelle
(`olfa_engine.wortgrenzen_reparieren`, im Artefakt `wortgrenzenReparieren`).
Über ein Satzende hinweg wird nie verbunden.

**4. Ein blinder Zweitdurchgang ist möglich und empfohlen.** Derselbe Text in
einem neuen, leeren Chat, anders formuliert, damit die zweite Antwort nicht
die erste abschreibt. Die Sicherheit einer Zielform wird nicht vom Modell
übernommen, sondern berechnet:

| Lage | Sicherheit |
|---|---|
| Regelfund | 1,00 |
| beide Durchgänge einig | die niedrigere der beiden |
| nur ein Durchgang hat es gesehen | höchstens 0,70 |
| gar kein Zweitdurchgang | höchstens 0,80 – ausser das Zielwort ist formgleich |
| Durchgänge uneinig | höchstens 0,60 – unter der Schwelle |

Liegt sie unter 0,85, wird keine präzise Kategorie ausgegeben, sondern der
Fall zur Kontrolle vorgelegt – mit beiden Zielformen.

Der Deckel von 0,80 gilt der *Bestimmung* des Zielworts. Ist das Zielwort
**formgleich** – dieselben Buchstaben, nur Gross-/Kleinschreibung oder
Leerzeichen anders (`wichtigste` → `Wichtigste`, `Freitag Morgen` →
`Freitagmorgen`) –, legt der Text selbst fest, welches Wort gemeint ist. Dann
zählt die Sicherheit, die das Modell selbst angibt. Bei `gescha` → `geschah`
bleibt der Deckel: Da musste ein Wort erst erschlossen werden.

**5. Vollständigkeit wird nicht behauptet.** Kein Wort gilt als geprüft, nur
weil eine Liste vorliegt. Im Freitextmodus steht jedes nicht gemeldete Wort
auf `offen`, und die App schreibt hin, wie viele das sind. Das Diktat mit Vorlage
kennt dagegen den Status jedes Wortes. Dazu kommt der Halluzinationsfilter:
Eine gemeldete Originalform, die nirgends im Text steht, wird verworfen –
eine verzählte Wortnummer dagegen nicht, denn das Wort selbst trifft ein
Modell zuverlässiger als seine Nummer.

### Freie Analyse durch das Sprachmodell

Der zweite Reiter ist der alte Weg und bleibt für das, was die OLFA-Liste
nicht abdeckt: Das Modell benennt die Fehler selbst, auch **Grammatik**, und
legt dafür eigene Fehlerarten an (siehe unten). Für die Rechtschreibung ist
die OLFA-Analyse genauer, weil dort das Regelwerk klassifiziert.

### Von Hand

Für alles, was keiner dieser Wege sieht: Satzzeichen, Silbentrennung am
Zeilenende, unleserliche Stellen.

---

Alle Wege enden in **derselben Bestätigungsliste**: Sie bestätigen jede Zeile
einzeln und ändern die Kategorie, wo nötig – **vorgeschlagen wird, nie
automatisch übernommen**. Unsichere Zeilen sind vorab abgewählt. Eine
Umstufung wird als Muster gespeichert und beim nächsten gleichen Fall
vorgeschlagen.

Beispiele für Zuordnungen der Engine:

| Original | Geschrieben | Zuordnung |
|---|---|---|
| Haus | haus | 01 – Klein- für Grossschreibung |
| kommen | komen | 07 – Einfachschreibung für Konsonantenverdoppelung |
| hat | hatt | 08 – Verdoppelung für Einfachschreibung |
| Zahn | Zan | 09 – markierte Länge fehlt |
| Fuss | Fus | 07 – s für ss (Fördermerkmal F3: nach Langvokal) |
| Preise | Preisse | 11 – Verdoppelung nach Diphthong (F3) |
| Strasse | Straße | 37 – ß gibt es in der Schweiz nicht (13–16 entfallen, «sonst Nr. 37») |
| Hände | Hende | 17 – e für ä bei kurzem /ɛ/ |
| Bären | Beren | 34 – e für langes ä ist Falscher Vokal, nicht 17 |
| Hund | Hunt | 19 – p, t, k für b, d, g |
| Vater | Fater | 23 – f für v |
| wenig | wenich | 27 – ch für g im Silbenende |
| nicht | nich | 29 – Konsonantenzeichen fehlt |
| Schule | Sule | 33 – s für sch: Graphem für Graphem, kein fehlendes Zeichen |
| Garten | Graten | 35 – Zeichenumstellung |
| Bücher | Bucher | 36 – Umlautbezeichnung |

Ein Test prüft jede dieser Zeilen gegen die Engine – das README ist hier eine
Zusage, keine Beschreibung.

---

## Grammatik, Syntax, Zeichensetzung, Textebene: die feste Liste

Die OLFA-Liste deckt die Rechtschreibung ab (Bereich A). Für die Bereiche
B–E gibt es eine zweite **feste, fachlich begründete Liste** mit 33
Kategorien (`data/grammatik_kategorien.json`): schulgrammatische
Standardterminologie, Kommaregeln nach amtlichem Regelwerk, Helvetismen
ausdrücklich zulässig.

| Bereich | Kategorien (Auswahl) |
|---|---|
| **B** Grammatik / Morphologie | Kasus, Präpositionswahl, Genus, Numerus, Kongruenz Subjekt–Verb, Kongruenz in der Nominalgruppe, Artikel, Pronomen, Verbform, Tempus, Modus, Komparation |
| **C** Syntax | Verbstellung im Hauptsatz, Verbstellung im Nebensatz, Satzklammer, Satzfragment, Satzverknüpfung, unklarer Bezug, Satzkomplexität |
| **D** Zeichensetzung | Komma zwischen Haupt- und Nebensatz, in Aufzählungen, bei Einschub und Infinitivgruppe, sonstige Kommafälle, Satzschlusszeichen, direkte Rede, Apostroph |
| **E** Textebene | Wortwahl, Wiederholung, Register, Kohärenz, Kohäsion, Aufbau, Aufgabenerfüllung |

Jede Kategorie trägt Beschreibung, Beispiel und einen Förderhinweis; beides
steht im Analyse-Prompt, damit das Modell die vorhandene Kategorie trifft,
statt eine eigene zu erfinden. Die Kennung folgt dem Muster `B:Kasus`.
Warum fest? Die gelernten Arten (unten) waren beweglich, aber nicht
vergleichbar: Was in einem Text «Kasus» hiess, hiess im nächsten «Fall». Ein
Längsschnitt braucht eine stabile Liste.

### Übersicht je Bereich

Unter *Auswertung* steht über den Förderbereichen eine **Übersicht je
Bereich**: Rechtschreibung, Grammatik, Syntax, Zeichensetzung, Textebene,
jeweils mit der Zahl der Fehler. Ein Bereich zeigt seine Kategorien mit
Anteil und Förderhinweis – und darunter **alle konkreten Fehler des Kindes**
in diesem Bereich: Datum, Text, Geschrieben, Richtig, Kategorie, Satz. Die
Förderbereiche F1–F10 beantworten «Was üben wir?» für die Rechtschreibung;
diese Ansicht beantwortet die Frage davor: Wo liegt das Problem überhaupt?

## Gelernte Fehlerarten

Was in keine der beiden Listen passt, benennt das Sprachmodell selbst und
ordnet es hierarchisch ein:

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
* OLFA spricht bei 19/20 vom **Silbenendrand** (alle Elemente nach dem
  Silbenkern, S. 23) und bei 27/28 vom **Silbenende**. Die Engine prüft: nach
  einem Vokal, vor einem Konsonanten oder am Wortende, nicht am Wort- oder
  Morphemanfang (\*droz → 33, S. 18); 27/28 nur in -ig/-ich (S. 24–25).
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
  ss; die Kategorien 13–16 entfallen (Version CH), ein ß ist Kategorie 37.

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

**Stand: 1255 Tests, alle grün.** Abgedeckt sind:

| Datei | Prüft |
|---|---|
| `test_stress_sek1.py` | Belastungskorpus: 207 realistische Sek-I-Fehler (de-CH) ausserhalb des Goldstandards, mit den Original-Begründungen für die nicht naheliegenden Fälle; Umschriften (ue/ä, kw/qu), ck für g, Getrenntschreibung im Diktat |
| `test_diffing.py` | Wort- und Buchstabenabgleich, Kategorie-Vorschläge, Kennzahlen |
| `test_analysis.py` | Trendeinstufung, Schwellen, Normierung, Empfehlungsreihenfolge |
| `test_docx_export.py` | Gültige .docx, Seitenumbruch Vorder-/Rückseite, keine Lösungen auf der Aufgabenseite |
| `test_pdf_export.py` | Gültige PDF, Seitenfolge, Lösungsblatt nur auf Wunsch, Zeichenersatz für Pfeile und Aufzählungspunkte, gleiche Signaturen wie die Word-Fassung |
| `test_auftraege.py` | Prompt-Aufbau, Auftragsnummern, Zerlegen der Chat-Antwort, Rückfall auf Fliesstext, Anforderungsniveau je Schwierigkeitsgrad |
| `test_validation.py` | Plausibilitätsprüfungen für Diktat und Blatt |
| `test_db.py` | Datentrennung zwischen Profilen, Freigabe, freie Texte, Umhängen über Profile hinweg |
| `test_olfa_und_export.py` | Kategorienliste, unbesetzte Nummern 21/22, Testmodus, CSV/JSON-Export, `.gitignore` |
| `test_charts.py` | Diagramme, feste Farbreihenfolge, Serienbegrenzung |
| `test_olfa_engine.py` | Goldstandard: 291 Wort- und 13 Satzpaare (§19, A.1, Bau-Prompt, Grenzfallkorpus), Graphemsegmentierung, Transposition, Nie-Raten, Konsequenzprüfung C.1, Validator §17/A.5, Konfidenz C.2, Halluzinationsfilter, Umstufungsmuster C.3 |
| `test_blatt.py` | Förderplan (Ebene nach KW, Lernwörter, Umfang), JSON-Aufgaben lesen und in Drucktext wandeln, Prüfung mit der Engine, Bearbeiten/Verschieben/Ersetzen, Teilprompt und Antwort, Rückfall auf das alte Textformat |
| `test_ui_blaetter.py` | Blattseite durchgespielt: Regler → Prompt → JSON-Antwort → Aufgabenkarten → Chip-Prompt → Aufgabe ersetzen → Entfernen → Speichern |
| `test_original.py` | Jedes gedruckte Beispiel des Originals (181) und der Schülertext S. 48 (92 Fehler) durch die Engine; Version CH (ß → 37, 13–16 gesperrt); Wortgrenzen mit Folgefehlern; Out-of-the-box: jedes Beispiel mit vertauschter Gross-/Kleinschreibung und im Trägersatz durch den Diktatmodus |
| `test_olfa_werte.py` | Rechenproben aus dem Original: Abb. 7 (S. 49), Beispiel Olaf (S. 33–35), Tabelle 5 und Formeln (S. 29–30), Zählregel S. 16, Wächter und KW-Bänder S. 36 |
| `test_grammatik.py` | Feste Liste B–E: Vollständigkeit, de-CH-Prosa, Helvetismen, Kennungen, Register, Analyse-Prompt und Rücklesen |
| `test_taxonomie.py` | Pfade begradigen, Dubletten, Gegenteile nicht verschmelzen, Register, Schwerpunkte |
| `test_analyse.py` | Analyse-Prompts, JSON zurücklesen, neue Fehlerarten, Aufräumplan, Regler Klassiker/Sondierung |
| `test_feedback.py` | Rückmeldung «Das ist gut / Das üben wir als Nächstes»: fehlerfreier Durchgang, Bereiche ohne Treffer, Begrenzung der Liste |
| `test_ui_diktiert.py` | Freies Diktat (Diktierfunktion): eigenes Fehlerprofil im Reiter «Diktieren» inkl. Bereich A, Kennwerte nur aus geschriebenen Texten, Infoblatt-Bezeichnung |
| `test_freitext.py` | Freitextmodus: Regelprüfungen ohne Modell, Zielwort-Prompt (erst der Satzsinn, Stolperstellen), blinder Zweitdurchgang und Sicherheitsdeckel, formgleiche Zielwörter, Wortgrenzen samt Kontextprüfung um das Wort («Freitag Morgen»), ehrliche Vollständigkeit, Modusauswahl |
| `test_ui_fehlerseite.py` | Genau drei Modi, Vorlage-Umschalter nur beim Diktat, gefilterte Textwahl, Erfassung direkt auf der Seite, Diktat ohne Vorlage zählt normal, Freies Diktat getrennt, Umordnen |

Zusätzlich wurde die Oberfläche durchgespielt – von Hand im Browser und
kopfrechnend über `streamlit.testing`: Alle sechs Bereiche rendern
fehlerfrei, der komplette Diktat-Ablauf (Prompt erzeugen → Ergebnis einfügen
→ Prüfung → Freigabe → Archiv) läuft durch, und ebenso der Analyse-Ablauf für
einen freien Text (Modus wählen → Prompt → JSON einfügen → Bestätigungsliste →
Übernehmen), inklusive Anlegen einer neuen Fehlerart und Wiederverwenden einer
bestehenden.

**Noch offen / bewusst nicht gebaut:**
* Die Oberfläche ist bis auf `test_ui_fehlerseite.py` nicht automatisiert
  geprüft; sonst wurde sie von Hand und mit Skripten ausserhalb des
  Repositorys durchgespielt.
* Es gibt keine Mehrbenutzer-Funktion und keine Synchronisierung zwischen
  Geräten – bewusst, weil das den Datenschutzaufwand vervielfachen würde.

---

## Projektaufbau

```
app.py                        Einstiegspunkt (Streamlit)
data/olfa_kategorien.json     Die 37 OLFA-Fehlerkategorien (editierbar)
data/grammatik_kategorien.json Feste Liste für Grammatik, Syntax, Zeichensetzung, Textebene
daten/                        Lokale Daten – NICHT im Repository
  rstrainer.sqlite3           Profile, Texte, Fehler, Blätter, Aufträge
  fehlerarten.json            Vom Modell gelernte Fehlerarten
  export/                     CSV, JSON, .docx, Diagramme
rstrainer/
  config.py                   Pfade und fachliche Voreinstellungen
  db.py                       SQLite-Schema und Zugriffe
  olfa.py                     Kategorienliste laden, speichern, abfragen
  olfa_engine.py              Deterministische OLFA-Engine: Grapheme, Baum, Validator, Förderbereiche
  grammatik.py                Feste Kategorienliste B–E laden und beschriften
  taxonomie.py                Gelernte Fehlerarten: anlegen, begradigen, ordnen
  kategorien.py               Gemeinsame Sicht auf beide Kategoriensysteme
  textwerkzeuge.py            Tokenisierung, Normalisierung, Kontext
  diffing.py                  Wort- und Buchstabenabgleich
  analysis.py                 Trendberechnung und Empfehlungslogik
  prompt_templates.py         >> Die Prompt-Vorlagen – zum Anpassen gedacht <<
  auftraege.py                Prompts bauen, Chat-Ergebnis, Analyse und Zielwörter zerlegen
  validation.py               Plausibilitätsprüfungen vor der Freigabe
  docx_export.py              Übungsblatt, Informationsblatt, Verlaufsbericht (Word)
  pdf_export.py               Dieselben Dokumente als PDF, gleiche Signaturen
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
