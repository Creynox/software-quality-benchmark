# BLE/ELVA – Benchmark-V1-Readiness und Arbeitscheckliste

**Stichtag:** 12.10.2026 · **Scope:** zuerst Workflow Produkt → Probenahmeplan → Probe → Messung → Bewertung → Freigabe/Bericht. **Keine Neuanlage von Normen** und keine vollständige Norminventur als Voraussetzung. Die Normenhistorie und korrekte Bewertungsgrundlagen bleiben Datenintegritätsgrenzen.

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
| 15 lokale Unit-/Mock-/Chromiumtests, Scenario-Preflight | [t] | Codex-Vorlauf, **nicht** neuer Branch |
| BLE `127.0.0.1:5059` + eigene DB `55432`, 77 Migrationen, Testkonto | [t] | Codex-Vorlauf; momentane Erreichbarkeit erneut prüfen |
| Echte BLE-Anbindung ohne Modellaufruf: 3 Screenshots | [t] | No-cost Mock-Smoke; 0 UI-Aktionen; fachlich INCONCLUSIVE |
| Neuer read-only `doctor` prüft BLE-Health und Chromium | [x] | `sqbf/doctor.py`, `tests/test_doctor.py`; lokaler Nachtest offen |
| Normenfreie Prozessbaseline STS 0-45 | [x] | `scenarios/sts-0-45-product-core-v0.2.json`, nur Szenario, kein Live-Test |
| Offenbleibender Fixture-Vertrag für diese Baseline | [x] | `fixtures/enzberg-product-core-v0.2.json`, `status=NOT_PROVISIONED` |

## B. In Reihenfolge abzuarbeiten

| ID | Status | Pflichtarbeit | Abschlussnachweis |
|---|---|---|---|
| A1 | [ ] | Den neuen Branch in einem sicheren Worktree lokal prüfen; Unit-/Browser- und Scaffoldtests wiederholen (#12/#13) | Tatsächliche Befehle, Version, Exit-Code, 0 unerklärte Fehler |
| A2 | [ ] | Read-only `python -m sqbf.cli doctor --url http://127.0.0.1:5059/` ausführen | Health/Chromium/Abo-CLI/Session-/Fixture-Gaps als JSON |
| A3 | [ ] | Isolierte **minimale** Werk-/Labor-/Auftraggeber-Stammdaten und Laborleitungsrechte erstellen/prüfen; ohne neue Normen | DB-/Scope-Identität, definierter Ausgangszustand und keine Produkte |
| A4 | [ ] | Sicheren Fixture-Setup/Reset implementieren und nur gegen eindeutig isolierte DB testen (#11) | Mehrfachlauf identisch, 5433 und bestehender Checkout unberührt |
| A5 | [ ] | Unabhängigen read-only Produkt-Persistenz-Oracle außerhalb des UI-Agents implementieren (#11) | Produkt-/Werkbezug und gespeicherte Pflichtdaten unabhängig bestätigt |
| A6 | [ ] | Codex-CLI/Claude-Code-Abologin, Vision-Screenshot-Eingabe und Modellverfügbarkeit lokal verifizieren (#14) | Nur Abo-Kontingent, keine PAYG-/API-Keys; echte Tool-/Dateiisolation nachweisen |
| A7 | [ ] | Einziger **sicherer** Agenten-Schritt Screenshot → JSON-Aktion → Playwright testen (#14) | 1 bestätigte Aktion, keine unerlaubten Tools/Dateisicht, kontrollierte Limits |
| B1 | [ ] | **LAB-01** Produkt STS 0-45 ohne Normenneuanlage speichern und erneut öffnen (#11) | UI-Evidence plus unabhängiger Oracle; kein LLM-Selbstergebnis als PASS |
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
- **Keine GitHub Actions, keine zusätzlichen API-Kosten und keine stillen Pay-as-you-go-Fallbacks**; Abo-Agentenintegration ist bis #14 noch ausstehend.
- Git-Regeln: nur Feature-Branch/PR, keine direkten main-Commits, kein Merge ohne Abnahme.
