# Completion Report – lokaler SQBF-Umgebungsabschluss

## Bewertung: PARTIAL GO

Die technische MVP-Umgebung und die getestete Reparatur sind bereit. Der tatsächliche
LAB-01-Produktnachweis bleibt offen: der einzelne Pilot wurde durch einen Harnessfehler
vor dem Formular blockiert. Keine Produktanlage oder fachliches PASS behauptet.
Kein automatischer zweiter Live-Lauf.

## Erledigte Abschlussarbeiten

1. PR-weite technische Sicherheits-/Ausführungsprüfung: Schema/Keys, Provider ohne Tools,
   zeitbegrenzte Prozesse, private Artefakte, Oracle/Scope-Trennung, generische Vorlage,
   CLI-Sicherheitsgates und Dokumentationsabgleich. Vier konkrete Probleme beseitigt:
   PostgreSQL-Init-Socket-Rennen, private Credential-Datei-ACL, Reviewer-Bildlimit,
   SPA-Pfadbindung des nativen Guards. Keine formale fremde GitHub-Approval erfunden;
   PR #10 bleibt Draft und ungemergt.
2. Neue isolierte Arbeitskopie: BLE 5081 / PostgreSQL 55433, Container
   sqbf-lab01-4f3d8a3ee82a, DB sqbf_lab01_4f3d8a3ee82a, eigenes Volume.
   Private Golden-pg_dump mit SHA-256, zehn übereinstimmende Ausgangstablehashes,
   neue DPAPI-Benutzerdateien, beide App-Connection-Strings nur auf Arbeitskopie,
   Seeding aus. Quelle 5080/55432 vor/nach unverändert, keine Resets.
3. LAB-01-v0.3: genau ein synthetisches STS 0–45-Produkt, Werk Enzberg,
   unbound_mix / sts, Gemisch / Unbound / mixture, 0/45, Kalkstein / gebrochen.
   Ein Save, keine Norm-/Proben-/Berichtsänderungen, Wiederöffnung nur zur Ansicht.
   Controller-only SELECT-only Persistenzprüfer; Modelle sehen nur Screenshots/Aufgabe.
4. Echter Pilot ausgeführt und vollständig gesichert; Ergebnis fachlich nicht abgenommen.
5. Start, neue Working Copy, Wiederanlauf, Session-Erneuerung, OAuth, Gates,
   Evidenz/Retention und sichere Wiederherstellung ohne Reset sind versioniert in
   projects/ble-elva/operations.md. Veraltete README/Projekt-/Issue-Angaben korrigiert.

## Tatsächlicher Live-Lauf

- Run b0834f9f-3777-497c-9dae-bd28369b9fb0, SQBF e111cdb28f52bd8c2237c10170e87e25ff5f3937.
- Archivierter Verdict NO-GO / Executor BLOCKED; 22 Aktionen, kein Speicherklick.
- 128.99 s, davon 111.0099 s Modellwartezeit und 17.9801 s übrige Runner-/Oraclezeit.
- 24 Pilotcalls: 23 gpt-6-luna und ein unabhängiger gpt-6.1-sol-Review.
- Zusätzlich ein synthetischer Reviewer-Kompatibilitätstest: Vision/JSON PASS.
- 55,578 Pilot-Tokens + 162 Kompatibilität = 55,740 technische Tokens, 25 Requests.
- Separate ChatGPT-Plan-OAuth, kein API-Key/PAYG/Provider-Fallback.
- 23 PNGs, alle Manifest-SHA-256 geprüft. Events, Usage, Reviewer, Scores,
  unabhängige Baseline/Nachprüfung, Run-Index und Markdown lokal geschützt.
- Reviewer FAIL, Scores 5/2/1/1. Diese Findings sind **kein belastbarer BLE-UX-Befund**,
  weil der Controller-Guard selbst die angeforderten Klicks unterdrückte.
- Persistenz-Oracle FAIL (erwartetes Produkt fehlt); isolierte Arbeitsbestände und
  geschützte Golden-Quelle unverändert. Kein Real-/Produktionsdatenwrite.

## Ursachen- und Reparaturnachweis

Der JavaScript-Guard erfasste location.pathname einmal beim initialen Seitenaufruf.
Nach Blazor-SPA-Navigation blieb sein Kontext auf der Startseite. Der Controller-Hit-Test
las hingegen den aktuellen Pfad und erlaubte die Modellklicks. Der native Guard
unterdrückte sie. Ein synthetischer Browser-Regressionstest reproduziert vor Fix
0 statt 1 ausgelieferten Klick, Exit 1. Fix liest den aktuellen Pfad bei jedem Event.
Die Schreibgrenzen bleiben erhalten; zusätzlich Stop nach drei identischen wirkungslosen
Klicks, keine weitere Executor-Anfrage statt einer verschwenderischen Schleife.

Reparaturcommit dde2ca076bfd35b85a5dede5d2e2a096d6f493ee.
`D:\Entwicklung\Benchmark\.venv\Scripts\python.exe -m unittest discover -s tests -v`
**134/134 Tests PASS, keine Skips, Exit 0, 12.486 s.**

Modellfreie reale Navigationsprüfung mit neuer Session-Browserinstanz und repariertem
Guard: sichtbare Produktnavigation + gleicher Neues-Produkt-Klick erreicht /products/new,
Save-Zähler 0, Modellcalls 0, DB-Vorher/Nachher exakt unverändert. Private Evidenz unter
D:/Temp/sqbf-lab01-working-20261013/spa-navigation-verification.

## Identität, Software und Schutz

Signierte Session, aktiver sqbf-laborleitung, erwarteter Tenant, Laborleiter-Rolle,
products.manage, genau ein Enzberg-Plant- und Tenant-Scope, keine globalen Rechte:
alle zehn independent Scope-Checks PASS, Exit 0. Session in zwei neuen Kontexten/Reloads.

BLE-Arbeitsprozess PID33196, geschützter Quellprozess PID54268; gestartete Assembly
1.0.0+c51ea2229b3513aa59e659774fe8ce44cdd81859, DLL-SHA256
 d0109a37a06f91aff137a27f26433f6dbc6696f28db21514e7f63cc97c13b2d4.
Fixture-Worktree fb933961099a6dd6da301998365d22ccb6921857 separat; kein identischer
Quell-HEAD-/reproduzierbarer BLE-Build behauptet. Normaler BLE-PID46152/5059 und
PostgreSQL ble-postgres/5433 unverändert, keine Operationen an deren Daten.
Alle 44 ursprünglichen CORE-Run-/Index-Dateien gegen lokale Hashliste unverändert;
GO-Run 04bd06b3-f868-4390-b7d6-3df67e9cb85f bleibt erhalten.

## GitHub und offene Abnahme

#12 lokale QA, #13 Vorlage und #14 initialer OpenAI-Abo-Pfad abgeschlossen.
#17/#18/#19 bleiben bereits abgeschlossene CORE-Nachweise. #11 bleibt offen,
bis ein gültiger LAB-01-Lauf das Produkt tatsächlich speichert und unabhängig bestätigt.
#9 ist weiterhin das breitere Epic; komplette Enzberg-W25-Golden-Week/Portfolio (#16)
und Normenszenario (#15) sind keine durch diesen MVP-Piloten erfüllten Kriterien.
Keine neue Issue-Welle, Actions, Merge, main-Commits oder Secrets in GitHub.

Nächster einzelner Schritt: gültigen LAB-01-Piloten mit getesteter SPA-Reparatur und
unveränderter leerer Working Copy ausführen; erneut Gates prüfen und bei Bedarf
separate OAuth-Anmeldung. Ein erfolgreicher Produkt-Oracle ist die verbleibende Abnahme.
