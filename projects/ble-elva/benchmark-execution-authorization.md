# BLE/ELVA – Dauerhafte, begrenzte Ausführungsfreigabe: CORE-SMOKE-01

**Entscheidung des Product Owners:** 13.10.2026.  
**Status:** FREIGEGEBEN IM RAHMEN DIESES VERTRAGS.  
**Referenz:** SQBF Issues #17 (Pilot), #14 (ChatGPT-Plan-Provider), PR #10.  
**Gültigkeit:** Bis zum ausdrücklichen Widerruf oder einer sicherheitsrelevanten Änderung des beschriebenen Setups. Diese Freigabe ist eine Ausführungsregel, **kein bereits bestandener Benchmark**.

## Berechtigter Scope

- **Nur Szenario `CORE-SMOKE-01`** (read-only UI: Produktübersicht suchen, nach STS 0–45 filtern, Leerzustand feststellen, Filter zurücksetzen).
- **Nur dedizierte BLE-Webinstanz `http://127.0.0.1:5080/`** und die vorher unabhängig identifizierte isolierte Benchmarkdatenbank `ble_benchmark_20261012` im Container `ble-benchmark-pg-20261012`, PostgreSQL-Hostport `127.0.0.1:55432`.
- **Nur synthetischer Testbenutzer `sqbf-laborleitung`**, bestehende lokal DPAPI-geschützte Benchmark-Credentials; Credentials, Cookies, Tokens, Passwörter, Schlüssel niemals in Prompts, Modellinputs, Reports, Git oder stdout.
- **Nur ausdrücklich autorisierter `chatgpt_plan`-Provider mit ChatGPT-Abonnementkontingent** und freigegebenen, tool-losen Modellen. **Kein API-Key, kein PAYG, keine Zusatzcredits, keine Provider-Fallbacks.**
- **Ein Benchmarklauf pro explizitem Benutzer-/Codex-Ausführungsauftrag** (auch dieser Auftrag zählt als Freigabe eines einzelnen Laufs nach bestandenem Session-Gate). **Kein automatischer Wiederholungsversuch** nach FAIL/BLOCKED, kein periodisches/unbeaufsichtigtes Anstoßen ohne Auftrag. Kein unbegrenzter Agentenloop.
- **Harte Obergrenzen:** 5 Minuten Gesamtlaufzeit einschließlich Modell/Reviewer/Oracle, 10 validierte sichtbare UI-Aktionen, höchstens 12 Modellaufrufe im Run (Review-Budget einschließlich), die zusätzlich im Harness einzeln begrenzt werden; keine stillen Budget-Erhöhungen.
- **Session-Erneuerung ist innerhalb eines freigegebenen Auftrags erlaubt**, wenn die bestehende Session unbrauchbar ist: höchstens ein automatischer Loginversuch mittels vorhandener lokal DPAPI-geschützter Anmeldedaten, anschließend modellfreie Wiederherstellungsprüfung und unabhängige Identitäts-/Werk-Scope-Bestätigung. Wenn ein gültiger Sessionzustand bereits existiert, **nicht unnötig neu anmelden**. Bei fehlgeschlagener Erneuerung STOP/BLOCKED_SESSION und **kein Benchmarklauf**. Ein erneuter OAuth-Consent des ChatGPT-Plans darf nicht umgangen oder vorgetäuscht werden; erforderliche Benutzerinteraktion bleibt erforderlich.
- **Vor jedem Modellaufruf:** model-free Session-Gate auf 5080, Session-Identität/Scopes, geprüfter Software-Build, unabhängiger Oracle-Baseline-Snapshot und geprüfte UI-Guards.
- **Bei Sicherheits-, Datenintegritäts-, Identitäts-/Berechtigungs-, Provider-/Abrechnungs-, Laufzeit- oder anderen kritischen Fehlern sofort fail-closed stoppen.** UI-Aktionen ausschließlich innerhalb der read-only Allowlist; kein Produktspeichern, keine Datenbankwrites/Resets/Migrationen, kein Ausweichen auf 5059/5433, keine echten Kundenaktionen.
- Ein gewöhnlicher erfolgreicher Login darf die üblichen **ausschließlich testkonto-bezogenen Auth-Metadaten** aktualisieren. Das ist kein Freibrief für fachliche Datenmutationen.
- Nach einem Run: unabhängiger read-only Vorher/Nachher-Oracle, sichtbare Evidenz, Run-ID, Scores/Findings, technische und fachliche Verdicts getrennt, lokale geschützte Artefakte; redigierte Zusammenfassung in Issue #17 / PR #10.
- **Git-Hygiene:** Vor Cloud-Änderungen lokal `git status`, `git worktree list`, `git fetch origin`, in geeignetem sauberem Worktree `git pull --ff-only origin feature/ble-blackbox-mvp-runner`. Keine fremden Worktrees/Dateien überschreiben, keine direkten main-Commits, kein Force Push, kein `reset --hard`/`git clean`, keine GitHub Actions, kein automatischer Merge.

## Abgrenzung

Die Freigabe deckt **nicht** die schreibende Labor-Produktanlage LAB-01, weitere LAB/ANA/WPK/UX/GUIDE/SEC-Szenarien, neue Normen, produktive Datenbanken, andere Benutzerkonten oder andere Endpunkte ab. Neue Sicherheitsarchitektur, veränderte Berechtigungen oder vergrößerte Budgets müssen erneut beurteilt werden.

**Konkurrenzregel:** Diese spätere PO-Entscheidung ersetzt die älteren einzelauftragsbezogenen „kein Benchmark-Retry / kein Run“-Sperren **nur für künftig ausdrücklich erteilte CORE-SMOKE-01-Aufträge und nur innerhalb dieser Grenzen**. Ein abgebrochener oder gescheiterter Run wird nicht automatisch erneut gestartet.

## Aktueller evidenzbasierter Ausgangsstand

Bei Stand `60813d06c6e69ce287a48f3a33d300852ca75f93` war der korrigierte automatische Laborleitungs-Login lokal einmal erfolgreich; Session-Check in zwei Browserkontexten, separates Identity-/Scope-Gate und DB-No-Write-Oracle waren PASS. Die Session muss **bei Ausführung erneut** auf Gültigkeit geprüft werden. Der einzige frühere echte CORE-SMOKE-01-Versuch endete vor der ersten UI-Aktion mit NO-GO/BLOCKED_SESSION. Noch kein erfolgreicher End-to-End-Benchmark behauptet.
