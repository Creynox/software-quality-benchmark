# NSN014 Punktebericht

Spezifikation NSN014-REPORT-SPEC 1.3.0 (SHA256 d2b2b7608a61833a9dc77aceb1c176a7ca6733bccf97ded5951d5b7345931c6b). Der Bericht entsteht allein aus gemessenen Ergebnissen, ohne Freitext und ohne Annahmen. Jeder der 46 Prüfpunkte hat genau einen Status: bestanden, nicht bestanden, nicht entschieden, ungültig oder nicht ausgeführt. Nur ein bestandener Prüfpunkt zählt einen Punkt; „nicht entschieden“ ist kein Bestehen.

- Lauf: run-1; Suite ENZBERG-NSN014 v0.4.1; Bewertung nsn014-objective-v1; UX-Rubrik nsn014-ux-rubric-v1
- Executor: exec; Reviewer: rev; SQBF-Commit abc; BLE-Build ble

## 1. Kennzahlen

| Kennzahl | Wert |
|---|---|
| Ergebnis des Laufs | nicht bestanden |
| Lauf bestanden | nein |
| Gründe für das Ergebnis | CHECKS\_FAILED=1; STAGES\_FAILED=0 |
| Punkte | 2 von 46 |
| Punkte in Prozent | 4,3 % |
| Objektiv entschiedene Prüfpunkte | 3 von 46 (6,5 %) |
| Bestanden unter den entschiedenen | 66,7 % |
| bestanden | 2 |
| nicht bestanden | 1 |
| nicht entschieden | 42 |
| ungültig | 0 |
| nicht ausgeführt | 1 |
| Stufen ausgeführt | 11 von 12 |
| Abbruchgrund | Zeitgrenze erreicht |
| Speicherquote | 100,0 % |
| Technischer Status | COMPLETED |
| Kritischer Stopp | — |
| Art des Laufs | Benchmark-Lauf |

## 2. Ergebnis je Stufe

| Stufe | Bezeichnung | Stufenergebnis | Punkte | bestanden | nicht bestanden | nicht entschieden | ungültig | nicht ausgeführt |
|---|---|---|---|---|---|---|---|---|
| NSN014-PLAN | Planproben anlegen | PASS | 1 von 1 | 1 | 0 | 0 | 0 | 0 |
| NSN014-RECEIPT | Probeneingang prüfen | INCONCLUSIVE | 0 von 1 | 0 | 0 | 1 | 0 | 0 |
| NSN014-PREPARATION | Abschlämmung und Entnahmen erfassen | INCONCLUSIVE | 1 von 10 | 1 | 0 | 9 | 0 | 0 |
| NSN014-SIEVE | Siebanalyse erfassen | INCONCLUSIVE | 0 von 10 | 0 | 1 | 9 | 0 | 0 |
| NSN014-SHAPE | Kornform erfassen | INCONCLUSIVE | 0 von 5 | 0 | 0 | 5 | 0 | 0 |
| NSN014-BOILING | Kochversuch erfassen | INCONCLUSIVE | 0 von 4 | 0 | 0 | 4 | 0 | 0 |
| NSN014-SE | Sandäquivalent erfassen | INCONCLUSIVE | 0 von 1 | 0 | 0 | 1 | 0 | 0 |
| NSN014-ASSESS | Bewertungsansicht prüfen | INCONCLUSIVE | 0 von 1 | 0 | 0 | 1 | 0 | 0 |
| NSN014-WPK | Plan gegen Fertiggestelltes prüfen | INCONCLUSIVE | 0 von 1 | 0 | 0 | 1 | 0 | 0 |
| NSN014-ANALYSIS | Analytik prüfen | INCONCLUSIVE | 0 von 1 | 0 | 0 | 1 | 0 | 0 |
| NSN014-REPORT | Prüfberichte erzeugen | INCONCLUSIVE | 0 von 10 | 0 | 0 | 10 | 0 | 0 |
| NSN014-RIGHTS | Rechte der Werksleitung prüfen | NOT\_RUN | 0 von 1 | 0 | 0 | 0 | 0 | 1 |
| Summe |  |  | 2 von 46 | 2 | 1 | 42 | 0 | 1 |

## 3. Prüfpunkte ohne Bestanden nach Ursprung

| Ursprung | Bedeutung | Anzahl |
|---|---|---|
| MODELL | Modell (hat aufgegeben, nicht gespeichert, Feld nicht übernommen) | 37 |
| MODELL/SUITE | Modell und Test-Suite gemeinsam (vorher abgelehnte Aktion) | 0 |
| SUITE | Test-Suite (Guard, Wortlaut, Harness) | 0 |
| PROVIDER | Provider (Anfrage ausgefallen) | 0 |
| VORSTUFE | Voraussetzung fehlt oder Modul nicht erreicht | 0 |
| UNKLAR | Ursprung aus den Daten nicht bestimmbar | 5 |
| NICHT\_AUSGEFUEHRT | Stufe nicht ausgeführt | 1 |
| UNGUELTIG | Messung ungültig | 0 |
| BLE-ABWEICHUNG | objektive Abweichung, durch unabhängige Oracles belegt (fachlich zu bestätigen) | 1 |

Der Ursprung ordnet einen Prüfpunkt ohne Bestehen nach aufgezeichneten Fakten ein; er ist kein Urteil über BLE. Ein BLE-Fehler ist ausschließlich ein Prüfpunkt „nicht bestanden“ (Ursprung BLE-ABWEICHUNG, fachlich zu bestätigen). Bedienbeobachtungen des Reviewers stehen unbestätigt in Abschnitt 8.

## 4. Alle Prüfpunkte

| Prüfpunkt | Status | Ursprung | Klasse |
|---|---|---|---|
| NSN014-PLAN | bestanden | — | — |
| NSN014-RECEIPT | nicht entschieden | UNKLAR | — |
| NSN014-PREPARATION/P01 | bestanden | — | — |
| NSN014-PREPARATION/P02 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-PREPARATION/P03 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-PREPARATION/P04 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-PREPARATION/P05 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-PREPARATION/P06 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-PREPARATION/P07 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-PREPARATION/P08 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-PREPARATION/P09 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-PREPARATION/P10 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-SIEVE/P01 | nicht entschieden | UNKLAR | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-SIEVE/P02 | nicht bestanden | BLE-ABWEICHUNG | PERSISTED\_VALUE\_DEVIATION |
| NSN014-SIEVE/P03 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-SIEVE/P04 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-SIEVE/P05 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-SIEVE/P06 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-SIEVE/P07 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-SIEVE/P08 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-SIEVE/P09 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-SIEVE/P10 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-SHAPE/P01 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-SHAPE/P05 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-SHAPE/P06 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-SHAPE/P09 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-SHAPE/P10 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-BOILING/P01 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-BOILING/P04 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-BOILING/P05 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-BOILING/P10 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-SE/P01 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-ASSESS | nicht entschieden | UNKLAR | — |
| NSN014-WPK | nicht entschieden | UNKLAR | — |
| NSN014-ANALYSIS | nicht entschieden | UNKLAR | — |
| NSN014-REPORT/P01 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-REPORT/P02 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-REPORT/P03 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-REPORT/P04 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-REPORT/P05 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-REPORT/P06 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-REPORT/P07 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-REPORT/P08 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-REPORT/P09 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-REPORT/P10 | nicht entschieden | MODELL | EXECUTOR\_REPORTED\_BLOCKED |
| NSN014-RIGHTS | nicht ausgeführt | NICHT\_AUSGEFUEHRT | — |

## 5. Bedienkennzahlen

| Messwert | Wert |
|---|---|
| Aufgaben mit Bedienmessung | 1 |
| Modul erreicht | 1 |
| Modul nicht erreicht | 0 |
| Modul erreicht: nicht erfasst | 0 |
| Aktionen | 10 |
| Scrolls | 2 |
| Scrolls nach der letzten Eingabe | 1 |
| Klicks | 3 |
| Eingaben | 4 |
| Tastendrücke | 1 |
| Wartezeiten | 0 |
| abgelehnte Aktionen | 0 |
| Speichern: gespeichert | 1 |
| Speichern: Speichern nicht nötig (Zuteilung) | 0 |
| Speichern: Klick auf Speichern abgelehnt | 0 |
| Speichern: alles eingegeben, nicht gespeichert | 0 |
| Speichern: nur teilweise eingegeben, nicht gespeichert | 0 |
| Speichern: Modul nicht erreicht | 0 |
| Speichern: nicht zutreffend (Lese- oder Berichtsaufgabe) | 0 |
| Speicherquote | 100,0 % |

## 6. Aufwand

| Messwert | Wert |
|---|---|
| Modellanfragen | 10 |
| Anfragen Executor | 8 |
| Anfragen Reviewer | 2 |
| Laufzeit in Sekunden | 600 |
| Modell-Wartezeit in Sekunden | 301 |
| Tokens (bekannte Summe) | 1500 |
| Anfragen ohne Tokenangabe | 1 |

## 7. Vergleichbarkeit

| Schlüssel | Wert |
|---|---|
| spec\_version | 1.3.0 |
| suite\_sha256 | s |
| dataset\_sha256 | d |
| reference\_projection\_sha256 | p |
| allocation\_reference\_sha256 | a |
| executor\_instructions\_sha256 | i |
| guard\_rules\_sha256 | g |
| review\_schema\_sha256 | r |
| executor\_model | exec |
| reviewer\_model | rev |
| viewport | 1280x800 |
| browser\_version | 1.0 |

Zwei Läufe sind nur vergleichbar, wenn alle Werte dieser Tabelle gleich sind; sonst unterscheiden sich die Messbedingungen, nicht nur die Ergebnisse.

## 8. Beobachtungen des Reviewers (nicht in den Punkten)

Reviewer-Antworten: 1; ausgefallene Reviews: 0. Der Reviewer antwortet je Aufgabe im festen JSON-Schema (Urteil, vier Werte von 0 bis 5, Befunde). Seine Antworten sind unbestätigte Beobachtungen: Sie werden hier nur gezählt und ändern weder einen Prüfpunkt noch einen Punkt noch das Ergebnis des Laufs. Der Wortlaut der Befunde steht im Anhang A4.

| Urteil des Reviewers | Anzahl |
|---|---|
| PASS | 1 |
| FAIL | 0 |
| INCONCLUSIVE | 0 |

| Dimension | Anzahl | Minimum | Mittelwert | Maximum |
|---|---|---|---|---|
| findability | 1 | 3 | 3,0 | 3 |
| clarity | 1 | 4 | 4,0 | 4 |
| task\_progress | 1 | 5 | 5,0 | 5 |
| error\_recovery | 0 | — | — | — |

| Kategorie | critical | major | minor | info |
|---|---|---|---|---|
| BLE\_DEFECT\_CANDIDATE | 0 | 0 | 0 | 0 |
| UX\_IMPROVEMENT | 0 | 0 | 0 | 0 |
| AGENT\_DIFFICULTY | 0 | 0 | 0 | 0 |
| HARNESS\_SUSPECTED | 0 | 0 | 0 | 0 |
| UNCLEAR | 0 | 0 | 0 | 0 |

## 9. Konsistenzprüfung

| Regel | Anzahl |
|---|---|
| STAGE\_PASS\_WITH\_OPEN\_CHECK | 0 |
| STAGE\_FAIL\_WITHOUT\_FAILED\_CHECK | 0 |
| VERDICT\_GO\_WITH\_OPEN\_CHECK | 0 |
| ALL\_PASSED\_WITHOUT\_GO | 0 |
| DUPLICATE\_RECORD | 0 |
| CATALOGUE\_MISMATCH | 0 |
| UNKNOWN\_RESULT | 0 |

Befunde: keine

Prüfsumme der Punktekarte (SHA256): 6c76b6619a3f5de927759a3c0e062a98673e1b09328f7236d78bfee1c8672e24
