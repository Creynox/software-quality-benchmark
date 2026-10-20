# NSN014 Auswertungsbericht: feste, versionierte Definition

Entscheidung des PO vom 19.10.2026: Ein Benchmark-Lauf wird immer mit einem **Punktesystem** bewertet (bestanden / nicht bestanden je Prüfpunkt), aus
**Zahlen, Daten und Fakten**, ohne Annahmen und ohne reine Textbewertung. Sonst ist der Folgetest nicht sauber reproduzierbar und man kann nicht sagen,
ob ein Lauf gut oder schlecht war. Der Auswertungsbericht hat immer **dieselbe feste Definition**; sie ändert sich nur durch eine **neue Version**
(Erweiterung oder Feinanpassung).

Maschinenlesbare Definition: `projects/ble-elva/suites/nsn014-report-spec-v1.json` (Version 1.1.0). Umsetzung: `projects/ble-elva/tools/report_spec.py`.

## Was herauskommt

Jeder Lauf-Ordner enthält neben dem ausführlichen `completion-report.md`:

- **`punktebericht.md`**: der Bericht in der festen Form (neun Abschnitte, immer in dieser Reihenfolge, immer dieselben Tabellen und Sätze).
- **`scorecard.json`**: dieselben Zahlen maschinenlesbar (Schlüssel und Reihenfolge fest). Aus dieser Datei entsteht der Bericht; ein Agent liest sie, statt Text zu deuten.

`completion-report.md` beginnt mit dem Punktebericht und enthält dahinter als Anhang A0 bis A9 den bisherigen Detailbericht (Belege, Reviewer-Befunde im Wortlaut).

## Prüfpunkte und Punkte

Der Katalog hat seit Version 1.0.0 **46 Prüfpunkte** und ist fest: ein Prüfpunkt je Stufe für die sechs Einzelstufen (PLAN, RECEIPT, ASSESS, WPK, ANALYSIS,
RIGHTS) und einer je Position für die Messstufen und den Bericht (PREPARATION 10, SIEVE 10, SHAPE 5, BOILING 4, SE 1, REPORT 10). Jeder Prüfpunkt hat
genau einen Status:

| Status | Bedeutung | Punkte |
|---|---|---|
| bestanden | unabhängiges Oracle stimmt mit den freigegebenen Werten überein, Aufgabe vollständig | 1 |
| nicht bestanden | objektive Abweichung, vom unabhängigen Oracle belegt | 0 |
| nicht entschieden | kein objektives Ergebnis (Agent, Provider, Suite oder Vorstufe) | 0 |
| ungültig | die Messung selbst ist ungültig (Suite-Fehler), kein Befund über BLE | 0 |
| nicht ausgeführt | Stufe lief nicht (vorgelagerter Stopp) | 0 |

„Nicht entschieden“ ist **kein** Bestehen und **kein** Durchfallen: Es sagt, dass nichts gemessen wurde. Der **Ursprung** (Modell, Modell/Suite, Suite,
Provider, Vorstufe, unklar) ordnet das nach aufgezeichneten Fakten ein; er ist kein Urteil über BLE. Ein BLE-Fehler ist ausschließlich ein Prüfpunkt
„nicht bestanden“ (Ursprung BLE-ABWEICHUNG, fachlich zu bestätigen).

## Zahlen und Ergebnis des Laufs

- **Punkte** = Anzahl bestandener Prüfpunkte (von 46); **Punkte in Prozent**, **Abdeckung** (bestanden plus nicht bestanden, also objektiv entschieden),
  **Quote der bestandenen unter den entschiedenen**, **Speicherquote**. Alle auf eine Nachkommastelle, kaufmännisch gerundet.
- **Ergebnis des Laufs** in fester Reihenfolge: *ungültig* (ein Prüfpunkt ungültig oder technischer Status INVALID), *nicht bestanden* (mindestens ein
  Prüfpunkt oder eine Stufe durchgefallen), *abgebrochen* (Abbruchgrund, Ressourcen- oder Blockadestopp oder ein Prüfpunkt nicht ausgeführt), *bestanden*
  (alle 46 bestanden, Verdict GO, Konsistenzprüfung ohne Befund), sonst *unvollständig*. **Lauf bestanden: ja** gibt es nur bei *bestanden*.
- Zielwerte (etwa „mindestens 80 % Punkte“) sind bisher (Version 1.1.0) **nicht festgelegt**; das ist eine Entscheidung des PO und eine neue Version.

## Aufbau des Berichts (Abschnitte 1 bis 9)

1. Kennzahlen · 2. Ergebnis je Stufe · 3. Prüfpunkte ohne Bestanden nach Ursprung · 4. Alle Prüfpunkte · 5. Bedienkennzahlen (Aktionen, Scrolls, Scrolls nach der
letzten Eingabe, abgelehnte Aktionen, Speicherstatus) · 6. Aufwand (Anfragen, Zeit, Tokens) · 7. Vergleichbarkeit · 8. Beobachtungen des Reviewers (nur
gezählt, nicht in den Punkten) · 9. Konsistenzprüfung (Widersprüche zwischen Daten und Katalog).

## Der Reviewer (Sol-Agent) und alle anderen Agenten

Der Reviewer (gpt-6.1-sol) bleibt eine **getrennte Beobachtungsschicht** (Rubrik `nsn014-ux-rubric-v1`, JSON-Schema unverändert: Urteil, vier Werte von 0 bis 5,
Befunde). Seine Antworten erscheinen in Abschnitt 8 nur als **Zahlen** (Anzahl je Urteil, Minimum, Mittelwert und Maximum je Dimension, Anzahl Befunde je
Kategorie und Schweregrad) und ändern **keinen** Prüfpunkt, keinen Punkt und nicht das Ergebnis. Der Wortlaut der Befunde bleibt im Anhang A4.

Für jeden Agenten, der einen Lauf liest, zusammenfasst oder kommentiert (auch den Sol-Agenten), gilt (Spezifikation, Abschnitt `agent_rules`):

1. Zahlen, Status und Ergebnis werden aus `scorecard.json` bzw. `punktebericht.md` übernommen; nicht neu berechnet, geschätzt oder gerundet.
2. Es gibt kein anderes Ergebnis als das Ergebnis des Laufs und kein anderes Bestehen als den Status eines Prüfpunkts. „Gut“, „schlecht“, „vermutlich“,
   „wahrscheinlich“ ersetzen keine Zahl.
3. Jede Aussage nennt ihre Quelle: Prüfpunkt-ID, Zahl aus einem Abschnitt oder eine Belegdatei des Laufs.
4. Ein BLE-Fehler ist nur ein Prüfpunkt „nicht bestanden“; alles andere, auch jede Reviewer-Beobachtung, ist unbestätigt und wird so bezeichnet.
5. Läufe werden nur verglichen, wenn Abschnitt 7 gleich ist (`suite-score --run A --compare-with B` nennt die abweichenden Schlüssel).
6. Struktur, Reihenfolge, Spalten und Wortlaut ändern sich nur durch eine neue Version; ein Agent ergänzt oder ändert sie nicht von sich aus.

## Vergleichbarkeit

Zwei Läufe sind nur vergleichbar, wenn alle Werte in Abschnitt 7 gleich sind: Spezifikationsversion, Suite, Datensatz, Referenz- und Zuteilungsprojektion,
Executor-Anweisung, Klickregeln der Guards, Review-Schema, Modelle, Viewport und Browser. Sonst unterscheiden sich die Messbedingungen, nicht nur die Ergebnisse.

## Versionierung

| Änderung | Version | Folge |
|---|---|---|
| Katalog, Punktregel, Statusregel, Ursprungsregel oder Formel | MAJOR | Zahlen verschiedener MAJOR-Versionen sind nicht vergleichbar |
| neues Feld, neue Zeile oder neuer Abschnitt **am Ende**; ein aufgezeichneter Grund bekommt einen Ursprung, der vorher „unklar“ war | MINOR | bestehende Felder, Status und Punkte bleiben unverändert |
| Wortlaut, Beschriftung, Formatierung | PATCH | keine Zahl ändert sich |

Änderungsverlauf: **1.0.0** (19.10.2026) erste feste Definition. **1.1.0** (20.10.2026, MINOR): Ursprung „Suite“ für den Stufengrund `REPORT_ORACLE_UNAVAILABLE` (vorher „unklar“;
Lauf 8), „Technischer Status“ und „Kritischer Stopp“ als letzte Zeilen von Abschnitt 1; kein Status und kein Punkt ändert sich.

Jede Änderung braucht: neue Versionsnummer und Eintrag im Änderungsverlauf der Spezifikation, neuen gepinnten Hash und neue Golden-Datei im Test
(`tests/test_report_spec.py`, `tests/golden/`). Ohne das schlagen die Tests fehl: Die Definition kann sich nicht unbemerkt ändern. Eine MAJOR-Änderung
liegt als neue Datei `nsn014-report-spec-v2.json` neben der alten.

## Aufruf (modellfrei)

```powershell
& $python -m sqbf.cli suite-score --run D:/Temp/sqbf-regular-runs/<Lauf-ID>
& $python -m sqbf.cli suite-score --run <Lauf A> --compare-with <Lauf B>
```

Neue Läufe schreiben beide Dateien selbst (`scorecard.json`, `punktebericht.md`, in der Version zur Laufzeit). `suite-score` bewertet gespeicherte Läufe nach und legt die Dateien nur neu an, überschreibt
nie (eine abweichende bestehende Datei wird gemeldet). Liegt im Ordner schon eine Punktekarte einer anderen Version, bleibt sie unverändert, und die neue entsteht daneben als
`scorecard-<Version>.json` und `punktebericht-<Version>.md`.

## Nachbewertung der Läufe 5 bis 8 (Spezifikation 1.1.0, nur aus den gespeicherten Daten)

| Lauf | Ergebnis | Punkte | in Prozent | bestanden / nicht bestanden / nicht entschieden / ungültig / nicht ausgeführt |
|---|---|---|---|---|
| 5 (6c23f768) | nicht bestanden | 6 von 46 | 13,0 % | 6 / 1 / 20 / 0 / 19 |
| 6 (fdea63ef) | unvollständig | 17 von 46 | 37,0 % | 17 / 0 / 29 / 0 / 0 |
| 7 (b7a34e94) | unvollständig | 16 von 46 | 34,8 % | 16 / 0 / 30 / 0 / 0 |
| 8 (824fa661) | abgebrochen | 13 von 46 | 28,3 % | 13 / 0 / 32 / 0 / 1 |

Lauf 6 und Lauf 7 sind **nicht vergleichbar** (anderer Executor-Wortlaut), Lauf 7 und Lauf 8 ebenfalls nicht (andere Klickregeln, in Lauf 7 nicht erfasst); die Punktunterschiede sagen daher nichts über BLE.
Lauf 8 verlor die zehn Berichts-Prüfpunkte und RIGHTS durch einen Fehler der Berechnungs-Oracle (Ursprung „Suite“, siehe Abschnitt 26 des Abschlussberichts). Die Läufe 5 bis 8 haben nicht alle
Messwerte (Lauf 5 und 6 ohne Bedienmessung, Lauf 5 bis 7 ohne `guard_rules_sha256`, Lauf 7 ohne „Modul erreicht“); was nicht gemessen wurde, steht als „—“ im Bericht, nie als 0.

## Grenzen

- Alle Prüfpunkte zählen gleich (ein Punkt). Eine Gewichtung wäre eine MAJOR-Änderung und eine Entscheidung des PO.
- Die Punkte messen, wie viel die Suite objektiv entscheiden konnte und wie viel davon bestanden ist. Bei Lauf 6 und 7 begrenzen vor allem Modell und Suite die Punkte,
  nicht belegte BLE-Fehler. Der Ursprung in Abschnitt 3 zeigt das.
- Die UX-Rubrik des Reviewers ist weiterhin eine Skala von 0 bis 5 mit Freitext-Befunden. Eine Checkliste mit festen Ja/Nein-Fragen statt freier Werte wäre ein
  neues Review-Schema (neue Rubrikversion, Lauf nicht vergleichbar mit früheren) und braucht die Entscheidung des PO.
