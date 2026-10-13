# Completion Report – ausdrücklich freigegebener zusätzlicher LAB-01-Pilot

## Ergebnis: NO-GO für LAB-01, technische Reparatur lokal bestanden

Run `fc489109-17ac-4d47-8823-61d292c457e1`, tatsächlich geprüfter SQBF-Commit
`7b83bb29618d0d6aa8a8ee8ab2d2d82e0bc66a87`. Ein neuer Einzelpilot wurde vom PO
nach dem ersten Harnessfehler ausdrücklich freigegeben; frische separate OAuth-Anmeldung.
Keine weitere automatische Live-Wiederholung nach diesem Lauf.

## Gates und tatsächlicher Ablauf

Sauberer Worktree/Remote-HEAD synchron, gültige vorhandene Laborleiter-Session,
independent signed identity/Tenant/Laborleiter/products.manage/Enzberg-Scope und
exakter gestarteter BLE-Build geprüft vor OAuth und Modellen. Neue privat gespeicherte
Gates-Baseline: Quelle unverändert, Working Copy 0 Produkte, Golden-Dump-Hash korrekt.
Keine Session-Erneuerung nötig. Keine Main-/Actions-/Reset-/Merge-Operation.

Luna erreichte nach der SPA-Reparatur das neue Produktformular. Name STS 0–45,
aktive Ungebundenes-Gemisch-/STS-Klassifikation, synthetische Kalkstein-/gebrochen-
Werte und 0/45 wurden über die Oberfläche eingegeben. Beim folgenden Scrollversuch
änderte sich der obere Zahlenwert von 45 zu 44,9; nach Korrektur und erneutem Scrollen
wiederholte sich der Effekt. Executor stoppte BLOCKED ohne Save und ohne Wiederöffnung.

- Start 2026-10-13T21:57:18.408867Z; Ende 2026-10-13T21:59:54.643470Z.
- 156.23 s, 26 validierte UI-Aktionen, 28 Pilotcalls (27 Luna + ein Sol-Review).
- Zusätzlich ein synthetischer Sol-Vision-/JSON-Kompatibilitätstest PASS.
- 67,723 Pilot-Tokens + 162 Kompatibilität = 67,885 technische Tokens / 29 Requests.
- 136.768205 s Modellwartezeit, 19.461795 s übrige Runner-/Oraclezeit; keine Human-Zeit.
- Separater Reviewer INCONCLUSIVE, Scores 4/3/2/3, sieben Findings.
- 27 lokale PNGs, sämtliche SHA-256 geprüft; Events, Usage, Oracle davor/danach,
  Scores, Findings, Markdown, Run-Index und Completion Report privat gespeichert.
- Archiviertes Run-Verdict NO-GO unverändert. Nachanalyse INVALID_HARNESS:
  keine belastbare BLE-Speicher- oder Gesamt-UX-Abnahme aus diesem Versuch.

## Unabhängige Persistenz und Isolation

Persistenz-Oracle FAIL: Zielprodukt fehlt, kein Save. Übrige Working-Tabellen und
Golden-Quelle unverändert, nachträglicher SELECT-only Check weiterhin 0 Produkte.
Normen, Normzuordnungen, Proben und Berichte unverändert. Alle 44 ursprünglichen
CORE-Artefakte/Index-Dateien unverändert; erfolgreicher CORE-Run bleibt GO.
Normale BLE5059/PostgreSQL5433 weder verwendet noch verändert.

Working-Web 5081, PG55433, Container sqbf-lab01-4f3d8a3ee82a, DB
sqbf_lab01_4f3d8a3ee82a; eigene Volume-/DB-Identität bestätigt. BLE-Assembly
1.0.0+c51ea2229b3513aa59e659774fe8ce44cdd81859, DLL-SHA256
 d0109a37a06f91aff137a27f26433f6dbc6696f28db21514e7f63cc97c13b2d4.
Fixture-Worktree-HEAD fb933961… bleibt separat; kein Reproducible-Build-Claim.

## Nachgewiesene Runnerursache und Korrektur

Die Scrollantwort enthielt x/y für eine freie Fläche (u.a. 1150/724). `apply_action`
ignorierte bisher diese Werte und sendete nur `mouse.wheel`; der Mauszeiger blieb
nach dem Eingabeklick über dem Zahlenfeld. Deshalb erhielt dieses den Wheel-Event.
Das ist ein Ausführungsfehler des Harness, keine nachgewiesene BLE-Speicherstörung.

Synthetischer Chromium-Test reproduziert vor Fix 44.9 statt 45 und fehlende Pointer-
Bewegung, Exit 1. Fix `2f269f1867155efd6130c888778b50f0c9f9b389` bewegt die Maus
vor Wheel an die expliziten sichtbaren Koordinaten und validiert deren Vollständigkeit
und Viewport-Grenzen. Legacy-Scroll ohne Koordinaten bleibt unverändert. Keine
Tool-/DB-/Dateizugriffe der Modelle und keine Write-/Budget-/Retry-Grenzen aufgeweicht.

`D:\Entwicklung\Benchmark\.venv\Scripts\python.exe -m unittest discover -s tests -v`
**138/138 lokale Tests PASS, keine Skips, Exit 0, 13.963s**. Browsertest belegt,
dass der neue Scroll die Seite bewegt und den fokussierten Zahlenwert 45 erhält.
Reparatur ausschließlich lokal getestet, kein weiterer Modellaufruf/Live-Pilot.

## Abschluss

#11 bleibt offen: ein gültiger LAB-01-Lauf muss Speichern, Wiederöffnung und
unabhängigen Produkt-Persistenznachweis noch erbringen. Technischer Umgebungsstand
PARTIAL GO; dieser zusätzliche Einzelpilot NO-GO. PR #10 bleibt Draft.
Nächster einzelner Schritt: LAB-01 nach der Scroll-Reparatur mit erneut geprüften
Gates durchführen; ohne Auftrag keine weitere Live-Wiederholung.
