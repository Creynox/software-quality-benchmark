# NSN014 v0.4 – Abschlussbericht technische Fertigstellung (15.10.2026)

Auftrag: Issue #21 (PO-Auftrag vom 15.10.2026), Draft PR #10. Durchgeführt von Claude Code
(Opus 5.5) als alleiniger technischer Hauptagent; der Codex-WIP `a5d712c` wurde ohne Verlust
übernommen.

**Abschlussstatus bei Berichtserstellung: PARTIAL GO.** Der Code war technisch ausführungsbereit (die
modellfreie Readiness war bestanden), ein Live-Lauf hatte nicht stattgefunden. Zum Request-Budget und zur
Einzellauf-Freigabe war eine PO-Entscheidung nötig (Abschnitte 8, 10, 11).

**Nachtrag nach dem freigegebenen Einzellauf (Abschnitt 12):** Der Lauf `3d9c2706…` endete nach 19,7 s
als **NO-GO / INVALID_HARNESS**; elf Stufen sind NOT_RUN. Es liegt **keine gültige BLE-Messung** vor.
Die Ursachen sind behoben bzw. dokumentiert, ein Folgelauf braucht eine neue PO-Freigabe und eine PO-Entscheidung zu Position P06.

**Nachtrag Lauf 3 (Abschnitt 17):** `413f7abe…`, 16.10.2026: PARTIAL GO, alle zwölf Stufen durchgelaufen, PLAN und WPK PASS, zehn Stufen INCONCLUSIVE durch einen zu engen Guard (Menüeintrag „Prüfbericht“ nicht erkannt, Ablehnung beendet die Aufgabe, Hauptaktion „Testauftrag erzeugen“ nicht erlaubt). 124 Anfragen, 271.478 Tokens, 24 min. Keine Messung erfasst.

**Nachtrag Lauf 5 (Abschnitt 20):** Lauf 5 (6c23f768, 16.10.2026) ist `PARTIAL GO / RESOURCE_STOP`: erstmals objektiv belegte BLE-Ergebnisse (PLAN, RECEIPT, Abschlämmung P08, Siebanalyse P04/P06/P10 PASS), aber nur für fünf von zwölf Stufen. Abbruch nach 3.603 s, weil der Anmeldetoken nach etwa einer Stunde abläuft (HTTP 401); eine Entscheidung zum Token ist offen (Abschnitt 20.6). Das einzige FAIL (P09) war ein Auswertungsfehler (Feld nicht verlassen), mein Anker-Fix aus Abschnitt 19 war falsch (`<base href="/">`); beides behoben. 540 Anfragen, rund 1,37 Mio. Tokens.

**Nachtrag Lauf 4 (Abschnitt 19):** Lauf 4 (083896e6, 16.10.2026) war `NO-GO / INVALID_HARNESS` ohne gültige Messung (PLAN PASS, RECEIPT INCONCLUSIVE, PREPARATION INVALID, 9 Stufen NOT_RUN, 51 Anfragen). Ursache: ein einziger fehlgeschlagener Executor-Request beendete über einen allgemeinen Handler die Suite; dazu zwei fehlende Guard-Freigaben. Behoben und mit Trockenläufen (auch mit eingespielten Providerfehlern) belegt; zusätzlich werden abgeleitete Werte nie mehr BLE angelastet, solange ihre Eingaben fehlen. 441 Tests OK. Der nächste Lauf braucht eine neue Freigabe.

**Nachtrag Behebung (Abschnitt 18):** Die Ursachen von Lauf 3 sind behoben. Neues Werkzeug `suite-dry-run` führt den gesamten echten Stufenpfad mit den echten Guards und einem skriptierten Executor aus; der letzte Lauf ist `DRY_RUN_COMPLETED` (alle zwölf Stufen ohne Harness-Stopp, Ablehnung oder Vertragsbefund; PREPARATION und SHAPE nur wegen der drei von BLE nicht angebotenen Werte INCONCLUSIVE, Option A). 423 Tests OK. Neue Fixture bereit, nächster Lauf braucht eine neue Freigabe.

**Nachtrag nach Lauf 2 und der Vorbereitung (Abschnitte 15 und 16):** Lauf `45eb301f…` endete als
INVALID_HARNESS (Audit-Stempel). Die Vorbereitung für einen dritten Lauf ist modellfrei abgeschlossen: neue Fixture,
Seiteneffekt-Vertrag je Stufe, vollständiger Trockenlauf aller zwölf Stufen ohne Harness-Abbruch, neun dabei gefundene und behobene bzw. im Vertrag erfasste Befunde (16.2),
399 Tests OK. Offen ist nur die Budgetfreigabe (`BUDGET_APPROVAL_MISSING`) und die PO-Entscheidung zu drei von BLE nicht angebotenen Referenzwerten (16.5).

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

## 11. Nachtrag: Suite v0.4.1 (Budgetkandidat, nicht freigegeben)

Vorbereitet ist die Budgetvariante aus Abschnitt 8, Option B. Sie ist **nicht aktiv**, solange keine PO-Budgetfreigabe vorliegt.

- **Suite:** `projects/ble-elva/suites/enzberg-nsn014-v0.4.1.json`. Gegenüber v0.4 ändern sich nur `version`, `supersedes`, `change_note` und `resource_policy`: Profil `NSN014-CALIBRATION-v2`, höchstens 1.500 Modellanfragen und 10.800 s. Kein Retry, Ressourcenstopp bleibt INCONCLUSIVE, 600 s / 60 Aktionen bleiben weiche Marken. Stufen, Personas, Oracles und Referenzen sind unverändert (ein Test vergleicht alle Stufen). Die historische v0.4 ist unverändert; ihr Hash ist per Test festgeschrieben.
- **Validierungsvertrag:** `sqbf/calibration.py` kennt jetzt benannte Profile. Nur eine Policy, die `NSN014-CALIBRATION-v2` ausdrücklich nennt, darf bis 1.500 / 10.800 gehen. Policies ohne Profil, die CORE-/LAB-Pilotbudgets und die Suites v0.1–v0.4 behalten 1.000 / 7.200 bzw. ihre eigenen Grenzen. Tests decken beides ab, dazu die Stopps bei 1.500 Anfragen und 10.800 s.
- **Freigabe-Gate:** Eine Suite mit erweitertem Profil gilt erst als ausführungsbereit, wenn das private Fixture-Manifest einen Freigabeeintrag `suite_copy.budget_approval` enthält (`approved_by: PO`, Datum, Aussage, Profil, Suite-Hash, Grenzwerte). Fehlt er oder weicht ein Wert ab, ist die Readiness `BLOCKED` mit `BUDGET_APPROVAL_MISSING`; zusätzlich steht dort `other_gates: PASSED`, wenn alle übrigen Gates bestanden haben. Ein Lauf hält Profil und Freigabe im Manifest fest.
- **Privates Manifest:** `fixture-v041-budget-pending-20261015.json` (neue Datei, Original unverändert). Es ändert nur `suite_version`, den Suite-Hash (neu `451796ac…`, vorher `fbc65e91…`) samt Hash-Historie und den Änderungsvermerk. Datenbank, Container, Sessions und Referenzwerte sind unverändert. Es enthält **keine** Budgetfreigabe.
- **Offene Entscheidung:** Die PO-Budgetfreigabe (1.500 / 10.800) ist nicht erteilt, ebenso die Einzellauf-Freigabe aus Abschnitt 10. Beide gelten nur für die jeweils genannte Suite-Version, den Commit und das Manifest.

## 12. Live-Lauf 1 (3d9c2706-7e58-4979-8515-6fbc6cac9a1e) — Ergebnis und Folgerungen

**Durchführung.** Auf ausdrückliche PO-Freigabe (v0.4.1, 1.500 Anfragen / 10.800 s, genau ein Lauf) wurde am
15.10.2026 ein Lauf an Commit `b5f1107` gestartet. Alle Pre-Run-Gates waren bestanden (sauberer Quellstand, vier gültige
Sessions mit Identität, Tenant, Rolle und Enzberg-Scope, Runtime, Fixture, Hashes, Routen, Stufenverträge, Budgetfreigabe).
Nach der ChatGPT-Anmeldung lief der Lauf 19,7 s mit **3 Modellanfragen** (Executor 2, Reviewer 1; bekannte Executor-Tokens
3.381). Privat abgelegt im Lauf-Ordner `sqbf-regular-runs/3d9c2706-7e58-4979-8515-6fbc6cac9a1e` (außerhalb von Git).

**Objektives Ergebnis.**

| Stufe | Status | Grund |
|---|---|---|
| PLAN | INVALID_HARNESS | Reviewer-Anfrage fehlgeschlagen; Controller brach die Stufe ab (Abschnitt „Befund 2“) |
| RECEIPT … RIGHTS (11 Stufen) | NOT_RUN | vorgelagerter kritischer Stopp |

Kein PASS, kein FAIL, keine BLE-Abweichung. Die Datenbank ist unverändert (0 Proben, 0 LIMS, 0 Reports; der statische
Fixture-Zustand ist unverändert). Die Fixture-Lease ist verbraucht.

**Befund 1 — Voraussetzung der Testdaten, kein BLE-Fehler: Position P06 ist in den Quelldaten inaktiv.**
Der Executor klickte einmal „Proben anlegen / nachanlegen“. BLE lehnte ab („Das Produkt ist nicht aktiv und kann keine neue
Probe tragen.“); alle zehn Positionen blieben „noch nicht angelegt“. Das SELECT-only-Oracle bestätigt: genau ein Plan-Produkt
(Position P06) hat `is_active = false`, die übrigen neun sind aktiv und vollständig (Verwendungsbereich, Produktebene,
Normzuordnung). BLE verweigert die plan-weite Anlage also alles-oder-nichts. Diese Voraussetzung hat die Readiness nicht
geprüft; ohne den Reviewer-Fehler wäre die Stufe als `PLAN_SAMPLE_DEVIATION` (FAIL) erschienen und hätte einen Fixture-Zustand
fälschlich BLE angelastet. Behoben: Die Readiness prüft jetzt je Plan-Produkt Aktivität, Verwendungsbereich, Produktebene,
Besitzer-Scope und Normzuordnung (`PLAN_PRODUCT_PRECONDITION_FAILED`, nur Positions-IDs). An der echten Fixture meldet das Gate
exakt P06.
Beobachtung für BLE (unbestätigt, nicht als Issue angelegt): Die Meldung nennt das betroffene Produkt nicht, und die Planliste
kennzeichnet die inaktive Position nicht. Eine einzelne inaktive Position blockiert die Anlage aller Proben, ohne Hinweis, welche.
Evidenz: Screenshot `NSN014-PLAN/001-inspection.png`, Executor-Aussage, Oracle-Abfrage.

**Befund 2 — SQBF-Harness: Ein Reviewer-Ausfall durfte die Messung nicht abbrechen.**
Die Reviewer-Anfrage schlug nach 2,7 s fehl; die Nutzung ist leer, also kam keine Antwort an. Der Controller setzte daraufhin
die ganze Stufe auf INVALID_HARNESS und stoppte die Suite. Die Ursache des Anfragefehlers ist **nicht bewiesen**: Der isolierte Worker verschluckt
Fehlertexte bewusst, und ein weiterer Modellaufruf zur Diagnose war nicht freigegeben. Die kurze Dauer spricht für eine
sofortige Ablehnung durch den Provider, vermutlich wegen des neuen strikten Review-Schemas (verschachtelte Befunde,
nullbare Werte). Das ist nur eine Hypothese. Behoben bzw. verbessert:

- Die UX-Ebene ist jetzt „best effort“: Ein Reviewer-Ausfall wird mit festem Code festgehalten, schaltet den Reviewer für den Rest des
  Laufs ab (kein Retry, kein weiterer Verbrauch) und ändert nie ein objektives Ergebnis oder die Suite. UX bleibt dann NOT_EVALUATED.
- Der Worker meldet bei Provider-Fehlern einen Code aus einer Allowlist (z. B. `PROVIDER_HTTP_400`, `RESPONSE_SCHEMA_MISMATCH`),
  nie Provider-Text, Nutzdaten oder Tokens.
- Der Bericht nennt den Grund einer Stufe auch bei Controller-Fehlern und führt ausgefallene Reviews unter P2.

**Tests nach den Korrekturen:** 323 lokale Tests OK (vorher 311), Commit `65cd318`.

**Antworten auf die Fragen des Auftrags**

1. *Welche BLE-Prozesse funktionieren?* Nicht gemessen. Belegt ist nur, dass BLE die Anlage für ein inaktives Produkt konsistent und ohne Teilanlage
   verweigert.
2. *Welche schlagen fehl?* Keine objektiv belegte Abweichung.
3. *BLE oder SQBF?* Beide Auffälligkeiten liegen im Testaufbau: Fixture-Voraussetzung (P06) und Harness (Reviewer). Eine BLE-Beobachtung ist nur UX-seitig (oben).
4. *Größte UX-Hürden?* Aus diesem Lauf: fehlender Hinweis auf die inaktive Position und alles-oder-nichts-Anlage (unbestätigt). Sonst nicht bewertbar.
5. *Stärkste BLE-Verbesserung?* Nicht belegbar; Kandidat siehe 4.
6. *Reproduzierbar belegt?* Das Verhalten ist einmal beobachtet und durch das Oracle gestützt; nicht wiederholt (kein Retry erlaubt).
7. *BLE-Issues?* Noch keines; erst nach Bestätigung durch die PO bzw. einen weiteren Lauf.
8. *Retest nach BLE-Korrektur?* PLAN mit einer inaktiven Position (Meldung, Planliste) und danach alle zwölf Stufen.
9. *Nicht getestet?* Alle Stufen ab RECEIPT und der gesamte Datenerfassungs-, Rechen-, Bericht- und PDF-Umfang.
10. *Vollständig und valide?* Nein. Die Messung ist **INVALID** und unvollständig (1 von 12 Stufen versucht, keine gültig).

**Nächste Schritte (PO-Entscheidungen).**

1. **P06:** (a) in der isolierten Fixture das Produkt als dokumentierten Vorbereitungsschritt aktivieren (nur `is_active`; der
   zehnteilige Datensatz und alle Messwerte bleiben); (b) das Produkt per BLE-Oberfläche durch den Laborleiter aktivieren lassen
   (zusätzlicher Prozessschritt, Mehrverbrauch, außerhalb des PLAN-Auftrags); (c) P06 aus dem Plan nehmen (ändert den freigegebenen Datensatz).
   Empfehlung: (a), mit Vermerk im Manifest. Die Ablehnung bleibt als BLE-Beobachtung dokumentiert.
2. **Fixture und Freigabe:** Der Lauf hat die Lease verbraucht, auch wenn die Datenbank unverändert ist. Ein Folgelauf braucht eine ausdrückliche
   Freigabe für die Wiederverwendung dieser Fixture (Lease entfernen) oder für eine neue Fixture, dazu eine neue Einzellauf-Freigabe.
3. **Vorab-Probe des Providers (optional, empfohlen):** zwei Mini-Anfragen (Executor- und Review-Schema, leeres Bild) vor dem Lauf, um das
   Review-Schema zu bestätigen. Sie sind noch nicht implementiert und würden separat freigegeben.


## 13. Vorbereitung des Folgelaufs (15.10.2026, nach Lauf 1)

Auf PO-Freigabe: neue isolierte Fixture als Klon mit aktivem P06, und zwei synthetische Provider-Anfragen. Es wurde **kein** weiterer Live-Lauf gestartet.

**Einordnung P06.** Die Inaktivität war am 14.10. bereits als „Kontext, noch kein Messurteil“ in `docs/nsn014-fixture-acceptance.md` festgehalten (zehn Planpositionen, neun aktive Produkte). Die Readiness hat sie aber nicht als Voraussetzung der Plan-Anlage geprüft. Das ist seit `65cd318` ein Gate. Die historische Inaktivität bleibt als eigene UX-Beobachtung erhalten und ist kein bestätigter BLE-Fehler.

**Neue Fixture (Klon).** `suite-fixture-clone` (Commits `1ec5835`, `d7e5709`) hat das Volume der unveränderten Fixture byteweise kopiert und mit einer Prüfsumme über alle Dateien verglichen. Der Klon läuft als Container `sqbf-nsn014-4e460e296674` auf 127.0.0.1:55434 mit eigenem Web auf 5082.

- **Identität des Klons:** Rollen, Rechte, Views, Identitäten und alle vorbereiteten Zeilen sind identisch. Der Hash über **alle 426 öffentlichen Tabellen** ist vor und nach dem Klonen gleich.
- **Override:** Genau eine Spalte einer Zeile ist verändert, nämlich `workspace_products.is_active` von P06 (`false` auf `true`). Der Hash aller übrigen 425 Tabellen ist unverändert. Messwerte, Normzuordnungen, Planpositionen, Berechtigungen und Referenzen sind nicht geändert. Die Zeilen-Hashes vor und nach dem Update und der Hash des Statements stehen im privaten Manifest (`suite_copy.clone`).
- **Neues Manifest:** Neuer Fixture-Startzustands-Hash `15b88c88…` (vorher `5f1e231b…`), neue Fixture-ID und Fixture-Version 0.3. Das Manifest trägt **keine** Budgetfreigabe.
- **Quelle bleibt erhalten:** Der alte Container ist sauber gestoppt (Exit 0), nicht gelöscht. Volume, Runtime, Zugangsdaten, Sessions und die verbrauchte Lease sind unverändert. Der alte Web-Prozess wurde nach Identitätsprüfung beendet (PID gegen das Manifest geprüft). Der geschützte `ble-postgres` auf 5433 blieb unberührt.
- **Sessions:** Vier neue Anmeldungen, genau eine je Persona. Alle vier Sessions stellen wieder her (sie sehen jetzt zehn aktive Produkte), die signierte Identität, die Rolle und der Enzberg-Scope sind bestätigt, und die geschützten Daten sind unverändert. Es wurde keine Anmeldung wiederholt.
- **Lease:** Die neue Fixture hat keine Lease; die Lease der alten bleibt als Beleg.

**Nachweise.** 344 lokale Tests OK (vorher 323). Modellfreie `run-suite`-Readiness mit v0.4.1 und dem neuen Manifest: Alle Gates bestanden, die Readiness bleibt nur an der fehlenden Budgetfreigabe **BLOCKED** (`BUDGET_APPROVAL_MISSING`, `other_gates: PASSED`). Dazu zählen:

- sauberer Quellstand,
- Plan-Produkte, Sessions und Scopes,
- Runtime-Identität,
- Stufenverträge,
- Plan-Formular und Routen,
- leerer Startzustand.

Das ist gewollt: Die Freigabe wird erst mit der neuen Einzellauf-Freigabe eingetragen.

**Provider-Vorabprüfung.** Das Werkzeug `suite-provider-probe` ist gebaut und getestet: zwei synthetische Anfragen, ein generiertes Farbblock-Bild, keine BLE-Daten, kein Retry, und ein gespeichertes Ergebnis mit festen Codes. `run-suite --provider-probe` blockiert bei einer fehlgeschlagenen oder veralteten Probe. Zwei Ausführungsversuche sind beide am Browser-Anmeldefenster (300 s) gescheitert, bevor ein Modell aufgerufen wurde. Die Probe ist deshalb **noch nicht ausgeführt**; Reviewer- und Executor-Schema sind **nicht bestätigt**, und der UX-Benchmark gilt bis dahin nicht als bereit.

**Nachgebessert beim Klonen.** Die ersten Subprozess-Ausgaben liefen mit der Standard-Codepage; Dekodierfehler (von der deutschen `taskkill`-Ausgabe) betrafen keine Prüfausgabe, und alle Prüfungen waren nicht leer und bestanden. Seit `d7e5709` werden Docker- und psql-Ausgaben strikt als UTF-8 gelesen.

**Fehlt noch für einen validen vollständigen Lauf:**

1. Die Probe: Browser-Bestätigung innerhalb von 5 Minuten nach dem Start.
2. Eine **neue ausdrückliche Einzellauf-Freigabe** mit Suite-Version, Commit, Manifest, Provider, Budget und Datengrenze. Danach erstelle ich die freigegebene Manifest-Kopie und wiederhole die Readiness unmittelbar vor dem Start.

## 14. Provider-Probe bestanden (15.10.2026)

Im dritten Versuch hat die Browser-Anmeldung innerhalb des Fensters geklappt. Die Probe hat genau zwei synthetische Anfragen gesendet (generiertes Farbblock-Bild, keine BLE-Daten): **PROBE_PASS**.

| | Modell | Ergebnis | Dauer | Tokens (gesamt) |
|---|---|---|---|---|
| Executor-Schema | gpt-6-luna | akzeptiert, gültige Aktion | 2,8 s | 294 |
| Review-Schema | gpt-6.1-sol | akzeptiert, gültiges Review mit null-Werten und Befund | 4,7 s | 729 |

Beide Modelle stehen im Modellkatalog. Das gespeicherte Ergebnis ist an Modelle und Schema-Hashes gebunden und gilt 12 Stunden.

**Folgerung für Lauf 1:** Das strikte Review-Schema wird akzeptiert. Die Hypothese „Provider lehnt das Schema ab“ ist damit **widerlegt**; die Ursache des ersten Reviewer-Ausfalls bleibt unbewiesen (denkbar sind Eingaben dieser Anfrage, z. B. die Screenshots oder der Aufgabentext). Deshalb schaltet sich der Reviewer erst nach **drei aufeinanderfolgenden** Fehlern ab (`e151761`); jeder Fehler wird mit festem Code vermerkt, und ein Erfolg setzt den Zähler zurück. Ein einzelner Ausfall entfernt also nicht mehr die ganze UX-Ebene, und die Fehlercodes zeigen beim nächsten Lauf die Ursache.

**Readiness** (`run-suite`, v0.4.1, neue Fixture, `--provider-probe`): Alle Gates bestanden, darunter Plan-Produkte (zehn von zehn anlegbar), Probe (`PROBE_PASSED`, UX-Ebene abgesichert), Sessions, Scopes, Runtime und Stufenverträge. Blockiert ist nur `BUDGET_APPROVAL_MISSING`, mit `other_gates: PASSED` und 0 Modellaufrufen. 345 lokale Tests OK.

**Verbleibender Freigabepunkt:** eine neue ausdrückliche Einzellauf-Freigabe mit Suite-Version, Commit, Manifest, Provider, Budget und Datengrenze. Mit ihr trage ich die Budgetfreigabe in eine Manifest-Kopie ein und wiederhole die Readiness unmittelbar vor dem Start.

## 15. Live-Lauf 2 (45eb301f-ea0a-4b93-810e-57deaadbc586) — Ergebnis

**Bewertung: Lauf NO-GO / INVALID_HARNESS. Es liegt weiterhin keine gültige Gesamtmessung vor.** Die PLAN-Stufe war fachlich erfolgreich, wurde aber vom Controller wegen eines Fehlers im Harness ungültig gesetzt; elf Stufen sind NOT_RUN. Der Lauf ist nach Vertrag beendet, es gibt keinen zweiten Versuch.

**Durchführung.** Genau ein Lauf auf PO-Freigabe (PR #10, 15.10.2026): SQBF `06d7a883d48ef0582cb240cf030b3d549ed1e144` (sauber), Suite v0.4.1 (`451796ac…`), Fixture `nsn014-ux-4e460e296674` mit aktivem P06, `chatgpt_plan`, Executor `gpt-6-luna`, Reviewer `gpt-6.1-sol`, Profil `NSN014-CALIBRATION-v2`. Die Freigabe stand in einer neuen, privaten Manifest-Kopie (Hash `83a6bc6e…`); historische Manifeste blieben unverändert. Die Readiness unmittelbar davor war vollständig bestanden (inklusive Probe, Plan-Produkte 10/10, vier Sessions mit Identität und Scope).

**Stufenmatrix (alle zwölf Aufgaben)**

| # | Stufe | Objektiver Status | Grund / Abhängigkeit |
|---|---|---|---|
| 1 | PLAN | **INVALID_HARNESS** | Controller: `STATIC_FIXTURE_CHANGED` (Fehlalarm, siehe unten). Evidenz der Stufe selbst: Oracle PASS |
| 2–12 | RECEIPT, PREPARATION, SIEVE, SHAPE, BOILING, SE, ASSESS, WPK, ANALYSIS, REPORT, RIGHTS | **NOT_RUN** | `UPSTREAM_CRITICAL_STOP`; alle hängen von PLAN ab |

Die Status werden so ausgewiesen, wie der Lauf sie erzeugt hat. Es ist keine Stufe als PASS markiert.

**PLAN im Detail**
- **Objektiv:** Der unabhängige Receipt-Oracle (`after_plan`) bestätigt **10 von 10** planverknüpfte Proben (Identität, Besitzer, Produkt, Kunde/Projekt, Probenahmedatum, Planposition), keine fehlenden oder abweichenden Positionen, 0 LIMS-Datensätze und keine verwaisten. Die Anlage geschah genau einmal (ein Klick, ein Executor-Abschluss).
- **Technisch:** 29,9 s Stufenlaufzeit, 34,3 s gesamt. Sichtbar: BLE zeigt „10 Probe(n) angelegt.“ und die Proben-IDs `ENZBERG-20260508-NSN-014-01` bis `-10`.
- **Modellverbrauch:** **3 von 1.500 Anfragen** (0,2 %): Executor 2 (3,7 s und 4,8 s; 1.616 und 1.710 Tokens), Reviewer 1 (19,1 s; 3.710 Tokens). Zeitverbrauch 34 von 10.800 s. Keine unbekannte Nutzung. Das Ressourcenlimit war nie erreicht.
- **UI-Aktionen:** 1 Klick, dann „done“. Keine abgelehnte Aktion, kein Stillstand.
- **Reviewer (UX, `nsn014-ux-rubric-v1`):** Auffindbarkeit 5, Klarheit 4, Aufgabenfortschritt 5, Fehlerbehandlung **NOT_EVALUATED** (kein Fehlerfall sichtbar). Der Reviewer-Aufruf hat diesmal funktioniert; der Ausfall aus Lauf 1 trat nicht auf.
- **Findings des Reviewers (unbestätigt):** (a) *UX_IMPROVEMENT, minor:* Die grüne Erfolgsmeldung liegt rechts unten über den Zeilen 9 und 10 und verdeckt dort den Status. Die Zustandskontrolle aller zehn Positionen ist gleichzeitig erschwert (Bild 2). (b) *UNCLEAR, info:* Die Executor-Aussage „alle Positionen stehen auf Neu“ war wegen dieser Überlagerung nicht vollständig unabhängig ablesbar.

**Blocker und technische Ursache (Harness, SQBF).** Nach jeder Stufe vergleicht der Controller die geschützten Tabellen mit dem Ausgangszustand; nur fünf Tabellen waren als veränderlich zugelassen. Die genehmigte Plan-Aktion von BLE stempelt aber die Audit-Spalten der Planzeile: `sampling_plans.updated_at` (exakt zum Klick-Zeitpunkt 14:04:19 UTC) und `updated_by`. Der Controller hat diese legitime Nebenwirkung der freigegebenen Fähigkeit als Datenänderung gewertet, die Stufe auf INVALID_HARNESS gesetzt und die Suite beendet. Beim Klonen und in Lauf 1 trat das nicht auf, weil dort kein BLE-Schreibzugriff stattfand.

**Beleg aus den Daten.** Gegenüber der unverändert erhaltenen Quell-Fixture (schreibgeschütztes Volume, temporäre Kopie, danach entfernt) unterscheidet sich in den **16 geschützten Tabellen** nur `workspace_products` (der dokumentierte P06-Override). `sampling_plans` ist ohne Audit-Spalten identisch. Es gibt keine Änderung an Referenzdaten, Normen, Messwerten, Produkten oder Rechten durch den Lauf.

**Korrektur (Commit `049a3f8`, 354 Tests OK).** Das Gate vergleicht eine abweichende Tabelle zusätzlich ohne `updated_at` und `updated_by` mit dem bei der Readiness erfassten Zustand. Nur eine reine Audit-Differenz wird toleriert und im Stufenergebnis und in den Abschluss-Oracles ausgewiesen (`audit_only_changes`). Jede substanzielle Änderung, jede Zeilenzahl-Änderung und jede Änderung der Tabellenmenge bleibt ein harter Stopp. Die Korrektur ist nur offline getestet und in einem echten Lauf noch nicht bestätigt.

**Abschluss-Oracles dieses Laufs:** Der Receipt-Oracle meldet FAIL für `after_modules` (P01 verlangt nach den Modulstufen einen LIMS-Datensatz, die Modulstufen liefen nicht), Messwerte, Zuteilungen und Reports FAIL, weil nichts erfasst oder generiert wurde (Folge von NOT_RUN, kein BLE-Befund). Berechnungen: PASS ohne Gegenstand (kein Report). Die Gesamtwerte dieses Laufs sind damit nicht aussagekräftig.

**Sicherheit und Datenintegrität.** Vor dem Lauf und je Stufe: Persona-Scope und signierte Identität bestanden; Fixture-, Datenbank- und Runtime-Identität; vier gültige Sessions; Plan-Produkte 10/10. Der Executor erhielt nur Screenshots, die Aufgabe und seine Aktionsliste, keine Zugangsdaten, Tokens oder Cookies. Der Reviewer erhielt ausgewählte Screenshots und die als unverifiziert markierte Executor-Aussage. Gemessene Originalwerte (K3) wurden noch nicht an ein Modell gesendet, da keine Messstufe lief. Die Quell-Fixture, die Golden-Quelle und alle historischen Artefakte sind unverändert. Die verbrauchte Fixture enthält jetzt 10 Proben und eine Lease.

**Findings getrennt**

| Art | Befund | Status |
|---|---|---|
| BLE-Produkt | Keine objektive Abweichung. Die planbezogene Anlage von zehn Proben funktioniert (Oracle PASS). | belegt |
| BLE-UX (unbestätigt) | Erfolgsmeldung verdeckt Status der Positionen 9 und 10 bei 1280×800. | kein Issue |
| BLE-UX (unbestätigt, aus Lauf 1) | Meldung zum inaktiven Produkt nennt es nicht, Planliste markiert es nicht. | kein Issue |
| SQBF-Harness | Statisches Gate wertete Audit-Stempel einer genehmigten BLE-Aktion als Datenänderung. | behoben, offline getestet |
| SQBF-Harness (Prozess) | Der Schreibpfad der freigegebenen Fähigkeit war vor dem Live-Lauf nicht gegen reale BLE-Nebenwirkungen geprüft. Eine Nachprüfung der übrigen Stufen steht aus. | offen |

**Artefakte (privat, schreibgeschützt, außerhalb von Git).** `run.json`, `cases.json`, `accounting.json`, `completion-report.md`, Events, zwei Screenshots. Hash-Manifest: `45eb301f-…-artifact-hashes.json` (Wurzel-Hash `bf441c57…`); `run.json` hat den SHA-256 `c1a277b3…`.

**Antworten auf die Fragen des Auftrags:** (1) Funktionierend: die planbezogene Probenanlage. (2) Scheiternd: nichts belegt. (3) Fehler: SQBF (Harness), nicht BLE. (4) UX-Hürden: nur die verdeckende Erfolgsmeldung, schwach belegt. (5) Verbesserung: Meldung außerhalb der Tabelle platzieren, inaktive Produkte kenntlich machen (beides unbestätigt). (6) Reproduzierbar belegt: bisher nur die Plananlage. (7) Issues: keines. (8) Retest: PLAN, danach alle zwölf Stufen. (9) Nicht getestet: alle Stufen ab RECEIPT. (10) Vollständig und valide: **nein**.

**Für einen Folgelauf nötig:**
1. Eine neue Fixture aus der unveränderten Quell-Fixture mit P06-Override. Das Klon-Werkzeug erwartet eine laufende Quelle mit Web; die Quelle ist gestoppt. Für den Weg gilt: die aktuelle Fixture stoppen, die Quelle starten und klonen. Das ist ein zusätzlicher Arbeitsschritt.
2. Eine neue ausdrückliche Einzellauf-Freigabe.
3. Vorab, soweit möglich, eine Prüfung der erwarteten BLE-Nebenwirkungen der übrigen Stufen: Auch dort könnten Audit-Stempel oder weitere Tabellen betroffen sein. Das Gate bleibt bei jeder substanziellen Änderung strikt.

## 16. Vorbereitung des dritten Laufs (15.10.2026, Issue #21): neue Fixture, Seiteneffekt-Vertrag, vollständiger Trockenlauf

**Bewertung: modellfrei vorbereitet, technisch geprüft. Es gab keine Modellaufrufe, keinen dritten Live-Lauf und keinen Merge. Der einzige offene Blocker der Readiness ist `BUDGET_APPROVAL_MISSING`.** Das Ziel dieses Abschnitts ist, die Ursache wiederholter `INVALID_HARNESS`-Abbrüche zu beseitigen: Statt nach jedem Live-Lauf einen einzelnen Controller-Fehler zu reparieren, wurde die gesamte Prozesskette vorab gegen echtes BLE-Verhalten gelaufen.

### 16.1 Vorgehen

1. **Neue, vollständig isolierte Fixture** `nsn014-ux-e781d1466b55` (Container `sqbf-nsn014-e781d1466b55`, Web 5082, PostgreSQL 55434, Purpose `fixture`). Quelle ist die verifizierte, gestoppte und nie gestartete Quell-Fixture; das Volume wurde byteweise kopiert und gegen die beim Stoppen festgehaltene Prüfsumme (`9ae39dba…`) verglichen; der Klon stimmt in den 22 geschützten Tabellen mit der vorbereiteten Baseline überein. Danach wurde der Hash aller 426 öffentlichen Tabellen vor und nach Override und Replay verglichen: verändert sind genau `workspace_products` (P06 aktiv) sowie die zwei replizierten Konfigurationstabellen. Im Manifest steht keine Budgetfreigabe; es gibt keine Lease. Die bisherigen Fixtures (Quelle, Lauf 1, Lauf 2, vier Wegwerfkopien) bleiben unverändert erhalten.
2. **Wegwerfkopien für Trockenläufe.** Fünf Kopien derselben Quelle (`--purpose scratch`). Auf ihnen lief ein skriptgesteuerter, modellfreier „idealer Executor“ durch die UI, mit einem Zeilen- und Spaltendiff über alle Tabellen vor und nach jeder Aktion (nur Tabellen, Zähler und Spaltennamen, keine Werte) und den unabhängigen Oracles auf den realen, von BLE geschriebenen Daten.
3. **Vollständiger Lauf in der Reihenfolge des Runners** (Kopie 5): alle zwölf Stufen, jede Stufe in `guarded_stage` mit dem echten Vertrag. Ergebnis siehe 16.4.

### 16.2 Befunde des Trockenlaufs und ihre Behebung

| # | Befund (belegt durch Diff oder Oracle auf echten Daten) | Wirkung im Live-Lauf ohne Behebung | Behebung |
|---|---|---|---|
| 1 | **Fehlende Produktkonfiguration:** Die Fixture hatte keine Zeilen in `lims_product_test_modules` und nur die 28 generischen `workspace_sampling_rules`. BLE sperrte Messformulare und bot nur 2 von 9 Entnahmekarten an. | Messstufen unausführbar | Replay aus der normalen lokalen BLE-Datenbank (nur lesend): 51 Modulzeilen, 37 Produktregeln; deterministische Ids, Tabellenhash vorher/nachher belegt genau diese zwei Änderungen. |
| 2 | **Audit-Stempel:** Plananlage stempelt `updated_at`/`updated_by` genau einer Zeile von `sampling_plans`. Die erste Korrektur duldete reine Audit-Differenzen in jeder geschützten Tabelle und jeder Stufe. | zu breite Toleranz | Vertrag: genau eine Freigabe (Stufe PLAN, Tabelle `sampling_plans`, Zielzeile = Plan-Id, Spalten `updated_at`/`updated_by`, höchstens eine Zeile). In jeder anderen Stufe, Tabelle, Zeile oder Spalte bleibt jede Änderung ein harter Stopp. |
| 3 | **Dezimalpunkt:** BLE parst de-DE; ein Punkt ist ein Tausendertrenner. „557.9“ wurde als 5579 gespeichert (Waschen P01/P02, ×10), ohne Fehlermeldung. | stille Datenverfälschung, falsches FAIL | Executor erhält und der Guard erlaubt nur deutsche Schreibweise (Komma). Ein Punkt wird abgelehnt. Anweisung ergänzt. |
| 4 | **Pfannenzeile der Hauptsiebung** heißt „Boden“, „Pfanne“ oder „Anteile gesamt < x mm“ und gehört zu Sieb 0; der Guard kannte nur Siebweiten und blockierte das Feld. | Feld nie eingebbar | Zeilenzuordnung im Guard. |
| 5 | **Teilsiebung:** „K-Basis“ ist schreibgeschützt (aus Feuchte/Abschlämmung berechnet); der Pfannenverlust je Turm wird nicht gespeichert (NULL), BLE zeigt ihn nur als „Siebverlust“. | Position stets unvollständig bzw. falsches FAIL | beide sind keine Eingabefelder mehr; der Pfannenverlust wird im Oracle nicht verglichen, alle anderen Punktwerte weiter exakt. |
| 6 | **Report-Oracle:** BLE speichert den Status `DRAFT`, das Oracle erwartete `Draft` und lehnte jeden Bericht ab. | REPORT würde trotz korrekter Berichte FAIL/INCONCLUSIVE (Stufe 11 von 12) | Erkennung unabhängig von der Schreibweise; jeder andere Status bleibt kein Entwurf. |
| 7 | **PDF-Identität:** BLE bricht die Probennummer nach einem Bindestrich um („…0508- NSN-014-02“); die Textprüfung fand den Code nicht. | alle PDFs „IDENTITY_TEXT_MISSING“ | Vergleich ohne Leerraum. |
| 8 | **Lazy LIMS-Daten:** „Teilsiebung starten“ legt Kunde, Produkt, Projekt, Probe und Prüfverfahren im LIMS an. Die ersten Ergebnisspeicherungen legen `lims_probe_test_modules` an. | unbekannte Tabellen | im Vertrag je Stufe geführt; nicht gelistete Schreibzugriffe sind Befunde ohne Abbruch. |
| 9 | **Diagnose:** `side_effect_probe` meldete nur „psql failed“; `scope_check` decodierte lokalisierte PowerShell-Fehlertexte mit der Plattform-Codepage und beendete einen Reader-Thread. | schwer auffindbare Controller-Fehler | Fehlerzeile und UTF-8. |

### 16.3 Seiteneffekt-Vertrag (Stufen, Aktionen, Tabellen, Zielzeilen)

Der Vertrag liegt unter `projects/ble-elva/suites/enzberg-nsn014-side-effects-v1.json` und ist im Lauf-Manifest über seinen Hash festgelegt (die Suite v0.4.1 und ihr Hash `451796ac…` bleiben unverändert).

| Stufe | Modus | Beobachtete Schreibzugriffe im Trockenlauf |
|---|---|---|
| PLAN | schreibend | `samples` +10, `probe_applied_standards` +10; Audit-Stempel auf 1 Zeile `sampling_plans` |
| RECEIPT, ASSESS, WPK, ANALYSIS, RIGHTS | lesend | keine |
| PREPARATION | schreibend | Entwurf: `lims_sieblinie_ergebnis`/`_punkt`; Eingabe: `workspace_sampling_info`, `lims_agg_uf_fine_tests`; erste Speicherung: `lims_probe_test_modules` |
| SIEVE | schreibend | `lims_sieblinie_*`, `workspace_sampling_info`, `workspace_work_items`, `samples`, `lims_probe_test_modules`; Teilsiebung: `lims_customer`, `lims_product`, `lims_project`, `lims_sample`, `lims_sample_portion`, `lims_sample_test`, `lims_test_method`, `lims_sample_derived_*` |
| SHAPE | schreibend | `workspace_particle_shape_results`, `…_fraction_results`, `workspace_work_items`, `lims_probe_test_modules` |
| BOILING | schreibend | `workspace_boiling_test_results`, `workspace_work_items`, `lims_probe_test_modules` |
| SE | schreibend | `workspace_sand_equivalent_results`, `workspace_work_items`, `lims_probe_test_modules` |
| REPORT | schreibend | `ble_reports` +1, `workspace_probe_report_entries` +1 je Bericht; der PDF-Download schreibt nichts |

Prüfung im Runner (`stage_effects.py`, `guarded_stage`, getrennt von den Oracles):
- **Hart (INVALID_HARNESS):** geschützte Tabellen der vorbereiteten Baseline ändern sich außerhalb der einen Freigabe, auch durch denselben Stempel in einer anderen Stufe; oder eine Stufe beginnt nicht exakt im Endzustand der vorherigen (Schreibzugriff außerhalb der Suite: BLOCKED).
- **Befund ohne Abbruch:** jede andere Tabelle (Hash aller 426 öffentlichen Tabellen, Controller READ ONLY, rund 1 s je Aufnahme), die eine Stufe ändert, ohne dass der Vertrag sie nennt (`UNEXPECTED_TABLE_WRITE`), und jede Änderung in einer lesenden Stufe (`WRITE_IN_READ_ONLY_STAGE`). Das verhindert, dass ein legitimer, im Trockenlauf nicht gesehener BLE-Schreibzugriff erneut zum Abbruch führt, und macht ihn trotzdem sichtbar.
- Die Abschluss-Prüfung vergleicht den Endzustand mit der vorbereiteten Baseline unter derselben einen Freigabe und weist Umfang und Befunde aus.

### 16.4 Ergebnis des vollständigen Trockenlaufs (Kopie 5, Reihenfolge des Runners)

Alle zwölf Stufen liefen durch, **ohne harten Stopp, ohne Befund des Vertrags und ohne externe Änderung zwischen den Stufen**; einzige geschützte Änderung ist der freigegebene Stempel auf einer Zeile `sampling_plans`. Abschluss-Oracles auf den echten Daten:

| Oracle | Ergebnis |
|---|---|
| Statisches Gate (Baseline, Vertrag) | unverändert; Stempel: `sampling_plans`, 1 Zeile, `updated_at`/`updated_by` |
| Empfang (`after_modules`) | PASS (10 Proben, 1 LIMS-Probe, keine verwaiste) |
| Waschen, Siebung, Teilsiebung, Kochen, Sandäquivalent | PASS |
| Berichte (10 Berichte, 10 PDFs, Identität, Zahlen) | PASS |
| Berechnungen (Nachrechnung aus gespeicherten Rohwerten) | PASS |
| Zuteilungen | FAIL für **P01 und P06** (siehe 16.5) |
| Kornform | FAIL für **P06** (siehe 16.5) |

### 16.5 Was BLE in der echten Reihenfolge nicht anbietet (Abweichung Referenz gegen Produktkonfiguration)

In der Reihenfolge des Runners (je Position erst Zuteilungen, dann Waschen) bietet BLE drei Referenzwerte nicht an. Das ist weder ein Fehler des Executors noch des Harness:

| Position | Fehlt | Ursache (aus den Daten belegt) |
|---|---|---|
| P01 | Entnahme „Koch 8 mm“ | Solange eine Probe kein gespeichertes Ergebnis hat, leitet BLE die Entnahmekarten aus den **Produktmodulen** ab; das Produkt von P01 führt das Kochmodul nicht. Nach der ersten Speicherung (Probenmodulzeilen aus den Normen) erscheint die Karte. |
| P06 | Kornform-Zuteilungen 16 und 22,4 mm und die Kornform-Messung | Das Produkt von P06 hat das Kornform-Modul in der Kundenkonfiguration **inaktiv** (in der Quelle ebenso; der Replay kopiert die Werte). Die Referenzdaten enthalten Kornformwerte. |

Zusätzlich beobachtet (kein Fehlalarm, aber relevant für die Reihenfolge): Fünf Produkte (P01, P05, P06, P09, P10) schließen die Kornform-Prüfverfahren aus. Die Kornform-Karten erscheinen deshalb **nur, solange eine Probe noch kein gespeichertes Ergebnis hat**; die erste Speicherung (z. B. Waschen) legt die Probenmodulzeilen unter Beachtung dieses Ausschlusses an, danach fehlen die Karten. Das Ergebnis einer Stufe hängt damit von der Reihenfolge ab. Der Runner arbeitet je Position erst Zuteilungen, dann Waschen; in dieser Reihenfolge sind alle Kornform-Werte außer denen von P06 erreichbar. In meiner ersten Trockenlauf-Reihenfolge (Waschen zuerst) waren sie es nicht, was den Befund aufdeckte.

**Behandlung im Harness.** Der Runner erfasst je Position, welche der freigegebenen Felder die Seite angeboten hat. Waren Felder nicht vorhanden und wurde alles Vorhandene eingegeben und gespeichert, ist die Position `INCOMPLETE` mit `APPROVED_FIELDS_NOT_PRESENT_ON_PAGE`, niemals `FAIL`. Die Stufen PREPARATION und SHAPE werden dadurch bei einem idealen Executor `INCONCLUSIVE` bleiben, mit acht bzw. vier bestandenen Positionen im Positionsergebnis. Die Klassifikation ist offline getestet und im Live-Lauf noch nicht bestätigt. **Es wurden weder Referenzdaten noch Kundenkonfiguration verändert.**

**Entscheidungsvorschlag für den PO (vor dem Live-Lauf):**
- A (Empfehlung für den ersten Realwert-Lauf): so lassen. Die Abweichung ist ein echtes, reproduzierbares BLE-Ergebnis der Kundenkonfiguration.
- B: dokumentierter Fixture-Override (Kornform-Modul von P06 aktivieren), analog zum Override für das inaktive Plan-Produkt. Das ist eine Abweichung von der Kundenkonfiguration und ändert, was das Benchmark misst; deshalb nicht ohne PO-Entscheidung.
- C: Referenz korrigieren (die drei Werte als „nicht eingebbar“ markieren). Gleiches Argument; ändert die freigegebene Referenz.
- D: für P01 eine zweite Zuteilungsrunde nach dem Waschen. Ändert den Ablauf der Stufe und die Anfragezahl.

### 16.6 Readiness (modellfrei, Suite v0.4.1, neue Fixture)

`run-suite` ohne `--execute`, mit der Provider-Probe vom 15.10.2026 (`PROBE_PASSED`, UX-Ebene abgesichert, 5,6 h alt, gültig 12 h): alle Gates bestanden (Quell-Commit sauber, Referenzen und Suite gebunden, Stufenverträge, Seiteneffekt-Vertrag geladen, Hash aller öffentlichen Tabellen, Baseline, Runtime, leerer Start, Plan-Produkte 10 von 10, Plan-Formular, Einstiegsrouten, vier Sessions mit Scope), **0 Modellaufrufe, 0 Schreibzugriffe**. Blockiert ist nur `BUDGET_APPROVAL_MISSING` (Profil `NSN014-CALIBRATION-v2`, 1.500 Anfragen / 10.800 s; Mindestbedarf 640 Anfragen). Die Budgetfreigabe bleibt bis zu einer ausdrücklichen PO-Freigabe der erwartete letzte Blocker.

### 16.7 Tests

**399 Tests OK** (vorher 367): Vertrag (Schema, zwölf Stufen, ungültige Verträge), zeilengenaue Audit-Freigabe (positiv und alle Negativfälle: andere Zeile, andere Spalte, andere Stufe, andere Tabelle, hinzugefügte oder entfernte Zielzeile), Stufenfolge (Start ≠ Ende der Vorstufe), Befunde, Sammler (nur SELECT, READ ONLY, keine unsicheren Bezeichner), Dezimalkomma, Pfannenzeile, abgeleitete Teilsiebwerte, `APPROVED_FIELDS_NOT_PRESENT_ON_PAGE` gegen echte Auslassung und FAIL, Berichtsstatus, umbrochene Probennummer im PDF.

### 16.8 Grenzen und offene Punkte

- Der Trockenlauf ist ein idealer, skriptgesteuerter Executor. Er belegt, dass die Kette technisch tragfähig ist, nicht, dass ein Modell sie bewältigt. Neue Schreibpfade, die nur ein Modell findet, melden sich als Befund `UNEXPECTED_TABLE_WRITE`, nicht als Abbruch.
- Die Trockenlauf-Skripte liegen privat im Scratchpad dieser Sitzung (Pfade siehe Bericht in Issue #21), nicht im Repository.
- Zwei BLE-Beobachtungen sind **unbestätigt** und noch nicht als Issue angelegt (Vorschlag an den PO): (1) stille Fehlinterpretation von Dezimalpunkten in Messfeldern (kein Hinweis, Wert ×10); (2) Entnahmekarten hängen davon ab, ob die Probe schon ein gespeichertes Ergebnis hat (Rückfallpfad über Produktmodule, danach Pfad über Probenmodule mit Ausschlüssen).
- Die Provider-Probe gilt bis 16.10.2026, 01:18 UTC; danach ist eine neue nötig (zwei synthetische Anfragen, OAuth-Anmeldung des PO).

## 17. Live-Lauf 3 (413f7abe-71ad-4027-97a8-27760a5c5378) — Ergebnis

**Bewertung: PARTIAL GO. Technisch vollständig durchgelaufen (alle zwölf Stufen, kein Harness-Abbruch), funktional aber nur zwei Stufen entschieden.** PLAN und WPK sind PASS, zehn Stufen INCONCLUSIVE. Es liegt keine objektiv belegte BLE-Abweichung vor und keine einzige Messung wurde erfasst. Der Lauf ist nach Vertrag beendet, es gibt keinen zweiten Versuch; die Fixture `nsn014-ux-e781d1466b55` ist verbraucht (Lease).

**Durchführung.** Genau ein Lauf auf PO-Freigabe vom 16.10.2026 (Antwort „Ja, 1 Lauf so starten“): SQBF `ef06e389…`, Suite v0.4.1 (`451796ac…`), `chatgpt_plan`, Executor `gpt-6-luna`, Reviewer `gpt-6.1-sol`, Profil `NSN014-CALIBRATION-v2`. Die Freigabe stand in einer neuen, privaten Manifest-Kopie. Davor: Sessions erneuert (je Persona ein Login), neue Provider-Probe `PROBE_PASSED`, Readiness `READY_FOR_SINGLE_SUITE_RUN` (Budget freigegeben).

**Verbrauch (für die Einschätzung des Abo-Kontingents).** 124 von höchstens 1.500 Anfragen (Executor 73, Reviewer 51), 271.478 Tokens gesamt (Executor 126.415, Reviewer 145.063; alle Werte bekannt), 1.461 s von 10.800 s (Modellwartezeit 1.315 s). Eine Anfrage kostet im Mittel rund 2.200 Tokens, der Reviewer rund 2.800, der Executor rund 1.700. Ein vollständiger Durchlauf mit allen Eingaben braucht nach der Untergrenze mindestens 640 Anfragen, also grob das Fünffache dieses Laufs.

| Stufe | Status | Anfragen (Exec/Rev) | Aktionen und Grund |
|---|---|---|---|
| PLAN | **PASS** | 2/1 | 1 Klick, Oracle `after_plan` 10 von 10 |
| RECEIPT | INCONCLUSIVE | 1/1 | erste Aktion (Klick) abgelehnt (`INSPECTION_ACTION_SCOPE_DENIED`) |
| PREPARATION | INCONCLUSIVE | 14/14 | 12 von 14 Aufgaben: erste Aktion abgelehnt (`MEASUREMENT_ACTION_SCOPE_DENIED`), 2 mal vom Modell selbst „blocked“ |
| SIEVE, SHAPE, BOILING, SE | INCONCLUSIVE | 11/11, 5/5, 4/4, 1/1 | in jeder Aufgabe die erste Aktion abgelehnt |
| ASSESS, ANALYSIS, RIGHTS | INCONCLUSIVE | je 1/1 | erste Aktion abgelehnt |
| WPK | **PASS** | 1/1 | „done“ ohne Aktion |
| REPORT | INCONCLUSIVE | 31/10 | 8 angenommene Klicks (Menü öffnen), 9 Ablehnungen (jeweils nach dem Öffnen), 13 Scrolls, 1 „blocked“; kein Bericht erzeugt |

**Was der Lauf bestätigt hat.** Die Vorbereitung hat gewirkt: kein Harness-Abbruch, der Audit-Stempel wurde nur an der freigegebenen Stelle toleriert (`sampling_plans`, 1 Zeile, `updated_at`/`updated_by`), das Abschluss-Gate meldet die geschützten Daten als unverändert, es gibt keinen Seiteneffekt-Befund und die Berechnungen sind PASS. Nach den Abschluss-Oracles enthält die Fixture nur die zehn Plan-Proben (keine Messdaten, keine Berichte). Die Abschluss-Oracles Empfang, Messwerte, Zuteilungen und Berichte sind FAIL, weil nichts erfasst wurde; das ist Folge der Ablehnungen und kein BLE-Befund.

**Ursachen (Harness, SQBF; durch Quelltext und Live-DOM belegt).**
1. **REPORT, sicher:** Das Menü der Probe öffnet sich, aber der Eintrag „Prüfbericht“ ist in BLE ein `div.mud-menu-item`. Der Inspektions-Guard erkennt nur `button` und `.mud-list-item` und stuft den Eintrag als „blocked“ ein. Ein Bericht kann so nie erzeugt werden. Mein Trockenlauf hat den Eintrag direkt per Playwright geklickt und den Guard dabei nicht durchlaufen.
2. **Messstufen, sehr wahrscheinlich:** Die echte Probenseite stellt „Nächster Schritt: Testauftrag erzeugen“ als Hauptaktion dar und meldet „Testauftrag erzeugen, um Module zu starten“. Der Guard erlaubt diese Schaltfläche nicht (sie schreibt Arbeitsschritte). Das Modell folgt der Seite und wird abgelehnt; zwei Aufgaben haben es als „blocked“ begründet. Die „Erfassen“-Links der Modulkarten sind echte Links und für das passende Modul erlaubt (nachgeprüft); eine erfolgreiche Nutzung ist in keiner Aufgabe protokolliert. Der Trockenlauf ist per Direkt-URL direkt in die Modulseite gegangen und hat diesen Einstieg nie gesehen.
3. **Eine abgelehnte Aktion beendet die Aufgabe.** Die erste Ablehnung setzt die Aufgabe auf REJECTED, das Modell bekommt keine zweite Chance. Das macht jeden Fehlklick zum Totalverlust der Aufgabe.
4. **RECEIPT, ASSESS, ANALYSIS, RIGHTS:** Auch hier endete die Aufgabe an der ersten Ablehnung. Welches Element geklickt wurde, ist nicht festgehalten (abgelehnte Aktionen wurden ohne Ziel protokolliert). Ob das ein Guard-Defekt oder ein erlaubnisfreies Element war, ist offen.

**Ehrliche Einordnung.** Das ist erneut ein Harness-Befund, kein BLE-Befund, diesmal aber kein Abbruch, sondern ein zu enger Guard in Verbindung mit einem Trockenlauf, der den Guard umgangen hat. Der Lauf hat gezeigt, dass die technische Kette (PLAN, Seiteneffekt-Vertrag, Oracles, Budget, Konten) trägt und die UX-Ebene arbeitet. Die Reviewer-Befunde („Scope-Denied“, „Testauftrag erzeugen“) sind unbestätigte Beobachtungen.

**Nächste Schritte (alle modellfrei, vor einem weiteren Lauf):**
1. Guard-Defekt „Prüfbericht“ beheben (MudMenuItem) und alle Klickziele der Inspektions- und Messguards gegen das echte DOM prüfen.
2. Abgelehnte Aktionen ohne Wirkung zurückmelden und die Aufgabe fortsetzen (bis zu einer kleinen Obergrenze je Aufgabe) und das Ziel (Rolle, Beschriftung) der abgelehnten Aktion protokollieren.
3. PO-Entscheidung: Soll „Testauftrag erzeugen“ als einmalige Einrichtungsaktion je Probe erlaubt werden (BLEs eigener Prozessschritt, schreibt Arbeitsschritte), oder soll die Aufgabe das Modell auf „Erfassen“ hinweisen?
4. Der Trockenlauf läuft künftig mit dem echten Guard in der Schleife (skriptgesteuerter Executor, der nur Aktionen ausführt, die der Guard zulässt) und beginnt wie das Modell auf der Probenübersicht. Danach neue Fixture und neue Freigabe.

Rohdaten: privat in `D:/Temp/sqbf-regular-runs/413f7abe-…` (Ereignisse, Screenshots, `run.json`, `cases.json`, `accounting.json`).

## 18. Behebung der Fehler aus Lauf 3 und Trockenlauf mit echtem Guard (16.10.2026)

**Bewertung: Die Harness-Fehler aus Lauf 3 sind behoben und in einem vollständigen, modellfreien Durchlauf mit den echten Guards nachgewiesen (`DRY_RUN_COMPLETED`). Es gab keine Modellaufrufe und keinen weiteren Live-Lauf.** Ein vierter Lauf braucht eine neue Fixture (liegt bereit) und eine neue ausdrückliche Freigabe.

### 18.1 Warum der Trockenlauf Lauf 3 nicht verhindert hat

Mein erster Trockenlauf (Abschnitt 16) ging per Direkt-URL in die Modulseiten und klickte Menüeinträge mit Playwright. Er hat die Guards deshalb nie durchlaufen. Das Modell startet dagegen auf der Probenseite und kann nur über den Guard handeln. Lauf 3 hat das offengelegt. Die Konsequenz ist ein neues Werkzeug, das den gesamten echten Stufenpfad ausführt und nur die Modelle ersetzt.

### 18.2 Das Werkzeug `suite-dry-run`

`python -m sqbf.cli suite-dry-run …` führt alle zwölf Stufen über denselben Code wie ein Live-Lauf aus: Persona-Scope, Stufenläufer, beide Guards (Ereignisskript und Controllerprüfung), Transportrichtlinie, Seiteneffekt-Vertrag je Stufe, unabhängige Oracles und Abschluss-Gates. Ersetzt sind nur die Modelle: der Executor durch einen skriptgesteuerten Stellvertreter, der dieselben strikten JSON-Aktionen liefert (Klick mit Koordinaten, Text, Taste, Scrollen, Warten, done/blocked), ausgehend von der Probenübersicht wie das Modell; der Reviewer durch eine neutrale Bewertung. Das Werkzeug verweigert jede Fixture, die nicht als Wegwerfkopie (`--purpose scratch`) angelegt wurde oder deren Lease schon vergeben ist. Eine abgelehnte skriptierte Aktion gilt als Lücke der Guards (`guard_coverage_gaps`), nie als BLE-Befund. Es ist ab jetzt Vorbedingung jedes Live-Laufs.

### 18.3 Gefundene und behobene Fehler

| # | Fehler (belegt) | Wirkung im Live-Lauf | Behebung |
|---|---|---|---|
| 1 | Menüeintrag „Prüfbericht“ ist in BLE ein `div.mud-menu-item`; der Guard kannte nur `button` und `.mud-list-item`. | REPORT konnte nie einen Bericht erzeugen (Lauf 3). | Erkennung von `.mud-menu-item` und `[role=menuitem]`; „Probe löschen“ bleibt gesperrt. |
| 2 | Die erste abgelehnte Aktion beendete die Aufgabe. | 11 von 12 Aufgaben in Lauf 3 ohne Beobachtung. | Eine abgelehnte Aktion hat keine Wirkung, wird dem Executor als `rejected_by_controller` zurückgemeldet und das Ziel (Rolle, Beschriftung, nie Werte) protokolliert; die Aufgabe endet erst nach drei Ablehnungen. |
| 3 | Hauptaktion „Testauftrag erzeugen“ der Probenseite war nicht erlaubt. | Messstufen: Aufgabe an der ersten Aktion beendet. | Einmalig je Probe erlaubt. Die Aktion schreibt nur `workspace_work_items` (eine Zeile je Pflichtmodul) und den Probenstatus, nicht die Probenmodulzeilen (gemessen); die Entnahmekarten bleiben unverändert. Seiteneffekt-Vertrag ergänzt. |
| 4 | Lesestufen kannten je Seite nur zwei Bedienelemente (z. B. 2 von 57 auf der Probenliste). | RECEIPT, ASSESS, ANALYSIS, RIGHTS an der ersten Aktion beendet. | Liste rein darstellender BLE-Bedienelemente (Schnellfilter, Ansichten, Sortierung, Zeiträume, Tabs, Auswahllisten, Kennzahlenkacheln, Probencodes, Anker auf derselben Seite) und die Modulseiten der Proben als lesende Ziele. Alles Schreibende bleibt gesperrt (getestet: Neue Probe, Plan bearbeiten, Abschließen, Archivieren, Löschen, Prüfbericht erstellen, Speichern u. a.). |
| 5 | Schreibprüfung der Messstufe verglich den ganzen Empfangs-Zustand. | „Teilsiebung starten“ legt die LIMS-Probe an, SIEVE wäre `INVALID_HARNESS` (`UNRELATED_MEASUREMENT_WRITE`). | Verglichen werden nur Probenidentitäten und Planpositionen. |
| 6 | Report-Oracle rechnete mit leeren Werten. | Eine halb erfasste Kornform-Fraktion löste `TypeError` aus, REPORT wurde BLOCKED und beendete die Suite. | Fehlende Werte liefern keine Erwartung. |
| 7 | Mausrad über einem Eingabefeld wurde komplett unterdrückt. | Die Seite war über der Feldspalte nicht scrollbar (Siebtabelle: halbe Breite); ein Modell würde stillstehen. | Nur das fokussierte Feld wird geschützt. |
| 8 | Vorbelegte Felder (Einwaage aus der Zuteilung, Rest der Siebzeile): „250“ + „250“ ergab 250250. | Der Controller hätte das als gespeicherte Wertabweichung von BLE (`FAIL`) gewertet, obwohl der Executor angehängt hat. | Ein Feld zählt erst als erfasst, wenn es danach exakt die freigegebene Zahl zeigt; Anweisung an den Executor: Inhalt zuerst markieren (ControlOrMeta+A). |

### 18.4 Ergebnis des letzten Trockenlaufs (frische Kopie, 1.232 skriptierte Aktionen)

`DRY_RUN_COMPLETED`: kein Harness-Stopp, keine abgelehnte skriptierte Aktion, kein Vertragsbefund. Erwartet und unverändert nach PO-Entscheidung Option A (16.10.2026: „lassen wirs erstmal so“):

| Stufe | Ergebnis |
|---|---|
| PLAN, RECEIPT, SIEVE (10 Positionen, mit Teilsiebung), BOILING, SE, ASSESS, WPK, ANALYSIS, REPORT (10 Berichte, 10 PDFs), RIGHTS | **PASS** |
| PREPARATION | INCONCLUSIVE: 8 von 10 Positionen PASS; P01 (Koch 8 mm vor der ersten Speicherung) und P06 (Kornform) `INCOMPLETE / APPROVED_FIELDS_NOT_PRESENT_ON_PAGE` |
| SHAPE | INCONCLUSIVE: 4 von 5 Positionen PASS; P06 wie oben |

Abschluss-Oracles: Empfang PASS, Berichte PASS, Berechnungen PASS, statisches Gate unverändert (Stempel nur `sampling_plans`, 1 Zeile). Messwerte und Zuteilungen FAIL ausschließlich wegen der drei von BLE nicht angebotenen Werte.

### 18.5 Neue Fixture und Tests

Fixture `nsn014-ux-b2e3a4b1d45a` (privat, `D:/Temp/sqbf-nsn014-fixture-20261016-prepared`) aus der gestoppten Quelle (Prüfsumme `9ae39dba…`), Purpose `fixture`, ohne Freigabe und Lease, Sessions verifiziert. **423 Tests OK** (vorher 399), davon neu: Guard im echten Chromium (Menüeintrag, darstellende Bedienelemente, gesperrte schreibende Elemente, Anker, Testauftrag mit Latch, Mausrad), weiche Ablehnung (Fortsetzung, Obergrenze, kritische Ablehnung), Schreibprüfung mit LIMS, Report-Oracle mit Lücken, Feldinhalt nach dem Tippen, skriptierter Executor, Verweigerung nicht-scratch Fixtures.

### 18.6 Grenzen

- Der skriptierte Executor ist ein sorgfältiger Nutzer. Ein Modell kann andere Bedienelemente wählen, schneller handeln (BLE rechnet nach dem Verlassen eines Feldes neu und verschiebt das Layout) oder etwas anderes erkunden. Solche Fälle erscheinen jetzt als weiche Ablehnungen mit Ziel statt als Totalverlust; der Lauf wird sie zeigen.
- Die Lesestufen sind offene Erkundungsaufgaben; die Liste lesender Bedienelemente deckt die gescannten Seiten ab, nicht jede denkbare Auswahl.
- P01 (Koch 8 mm) und P06 (Kornform, Modul inaktiv) bleiben nach Option A unvollständig; PREPARATION und SHAPE sind deshalb auch bei einem idealen Executor INCONCLUSIVE, die übrigen Positionen werden dennoch entschieden.
- Die Klassifikationen sind offline und im Trockenlauf bestätigt, in einem Lauf mit Modell noch nicht.
- Für den nächsten Lauf nötig: ausdrückliche Einzellauf-Freigabe, aktuelle Provider-Probe (die vom 16.10.2026 gilt bis 22:02 UTC), Readiness unmittelbar davor.

## 19. Lauf 4 (083896e6, 16.10.2026): Ergebnis, Ursachen und Behebung

**Bewertung: Lauf 4 ist `NO-GO / INVALID_HARNESS`. Es liegt keine gültige Messung vor, und es gibt keinen BLE-Befund.** PLAN bestand, RECEIPT blieb unentschieden, PREPARATION wurde ungültig, neun Stufen liefen nicht. Ursache war nicht BLE, sondern die Steuerung: ein einziger fehlgeschlagener Executor-Request hat über einen allgemeinen Fehlerhandler die Stufe und damit die Suite beendet. Daneben fehlten zwei Guard-Freigaben. Alles ist offline behoben und mit Trockenläufen belegt; es gab dabei keinen Modellaufruf. Die Freigabe von Lauf 4 ist verbraucht.

### 19.1 Verlauf

SQBF-Commit `81e48e9`, Fixture `nsn014-ux-b2e3a4b1d45a` (damit verbraucht), 13:20 UTC, **51 Anfragen** (46 Executor, 5 Reviewer; bekannte Tokens 95.440 Executor, 23.542 Reviewer; eine Anfrage ohne Nutzungsangabe), 419 s von 10.800 s.

| Stufe | Ergebnis | Was geschah |
|---|---|---|
| PLAN | **PASS** | Planproben einmal angelegt (10 Proben), Oracle bestätigt. |
| RECEIPT | INCONCLUSIVE | Der Executor klickte auf eine Zeile der Probenliste (`Probe … auswählen`); der Guard lehnte sie ab, der Executor meldete danach `blocked`. |
| PREPARATION | **INVALID_HARNESS** | P01 Zuteilungen und Abschlämmung: `blocked`. P02 Abschlämmung: `blocked` (kein Speichern-Element gefunden). P03: eine Executor-Anfrage schlug fehl, der allgemeine Handler machte daraus `MEASUREMENT_RUNNER_ERROR`; die Stufe wurde INVALID und die Suite beendet. |
| SIEVE bis RIGHTS (9) | NOT_RUN | `UPSTREAM_CRITICAL_STOP`. |

Statisches Gate unverändert (nur Audit-Stempel `sampling_plans`, 1 Zeile), keine Vertragsbefunde.

### 19.2 Ursachen

| # | Ursache | Beleg | Behebung |
|---|---|---|---|
| 1 | **Ein fehlgeschlagener Executor-Request beendete die Suite.** Jede Ausnahme außerhalb der erwarteten Fälle wurde zu `INVALID_HARNESS` und löste den kritischen Stopp aus. | Letzter Executor-Request ohne Nutzungsangabe (`usage {}`): das entsteht nur, wenn der Aufruf selbst eine Ausnahme warf, hier nach 6 s. Der Ausnahmetyp wurde nicht protokolliert, die Schlussfolgerung stützt sich also auf die Abrechnung, nicht auf eine Fehlermeldung. | Neuer Pfad `ask_executor`: ein fehlgeschlagener Request oder eine Antwort ohne Aktionsobjekt beendet nur diese Aufgabe als `INCONCLUSIVE` (`EXECUTOR_REQUEST_FAILED`, kein Wiederholen, keine Reviewer-Anfrage danach). Drei Fehlschläge in Folge stoppen die Suite als unvollständig (`EXECUTOR_UNAVAILABLE_AFTER_REPEATED_FAILURES`). Jeder Harness-Fehler protokolliert künftig den **Klassennamen** der Ausnahme (nie die Meldung). |
| 2 | Same-page-Anker „Zu den Modulen“ (`#module-bereich`) wurde in den Messstufen abgelehnt. Nach „Testauftrag erzeugen“ landete der zweite Klick darauf. | 3 Ablehnungen im Ereignisprotokoll. | Hash-Anker der aktuellen Seite erlaubt (scrollt nur); andere Anker, Fremdseiten und Query bleiben gesperrt (Test im echten Chromium). **Korrigiert in Abschnitt 20.3 (Nr. 3): In BLE ist es wegen `<base href="/">` kein Anker der aktuellen Seite, die Freigabe wurde zurückgenommen.** |
| 3 | Zeile der Probenliste ohne `aria-selected` wurde abgelehnt. | `tr "Probe ENZBERG-… auswählen"`; RECEIPT endete mit einem einzigen Versuch. | Regel auf `tr[aria-label^="Probe "][aria-label$="auswählen"]` auf `/samples` (lesend); andere Zeilen und Seiten bleiben gesperrt. |
| 4 | Der Executor gab nach einer einzigen Ablehnung auf. Ein Klick landete wegen der Neuberechnung von BLE auf einem anderen Element als im Screenshot. | Klick bei (757, 336), wo der Screenshot „Entwurf anlegen“ zeigte; der Guard fand dort ein Eingabefeld (Ziel `input`). Vermutung: Layoutwechsel zwischen Screenshot und Klick. | Anweisung ergänzt: Nach einer Ablehnung zuerst den neuesten Screenshot lesen, die Seite kann sich bewegt haben. Das Verhalten des Modells bleibt Messgegenstand. |

**Beobachtung ohne Befundstatus (Reviewer, unbestätigt):** Auf den Modulseiten liegt „Speichern“ oben und scrollt mit der Seite weg. Der Executor scrollte in P02 zehnmal nach unten, fand es nicht und meldete `blocked`. Das ist ein UX-Kandidat (`UX_IMPROVEMENT`), kein belegter BLE-Defekt.

### 19.3 Zusätzlicher Fund im Trockenlauf mit Fehlerinjektion: abgeleitete Werte

Zur Prüfung der Behebung habe ich dem skriptierten Executor drei Fehler vorgegeben (`suite-dry-run --inject-executor-faults "9:raise,40:not_object,150:raise"`: zwei Providerfehler, eine Antwort ohne Aktionsobjekt). Die Stufen liefen weiter (richtig). Dabei zeigte sich ein zweiter, schwerer wiegender Fehler der Auswertung:

- Fiel in PREPARATION die Zuteilung von P01 aus, wertete SIEVE P01 als `FAIL / PERSISTED_VALUE_DEVIATION`.
- Ursache: BLE leitet die **Aufbereitungsmasse der Teilsiebung** (`lims_sample_derived_test_step.taken_mass`) aus der **Zuteilung des Pfannenmaterials** (Zielprozess `Siebanalyse`, bei P01 560 g) ab. Ohne diese Zuteilung speichert BLE 0. Referenz 560, gespeichert 0, Executor hatte alle seine Felder eingegeben: der Controller hielt das für eine BLE-Abweichung.
- Das wäre in einem Lauf mit Modell genau dann passiert, wenn das Modell die Zuteilung nicht erfasst (in Lauf 4 war P01 Zuteilung `blocked`). Ein falscher BLE-Befund.
- Behebung: Eine Abweichung abgeleiteter Werte (Aufbereitung, Teilsiebserie) zählt nur, wenn ihre Eingaben wie freigegeben gespeichert sind (Abschlämmung ohne Abweichung, Zuteilung `Siebanalyse` vorhanden). Sonst ist die Position `INCOMPLETE / DERIVED_VALUE_UPSTREAM_INCOMPLETE`, nie `FAIL`. Fehlt die Evidenz, gilt die Lücke als vorhanden. Abweichungen eigener Eingaben bleiben davon unberührt.

### 19.4 Trockenläufe nach der Behebung (frische Wegwerfkopien, 0 Modellaufrufe)

| Lauf | Ergebnis |
|---|---|
| Mit Fehlerinjektion (Aufrufe 9, 40 und 150: Providerfehler bei P01/P06 Zuteilung, Antwort ohne Aktionsobjekt bei P02 Abschlämmung) | `DRY_RUN_COMPLETED`: kein Harness-Stopp, alle zwölf Stufen liefen. PREPARATION: P01, P02, P06 `INCOMPLETE / EXECUTOR_REQUEST_FAILED`, die übrigen sieben PASS. SIEVE: P01 `INCOMPLETE / DERIVED_VALUE_UPSTREAM_INCOMPLETE`, die übrigen neun PASS (vor der Behebung des Abschnitts 19.3: P01 FAIL). REPORT: alle zehn PASS. |
| Sauber (1.232 skriptierte Aktionen) | `DRY_RUN_COMPLETED`: kein Harness-Stopp, keine abgelehnte skriptierte Aktion, kein Vertragsbefund. PLAN, RECEIPT, SIEVE (10 Positionen), BOILING, SE, ASSESS, WPK, ANALYSIS, REPORT (10 Berichte, 10 PDFs), RIGHTS **PASS**. PREPARATION (8 von 10) und SHAPE (4 von 5) INCONCLUSIVE ausschließlich wegen der drei von BLE nicht angebotenen Werte (Option A). Ein früherer sauberer Lauf zeigte REPORT P01 `PDF_NOT_DOWNLOADED`: der skriptierte Executor traf die Berichtsseite vor dem Aufbau ihres Menüs und gab auf; er wartet jetzt bis zu zehn Sekunden. Es war ein Fehler des Stellvertreters, nicht der Guards. |

### 19.5 Tests

**441 Tests OK** (vorher 423). Neu: Executor-Ausfall je Messposition und je Inspektionsstufe (Providerfehler, Zeitüberschreitung, Antwort ohne Objekt, Zähler und Stopp nach drei, Zurücksetzen nach Erfolg), Klassenname im Harness-Fehler ohne Meldungstext, Fortsetzung der übrigen Positionen, Anker und Probenzeile im echten Chromium, abgeleitete Werte (Lücke, kein Lückenfall, eigene Abweichung bleibt FAIL, fehlende Evidenz), Zuteilungs-Oracle `prerequisite_gaps`, Fehlerinjektion und PDF-Wartezeit im skriptierten Executor.

### 19.6 Grenzen

- Der Trockenlauf kann Verhalten eines Modells nicht vorhersagen (andere Bedienelemente, Tempo, Aufgeben nach einer Ablehnung). Er belegt, dass Fehler der Steuerung nicht mehr die Suite beenden.
- Die genaue Ausnahme in Lauf 4 ist unbekannt (nicht protokolliert). Ob der Provider, die Antwort oder der Worker versagte, bleibt offen; die Behebung deckt alle drei Fälle ab und protokolliert beim nächsten Mal die Klasse.
- Abgeleitete Werte: Bekannt ist die Abhängigkeit der Aufbereitungsmasse von der Zuteilung `Siebanalyse` und, konservativ angenommen, der Teilsiebserie von der Abschlämmung. Weitere Abhängigkeiten sind nicht ausgeschlossen; sie würden als FAIL erscheinen und wären im Bericht zu prüfen.
- P01 (Koch 8 mm) und P06 (Kornform) bleiben nach Option A unvollständig.
- Für einen fünften Lauf nötig: neue Fixture, neue ausdrückliche Einzellauf-Freigabe, Provider-Probe (die vom 16.10.2026 gilt bis 22:02 UTC), Readiness unmittelbar davor.

## 20. Lauf 5 (6c23f768, 16.10.2026): erste belastbare Messungen, Abbruch durch ablaufenden Anmeldetoken

**Bewertung: `PARTIAL GO`, technisch `RESOURCE_STOP`. Erstmals gibt es objektiv belegte BLE-Ergebnisse, aber nur für fünf von zwölf Stufen und nur für einen Teil der Positionen. Der Lauf endete nach 3.603 s, weil der Anmeldetoken des Providers nach etwa einer Stunde abläuft (HTTP 401). Es gibt keine belegte BLE-Abweichung: Das einzige `FAIL` (PREPARATION P09) war ein Fehler meiner Auswertung (Abschnitt 20.3).** Die Freigabe von Lauf 5 ist verbraucht.

### 20.1 Verlauf

SQBF-Commit `713a273`, Fixture `nsn014-ux-76b2f16e82ec` (verbraucht), 16:06 bis 17:06 UTC. Zwei vorangegangene Startversuche (15:42 und 15:48 UTC) endeten vor jeder Anfrage, weil die Browser-Anmeldung nicht rechtzeitig bestätigt wurde (Datensätze `9dacf9bd`, `d25f754a`, 0 Anfragen, Fixture und Freigabe unberührt).

| Stufe | Objektives Ergebnis | Inhalt |
|---|---|---|
| PLAN | **PASS** | Planproben einmal angelegt, Oracle bestätigt. |
| RECEIPT | **PASS** | Plan- und Empfangsansicht gelesen, Oracle bestätigt. Ein Klick auf „Toggle Beprobung“ wurde abgelehnt (20.3). |
| PREPARATION | FAIL (falsch, 20.3) | Abschlämmung **P08 PASS**. P01 bis P05: Executor meldete `blocked` (meist nach der abgelehnten Navigation, 20.3). P06, P07, P10: `APPROVED_FIELDS_NOT_PRESENT_ON_PAGE`. P09: falsches FAIL, siehe 20.3. |
| SIEVE | INCONCLUSIVE | **P04, P06, P10 PASS** (gespeichert, Werte wie freigegeben persistiert). P02 und P05: `done` ohne Speichern. P03, P08, P09: `blocked`, kein Speichern-Element gefunden. P01: Boden/Pfanne-Zeile ohne Eingabefeld, Teilsiebung mit 0 g Einwaage. P07: Klick auf die Beschriftung „Einwaage“ abgelehnt, der Executor gab auf. |
| SHAPE | INCONCLUSIVE | Abbruch: drei Anfragen in Folge `PROVIDER_HTTP_401`. |
| BOILING bis RIGHTS (7) | NOT_RUN | `UPSTREAM_CRITICAL_STOP`. |

Verbrauch: **540 Anfragen** (513 Executor, 27 Reviewer), **3.603 s**, bekannte Tokens 1.225.271 (Executor) und 147.434 (Reviewer), zusammen rund 1,37 Mio. in einer Stunde, etwa 2,5 Tausend je Anfrage (6 Anfragen ohne Nutzungsangabe, darunter die Ausfälle). Statisches Gate unverändert (nur Audit-Stempel `sampling_plans`), keine Vertragsbefunde. Fehlerhandhabung aus Abschnitt 19 bewährt: ein Executor-Ausfall (`RESPONSE_NOT_JSON`, P09) und zwei Reviewer-Ausfälle beendeten nur die jeweilige Position bzw. Bewertung.

### 20.2 Belastbare BLE-Ergebnisse

- Planproben anlegen (PLAN) und Probenübersicht (RECEIPT): objektiv bestanden.
- Abschlämmung P08: Eingaben vollständig erfasst, gespeichert und wie freigegeben persistiert.
- Siebanalyse P04, P06, P10: gespeichert, Werte wie freigegeben persistiert.
- Kein anderes Ergebnis ist objektiv entschieden.

### 20.3 Fehler der Steuerung

| # | Fehler | Beleg | Behebung |
|---|---|---|---|
| 1 | **Anmeldetoken läuft nach etwa einer Stunde ab.** Der ChatGPT-Plan-Zugriff wird bewusst ohne Refresh betrieben (kein Refresh-Speicher); ein Lauf von mehr als einer Stunde kann so nicht enden. | Abbruch bei 3.603 s, dreimal `PROVIDER_HTTP_401` in SHAPE. Schon der Mindestbedarf der Suite (640 Anfragen) braucht länger. | Ein 401/403 stoppt die Suite sofort (`PROVIDER_AUTHORIZATION_EXPIRED`) statt nach drei weiteren Positionen. **Die eigentliche Lösung ist eine Entscheidung des PO** (Abschnitt 20.6). |
| 2 | **Falsches `FAIL` bei P09 (Zuteilung).** Der Executor tippte den Wert, die nächste Antwort war kein JSON (`RESPONSE_NOT_JSON`), das Feld wurde nie verlassen. BLE speichert beim Verlassen eines Feldes, also wurde nichts gespeichert. Der Controller wertete „alles eingegeben, nichts persistiert“ als `PERSISTED_VALUE_DEVIATION`. | Zuteilungs-Oracle: keine einzige Zuteilung persistiert. Ergebnis `EXECUTOR_FAILED` bei `fully_entered=true`. | Am Aufgabenende wird das noch fokussierte freigegebene Feld festgehalten; ein Wert in einem noch fokussierten Feld gilt als nicht übernommen. Eine Abweichung ist dann `INCOMPLETE / LAST_FIELD_NOT_COMMITTED`, nie `FAIL`. Die Anweisung nennt „Feld mit Tab verlassen“. |
| 3 | **Meine Korrektur aus Abschnitt 19 zum Anker „Zu den Modulen“ war falsch.** Sie wurde nur an einer nachgebauten Seite getestet. In BLE steht `<base href="/">`: `href="#module-bereich"` wird zu `/#module-bereich`, der Klick verlässt die Probe und landet auf der Startseite (auf einer Wegwerfkopie reproduziert). Der Guard hat ihn sechzehnmal zu Recht abgelehnt, die Modelle gaben danach meist auf („kein anderer Weg zu den Modulen“). | 16 Ablehnungen (15 in PREPARATION, 1 in SHAPE); DOM-Prüfung auf Wegwerfkopie. | Freigabe zurückgenommen, Test mit `<base href="/">` ersetzt. Anweisung: Die Module stehen als Karten weiter unten auf der Probenseite, Feld selbst anklicken (nicht Beschriftung), letzten Wert mit Tab übernehmen. |
| 4 | Klick auf „Toggle Beprobung“ (Seitenleiste) in RECEIPT abgelehnt. | 1 Ablehnung. | Seitenleistengruppen (`.mud-nav-group`, „Toggle <Name>“) sind lesend; Test im echten Chromium. |
| 5 | Reviewer-Ausfälle ohne Klassenname. | 2 Ausfälle (`REVIEWER_CALL_FAILED`). | Ereignis protokolliert die Ausnahmeklasse. |

### 20.4 Beobachtungen zu BLE (unbestätigt, kein Issue angelegt)

- **„Zu den Modulen“ führt von der Probenseite auf die Startseite** (statt zu scrollen), wegen `<base href="/">` und eines reinen Fragment-Links. Auf einer Wegwerfkopie reproduziert. Kandidat für einen BLE-Fehler.
- **„Speichern“ liegt oben im Modulkopf und scrollt mit weg.** Bei vier der zehn Siebanalysen speicherte der Executor nicht (P02, P05 `done` ohne Speichern; P03, P08 `blocked`). Der Reviewer widersprach in einem Fall (Schaltfläche sei oben sichtbar): Mischung aus UX-Kandidat und Agentenschwierigkeit.
- **Die Ergebnisfelder der Abschlämmung** („Trockenmasse nach Waschen“, „Abschlämmverlust“, „Feinanteil lokal“) blieben leer, bis die Siebanalyse ihre Hauptprobenmasse kennt; die Seite meldet in einem Fall „Hauptprobenmasse nicht verfügbar, zuerst Siebanalyse mit Wägung“. Das koppelt die Reihenfolge von PREPARATION und SIEBUNG.
- Laut Executor-Aussage ist die Siebanalyse von P09 „nicht bewertbar, kein wirksamer Grenzwertsatz zugeordnet“ (Produktkonfiguration; unbestätigt).
- Reviewer-Zahlen (unbestätigt): UX-Verbesserung major 2 / minor 25, Agentenschwierigkeit major 5 / minor 15, SQBF-Kandidat major 9 / minor 3 (zwölf), Unklar major 5 / minor 3 / info 37. Die zwölf „SQBF-Kandidaten“ betreffen alle abgelehnte Klicks (Anker, Kochversuch-Link, Beschriftung, Seitenleiste); der Reviewer sieht die Ablehnung und kann nicht entscheiden, ob sie berechtigt war.

### 20.5 Nach der Behebung

Offline behoben, 0 Modellaufrufe. Neu: Abweichungen in noch fokussierten Feldern sind `INCOMPLETE / LAST_FIELD_NOT_COMMITTED`; Anker-Freigabe zurückgenommen und mit der echten Seitenstruktur (`<base href="/">`) getestet; Seitenleistengruppen lesend; HTTP 401/403 stoppt sofort; Reviewer-Ausfälle nennen die Ausnahmeklasse; Anweisung an den Executor ergänzt.

| Trockenlauf (frische Wegwerfkopie) | Ergebnis |
|---|---|
| Sauber (1.232 skriptierte Aktionen) | `DRY_RUN_COMPLETED`, unverändert zum Stand vor Lauf 5: PLAN, RECEIPT, SIEVE (10 Positionen), BOILING, SE, ASSESS, WPK, ANALYSIS, REPORT (10 PDFs), RIGHTS **PASS**; PREPARATION (8 von 10) und SHAPE (4 von 5) INCONCLUSIVE nur wegen der drei von BLE nicht angebotenen Werte (Option A). Keine abgelehnte skriptierte Aktion, kein Vertragsbefund. |
| Mit drei eingespielten Providerfehlern (Aufrufe 9, 40, 150) | `DRY_RUN_COMPLETED`, alle zwölf Stufen liefen; nur P01, P02, P06 in PREPARATION `EXECUTOR_REQUEST_FAILED`, SIEVE P01 `DERIVED_VALUE_UPSTREAM_INCOMPLETE`, alles andere wie im sauberen Lauf. |

Grenzen der Trockenläufe: Der skriptierte Executor verlässt jedes Feld mit Tab und kennt den Weg zu den Modulkarten; die Wirkung der neuen Anweisung und des Feldfokus am Aufgabenende ist deshalb nur durch Tests, nicht durch einen Trockenlauf belegt. **446 Tests OK** (vorher 441).

### 20.6 Offene Entscheidung: Anmeldetoken und Laufdauer

Eine vollständige Suite braucht mindestens 640 Anfragen; Lauf 5 schaffte in einer Stunde 540 Anfragen für 4 von 12 Stufen. Hochgerechnet (PREPARATION und SIEVE lagen gut 25 % über der Schätzung) sind etwa 850 bis 1.000 Anfragen und zwei bis drei Stunden zu erwarten, mit rund 2,5 Mio. Tokens. Ein Token von einer Stunde reicht dafür nicht.

| Option | Wirkung | Bewertung |
|---|---|---|
| A. **Refresh im Arbeitsspeicher** mit dem beim Login zurückgegebenen Token; nie auf Platte, stirbt mit dem Prozess | Lauf ohne weitere Eingriffe möglich | Empfohlen. Ändert die Anmeldegrenze, braucht Ihre ausdrückliche Zustimmung. |
| B. Neue Browser-Anmeldung während des Laufs | Der Lauf pausiert, Sie bestätigen alle ~55 Minuten | Sicherheitsmodell unverändert, aber Sie müssen die ganze Zeit am Rechner sein. |
| C. Suite in zwei Läufe teilen | Zwei Freigaben | Nicht ohne Umbau möglich (jede Fixture und Lease ist einmalig, Stufen bauen aufeinander auf). |

### 20.6a Entscheidung des PO und Umsetzung (17.10.2026)

Der PO wollte nicht je Lauf, Stunde und Agent im Browser bestätigen, sondern **einmal für mehrere Läufe und Agenten**. Gewählt wurde ein **gespeicherter, verschlüsselter und automatisch erneuerter Login** (ausdrückliche Erlaubnis: „Ja, verschlüsselt speichern“). Umgesetzt in `sqbf/plan_credentials.py` und `plan_login.py`: `--keep-signed-in` (eine Browser-Bestätigung, prüft sofort die Erneuerung), `--status`, `--check`, `--forget`; Speicher mit Windows-DPAPI für den aktuellen Benutzer, nur für diesen lesbar, höchstens sieben Tage; Erneuerung 5 Minuten vor Ablauf durch den jeweils bedürftigen Prozess unter einer Sperre, damit mehrere Läufe sich einen Login teilen und ein rotierender Refresh-Token nie zweimal verbraucht wird; der Suite-Prozess bekommt nur den Speicherpfad. Ein abgelehnter Login stoppt die Suite sofort. Getestet mit einem simulierten Token-Endpunkt (20 Tests, darunter echtes DPAPI und fünf parallele Prozesse). **Nicht belegt:** ob der Provider für diesen Client einen Refresh-Token ausgibt und die Erneuerung zulässt; das zeigt die erste Anmeldung mit `--keep-signed-in` (sie erneuert einmal, bevor sie Erfolg meldet, und löscht den Login, falls der Provider ablehnt). Dann wäre Option B (Neu-Anmeldung während des Laufs) der Rückfall.

### 20.7 Grenzen

- Nur fünf Stufen laufen mit Modell; BOILING, SE, ASSESS, WPK, ANALYSIS, REPORT, RIGHTS und der größte Teil von SHAPE bleiben ungeprüft.
- Viele Positionen scheiterten am Verhalten des Modells (Aufgeben nach einer Ablehnung, Speichern nicht gefunden); das ist Messgegenstand, aber kein BLE-Befund.
- Die Reihenfolge PREPARATION vor SIEVE (Abschlämmung vor Hauptprobenmasse) kann Ergebnisse verfälschen; das ist ein Kandidat für eine Anpassung der Suite, nicht von BLE.
