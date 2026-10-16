# Lokaler Betrieb: CORE-SMOKE-01 und LAB-01

Alle Befehle aus dem geprüften SQBF-Repository-Root. Python:
`D:\Entwicklung\Benchmark\.venv\Scripts\python.exe`.
Kein Setup/Reinstall nötig, solange die vorhandene Umgebung funktioniert.

## Instanzen und Build

| Zweck | BLE | PostgreSQL | Veränderung |
|---|---|---|---|
| Geschützte Golden-Quelle / CORE-SMOKE | 127.0.0.1:5080 | 55432, ble_benchmark_20261012 | Kein Produktwrite/Reset |
| LAB-01 disposable Arbeitskopie | 127.0.0.1:5081 | 55433, neuer sqbf_lab01_* Name/Volume | Genau ein UI-Produktwrite |
| Normale lokale Umgebung | 5059 | 5433 | Unberührt |

Laufende Assembly und DLL-SHA werden durch `scope-check` unabhängig dem Listener
zugeordnet. Worktree-HEAD ist **kein** Ersatz für den gestarteten Build. Der aktuelle
Assembly-Stand lautet `1.0.0+c51ea2229b3513aa59e659774fe8ce44cdd81859`.
Der Fixture-Worktree-HEAD `fb933961…` ist separat. Keine Behauptung eines reproduzierbaren
BLE-Quellcodebuilds aus dieser abweichenden Worktree-Version.

## Neue Golden-basierte Arbeitskopie

```powershell
$python = 'D:\Entwicklung\Benchmark\.venv\Scripts\python.exe'
$bleRoot = 'D:\Entwicklung\BLE-worktrees\sqbf-lab01-fixture\src\BLE.Web'
& $python -m sqbf.cli working-fixture `
  --source projects/ble-elva/fixtures/enzberg-product-core-v0.2.json `
  --output D:\Temp\sqbf-lab01-NEW-PRIVATE-DIRECTORY `
  --application-root $bleRoot
```

Nur bei freien 5081/55433 und neuem Ausgabepfad. Das Werkzeug prüft Quelle und Build,
erstellt einen privaten `pg_dump -Fc` mit SHA-256 sowie neue DB/Volume/Container,
restauriert ohne ursprünglichen Owner und bestätigt alle zehn Ausgangshashes.
Es erstellt keine Normen. Die Quelle wird davor/danach ausschließlich lesend geprüft.
Neue zufällige DB-Passwörter werden Windows-benutzergebunden DPAPI-geschützt; die
Credential-Dateien haben eigene restriktive ACL. `golden.dump` ist schreibgeschützt,
die lokale Manifestdatei enthält Hash/Identitäten, keine Passwörter.

Bei Fehler kein Reset/Retry. `provisioning-state.json` und private Logs prüfen.
Readiness erfordert den endgültigen PostgreSQL-TCP-Server, nicht dessen temporären
Init-Socket. Ein verbliebener Container wird nicht automatisch wiederverwendet.

Zum Wiederherstellen einer sauberen Produktbaseline eine **neue** Arbeitskopie
erzeugen. Vorher ausschließlich den alten, anhand Manifest/Listener/Build erneut
identifizierten Arbeitsprozess und zugehörigen `sqbf-lab01-*`-Container stoppen.
Volumes und Run-Evidenz behalten; kein Löschen, `down -v`, Truncate oder Reset.
Keine PID/Container-Namen ungeprüft aus einer alten Anleitung übernehmen.

## Vorhandene Arbeits-Webinstanz neu starten

```powershell
& $python -m sqbf.cli working-web --fixture <private-fixture.json> --application-root $bleRoot
```

Der Port muss frei sein, Docker-Identität und DLL-Hash müssen exakt stimmen.
DB-Verbindung kommt aus der privaten Controller-DPAPI-Datei; beide BLE-Connection-
Strings zeigen ausschließlich auf die Arbeitskopie. Startup-Seeding bleibt aus.
Bei belegtem Port nicht den unbekannten Prozess beenden. Die ausgegebene PID ist
ein Startnachweis; erst das anschließende Scope-Gate bestätigt den laufenden Build.

## Session und Modellanmeldung

Vor jeder Ausführung `session-check` mit der gewünschten Szenariodatei, Ziel-URL
und lokalem Storage-State durchführen. Zwei neue Browserkontexte plus Reload
müssen authentifiziert bleiben. Dann `scope-check` mit der passenden Fixture,
`--identity-application-root $bleRoot` und lokal gebautem `IdentityCheck.dll`.

Wenn die BLE-Session abgelaufen ist, höchstens **ein** automatischer Login mittels
`session --credentials <private-DPAPI-Datei> --username sqbf-laborleitung
--output <neuer-privater-Dateipfad> --url <exakte-Ziel-URL>`; alte Session behalten.
Danach beide Gates wiederholen. Fehler beendet den Auftrag, keine stillen Versuche.

Der separate OpenAI-OAuth-Dialog bleibt Benutzerinteraktion. Callback-Empfänger
muss während der Anmeldung laufen; CLI nicht beenden. Tokens verbleiben nur im
Speicher, deshalb ist bei einem neuen Prozess erneut Anmeldung erforderlich.
Dies ist keine erneute PO-Pilotfreigabe. Keine Codex-Tokens kopieren oder auslesen.

## LAB-01 ausführen

Nur nach gültigem Auftrag, bestandenem Gate und lokalen Tests:

```powershell
& $python -m sqbf.cli run `
  --scenario projects/ble-elva/scenarios/sts-0-45-product-core-v0.3.json `
  --url http://127.0.0.1:5081/ --fixture <private-fixture.json> `
  --software-version '1.0.0+c51ea2229b3513aa59e659774fe8ce44cdd81859' `
  --storage-state <private-session.json> --fixture-ready `
  --identity-application-root $bleRoot --identity-verifier <IdentityCheck.dll> `
  --executor-provider chatgpt_plan --executor-model gpt-6-luna `
  --analyst-provider chatgpt_plan --analyst-model gpt-6.1-sol `
  --output D:\Temp\sqbf-lab01-runs
```

JSON/Keys, native Event-Guard und Controller-Hit-Test stimmen überein. Nur sichtbare
Kernfelder und exakt festgelegte synthetische Werte, ein Save, anschließend List/
Wiederöffnung nur zur Ansicht. Der Screenshot-Agent erhält keine Controller-Daten.
Nach jedem Versuch werden Persistenz und alle übrigen geschützten Tabellen sowie
die Golden-Quelle unabhängig gelesen. FAIL bleibt erhalten, kein automatischer Retry.

## NSN014 v0.4 – reguläre Suite

Modellfreie Readiness unmittelbar vor jedem Lauf (ohne `--execute`, keine Modell- oder
DB-Schreibzugriffe; prüft unter anderem einen sauberen SQBF-Commit, Stufenverträge, Sessions,
Runtime, leeren Start, Plan-Formular und Einstiegsrouten):

```powershell
& $python -m sqbf.cli run-suite --suite projects/ble-elva/suites/enzberg-nsn014-v0.4.json `
  --fixture <privates-plan-flow-manifest.json> --dataset <privat>\dataset-ux-source-v1.json `
  --projection <privat>\reference-projection-ux-v1.json --allocations <privat>\allocation-reference-v1.json
```

Live-Lauf nur mit ausdrücklicher PO-Ausführungsfreigabe für genau diesen Lauf: derselbe Befehl
mit `--execute` (Standardausgabe `D:/Temp/sqbf-regular-runs`). Frische ChatGPT-Plan-OAuth,
einmalige Fixture-Lease, kein Retry; bei abgelaufener Session höchstens eine kontrollierte
Erneuerung je Persona. Ergebnis: `run.json`, `cases.json`, `accounting.json` und deutscher
`completion-report.md` im privaten Lauf-Ordner. Details:
[Abschlussbericht](../../docs/nsn014-v04-completion-report.md).

## NSN014: Fixture-Klon und Provider-Probe

Beide Befehle laufen ohne `--execute` nur als Plan bzw. lesende Vorprüfung.

```powershell
# Klon einer unveränderten, verbrauchten Fixture mit genau einem dokumentierten Override (P06 aktiv):
& $python -m sqbf.cli suite-fixture-clone --source-fixture <manifest> --controller-credentials <controller-credentials.dpapi.json> `
  --output-dir <neuer-privater-Ordner> [--execute]
# Danach vier gefuehrte Anmeldungen (je Persona eine) und die Readiness:
& $python -m sqbf.cli suite-sessions --fixture <neuer-Ordner>\fixture-clone.json --output <...>\fixture-clone-sessions.json --report <...>\sessions-report.json

# Zwei synthetische Anfragen (Executor- und Review-Schema), frische OAuth, kein Retry:
& $python -m sqbf.cli suite-provider-probe --suite projects/ble-elva/suites/enzberg-nsn014-v0.4.1.json [--execute]
& $python -m sqbf.cli run-suite ... --provider-probe <provider-probe-....json>
```

Der Klon stoppt (löscht nicht) den Quell-Container und beendet das Quell-Web nach Identitätsprüfung, kopiert das Volume
mit Prüfsumme, vergleicht den Hash aller öffentlichen Tabellen und setzt danach nur `is_active` des genannten
Plan-Produkts. Es gibt keinen automatischen Rollback und keinen Retry; `clone-state.json` hält jede Phase fest. Die OAuth-Anmeldung
der Probe muss innerhalb von 300 s im Browser bestätigt werden.

## NSN014: Fixture aus gestoppter Quelle, Konfigurations-Replay, Seiteneffekt-Vertrag

Stand 15.10.2026 (Issue #21, Vorbereitung ohne Modellaufruf). Die verifizierte Quelle bleibt gestoppt und wird nie gestartet;
das Volume wird byteweise kopiert und gegen die beim Stoppen festgehaltene Prüfsumme geprüft.

```powershell
# Plan (nur lesend), dann Ausführung; der Besetzer der Ports 5082/55434 wird nach der Prüfung gestoppt (nicht gelöscht):
& $python -m sqbf.cli suite-fixture-clone --source-fixture <Quelle-Manifest> --controller-credentials <controller-credentials.dpapi.json> `
  --output-dir <neuer-privater-Ordner> --source-stopped --expected-tree-sha256 <Prüfsumme> `
  --occupant-fixture <Manifest-der-laufenden-Fixture> --purpose scratch|fixture --session-seed-fixture <Manifest-mit-neuesten-Sessions> [--execute]
```

Der Klon ersetzt zusätzlich zum Plan-Produkt-Override die fehlende Produktkonfiguration durch einen **Replay aus der normalen lokalen
BLE-Datenbank** (nur lesend): `lims_product_test_modules` (51 Zeilen) und die produktbezogenen `workspace_sampling_rules` (37 Zeilen).
Ohne sie sperrt BLE die Messformulare und bietet nur 2 von 9 Entnahmekarten an. Jede Phase und jede geänderte Tabelle wird im
Klon-Nachweis festgehalten. `--purpose scratch` erzeugt eine Wegwerfkopie für Trockenläufe; nur `--purpose fixture` ist für einen Lauf bestimmt.

Seiteneffekt-Vertrag: `projects/ble-elva/suites/enzberg-nsn014-side-effects-v1.json` legt je Stufe fest, ob sie lesend ist
oder welche Tabellen sie beschreiben darf. Die Prüfung im Runner (`stage_effects.py`, `guarded_stage`):

- geschützte Tabellen (Baseline der vorbereiteten Fixture): nach jeder Stufe unverändert, Ausnahme ist genau eine Audit-Freigabe
  (`NSN014-PLAN`, Tabelle `sampling_plans`, Zielzeile = Plan-Id, Spalten `updated_at`/`updated_by`, höchstens 1 Zeile);
- jede Stufe beginnt exakt im Endzustand der vorherigen (Schreibzugriffe außerhalb der Suite stoppen sie);
- alle anderen Tabellen (Hash aller öffentlichen Tabellen, Controller READ ONLY): nicht gelistete Schreibzugriffe sind Befunde
  (`UNEXPECTED_TABLE_WRITE`, `WRITE_IN_READ_ONLY_STAGE`) ohne Abbruch.

Der Vertrag ist im Lauf-Manifest über seinen Hash festgelegt. Für Trockenläufe gibt es die Werkzeuge `module_replay.py` und
`side_effect_probe.py` (Zeilen- und Spaltendiff je Aktion, nur Spaltennamen und Zähler, keine Werte).

## NSN014: Trockenlauf mit echtem Guard (vor jedem Live-Lauf)

Modellfrei, auf einer frischen Wegwerfkopie (`suite-fixture-clone --purpose scratch`, dann `suite-sessions`). Das Werkzeug verweigert jede
andere Fixture, weil es schreibt (Plan-Proben, Eingaben, Berichte):

```powershell
& $python -m sqbf.cli suite-dry-run --suite projects/ble-elva/suites/enzberg-nsn014-v0.4.1.json --dataset <privat>\dataset-ux-source-v1.json `
  --fixture <scratch>\fixture-scratch-sessions.json --projection <privat>\reference-projection-ux-v1.json --allocations <privat>\allocation-reference-v1.json `
  --output <scratch>\dry-run-1
```

Er führt alle zwölf Stufen über denselben Code wie ein Live-Lauf aus (Guards, Transportrichtlinie, Seiteneffekt-Vertrag, Oracles, Abschluss-Gates); nur die
Modelle sind ersetzt (skriptierter Executor, neutrale Bewertung). `dry-run-report.json` nennt je Stufe das Ergebnis, abgelehnte skriptierte Aktionen mit Ziel
(`guard_coverage_gaps`) und `harness_stops`. Erwartet ist `DRY_RUN_COMPLETED`; PREPARATION und SHAPE bleiben wegen der von BLE nicht angebotenen Werte
INCONCLUSIVE. Ein Lauf braucht danach eine neue Fixture (`--purpose fixture`) und eine neue Freigabe.

Mit `--inject-executor-faults "9:raise,40:not_object,150:raise"` spielt der skriptierte Executor beim n-ten Executor-Request einen Providerfehler
(`raise`) oder eine Antwort ohne Aktionsobjekt (`not_object`) ein. Erwartet: nur die betroffenen Positionen `INCOMPLETE / EXECUTOR_REQUEST_FAILED`,
kein Harness-Stopp, alle zwölf Stufen laufen. Vor jedem Live-Lauf einmal sauber und einmal mit Fehlerinjektion ausführen.

## Evidenz und Aufbewahrung

Private lokale Run-Ordner: PNGs mit SHA-256, Events, Usage, gemessene Modell-/Runnerzeit,
Oracle davor/danach, `run.json`, `report.md`, `completion-report.md`, Scores/Findings.
`list-runs --output <Run-Root> --result GO` verwendet exakten Verdict-Vergleich.
DB-Golden/DPAPI/Session nie in Git, Prompts oder GitHub-Berichten speichern.

Historische Runs und Snapshots unverändert behalten. Es gibt **keine automatische
Löschfrist oder Bereinigung**; Daten/Volumes nur auf ausdrücklichen Archivierungs-
oder Löschauftrag behandeln. Ein pausierter Container ist keine gelöschte Fixture.
Die technische Umgebung gilt lokal; Wheel-Verteilung/Enterprise-Betrieb und
statistische Kalibrierung sind keine Zusagen dieses MVP.
