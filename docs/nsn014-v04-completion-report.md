# NSN014 v0.4 – Abschlussbericht technische Fertigstellung (15.10.2026)

Auftrag: Issue #21 (PO-Auftrag vom 15.10.2026), Draft PR #10. Durchgeführt von Claude Code
(Opus 5.5) als alleiniger technischer Hauptagent; der Codex-WIP `a5d712c` wurde ohne Verlust
übernommen.

**Abschlussstatus: PARTIAL GO.** Der Code ist technisch ausführungsbereit (die modellfreie
Readiness ist bestanden), aber ein Live-Lauf hat nicht stattgefunden (funktional NOT_RUN). Der einzige verbleibende Blocker
ist die fehlende ausdrückliche PO-Ausführungsfreigabe für genau diesen v0.4-Lauf (Abschnitt 10).
Zum Request-Budget ist zusätzlich eine PO-Entscheidung nötig (Abschnitt 8).

## 1. Ergebnis in Kürze

- Alle zwölf v0.4-Stufen sind über echte Adapter integriert. Jede Stufe bekommt einen objektiven
  Status aus Controller- und unabhängigen Read-only-Oracles. Die UX-Bewertung durch den Reviewer ist
  davon getrennt, versioniert und vorläufig.
- Beim Prüfen gegen die echte Referenz habe ich drei Fehler gefunden und behoben, die einen Live-Lauf entwertet hätten:
  - Der SE-Lauf wäre mit einem Controller-Fehler abgebrochen.
  - Korrekt eingegebene SE-Werte wären als falscher BLE-FAIL gewertet worden.
  - Die WPK-Stufe begann auf einer Seite, die die WPK-Persona nicht öffnen darf.
- Lokale Regression: **305 Tests OK**. Modellfreie Readiness mit v0.4 und dem aktuellen
  Plan-Flow-Manifest: **READY_FOR_SINGLE_SUITE_RUN**, 0 Modellaufrufe, 0 DB-Schreibvorgänge.
- Es gibt noch kein BLE-Ergebnis. Die Fragen „was funktioniert / was nicht / BLE oder SQBF /
  UX-Priorität / Retest“ beantwortet der Abschlussbericht des ersten freigegebenen Laufs.

## 2. Stufenmatrix (v0.4, Reihenfolge der Suite)

| # | Stufe | Persona (BLE-Rolle) | Einstieg | Erlaubte Fähigkeit | Unabhängige Prüfung | Objektive FAIL-Klassen |
|---|---|---|---|---|---|---|
| 1 | PLAN | laboratory_lead (Laborleiter) | Plan-Detailseite | „Proben anlegen / nachanlegen“ einmal | Receipt-Oracle `after_plan` | PLAN_SAMPLE_DEVIATION; PLAN_SAMPLE_INTEGRITY (kritischer Stopp) |
| 2 | RECEIPT | laboratory_staff (Mitarbeiter) | /samples | nur lesen | Nebenwirkungsfreiheit, Receipt-Oracle `after_plan` (lazy LIMS ≤ 1) | – (fehlende Vorstufe → INCONCLUSIVE, inkonsistenter Planzustand → BLOCKED) |
| 3 | PREPARATION | laboratory_staff | /samples | Zuteilung + Abschlämmung, exakte Werte, ein Save | Allokations- und Mess-Oracle | PERSISTED_VALUE_DEVIATION |
| 4 | SIEVE | laboratory_staff | /samples | Siebung + Teilsiebung | Mess-Oracle (sieves, partial_series, preparation) | PERSISTED_VALUE_DEVIATION |
| 5 | SHAPE | laboratory_staff | /samples | Kornform je Fraktion | Mess-Oracle | PERSISTED_VALUE_DEVIATION |
| 6 | BOILING | laboratory_staff | /samples | Kochversuch inkl. Wiederholungen | Mess-Oracle | PERSISTED_VALUE_DEVIATION |
| 7 | SE | laboratory_staff | /samples | Sandäquivalent A/B | Mess-Oracle | PERSISTED_VALUE_DEVIATION |
| 8 | ASSESS | laboratory_lead | /samples | nur lesen | Nebenwirkungsfreiheit; Anzeige-Nachvollzug durch Reviewer | – |
| 9 | WPK | wpk_lead (Laborleiter, ohne `fpc.view`) | Plan-Detailseite | nur lesen | Nebenwirkungsfreiheit | – |
| 10 | ANALYSIS | plant_lead (Viewer) | /analytics | nur lesen | Nebenwirkungsfreiheit | – |
| 11 | REPORT | laboratory_lead | /samples/{Probe} | je Position ein nicht-offizieller Prüfbericht + ein PDF-Download | Report-Oracle (persistierte Basis), Berechnungs-Oracle, PDF-Prüfung | REPORT_RELATION_DEVIATION, REPORT_VALUE_DEVIATION, CALCULATION_DEVIATION, INVALID_PDF_ARTIFACT, PDF_IDENTITY_MISSING |
| 12 | RIGHTS | plant_lead | Plan-Detailseite | nur lesen | nur `.view/.read`-Rechte, Nebenwirkungsfreiheit | – |

Nach jedem Lauf prüfen die abschließenden Oracles Folgendes:
- statischer Fixture-Zustand
- Receipt `after_modules`
- alle Messarten
- Zuteilungen
- Reports
- Berechnungen

Rechte werden nie erweitert. Release, Signatur und Versand sind ausgeschlossen. Der Plan wird
nur über die bestehende Planaktion befüllt.

## 3. Status- und Bewertungsmodell

Die objektive Bewertung trägt die Version `nsn014-objective-v1`.

- **Statuswerte:**
  - PASS
  - FAIL
  - BLOCKED
  - INVALID_HARNESS (intern `INVALID`)
  - INCONCLUSIVE
  - NOT_RUN
  - NOT_IMPLEMENTED

  Keine Prozentzahl, kein Gesamtscore. Ein Aggregat ist nur dann PASS, wenn keine Stufe offen ist.
- **PASS** erfordert:
  - das Terminalsignal des Executors,
  - ein bestandenes unabhängiges Oracle,
  - nachgewiesene Evidenz.

  Ein „done“ des Executors oder ein Reviewer-PASS allein reicht nie.
- **FAIL** gilt nur, wenn ein Oracle eine Abweichung belegt. Bei Messstufen gilt zusätzlich: Der
  Controller hat jeden freigegebenen Wert exakt getippt und das Modul gespeichert gesehen.
  Andernfalls bleibt die Stufe INCOMPLETE/INCONCLUSIVE.
- **Kritische Stopps:**
  - technisches BLOCKED/INVALID
  - Ressourcenende
  - Identitätsfehler der Planproben

  Alle Folgestufen werden dann NOT_RUN. Es gibt keinen Retry und keinen Re-Login.
- **Guard und Fortschritt:**
  - Lehnt der Guard eine Aktion ab, endet nur diese Aufgabe (INCONCLUSIVE).
  - Eine ungültig gewordene Session ist BLOCKED.
  - Ein Stillstand (unveränderter Bildschirm + wiederholte identische Aktion) beendet die Aufgabe,
    ohne das gemeinsame Budget zu verbrauchen.
  - Nur ein Klick aktiviert Generieren, Plananlage, Download oder Speichern.
- **PDF:**
  - Ein unlesbarer oder verschlüsselter Download ist ein Artefaktbefund (INVALID_PDF_ARTIFACT).
  - Ein ausbleibender Download ist Produktevidenz (PDF_DOWNLOAD_NOT_RECEIVED).
  - Beides ist kein Harness-Fehler. Nur Controller-seitige Pfad- oder ACL-Probleme bleiben Harness-Fehler.
- **Berechnungs-Oracle:** Es rechnet aus den persistierten Rohdaten unabhängig nach:
  - SE-Einzelindizes und Mittelwert
  - Kochverlust je Wiederholung
  - Feinanteil < 0,063 mm aus dem UF-Modul
  - einfacher Siebdurchgang

  Die Toleranzen folgen der Speicherpräzision von BLE: 3 Nachkommastellen; Siebdurchgang
  2 Nachkommastellen je kumulierter Fraktion. Folgendes rechnet das Oracle nicht nach; es wird als
  **NOT_COVERED** ausgewiesen, nie als PASS oder FAIL:
  - Kornform-Endwert: BLE gewichtet über die Sieblinie und die Entnahmequellen.
  - Teilsiebung und gekoppelte Siebung: projektspezifische Skalierung.
- **UX-Ebene:** Rubrik `nsn014-ux-rubric-v1`, vorläufig.
  - Vier Dimensionen von 0 bis 5; `null` steht für NOT_EVALUATED.
  - Jeder Befund hat Kategorie, Schweregrad, Beobachtung, Erwartung, Vorschlag und Evidenzverweis.
  - Kategorien: BLE_DEFECT_CANDIDATE, UX_IMPROVEMENT, AGENT_DIFFICULTY, HARNESS_SUSPECTED, UNCLEAR.
  - Das UX-Urteil steht neben dem objektiven Status. Ein guter UX-Wert gleicht keinen Sicherheits-
    oder Datenfehler aus.

## 4. Evidenz und Versionierung je Lauf

Alle Artefakte liegen privat außerhalb von Git und sind je Lauf unveränderlich. Die Fixture kann
nur einmal verwendet werden (Lease nach OAuth).

- **`run.json`:**
  - Lauf-ID
  - Versionen von Suite, Bewertung, Rubrik und Review-Schema (Hash)
  - SQBF-Commit; nur ein sauberer Quellstand ist zulässig
  - BLE-Build und DLL-SHA
  - Hashes von Fixture-Manifest, Startzustand, Datensatz, Projektion und Allokation
  - Persona-Kontext (Rolle, Rechte-Hash, Stufen; keine Namen oder IDs)
  - Modelle, Viewport, Locale, Browserversion
  - Request-Schätzung, Zeiten, Accounting
  - abschließende Oracles, Stufenmatrix, UX-Zusammenfassung
  - Vergleichsschlüssel für Retests
- **`cases.json`, `accounting.json`:** werden nach jeder Stufe atomar fortgeschrieben.
  Dazu kommen Ereignisse und Screenshots/PDF-Seiten je Stufe mit SHA-256.
- **`completion-report.md` (deutsch):**
  - Stufenmatrix
  - „Was funktioniert“
  - „Was funktioniert nicht“
  - „BLE- oder SQBF-Problem“
  - UX-Befunde nach Kategorie und Schweregrad
  - Prioritäten P1–P4
  - Retest-Benchmark
  - Zeit/Nutzung
  - Stufendetails

## 5. Behobene Integrationsfehler

| Fehler | Wirkung ohne Fix | Commit |
|---|---|---|
| Vokabular der SE-Höhen (`sand_height` in der Referenz, `sand_height_mm` in der View) | SE-Stufe bricht mit Controller-Fehler ab; korrekte SE-Werte erscheinen als falscher FAIL; PDF-Review für P01 stürzt ab | `f4438e2` |
| Guard-Ablehnung beendete die ganze Suite | Ein abgelehnter Agentenklick stoppt alle Folgestufen | `2e8b4d6` |
| Scroll/Wait/Done über einem Bedienelement galt als Aktivierung | Falsche Generate-/Download-/Save-Zuordnung | `2e8b4d6` |
| Keine Stillstandserkennung; getippter Text nicht im Aktionsschlüssel | Budgetverbrauch ohne Fortschritt bzw. falscher Stillstand beim Tippen | `2e8b4d6` |
| Reviewer-Urteil bestimmte objektive Ergebnisse | Verstoß gegen #21 (KI-Urteil statt Oracle) | `2e8b4d6` |
| Ungültiges PDF als Harness-Ausnahme | Produkt-Artefaktfehler erscheint als SQBF-Fehler | `2e8b4d6` |
| Keine Prüfung berechneter Ergebnisse | Rechenfehler in Reports bleiben unentdeckt | `2e8b4d6` |
| Naiver Kornform-Index bzw. ungerundeter Siebdurchgang | Falsche CALCULATION_DEVIATION | `2e8b4d6` |
| Folgestufen nach kritischem Stopp als BLOCKED | Nicht ausgeführte Stufen erscheinen als blockiert | `2e8b4d6` |
| Mengenpräzedenz in `unvisited_deviations` | Falsche Positionszuordnung | `2e8b4d6` |
| WPK-Einstieg `/quality/wpk` für die WPK-Persona verweigert (fehlendes `fpc.view`, BLE korrekt „fail closed“) | WPK-Stufe startet auf „Kein Zugriff“ | `f4ecc0d` |
| Route-Handler mit zwei Parametern in der neuen Routen-Probe | Readiness-Probe schlägt fehl | `79e03fa` |

## 6. Tests

Ergebnis: `python -m unittest discover -s tests` im Worktree-Root, **305 Tests OK** (ca. 24,7 s).
Neue Testdateien:
- `tests/test_stage_support.py`
- `tests/test_calculation_oracle.py`
- `tests/test_stage_runners.py`

Erweitert:
- `tests/test_regular_runner.py`
- `tests/test_pdf_check.py`
- `tests/test_measurement_oracle.py`

Abgedeckt sind:
- Statusmodell, kritischer Stopp und NOT_RUN
- Null-Scores und Review-Schema
- Guard-Ablehnung, Session-Invalidierung, Stillstand
- Download-Timeout, ungültiges und echtes PDF, Doppel-Download, Klick-Aktivierung
- Plan-, Report- und Messklassifikation
- Vokabular-Roundtrip, Berechnungen und Toleranzen
- Quellcode-Gate, Request-Schätzung, Routen-Probes
- Persona-Kontext ohne Identitäten
- deutscher Bericht inklusive Escaping

## 7. Modellfreie Readiness

Befehl (ohne `--execute`; Pfade privat):

```powershell
& $python -m sqbf.cli run-suite --suite projects/ble-elva/suites/enzberg-nsn014-v0.4.json `
  --fixture <privat>\fixture-v04-plan-flow-ready-20261015.json --dataset <privat>\dataset-ux-source-v1.json `
  --projection <privat>\reference-projection-ux-v1.json --allocations <privat>\allocation-reference-v1.json
```

Ergebnis an `f4ecc0d`: **READY_FOR_SINGLE_SUITE_RUN**. Bestanden haben:
- Quellstand sauber
- Plan-Workflow und Rechte
- Referenz-Hashes
- Suite an Fixture gebunden
- Stufenverträge (35 Messaufgaben, 10 Report-Positionen, Vokabular-Roundtrip mit 80 Prüfungen)
- Request-Schätzung
- Methoden-Fixture
- Fixture-Gates inklusive aller vier Sessions (keine Erneuerung nötig)
- statischer Startzustand
- Identität der laufenden BLE-Runtime
- leerer Start (keine Proben, LIMS, Messungen, Zuteilungen, Reports)
- natives Plan-Formular
- fünf Einstiegsrouten

Dabei gab es 0 Modellaufrufe und 0 DB-Schreibvorgänge; die geschützten Daten blieben unverändert.

Drei vorherige Readiness-Läufe waren korrekt blockiert. Sie haben die Fehler aus Abschnitt 5
aufgedeckt (SE-Vokabular, Routen-Handler, WPK-Einstieg). Die private Evidenz liegt unter
`D:\Temp\sqbf-nsn014-readiness-20261015\`.

## 8. Budget (PO-Entscheidung erforderlich)

Die Untergrenze liegt bei **646 Modellanfragen** für einen vollständigen Lauf. Darin sind keine
Umwege, Scrolls, Dropdowns oder Korrekturen enthalten. Die harte Grenze liegt bei 1.000 (Faktor 1,55).

| Stufe | Anfragen |
|---|---|
| PLAN | 4 |
| RECEIPT | 3 |
| PREPARATION | 160 |
| SIEVE | 252 |
| SHAPE | 85 |
| BOILING | 48 |
| SE | 12 |
| ASSESS | 3 |
| WPK | 3 |
| ANALYSIS | 3 |
| REPORT | 70 |
| RIGHTS | 3 |

Frühere Live-Läufe brauchten 5,4–6,4 s Wandzeit pro Anfrage. Die 7.200-s-Grenze bindet daher erst
bei etwa 1.100–1.300 Anfragen; die Anfragegrenze bindet zuerst.

Risiko: Bei realistischem Mehrbedarf von 1,5–2× reicht das Budget voraussichtlich nicht bis
REPORT/RIGHTS. Diese Stufen würden dann INCONCLUSIVE (Ressourcenende). Die Fixture ist danach
verbraucht. #21 nennt zudem ein „deutlich geringeres“ Verbrauchsziel.

- **Option A:** v0.4 unverändert mit 1.000 Anfragen / 7.200 s. Die Messstufen sind
  aussagekräftig; ein Bericht bis PDF ist unwahrscheinlich.
- **Option B (empfohlen für den ersten Kalibrierungslauf):** v0.4.1, bei der sich nur
  `resource_policy` ändert, z. B. 1.500 Anfragen / 10.800 s als harte Obergrenzen. Dazu kommt eine
  neue private Manifest-Bindung (`suite_sha256`); die Datenbank wird nicht geändert. Nur so kann
  der Lauf voraussichtlich bis Auswertung/PDF kommen. Der tatsächliche Verbrauch wird gemessen und
  kalibriert spätere Läufe.

## 9. Verbleibende echte Einschränkungen

- Kein Live-Lauf, also noch keine BLE-Befunde.
- Kornform-Endwert und Teilsiebung/gekoppelte Siebung werden nicht unabhängig nachgerechnet
  (NOT_COVERED).
- Die Anzeige in den Lesestufen (ASSESS/WPK/ANALYSIS/RIGHTS) bewertet nur der Reviewer
  (`REVIEWER_ASSESSED`); es gibt kein DOM-Oracle für angezeigte Werte. Objektiv geprüft werden
  Nebenwirkungsfreiheit und Persona-Scope.
- Die UX-Rubrik ist vorläufig und nicht kalibriert; es gibt nur ein Reviewer-Modell.
- Die WPK-Persona hat als Laborleiter kein `fpc.view`, der FPC-Bereich ist also nicht Teil des Tests.
  Ob eine WPK-Funktionsrolle in BLE `fpc.view` haben sollte, ist eine Rollenmodell-Frage an
  BLE/PO. Bewusst wurde dazu kein Issue angelegt; die Beobachtung ist unbestätigt.
- Die Fixture ist nur einmal verwendbar. Für einen Retest wird eine neue Fixture aus der
  Golden-Basis gebraucht.
- Session-Cookies laufen ab (8 h gleitend), daher die Readiness direkt vor dem Lauf erneut
  ausführen. Höchstens eine kontrollierte Erneuerung je abgelaufener Persona.
- Für den Lauf ist eine frische ChatGPT-Plan-OAuth nötig (interaktiv). Den Modellkatalog prüft
  die Readiness nicht.

## 10. Offener Freigabepunkt für den Live-Lauf

#21 autorisiert ausdrücklich keinen v0.4-Live-Lauf; eine konkrete PO-Ausführungsfreigabe liegt
nicht vor. Die Freigabe müsste Folgendes festlegen:

- genau ein Lauf
- Suite v0.4 (oder v0.4.1 nach Abschnitt 8)
- SQBF-Commit
- aktuelles Plan-Flow-Manifest
- Provider `chatgpt_plan` mit Executor `gpt-6-luna` und Reviewer `gpt-6.1-sol` (Abo, interaktive OAuth)
- Datenübermittlung nach K3
- Budget
- kein Retry
- höchstens eine kontrollierte Session-Erneuerung je Persona
- private Ablage

Befehl nach Freigabe: der Readiness-Befehl aus Abschnitt 7 mit zusätzlich `--execute`.
