# Abgleich: Original OLFA 3–9+ (2023) ↔ technisches Manual / Ergänzung ↔ Engine

Stand bei Erstellung: **vor** jeder Engine-Änderung; Ergebnis nach Umsetzung siehe `abschlussbericht.md`. Messgrundlage: `abgleich_messwerte.md` (jedes gedruckte
Beispiel durch die Engine). Ergebnis heute: **Einzelbeispiele 146/181 (80,7 %)**,
**Schülertext S. 48: 40/52 Wörter (76,9 %)**. Ziel nach Umsetzung: 100 % bei allen Fällen, die
das Original eindeutig entscheidet; Widersprüche des Originals (W1–W6 in der Spezifikation §8)
werden als dokumentierte Auslegung behandelt.

Legende Befund: **A** = Engine weicht vom Original ab (Regel fehlt oder ist falsch);
**L** = nur Lexikon/Daten fehlen; **H** = Harness/Pipeline, nicht die Wortengine;
**E** = Entscheidung durch Lehrperson nötig; **✓** = übereinstimmend.

## 1 Regelabgleich

| Nr | Regel laut Original | Seite | Techn. Manual / Ergänzung | Engine heute | Befund | Vorschlag | Förderbereich |
|---|---|---|---|---|---|---|---|
| R1 | 17/18 gelten **nur bei kurzem /ɛ/**; e/eh für langes ä/äh → 34; äh für eh → 34; eu↔äu ohne Längenbedingung → 17/18 | 17, 22–23, 25 | Manual 7.2: «e↔ä → zuerst 17/18 prüfen» ohne Längenbedingung | e→ä immer 17, ä→e immer 18 (\*Medchen, \*Gesprech, \*fertrege, \*gefehrlich, \*ungefehr, \*Mähl falsch) | **A** | 17/18 nur, wenn der Zielvokal kurz ist (Lexikon/Heuristik); bei langem ä/äh, eh → 34; e für äh = 09 + 34 (\*ungefer S. 21); eh für äh = 34 (\*gefehrlich); äh für eh = 34 (\*Mähl). Unbekannte Länge → needs_context statt 17 | F4 / F10 |
| R2 | Konsonantersatz am **Wortanfang** ist 33, nie 19/20 (\*droz, \*kross/\*kroß) | 18, 25 | Manual 7.3 nennt nur Silbenendrand-Beispiele | `am_silbenrand` liefert an Position 0 True → 20/19 | **A** | Index 0 (und Morphemanfang) explizit vom Silbenendrand ausschliessen | F5 → F10 |
| R3 | Stimmhaftes Einzelzeichen für stimmloses **Doppelgraphem** = **zwei Fehler**: \*Sag/\*zurüg/\*schmegte = 20 + 07; \*pag für park = 29 + 20 | 19, 21, 23, 48 | Manual: Mehrfachfehler-Kapitel 10 allgemein, Fall nicht genannt | g→ck als ein Ereignis 33 | **A** | Substitution g/d/b ↔ ck/tt/pp (und tz? nein: z für tz = 07 allein, S. 21) in zwei Ereignisse zerlegen: 20 (Stimmhaftigkeit) + 07 (Einfachschreibung) | F5 + F1 |
| R4 | g für ng = 33 «nicht Nr. 29»; ch für sch = 33; ng für g = 33 (\*ubrings) | 25, 48 | Manual: keine Aussage zu Teilgraphemen | `teilgraphem()` wertet ng→g / sch→ch als «Graphem fehlt» 29 bzw. zugefügt 30 | **A** | Teilgraphem-Abgleich abschaffen: Mehrgraphem ↔ Einzelgraphem = Substitution 33 (Konsonant) / 34 (Vokal); Alignment-Kosten für ng/g, sch/ch, ch/g als «verwandt» (0,9), damit die Substitution gewählt wird | F10 |
| R5 | **s vor t/p als sch** (\*Schtein) = 37 | 25 | – | 30 (ch zugefügt) | **A** | sch für s vor t/p am Wort-/Morphemanfang → 37 (lautgetreue Schreibung, keine Kategorie 01–36) | F10 |
| R6 | **ie für i in Merkwörtern/Fremdwörtern** (\*wier, \*dier, \*mier, \*Maschiene, Tiger, Igel, Biber, Bison, Vornamen) = 37; 10 nur für zugefügtes Dehnungs-h | 21, 25, 47 | Manual 6.4: «zusätzliche Längenmarkierung, Zielvokal lang → 10» (ohne Ausnahme) | ie→i bei langem i = 10 | **A** | ie für i bei langem /iː/ → 37 mit Begründung «Ausnahmeschreibung/Merkwort»; ie für kurzes i bleibt 12; zugefügtes h bleibt 10/12 | F2 → F10 |
| R7 | **h zugefügt nach Diphthong** (\*seihn) = 10 | 48 | Manual 6.4 | 33 (h als Konsonantersatz) | **A** | eingefügtes h nach Vokal/Diphthong vor Konsonant oder Wortende → 10 (lang) / 12 (kurz) | F2 |
| R8 | ie für ih (\*ien für ihn) = 09; e für eh (\*get, \*seen) = 09 | 21, 26 | Manual 6.3 (09 vs 31) | ie→ih = 37 | **A** | ie ↔ ih als Längenmarker-Paar behandeln: ie für ih → 09, ih für ie → 10 (abgeleitet, im Original nicht gedruckt) | F2 |
| R9 | **Vokalisiertes r**: \*mia für mir, \*Tiea für Tier = nur 29 (a nicht als 32); \*aba für aber = 29 + 34 | 24 | – | \*mia/\*Tiea → 37 | **A** | a (oder e) an Stelle eines postvokalischen r → ein Ereignis 29 mit Vermerk «vokalisiertes r»; \*aba bereits korrekt (29 + 34) | F9 |
| R10 | 27/28 nur für die **-ig/-ich-Alternation** (alle Beispiele -ig, -ich, -lich; \*Vereinchen für Vereinigten = 27); \*Bug für Buch = 33 | 24, 25, 48 | Manual: «Spezifischer g/ch-Fall am Silbenende» ohne Einschränkung | ch↔g überall im Silbenende = 27/28 (\*Bug → 28) ; \*Vereinchen → 33 (Alignment) | **A** | 27/28 nur, wenn das g/ch auf <i> folgt (ich-Laut); sonst 33; Alignment ch~g als verwandt (siehe R4) | F5 / F10 |
| R11 | **Fremdwörter**: 37 nur an Stellen, die von deutscher Orthographie abweichen (\*Garasche 37, \*Karage 33; \*Bodigatz 37/37/29/37; \*July 37) | 25–26, 48 | Manual 37: «Garasche → Garage; nur echte Auffangkategorie» | FREMDGRAPHEME {ph, th, rh, y, c} → 37; g=/ʒ/ nicht erkannt → \*Garasche 33 | **A/L** | Lexikon-Feld `fremd` mit Positionen (Garage: g₂=/ʒ/; Maschine: i=/iː/ ohne ie); Ersatz an markierter Stelle → 37; sonst 01–36 | F10 |
| R12 | **Falsche Wortform** (\*rufte für rief) = **ein** Fehler 37 | 25 | – | 34 + 30 + 32 | **A** | Wortform-Fehler (Tempus/Flexion) als ein Ereignis 37 mit Grammatik-Querverweis (B:Tempus); Erkennung: Zielwort-Stufe liefert `formfehler`, offline Heuristik für schwache Formen starker Verben (-te an Präsensstamm) | F10 + Grammatik |
| R13 | **Zeichenumstellung** über Diphthonggrenzen (\*Prais für Paris) = 35 | 48 | Manual 9.3 (Graten) | 31 + 34 (ai als ein Graphem) | **A** | wie `_vokalpaar_auftrennen`: alternative Segmentierung prüfen, wenn sie eine Transposition ergibt | F9 |
| R14 | **sch im Schülerwort gegen ss+ch / s+ch im Ziel** (\*bischen für bisschen) = 07 | 21 | – | 29 + 30 (sch als ein Graphem gegen ss, ch) | **A** | Segmentierung des Schülerworts an Zielgrenzen ausrichten (sch → s+ch, wenn das Ziel s/ss + ch hat) | F1 |
| R15 | **Kasus-/Grammatikfehler** deskriptiv: \*ein für einem = 31 + 29; n für m = 33 (Version 2: n-m, m-n) | 24–25, 27–28 | Manual 13 | ✓ (\*ein 31+29, \*meinen 33) | ✓ | zusätzlich Querverweis Grammatik B:Kasus im Ereignis (schon vorgesehen) | F9 / Grammatik |
| R16 | \*das/dass: 07 bzw. 08, grammatisch bedingt, nie 13–16 | 21, 26 | ✓ | ✓ | ✓ | – | F1 |
| R17 | \*kreisförmigergarten → nur 05; \*Fel → 07; \*get → 09; Wortfuge fehlt → 29 | 21, 26 | ✓ | ✓ | ✓ | – | – |
| R18 | Getrenntes Kompositum: Nomenteil gross = kein 01; klein = +01; **Verbteil gross = +02** (\*weiter Reisen 04 + 02) | 20, 48 | Manual §5.1 (Nomenfall) | \*Zahn Arzt ✓, \*Zahn arzt ✓, \*Welt reise ✓; \*weiter Reisen nur 04 | **A** | Wortart des Ziels: Ziel klein geschrieben (Verb/Adverb) und Teil gross → 02 | F7 + F6 |
| R19 | Zusammenschreibung mit innerem Fehler: \*garnich → 05 + 29 | 48 | – | Pipeline erzeugt nur 05 | **H/A** | nach dem 05-Ereignis die Teile einzeln gegen die Zielwörter klassifizieren | F7 + F9 |
| R20 | **11 nach Langvokal**: \*denn für den = 11 | 22 | ✓ | 08, weil Lexikon «den/dem» als **kurz** führt | **L** | Lexikon korrigieren: den, dem, wen, wem = lang; Lexikon gegen Original-Beispiele prüfen (S. 21–22 Wörter) | F1 |
| R21 | v = /f/ in Erbwörtern (viel, viele, vier, vor, ver-, Vogel, Verträge) | 21, 24 | Manual 23–26 | ohne Lexikoneintrag needs_context (\*fiele, \*Ferg-, \*fertrege) | **L** | Standardannahme v=/f/ für ver-/vor-/viel-/voll- und Wörter des Grundwortschatzes; /v/ nur bei Lexikon-Markierung (Vase, Vulkan, Provinz, Klavier, Villa …) | F8 |
| R22 | **Alignment-Gleichstand**: \*ubrings (ng↔g, e, n fehlen) und \*Vereinchen (ch↔g, i, t fehlen) | 48 | – | wählt Löschung + spätere Substitution | **A** | Bei gleichen Kosten Substitution gleicher Position vor Löschung bevorzugen (deterministischer Tie-Break) | F9 |
| R23 | **ß in de-CH**: Original «13–16 entfallen, sonst Nr. 37» | 22, 59 | Ergänzung A.3: 13 = s für ss, 15 = ss für s; ß → 33 (Konsonantersatz) | 13/15 CH-Neubelegung, ß → 33 | **E** | Zwei Lesarten, Entscheidung in §2. Empfehlung: Kategorie nach Original (13–16 gesperrt, ß → 37, s/ss nach 07/08/11), Förderbereich F3 als Zusatzmerkmal | F1 / F3 |
| R24 | \*Könik für König: 33 (S. 25) vs. \*stendik: 19 (S. 17) | 17, 25 | Manual 7.3: 19 | 19 | **E** | Deutschschweizer Aussprache -ig = [ɪk] → k für g ist echte Auslautverhärtung → **19 beibehalten** (mit W1-Vermerk) | F5 |
| R25 | Gruppen I–III, KW, LW, RF, F/100, TF (Tabelle 5) | 29–35, 57 | Manual: nicht enthalten | Kategorienliste: `gruppe` = null bei allen 37; keine KW/LW/F-100-Berechnung | **A** (fehlt) | Gruppen aus S. 57 in `olfa_kategorien.json`; Auswertungsseite: Fehlersummen je Gruppe, %, KW, F/100, TF nach Klasse/Schultyp (Tabelle 5), RF, LW, KW-Band (S. 36), Warnungen (< 350 Wörter / < 50 Fehler; 37 > 3 %; Gruppe I dominant → OLFA 1–2) | – |
| R26 | Zählregeln: Zahlen/Einzelbuchstaben keine Wörter; getrenntes Kompositum ein Wort; Wiederholungen zählen, ggf. zweite Rechnung ohne Wiederholungen | 16, 19, 47 | – | `tokenisiere` zählt `\d+` als Token | **A** | Wortzählung nach Original; Doppelrechnung «ohne Wiederholungen» als Option | – |
| R27 | Punkt + Kleinschreibung → 01; Zeichensetzung sonst nicht | 26 | Manual §5 | Satzanfang klein wird als 01 geführt ✓ | ✓ | – | F6 |
| R28 | Version 2 Fehlerwörter (dass/dann/denn/wenn/…; -en; r; n-m …) | 28, 58 | – | nicht vorhanden | **A** (fehlt) | Marker als Zusatzfeld je Ereignis; Auswertung «Version 2» | F1/F9 |
| R29 | Mehrere Fehler pro Wort einzeln zählen; \*filfabek = 5 | 19, 23 | ✓ | ✓ (5 Ereignisse) | ✓ | – | – |
| R30 | 36/37 nicht in KW, aber in Gesamtfehler und F/100 | 25–26, 31 | Manual: – | – (keine Berechnung) | siehe R25 | – | – |

## 2 Entscheidung Lehrperson: ß und s/ss in de-CH (R23)

**Lesart Original (S. 22, 59):** 13–16 entfallen; taucht ein ß auf (zugewanderte Schüler), → 37.
Für s/ss-Fehler in Schweizer Zielschreibung gibt das Original keine eigene Kategorie: \*Fus für Fuss
ist nach dem Wortlaut von 07 («s für ss») ein 07-Fehler, \*Grüsse für Grüsse ist korrekt.
Die Vokallänge spielt dabei keine Rolle.

**Lesart Ergänzung A.3 (heutiger Stand des Tools):** 13 = s für ss nach Langvokal/Diphthong,
15 = ss für s nach Langvokal/Diphthong, 14/16 gesperrt, ß → 33. Vorteil: Förderbereich F3
(Merkwortschatz Fuss, Strasse, gross) bleibt von F1 (Schärfung) unterscheidbar.

**Empfehlung:** Original als Norm, Ergänzung als *Auswertungs-Zusatz*: Kategorie nach Original
(07/08/11 bzw. 37), zusätzlich Förderbereich F3, wenn die s/ss-Stelle nach Langvokal/Diphthong
steht. Damit bleiben Liste und KW mit dem Original vergleichbar, und die Förderdiagnose behält
die CH-Differenzierung. Das ändert die Gruppenzuordnung: bisherige 13-CH-Fälle zählen als 07
(Gruppe II), bisherige 15-CH-Fälle als 08 bzw. 11 (III bzw. I).

## 3 Über den Prompt hinaus: zusätzliche Kontrollen

1. **End-zu-End-Test Schülertext S. 48**: 52 Wortpaare, 92 Fehler, Sollsummen Abb. 7 (I/II/III 55/22/6, 36: 5, 37: 4, KW −32, F/100 48,9 bei 188 Wörtern) als Test der gesamten Berechnungskette, inkl. der dokumentierten 30/33-Abweichung (W2).
2. **Beispiel-Zähl-Checksummen je Seite** (`tests/original_korpus.py`): 181 Einzelfälle mit Seitenzahl – jeder Fall bleibt auf das Original rückführbar.
3. **Rechenprobe Olaf (S. 33–35)**: 125/523 → 23,9; KW 54; RF 3,3; LW 1,1 als Unit-Test der Formeln.
4. **Nie-Raten-Regel verschärft**: 17/18 und 10 dürfen ohne bekannte Vokallänge nicht «resolved» sein (needs_context).
5. **37-Quote-Wächter**: > 3 % der Fehler in 37 → Hinweis «Zuordnung überprüfen» (S. 26).
6. **Textmengen-Wächter**: unter 350 Wörtern oder 50 Fehlern → KW/LW als «vorläufig» kennzeichnen (S. 15, 49).
7. **Wiederholungsfehler**: Endrechnung wahlweise mit und ohne Wiederholungen (S. 19).
8. **Gruppe I dominant** (> 50 %) → Hinweis auf OLFA 1–2 (S. 28) und Vokalquantität (S. 36).
9. **Blindtest in beide Richtungen**: jedes Original-Beispiel zusätzlich mit vertauschter Gross-/Kleinschreibung und in einem Trägersatz durch die Volltext-Pipeline (Diktat- und Freitextmodus).

## 4 Vorgehen nach Freigabe (Schritt 4)

Reihenfolge: R20/R21 (Lexikon) → R2, R4, R22, R13, R14 (Alignment/Segmentierung) → R1, R6, R7, R8 (Vokallänge/Marker) → R3, R5, R9, R10, R11, R12 (Spezialregeln) → R18, R19 (Wortgrenzen) → R25, R26, R28, R30 (Auswertung, Gruppen, Zählung) → JS-Engine wortgleich nachziehen → alle Tests (735 bestehend + Original-Korpus + Schülertext + Rechenproben) → README.
