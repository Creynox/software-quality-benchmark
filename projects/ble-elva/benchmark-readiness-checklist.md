# BLE/ELVA – Benchmark-V1-Readiness und Arbeitscheckliste

**Stichtag:** 13.10.2026 · **Scope:** zuerst Workflow Produkt → Probenahmeplan → Probe → Messung → Bewertung → Freigabe/Bericht. **Keine Neuanlage von Normen** und keine vollständige Norminventur als Voraussetzung. Die Normenhistorie und korrekte Bewertungsgrundlagen bleiben Datenintegritätsgrenzen.

## Aktuell: reguläre Suite, 14.10.2026

**Gesamtstatus BLOCKED_DATA_REVIEW / Umsetzung läuft.** Der PO beauftragt die vollständige Enzberg-Serie einschließlich WPK und Rollen. Aktiver Kandidat ist NSN014 (08.05.2026), zehn bereits gespeicherte Proben; NSN018 ist nach Datenvergleich zurückgestellt.

- Tool-loser ChatGPT-Plan-Provider und echter CORE-SMOKE-01-GO nachgewiesen; #14/#17/#18/#19 abgeschlossen.
- LAB01 wurde zweimal real versucht; beide Nachanalysen INVALID_HARNESS, Reparaturen lokal getestet. Produkt-Persistenz-PASS bleibt offen (#11).
- Suite-Verträge, strikte Aggregation, Datenhash-/Vollständigkeitsprüfung und expliziter Sessioncheck für befüllte Fixtures implementiert.
- Alle vierzehn regulären Stufen weiterhin pending; noch keine vollständige Suite-Fixture, Stage-Guards, Scope-/Rollenabnahme oder echte Suite-Ausführung.
- DB-Rohwerte sind maßgeblich. SÄ-Methode verlangt mm; PO hat ursprüngliche cm-Eingaben erneut bestätigt, neue Projektion rechnet explizit mit Faktor 10. Beide STS-Teilsiebreihen vollständig gefunden. Normkontext und fachliche Entscheidungen bleiben offen. Keine synthetischen Ersatzmassen freigegeben.
- Die folgenden Tabellen dokumentieren den früheren MVP-Stand; sie sind keine aktuelle Lauf-/Sessionfreigabe. Aktueller Completion Report: `../../docs/regular-suite-setup.md`.

## Legende

- **[x] bereits implementiert** bedeutet nicht automatisch auf diesem Commit getestet.
- **[t] auf früherem lokalen Stand tatsächlich getestet**; Nachtest für aktuellen Branch offen.
- **[ ] offen**; nie als PASS ausweisen.
- Fortschrittsnachweis/Abnahme in GitHub-Issues und PR #10, nicht in GitHub Actions.

## A. Vorhandene technische Grundlage

| Nachweis | Stand | Quelle/Status |
|---|---|---|
| Generischer UI-Screenshot-Aktions-Runner, Guardrails, Evidence/Markdown | [x] | `sqbf/runner.py`, `models.py`, `reporting.py` |
| Versionierte, inhaltsleere neutrale Projektvorlage | [x] | `projects/_template`, `sqbf/scaffold.py`; #13 |
| BLE/ELVA-Profil und historisches Normen-Szenario | [x] | `projects/ble-elva`; normatives v0.1 zurückgestellt |
| Zwei echte SharePoint-Fachreferenzen übernommen | [x] | `projects/ble-elva/references`; originalgetreuer Vergleich belegt |
| Python 3.13, Playwright, Chromium installiert | [t] | Codex-Protokoll vom 12.10.2026 (lokaler PC) |
| 29 lokale Unit-/Mock-/Chromiumtests, Scenario-Preflight | [x] | Branch `b1ea29b` + lokale LAB-01-Änderungen; 29/29, Exit 0 am 13.10.2026 |
| BLE `127.0.0.1:5080` + isolierte DB `55432`, 77 Migrationen, Testkonto | [x] | Fixture-Container/Volume/DB-Identität und Enzberg live verifiziert; 5433 und 5059 unverändert |
| Echte BLE-Anbindung ohne Modellaufruf: 3 Screenshots | [t] | No-cost Mock-Smoke; 0 UI-Aktionen; fachlich INCONCLUSIVE |
| Neuer read-only `doctor` prüft BLE-Health und Chromium | [x] | lokaler Nachtest: BLE 200, Chromium READY, `TECHNICAL_SMOKE_READY` |
| Normenfreie Prozessbaseline STS 0-45 | [x] | `scenarios/sts-0-45-product-core-v0.2.json`, URL 5080; 25 Minuten/150 Aktionen; noch kein Produktlauf |
| Isolierte Fixture und Laborleitungs-Session | [x] | `READY_FOR_UI_PROCESS_PILOT`; Enzberg gewählt, Formularroute nach Session-Restore erreichbar; noch keine Speicherung |
| Read-only Oracle, LAB-01 Baseline | [x] | `sqbf_oracle_ro`, vor/nachgelagerte Assertions; Live-Baseline dokumentiert: 0 Produkte/Proben/LIMS-Proben/Berichte/Normzuordnungen, 15 Normen/Versionen |

## B. In Reihenfolge abzuarbeiten

| ID | Status | Pflichtarbeit | Abschlussnachweis |
|---|---|---|---|
| A1 | [x] | Branch im separaten Worktree synchronisiert und Unit-/Browser-/Scaffold-/Oracletests lokal ausgeführt | 29 Tests, Exit 0; `preflight` Exit 0; kein kostenpflichtiger Provider |
| A2 | [x] | Read-only Doctor auf `http://127.0.0.1:5080/` | Health HTTP 200, Chromium READY; technische Bereitschaft, kein KI-Benchmark |
| A3 | [x] | Isolierte Werk-/Testkonto-/Laborleitungs-Scope-Daten geprüft | Zielcontainer/DB/Volume, Enzberg und aktiver STS-Klassifikator bestätigt; keine Produkt-/Proben-/Berichtzeilen |
| A4 | [x] | Vorhandene additive Fixture-Provisionierung/Prüfung bestätigt | separater loopback Container/Volume, 5433 nicht verwendet; kein Reset in diesem Arbeitsschritt |
| A5 | [x] | Read-only Produkt-Persistenz-Oracle außerhalb des UI-Agents implementiert und getestet | Baseline live bestanden; nachgelagerter Produkt-PASS bleibt bis späterer Anlage offen |
| A6 | [ ] | Codex-CLI/Claude-Code-Abologin, Vision-Screenshot-Eingabe und Modellverfügbarkeit lokal verifizieren (#14) | Nur Abo-Kontingent, keine PAYG-/API-Keys; echte Tool-/Dateiisolation nachweisen |
| A7 | [ ] | Einziger **sicherer** Agenten-Schritt Screenshot → JSON-Aktion → Playwright testen (#14) | 1 bestätigte Aktion, keine unerlaubten Tools/Dateisicht, kontrollierte Limits |
| B1 | [ ] | **LAB-01** Produkt STS 0-45 ohne Normenneuanlage speichern und erneut öffnen (#11); derzeit ausdrücklich nicht ausgeführt | UI-Evidence plus unabhängiger Oracle; kein LLM-Selbstergebnis als PASS |
| B2 | [ ] | LAB-02 Probenahmeplan als eigene Scenario-/Fixture-Datei umsetzen | Befüllter Plan mit Produkt/Rotation, Wiederaufruf und Oracle |
| B3 | [ ] | LAB-03 Probenerzeugung und Probenbezug | Plan-/Probe-ID getrennt und nachgewiesen |
| B4 | [ ] | LAB-04 Messdatenerfassung, später Batch-Szenarien | Prüfmodulwerte je Probe/Teilprobe nachvollziehbar |
| B5 | [ ] | LAB-05 fachliche Bewertung und Pflichtvollständigkeit | Angelegte Probe benutzt historisch korrekte, nachgewiesene Regelbasis |
| B6 | [ ] | LAB-06 Freigabe und Prüfbericht | Laborleiterfreigabe, Endbericht, Audit/Report-Orakel |

## C. Später, getrennt

- [ ] Szenarien LAB-01…06 in Suites/Graph überführen, mit ausdrücklichen Start-/Exit-/Blockerbedingungen. Derzeit **keine Graph-Engine** implementiert (#9).
- [ ] Wiederholte Runs, Rollen-/Negativtests, Batch-Effizienz, Trendberichte.
- [ ] NORM-01 Normenanlage-UX und vollständige Normenkatalogpflege (#15, BLE #1136/#82) **zurückgestellt**.
- [ ] Kritischer Historienschutz aus BLE #1137 **nicht zurückgestellt**: vor fachlichem V1-GO prüfen, dass spätere Norm-/Grenzwertänderungen keine alten Ergebnisse umbewerten.

## Abnahmeregeln

- Erster Lauf kann **BLOCKED**, **INCOMPLETE** oder **INCONCLUSIVE** sein und bleibt ein nützlicher technischer Nachweis, ist aber **kein** fachlicher PASS.
- **Kein** echtes Testkonto/Fixtures-Reset ohne bestätigte Isolation; keine produktiven Kundendaten oder Kundensendungen.
- **Keine GitHub Actions, keine zusätzlichen API-Kosten und keine stillen Pay-as-you-go-Fallbacks**; Abo-Agentenintegration ist implementiert (#14 abgeschlossen); aktuelle Session, Kontingent und Modellverfügbarkeit bleiben Laufgates.
- Git-Regeln: nur Feature-Branch/PR, keine direkten main-Commits, kein Merge ohne Abnahme.
