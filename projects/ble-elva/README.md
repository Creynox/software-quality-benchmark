# BLE/ELVA – lokales SQBF-Profil

## Aktueller Stand

CORE-SMOKE-01 ist tatsächlich ausgeführt und unabhängig abgenommen: Run
`04bd06b3-f868-4390-b7d6-3df67e9cb85f`, technische Prüfung, No-Write-Oracle und
separater Reviewer PASS. Die historischen NO-GO-Läufe bleiben unverändert.

LAB-01 v0.3 prüft normfreie Produktanlage in einer neuen disposable Arbeitskopie
auf BLE 5081 / PostgreSQL 55433. Golden-Quelle 5080 / 55432 bleibt leer und geschützt;
normale BLE-/PostgreSQL-Instanzen bleiben unverändert. Synthetische Materialwerte
Kalkstein / gebrochen sind ausdrücklich Testdaten, keine realen Werkdaten.

## Ausführung und Nachweise

- [Betriebsanleitung](operations.md): Start, Working Copy, Session, OAuth, Gates,
  Pilotbefehle, Wiederherstellung und geschützte lokale Aufbewahrung.
- [CORE-Dauerfreigabe](benchmark-execution-authorization.md): 5 min / 10 Aktionen /
  12 Pilotcalls, read-only, ein Lauf pro Ausführungsauftrag, kein Retry.
- [LAB-Abschlussauftrag](lab01-execution-authorization.md): ein Pilot, 25 min /
  150 Aktionen / 152 Run-Calls, ein Speicherklick, unabhängiger Persistenznachweis.
- `tools/lab_guard.py`, `tools/lab_runner.py`, `tools/working_fixture.py` enthalten
  ausschließlich dieses Projektprofil. Generisches Template bleibt leer.

Nur der separat autorisierte tool-lose `chatgpt_plan` ist für CLI-Läufe freigegeben.
Historische OpenAI-/Anthropic-Key-Adapter bleiben im CLI gesperrt. Kein API-Key,
PAYG, Abo-Tokenexport, GitHub Actions oder automatischer Merge.

## Lokale Abnahme

```powershell
D:\Entwicklung\Benchmark\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests umfassen Chromium, private ACL, Schema/Keys, Fail-Closed-Gates, Timeouts,
Prozessbaum, Scope, Oracle, exakten Run-Index und reproduzierbare leere Projektvorlage.
Kein Health-200, Modell-DONE oder Screenshot allein gilt als fachliches PASS.

## Historische Szenarien

v0.2 und normenspezifisches v0.1 bleiben erhalten. TL SoB-StB 20 / ETV-StB-BW
sind keine Pflichtverknüpfungen des Produkt-Speichervertrags. Normenanlage und
breiteres Portfolio (#15/#16) bleiben getrennte Erweiterungen.
