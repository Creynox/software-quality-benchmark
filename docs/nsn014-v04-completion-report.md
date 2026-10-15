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
