# LAB-01: einmaliger Abschlussauftrag vom 13.10.2026

Der PO-Auftrag „dann schließe bitte einmal alle punkte sauber ab“ autorisiert die
besprochenen fünf Abschlussarbeiten: PR-Prüfung, reproduzierbare Fixture,
LAB-01-Integration, einen echten Produktpiloten und Betriebsdokumentation.
Die bestehende Dauerfreigabe für CORE-SMOKE-01 bleibt separat unverändert.

## Begrenzter Vertrag

- Genau ein LAB-01-Pilot, kein automatischer Retry, keine manuelle Produktanlage als Ersatz.
- Nur neue disposable Arbeitskopie auf BLE 5081 / PostgreSQL 55433, nach unabhängig
  geprüfter Docker-, Datenbank-, Session-, Rollen-, Tenant- und Enzberg-Identität.
- Geschützte Quelle 5080 / 55432, normale Instanzen 5059 / 5433 und historische Runs unverändert.
- Nur ein Produkt `STS 0–45`, Klassifikation `unbound_mix` / `sts`, Kategorie Gemisch,
  Verwendungsbereich Ungebundenes Gemisch, Produktstufe Fertiges Gemisch, Körnung 0/45.
- `Kalkstein` / `gebrochen` sind ausdrücklich **synthetische Fixture-Werte** aus den
  vorhandenen BLE-Ausprägungen; keine Behauptung über reale Enzberg-Produkte.
- Keine Normen, Editionen, Grenzwerte, Proben, Berichte, Änderungen bestehender Produkte.
- Höchstens 25 Minuten einschließlich Nachprüfung, 150 UI-Aktionen, 152 Run-Modellaufrufe
  einschließlich separatem Review; zusätzlich ein begrenzter synthetischer Reviewer-Test.
- Tool-loser `chatgpt_plan`, Executor `gpt-6-luna`, separater Reviewer `gpt-6.1-sol`.
  Kein API-Key/PAYG, Provider-Fallback, Budgetextension oder gespeicherter OAuth-Token.
- Modelle erhalten nur Bild, Aufgabe und öffentliche Aktionshistorie. Oracle und Scope
  bleiben im Controller; kein DB-/Datei-/Session-/Quellcodezugriff der Modelle.
- Private Windows-ACL vor ersten Artefakten, Secrets nur DPAPI/Pipes/Speicher.
- Ein Speicherklick; bei Abweisung oder Validierungsfehler Stop. Fachliches PASS erst
  durch SELECT-only Persistenz-Oracle, geschützte Tabellenhashes und unveränderte Quelle.
- Keine GitHub Actions, main-Commits oder automatischer Merge. PR bleibt Draft.

Ein einzelner bestandener Pilot beweist die technische Umgebung und diesen Prozess,
keine statistische Reproduzierbarkeit oder umfassende BLE-Fachabnahme.

## Zusätzlicher ausdrücklicher Einzelauftrag

Nach dem archivierten ersten Harnessfehler antwortete der PO: „Ja, einen neuen LAB-01-Piloten durchführen“. Dies autorisiert genau einen weiteren Einzelpilot mit erneut geprüften Gates und frischem OAuth, keine automatische Folge-Wiederholung. Dieser Auftrag wurde durch Run fc489109-17ac-4d47-8823-61d292c457e1 erfüllt (NO-GO, kein Save). Der darauffolgende Scroll-Fix ist nur lokal getestet.
