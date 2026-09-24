# Messwerte: jedes Beispiel des Originals durch die Engine (Stand vor Freigabe, keine Engine-Änderung)

Erzeugt mit `stress/original_lauf.py` aus `tests/original_korpus.py`. «needs_context» = Engine verlangt Kontext (v-Lautwert, Zielwort), kein Fehlurteil. Mehrwortfälle laufen nur durch die Wortgrenzen-Funktion (Harness), nicht durch die Volltext-Pipeline.


## Beispiele S. 16–28: 146/181 übereinstimmend (80.7 %)

| S. | Fehlschreibung | Zielwort | Original | Engine heute | Befund | Anmerkung |
|---|---|---|---|---|---|---|
| 16 | faren | fahren | 09 | 09 | ✓ |  |
| 16 | zusamen | zusammen | 07 | 07 | ✓ |  |
| 16 | feuen | freuen | 29 | 29 | ✓ |  |
| 17 | beser | besser | 07 | 07 | ✓ |  |
| 17 | Starten | Staaten | 09+30 | 09+30 | ✓ |  |
| 17 | sofor | sofort | 29 | 29 | ✓ |  |
| 17 | fertrege | Verträge | 01+23+34 | 01+needs_context+17 | ✗ | 34 nicht 17: langes ä |
| 17 | hund | Hund | 01 | 01 | ✓ |  |
| 17 | Ich | ich | 02 | 02 | ✓ |  |
| 17 | dan | dann | 07 | 07 | ✓ |  |
| 17 | felen | fehlen | 09 | 09 | ✓ |  |
| 17 | jetz | jetzt | 29 | 29 | ✓ |  |
| 17 | hbe | habe | 31 | 31 | ✓ |  |
| 17 | stendik | ständig | 17+19 | 17+19 | ✓ | e für ä bei kurzem /ɛ/; k für g |
| 18 | den | denn | 07 | 07 | ✓ |  |
| 18 | hir | hier | 09 | 09 | ✓ |  |
| 18 | Leker | lecker | 02+07 | 02+07 | ✓ |  |
| 18 | hatt | hat | 08 | 08 | ✓ |  |
| 18 | nich | nicht | 29 | 29 | ✓ |  |
| 18 | ein | einen | 31+29 | 29+31 | ✓ |  |
| 18 | droz | trotz | 33+07 | 20+07 | ✗ | Wortanfang: 33, nicht 20 |
| 18 | geritn | geritten | 07+31 | 07+31 | ✓ |  |
| 19 | sag | Sack | 01+20+07 | 01+33 | ✗ | drei Fehler |
| 20 | haus | Haus | 01 | 01 | ✓ |  |
| 20 | angst | Angst | 01 | 01 | ✓ |  |
| 20 | rufen | Rufen | 01 | 01 | ✓ | das Rufen |
| 20 | Kalt | kalt | 02 | 02 | ✓ |  |
| 20 | Kreisförmig | kreisförmig | 02 | 02 | ✓ |  |
| 20 | MäDchen | Mädchen | 03 | 03 | ✓ |  |
| 20 | LiMonade | Limonade | 03 | 03 | ✓ |  |
| 20 | Zahn Arzt | Zahnarzt | 04 | 04 | ✓ | kein 01 |
| 20 | weg laufen | weglaufen | 04 | 04 | ✓ |  |
| 20 | nach dem | nachdem | 04 | 04 | ✓ |  |
| 20 | Zahn arzt | Zahnarzt | 04+01 | 04+01 | ✓ |  |
| 20 | mit Leid | Mitleid | 04 | 04 | ✓ |  |
| 20 | mit leid | Mitleid | 04+01 | 04+01 | ✓ |  |
| 20 | zumbeispiel | zum Beispiel | 05 | 05 | ✓ |  |
| 20 | blauerfleck | blauer Fleck | 05 | 05 | ✓ |  |
| 20 | sehrviel | sehr viel | 05 | 05 | ✓ |  |
| 20 | ver graben | vergraben | 06 | 06 | ✓ |  |
| 20 | im mer | immer | 06 | 06 | ✓ |  |
| 20 | imer | immer | 07 | 07 | ✓ |  |
| 20 | hate | hatte | 07 | 07 | ✓ |  |
| 20 | wolte | wollte | 07 | 07 | ✓ |  |
| 20 | den | denn | 07 | 07 | ✓ |  |
| 20 | das | dass | 07 | 07 | ✓ |  |
| 21 | dan | dann | 07 | 07 | ✓ |  |
| 21 | wen | wenn | 07 | 07 | ✓ |  |
| 21 | jezt | jetzt | 07 | 07 | ✓ |  |
| 21 | bischen | bisschen | 07 | 29+30 | ✗ |  |
| 21 | zurük | zurück | 07 | 07 | ✓ |  |
| 21 | Sag | Sack | 07+20 | 33 | ✗ |  |
| 21 | Kaze | Katze | 07 | 07 | ✓ |  |
| 21 | paken | packen | 07 | 07 | ✓ |  |
| 21 | kallt | kalt | 08 | 08 | ✓ |  |
| 21 | hatt | hat | 08 | 08 | ✓ |  |
| 21 | dass | das | 08 | 08 | ✓ |  |
| 21 | imm | im | 08 | 08 | ✓ |  |
| 21 | alls | als | 08 | 08 | ✓ |  |
| 21 | beckommen | bekommen | 11 | 11 | ✓ | Morphemanfang |
| 21 | faren | fahren | 09 | 09 | ✓ |  |
| 21 | Har | Haar | 09 | 09 | ✓ |  |
| 21 | Kol | Kohl | 09 | 09 | ✓ |  |
| 21 | Schu | Schuh | 09 | 09 | ✓ |  |
| 21 | libe | liebe | 09 | 09 | ✓ |  |
| 21 | fil | viel | 09+23 | 23+09 | ✓ |  |
| 21 | seen | sehen | 09 | 09 | ✓ |  |
| 21 | ien | ihn | 09 | 37 | ✗ | ie für ih |
| 21 | ungefer | ungefähr | 09+34 | 34 | ✗ |  |
| 21 | dise | diese | 09 | 09 | ✓ |  |
| 21 | wi | wie | 09 | 09 | ✓ |  |
| 22 | frohr | fror | 10 | 10 | ✓ |  |
| 22 | wahr | war | 10 | 10 | ✓ |  |
| 22 | Schuhle | Schule | 10 | 10 | ✓ |  |
| 22 | denn | den | 11 | 08 | ✗ |  |
| 22 | wenn | wen | 11 | 11 | ✓ |  |
| 22 | kamm | kam | 11 | 11 | ✓ |  |
| 22 | hollen | holen | 11 | 11 | ✓ |  |
| 22 | greiffen | greifen | 11 | 11 | ✓ | CH-Hinweis |
| 22 | scharff | scharf | 11 | 11 | ✓ |  |
| 22 | Artzt | Arzt | 11 | 11 | ✓ |  |
| 22 | beckommen | bekommen | 11 | 11 | ✓ |  |
| 22 | geckocht | gekocht | 11 | 11 | ✓ |  |
| 22 | betzahlen | bezahlen | 11 | 11 | ✓ |  |
| 22 | Wiend | Wind | 12 | 12 | ✓ |  |
| 22 | Wahld | Wald | 12 | 12 | ✓ |  |
| 22 | erkähltet | erkältet | 12 | 12 | ✓ |  |
| 22 | Gescheft | Geschäft | 17 | 17 | ✓ |  |
| 22 | Beume | Bäume | 17 | 17 | ✓ |  |
| 23 | Medchen | Mädchen | 34 | 17 | ✗ | langes /ɛː/ → 34, nicht 17 |
| 23 | gefehrlich | gefährlich | 34 | 17 | ✗ | eh für äh → 34 |
| 23 | jätzt | jetzt | 18 | 18 | ✓ |  |
| 23 | Läute | Leute | 18 | 18 | ✓ |  |
| 23 | Korp | Korb | 19 | 19 | ✓ |  |
| 23 | nietlich | niedlich | 19 | 19 | ✓ |  |
| 23 | entlich | endlich | 19 | 19 | ✓ |  |
| 23 | filfabek | vielfarbig | 23+09+29+34+19 | needs_context+09+29+34+19 | ✗ | 5 Fehler |
| 23 | Nortsee | Nordsee | 19 | 19 | ✓ |  |
| 23 | Herpst | Herbst | 19 | 19 | ✓ |  |
| 23 | endscheiden | entscheiden | 20 | 20 | ✓ |  |
| 23 | Gesundheid | Gesundheit | 20 | 20 | ✓ |  |
| 23 | Quarg | Quark | 20 | 20 | ✓ |  |
| 23 | zurüg | zurück | 20+07 | 33 | ✗ |  |
| 23 | schmegte | schmeckte | 20+07 | 33 | ✗ |  |
| 24 | Fogel | Vogel | 23 | 23 | ✓ |  |
| 24 | ferlieren | verlieren | 23 | 23 | ✓ |  |
| 24 | fiele | viele | 23 | needs_context | ✗ |  |
| 24 | for | vor | 23 | 23 | ✓ |  |
| 24 | vertig | fertig | 24 | 24 | ✓ |  |
| 24 | Verne | Ferne | 24 | 24 | ✓ |  |
| 24 | vür | für | 24 | 24 | ✓ |  |
| 24 | Wase | Vase | 25 | 25 | ✓ |  |
| 24 | Wulkan | Vulkan | 25 | 25 | ✓ |  |
| 24 | Prowinz | Provinz | 25 | needs_context | ✗ |  |
| 24 | schvierige | schwierige | 26 | 26 | ✓ |  |
| 24 | vie | wie | 26 | 26 | ✓ |  |
| 24 | lustich | lustig | 27 | 27 | ✓ |  |
| 24 | Honich | Honig | 27 | 27 | ✓ |  |
| 24 | traurich | traurig | 27 | 27 | ✓ |  |
| 24 | Teppig | Teppich | 28 | 28 | ✓ |  |
| 24 | fröhlig | fröhlich | 28 | 28 | ✓ |  |
| 24 | nich | nicht | 29 | 29 | ✓ |  |
| 24 | Käuter | Kräuter | 29 | 29 | ✓ |  |
| 24 | Geburstag | Geburtstag | 29 | 29 | ✓ |  |
| 24 | Blusbruder | Blutsbruder | 29 | 29 | ✓ |  |
| 24 | Mutta | Mutter | 29+34 | 34+29 | ✓ |  |
| 24 | mein | meinen | 29+31 | 29+31 | ✓ |  |
| 24 | aba | aber | 29+34 | 34+29 | ✓ | a für -er |
| 24 | mia | mir | 29 | 37 | ✗ | vokalisiertes r: nur 29 |
| 24 | Tiea | Tier | 29 | 37 | ✗ | nur 29 |
| 24 | Märdchen | Mädchen | 30 | 30 | ✓ |  |
| 24 | artmen | atmen | 30 | 30 | ✓ |  |
| 24 | schwierge | schwierige | 31 | 31 | ✓ |  |
| 24 | mein | meine | 31 | 31 | ✓ |  |
| 24 | grade | gerade | 31 | 31 | ✓ |  |
| 25 | weiel | weil | 32 | 32 | ✓ |  |
| 25 | Kätzichen | Kätzchen | 32 | 32 | ✓ |  |
| 25 | liede | liebe | 33 | 33 | ✓ |  |
| 25 | Klatz | Platz | 33 | 33 | ✓ |  |
| 25 | nienlich | niedlich | 33 | 33 | ✓ |  |
| 25 | kross | gross | 33 | 19 | ✗ | CH-Form von *kroß/groß |
| 25 | gig | ging | 33 | 29 | ✗ | g für ng, nicht 29 |
| 25 | Bug | Buch | 33 | 28 | ✗ |  |
| 25 | Bur | Buch | 33 | 33 | ✓ |  |
| 25 | Könik | König | 33 | 19 | ✗ | Original: 33 (vgl. *stendik S. 17 → 19) |
| 25 | chön | schön | 33 | 29 | ✗ | ch für sch |
| 25 | meinen | meinem | 33 | 33 | ✓ | Grammatik n/m |
| 25 | schönem | schönen | 33 | 33 | ✓ |  |
| 25 | jewals | jeweils | 34 | 34 | ✓ |  |
| 25 | freundlech | freundlich | 34 | 34 | ✓ |  |
| 25 | ungefehr | ungefähr | 34 | 17 | ✗ |  |
| 25 | Mähl | Mehl | 34 | 18 | ✗ |  |
| 25 | Mädchin | Mädchen | 34 | 34 | ✓ |  |
| 25 | dröber | drüber | 34 | 34 | ✓ |  |
| 25 | met | mit | 34 | 34 | ✓ |  |
| 25 | Gesundeiht | Gesundheit | 35 | 35 | ✓ |  |
| 25 | Graten | Garten | 35 | 35 | ✓ |  |
| 25 | fuhrte | führte | 36 | 36 | ✓ |  |
| 25 | gefahrlich | gefährlich | 36 | 36 | ✓ |  |
| 25 | Schtein | Stein | 37 | 30 | ✗ |  |
| 25 | Sahl | Saal | 37 | 37 | ✓ |  |
| 25 | seer | sehr | 37 | 37 | ✓ |  |
| 25 | Garasche | Garage | 37 | 33 | ✗ | FW |
| 25 | Maschiene | Maschine | 37 | 10 | ✗ | FW |
| 25 | wier | wir | 37 | 10 | ✗ | Merkwort |
| 25 | dier | dir | 37 | 10 | ✗ |  |
| 25 | mier | mir | 37 | 10 | ✗ |  |
| 25 | July | Juli | 37 | 37 | ✓ |  |
| 25 | rufte | rief | 37 | 34+30+32 | ✗ | 1 Fehler |
| 26 | Karage | Garage | 33 | 33 | ✓ |  |
| 26 | kreisförmigergarten | kreisförmiger Garten | 05 | 05 | ✓ | kein 01 |
| 26 | Fel | Fell | 07 | 07 | ✓ |  |
| 26 | get | geht | 09 | 09 | ✓ |  |
| 27 | ein | einem | 31+29 | 31+29 | ✓ | Kasus |
| 27 | klein | kleinen | 31+29 | 29+31 | ✓ |  |
| 27 | mein | meinem | 31+29 | 31+29 | ✓ |  |
| 28 | den | dem | 33 | 33 | ✓ | Version 2: n-m |
| 22 | daß | dass | 37 | 33 | ✗ | CH: ß-Fehler → 37 (DE: 16) |
| 22 | mußten | mussten | 37 | 33 | ✗ | CH → 37 (DE: 16) |
| 22 | laß | las | 37 | 33 | ✗ | CH → 37 (DE: 14) |
| 22 | meißtens | meistens | 37 | 33 | ✗ | CH → 37 (DE: 14) |

## Schülertext S. 48: 40/52 übereinstimmend (76.9 %)

| S. | Fehlschreibung | Zielwort | Original | Engine heute | Befund | Anmerkung |
|---|---|---|---|---|---|---|
| 48 | un | um | 33 | 33 | ✓ | Z1 |
| 48 | nich | nicht | 29 | 29 | ✓ | Z1 |
| 48 | Luisch | Luis | 30 | 30 | ✓ | Z2 |
| 48 | Millderder | Milliardär | 31+34+37 | 37+34+17 | ✗ | Z2 |
| 48 | stad | stand | 29 | 29 | ✓ | Z2 |
| 48 | ein | einem | 31+29 | 31+29 | ✓ | Z3 |
| 48 | Prais | Paris | 35 | 31+34 | ✗ | Z3 |
| 48 | Sei | Seine | 29+31 | 29+31 | ✓ | Z3 |
| 48 | zweihunder | zweihundert | 29 | 29 | ✓ | Z3 |
| 48 | Bodigatz | Bodyguards | 37+37+29+37 | 37+31+29+29+33 | ✗ | Z3; tz auch als ts |
| 48 | weg | Weg | 01 | 01 | ✓ | Z4 |
| 48 | Reichste | reichste | 02 | 02 | ✓ | Z5 |
| 48 | Menschen | Mensch | 32+30 | 32+30 | ✓ | Z5 |
| 48 | Jarhuderts | Jahrhunderts | 09+29 | 09+29 | ✓ | Z6 |
| 48 | das | dass | 07 | 07 | ✓ | Z7 |
| 48 | seihn | seinen | 10+31+29 | 33+31 | ✗ | Z7 |
| 48 | Fergungungspag | Vergnügungspark | 23+29+36+30+29+29+20 | needs_context+29+36+30+29+20 | ✗ | Z7/8 |
| 48 | gansen | ganzen | 33 | 33 | ✓ | Z8; s auch als z |
| 48 | Vereinchen | Vereinigten | 31+27+29 | 31+29+33 | ✗ | Z8 |
| 48 | Starten | Staaten | 09+30 | 09+30 | ✓ | Z8 |
| 48 | nich | nicht | 29 | 29 | ✓ | Z9 |
| 48 | als | alles | 07+31 | 07+31 | ✓ | Z9 |
| 48 | ein | eine | 31 | 31 | ✓ | Z10 |
| 48 | Welt reise | Weltreise | 04+01 | 04+01 | ✓ | Z10 |
| 48 | Lander | Länder | 36 | 36 | ✓ | Z10 |
| 48 | ein | einen | 31+29 | 29+31 | ✓ | Z11 |
| 48 | geeignten | geeigneten | 31 | 31 | ✓ | Z11 |
| 48 | seine | sein | 32 | 32 | ✓ | Z11 |
| 48 | Epermntlarbor | Experimentallabor | 29+31+31+30 | 29+31+31+31+07+30 | ✗ | Z12; Original zählt 4 |
| 48 | sachen | Sachen | 01 | 01 | ✓ | Z12 |
| 48 | stig | stieg | 09 | 09 | ✓ | Z13 |
| 48 | Fliger | Flieger | 09 | 09 | ✓ | Z13 |
| 48 | im | ihm | 09 | 09 | ✓ | Z14 |
| 48 | ubrings | übrigens | 36+33+31+29 | 36+29+31+30 | ✗ | Z14 |
| 48 | grade | gerade | 31 | 31 | ✓ | Z15 |
| 48 | rein gehen | Reingehen | 01+04 | 04+01 | ✓ | Z15 |
| 48 | beser | besser | 07 | 07 | ✓ | Z16 |
| 48 | wurde | würde | 36 | 36 | ✓ | Z19 |
| 48 | Bugermeiter | Bürgermeister | 36+29+29 | 36+29+29 | ✓ | Z19 |
| 48 | Gesprech | Gespräch | 34 | 17 | ✗ | Z20 |
| 48 | vürte | führte | 24+09 | 24+09 | ✓ | Z20 |
| 48 | etwar | etwa | 30 | 30 | ✓ | Z20 |
| 48 | sofor | sofort | 29 | 29 | ✓ | Z21 |
| 48 | garnich | gar nicht | 05+29 | 05 | ✗ | Z22 |
| 48 | weiter Reisen | weiterreisen | 04+02 | 04 | ✗ | Z22 |
| 48 | gefuden | gefunden | 29 | 29 | ✓ | Z23 |
| 48 | fertrege | Verträge | 01+23+34 | 01+needs_context+17 | ✗ | Z23 |
| 48 | Italienan | Italienern | 34+29 | 34+29 | ✓ | Z24 |
| 48 | für | führen | 09+31+29 | 09+31+29 | ✓ | Z24 |
| 48 | koste | kostet | 29 | 29 | ✓ | Z25; Ziel kostet(e), alternativ 31 |
| 48 | Larbor | Labor | 30 | 30 | ✓ | Z26 |
| 48 | erfolg | Erfolg | 01 | 01 | ✓ | Z26 |
