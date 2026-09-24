# Abschlussbericht: Präzisierung nach dem Original OLFA 3–9+ (Schritt 5)

Stand: 24.09.2026. Grundlage: vollständige Lektüre des Originals (57 PDF-Seiten,
`protokoll_seiten.md`), Spezifikation (`spezifikation_olfa_3_9.md`), Abgleich
(`abgleich.md`) und die Freigabe der Lehrperson: **Version CH gilt** (13–16
entfallen, ß → 37), **\*Könik → 19**, keine Volltext-Fixture des Schülertexts.

## 1 Ergebnis in Zahlen

| Prüfung | vorher | nachher |
|---|---|---|
| Gedruckte Einzelbeispiele S. 16–28 (181) | 146 (80,7 %) | **181 (100 %)** |
| Schülertext S. 48, 52 Wörter / 92 Fehler | 40 Wörter (76,9 %) | **48 Wörter**; die 4 übrigen sind im Original selbst uneindeutig (W4, W7) oder Fremdwort-Mehrfachfehler und werden nur auf Plausibilität geprüft |
| Goldstandard Wortpaare / Satzpaare | 291 / 13 | 291 / 13 (Erwartungen an 33 Stellen auf das Original korrigiert) |
| Python-Tests | 735 | **997**, alle grün |
| JS-Engine gegen Python (233 Korpusfälle) | – | **233 gleich** (Kategorie und Förderbereich) |
| jsdom-Smokes (UI, Freitext, leer, PDF, Übersicht, Kennwerte) | 5 | 6, alle ohne Fensterfehler |

## 2 Umgesetzte Regeln (Nummern aus `abgleich.md`)

| Nr | Regel | Umsetzung | Seite |
|---|---|---|---|
| R1 | 17/18 nur bei kurzem /ɛ/; langes ä/äh → 34; e für äh = 09 + 34 | `vokalersatz` prüft die Vokallänge des Ziels; Markerteil als Zusatzereignis | 17, 21–23, 25 |
| R2 | Konsonantersatz am Wort-/Morphemanfang = 33 | `am_silbenrand` schliesst Index 0 und Morphemanfänge aus | 18, 25 |
| R3 | g/d/b für ck/tt/pp = 20 + 07 | zwei Ereignisse in `klassifiziere_op` | 19, 21, 23 |
| R4 | ng/g, sch/ch = Verwechslung 33 | Teilgraphem-Zerlegung entfernt; Verwandtschaft im Alignment | 25, 48 |
| R5 | sch für s vor t/p am Anlaut = 37; sonst ch zugefügt 30 | `konsonantersatz` | 25, 48 |
| R6 | ie für einfaches i bei /iː/ = 37, bei kurzem i 12 | `markierung_zuviel` | 21, 25 |
| R7 | h nach Vokal/Diphthong zugefügt = 10/12 | `graphem_zuviel` mit Kontext; h nie ersetzt (Alignment) | 48 |
| R8 | ie für ih = 09; ih für ie = 10 | `vokalersatz` | 21 |
| R9 | vokalisiertes r (\*mia) = nur 29 | `_vokalisiertes_r` | 24 |
| R10 | 27/28 nur nach <i> (-ig/-ich) | `konsonantersatz` | 24–25, 48 |
| R11 | Fremdwortstellen (\*Garasche) = 37 | Lexikonfeld `fremd` (Zeichenposition) | 25–26 |
| R12 | falsche Wortform = ein Fehler 37 | `formfehler`-Option; Zielwortliste darf `formfehler` setzen | 25 |
| R13/R14 | Buchstaben statt Grapheme (\*Prais, \*bischen) | Segmentierungsvarianten, wenigste Operationen gewinnt | 21, 48 |
| R18 | Verbkompositum mit grossem Teil = 04 + 02; 01 nur einmal, am Kopf | `wortgrenzen_ergebnis` | 20, 48 |
| R19 | 05 mit inneren Fehlern (\*garnich) | `zusammenschreibung_ergebnis`, in beiden Pipelines | 48 |
| R20/R21 | Lexikon: den/dem/wen/wem lang, Gespräch, Käse; v = /f/ in Erbwörtern | `VOKALLAENGEN`, `v_lautwert` mit Standardannahme | 21–24 |
| R22 | Alignment-Gleichstand: Ersetzung an gleicher Position | Positionsstrafe 0,01 | 48 |
| R23 | **Version CH**: 13–16 gesperrt, ß → 37; s für ss = 07, ss für s = 08/11; F3 als Fördermerkmal | `NEVER_ASSIGN`, `eszett_ereignis`, `f3`-Flag, `foerderbereich` | 22, 59 |
| R24 | \*Könik → 19 (Entscheid) | unverändert, im Korpus dokumentiert (W1) | 17, 25 |
| R25 | Gruppen I–III, KW, F/100, TF, RF, LW, Deutung | `GRUPPEN` in Engine und JSON; Modul `olfa_werte.py` / `olfa_werte.js`; Auswertungsseite und Artefakt | 29–37, 57 |
| R26 | Zählregel Wörter | `olfa_werte.woerter_zaehlen` (Zahlen, Einzelbuchstaben nicht) | 16, 47 |
| R30 | 36/37 nur in Gesamtfehler und F/100 | `berechnen` | 25–26, 31 |
| §3 | Wächter: Textmenge, 37 > 3 %, Gruppe I dominant, F/100 < 2·TF | `olfa_werte.warnungen` | 6, 15, 26, 28, 49 |

Nicht umgesetzt (bewusst): R28 Version-2-Fehlerwortmarker – die Auswertung
zeigt die konkreten Fehlwörter je Kategorie bereits in der Bereichsübersicht,
ein zusätzliches Markerfeld brächte keine neue Information; kann bei Bedarf
nachgerüstet werden.

## 3 Kontrollen über den Prompt hinaus

1. **Rechenproben des Originals als Tests**: Abb. 7 (188 Wörter, 92 Fehler, 55/22/6, F/100 48,9) und Beispiel Olaf (125/523, KW 54, RF 3,3, LW 1,1) in `tests/test_olfa_werte.py`. Dabei zwei Rechenfehler des Originals gefunden und dokumentiert (W3: LW −443 mit RF = TF; W8: Anteile 66,2/7,3 gegen S. 32 gerundet, KW −32 statt −33). Das Tool folgt den Formeln und zeigt den Rechenweg mit Seitenzahl.
2. **Innere Widersprüche des Originals** protokolliert (W1–W8), je mit Entscheid.
3. **Out-of-the-box-Tests**: jedes Beispiel mit vertauschter Gross-/Kleinschreibung (Graphemzuordnung unverändert) und jedes Beispiel im Trägersatz durch den Diktatmodus.
4. **Wortgleichheit** Python ↔ JS über alle 233 Korpusfälle geprüft (Kategorie und Förderbereich).
5. **Nie raten** verschärft: 17/18 und ie/i ohne bekannte Vokallänge bleiben `needs_context`; ein <h> nach Vokal wird nie gegen einen Buchstaben getauscht.
6. **Altbestand**: frühere 13/15-Einträge werden beim Laden auf 07/11 gehoben, nicht auf 37.

## 4 Offen / Hinweise für die Lehrperson

- Der Schülertext S. 48 ist nur als Wortpaare hinterlegt (kein Volltext), wie gewünscht.
- Bei sehr kurzen Texten kennzeichnet die Auswertung KW/LW als vorläufig (S. 15, 49); für belastbare Werte mehrere Texte zusammenfassen.
- Für Fremdwörter mit abweichender Schreibstelle (Garage, Orange …) trägt das Lexikon die Position; neue Fremdwörter können über das Zielwort-Lexikon ergänzt werden.
