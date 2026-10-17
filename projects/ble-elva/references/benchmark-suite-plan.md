# BLE/ELVA – fachlich abgeleiteter Benchmark-Testkatalog (Entwurf)

**Referenzen:** `BLE_Laborprozess_0-to-End_v0.2.md` und `BLE_Produktreferenz_2026.md` (SharePoint-Stände 06.10.2026); BLE Gate-1-Spezifikation: `Creynox/BLE#962`. Dies ist ein fachlicher **Plan**, keine automatisch ausführbare Graph-Engine oder bestandener Testlauf.

## Aktueller Umsetzungsstand 14.10.2026

Der PO hat die vollstaendige reguläre Serie mit WPK und mehreren Personas beauftragt. Aktiver Referenzkandidat ist **NSN014, 08.05.2026** (zehn Positionen), nach lesendem Abgleich mit Originalbericht. Datenreview und ausführbare Stufengates sind offen. Siehe `../suites/enzberg-nsn014-v0.1.json` und `../../../docs/regular-suite-setup.md`. Die nachstehende Taxonomie ersetzt keine Ausführungsabnahme.

## Szenarien / Reihenfolge

| Test-ID | Sichtbare Benutzeraufgabe | Fixture / unabhängiger Oracle | Reife |
|---|---|---|---|
| LAB-00 | BLE öffnen, Anmeldung und sichtbare Navigation prüfen | Isolierte Webinstanz, Testkonto; Browser-Evidence | No-cost Mock-Smoke tatsächlich durchgeführt, **0 Aktionen**, kein fachlicher PASS |
| LAB-01 | Enzberg STS 0-45 ohne neue Normedition anlegen, speichern, erneut öffnen; historisches Normenszenario v0.1 getrennt erhalten | Aktive STS-Klassifikation und Werk vorhanden; Produkt fehlt; unabhängiger Produkt-/Zuordnungscheck | Zwei echte Versuche INVALID_HARNESS; Reparaturen getestet, persistierter Produkt-PASS weiter offen (#11) |
| LAB-02 | Wochen-/Probenahmeplan aus Werk, Produkt, Prüfrotation/Anforderung erstellen | Synthetisches Werk mit mehreren Produkten/Prüfregeln; persistierter Plan | Nur Katalog |
| LAB-03 | Eingangsproben anhand Werk/Produkt/Datum identifizieren; Teilproben und Rückverfolgbarkeit | Erwartete Eimer/Proben, originale Plan-ID und eindeutige Probe-ID; getrennte Teilproben | Nur Katalog |
| LAB-04 | Mehrere Proben **batchorientiert** über Siebung, Trocknen/Waschen, Kornform, Kochversuch, Teilsiebung, SÄ bearbeiten | Vorgegebene Messdaten, definierte erwartete Mess-/Prüfmodulbezüge; keine echte physische Prüfung | Nur Katalog |
| LAB-05 | Vollständigkeit, angewandte Normedition, historische Grenzwerte und Ergebnisse korrekt bewerten; Wiederholungsprüfung nur im notwendigen Umfang | Unveränderliche Norm-/Grenzwert-/Bewertungssnapshots; Vorher-/Nachher-Vergleich | Nur Katalog, BLE #1137 |
| LAB-06 | Laborleiter-Freigabe, Prüfbericht erzeugen und anzeigen, Versand/Abgabe nachvollziehbar abschließen | Fachlicher Read-only Oracle für Status, Reportrevision, Historie; Test-Delivery-Sink statt realer Kundensendung | Nur Katalog |
| NORM-01 | Fehlende Normedition über berechtigte Oberfläche anlegen, erneut öffnen und finden | Isolierte Norm-Authoring-Fixture; berechtigte/unberechtigte Rollen | Issue #15, noch kein Szenario; BLE #1136 |

## Fachliche Besonderheiten aus der Originalquelle

- **Prüfserie/Plan-Nummer vs. eindeutige Probe-ID** trennen; Teilproben müssen dauerhaft auf eine Ursprungsprobe verweisen.
- Ein Gemisch hat typischerweise mehrere Eimer; mehrere Prüfpfade werden **als Arbeitsbatch** unabhängig vom Probenabschluss organisiert.
- Gegebene ca. 120°C/4h im alten Arbeitsablauf sind **kein allgemeiner Normparameter**; eine Benchmark-Fixture simuliert diese physischen Arbeiten mit freigegebenen Messwerten.
- Nach fehlender Teilprüfung darf nicht fälschlich ein vollständiger/freigegebener Bericht entstehen.
- Bei zweifelhaften Ergebnissen nur kleinstmögliche fachlich sinnvolle Teilprüfung wiederholen; Rückstellfristen auftraggeberabhängig.
- Original-Produktnamen bleiben Provenienz; z.B. „Godel“ nicht Produktname, HST/HGT und MWS bleiben offen.
- Normenänderung nach abgeschlossener Probe darf historische Ergebnisse nicht rückwirkend ändern.

## Was liegt wo?

- **Core-Harness:** `sqbf/runner.py` (Browser, Screenshot-Aktions-Loop, Limits, Evidence).
- **Agentenadapter:** `sqbf/providers.py` und tool-loser `chatgpt_plan`-Pfad (#14 abgeschlossen); keine PAYG-Nutzung für reguläre Suite.
- **BLE-Szenario:** `projects/ble-elva/scenarios/`, fachliche Einzelaufträge.
- **BLE-Fixture:** `projects/ble-elva/fixtures/` (Kontrakt, nicht automatisch provisionierte DB).
- **BLE-Fachquellen:** `projects/ble-elva/references/` (nur Controller/Design/Oracle; kein verdeckter Input für UI-Agent).
- **Oracle:** unabhängiger LAB01-/CORE-Oracle und Scope-Prüfer implementiert; vollständige Labor-/WPK-Stufenoracles noch offen.
- **Suite/Graph:** spätere Verbindung von LAB-01 → LAB-02 → ... → LAB-06 mit Start-/Pass-/Blockierbedingungen. **Noch nicht implementiert.**
- **Reports:** `sqbf/reporting.py`; lokal in `runs/`, nicht in Git.

## Historischer MVP-Plan (durch aktuellen PO-Auftrag erweitert)

1. Mit Codex lokal die beiden Quellen sowie dieses Testkatalog-Dokument auf fachliche und technische Lücken prüfen und ausschließlich LAB-01 vorbereiten.
2. Abo-basierten **Screenshot-only** Agentenadapter mit einem einzelnen Testbild und einer JSON-Aktion validieren (SQBF #14), ohne API-Keys oder Pay-as-you-go.
3. Nach isolierter Fixture und unabhängigem Oracle den STS-0-45-Lauf durchführen (SQBF #11).
4. Erst dann LAB-02 als konkrete Szenario-Datei anlegen; weitere Szenarien nacheinander.

**Keine GitHub Actions; keine automatischen parallelen Agenten oder reale Kundensendungen.**