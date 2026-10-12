# BLE/ELVA Blackbox Micro-Pilot V1

Dieses Projekt ist ein **separates konfiguriertes Profil** des generischen SQBF.
Der ausführbare SQBF-Kern enthält keine Enzberg-, Produkt-, WPK- oder Normlogik.

- Profil: `projects/ble-elva/project.json`
- Szenario: `scenarios/sts-0-45-product.json`
- reproduzierbarer, noch **nicht bereitgestellter** Startzustand: `fixtures/enzberg-sts-0-45-base-v1.json`
- allgemeine leere Vorlage: `projects/_template/` (niemals mit BLE-Dateien überschreiben)

Das Fixture-Manifest beschreibt die Voraussetzungen, erstellt aber **keine** Datenbank und kein Testkonto. Die isolierte BLE-Instanz und der eigenständige Persistenz-Oracle aus Issue #11 müssen vor einem fachlichen GO tatsächlich bereitstehen.

Erster Test: Als Laborleitung Produkt STS 0–45 in Enzberg anlegen, die vorbereiteten Regelwerke TL SoB-StB 20 und ETV-StB-BW verknüpfen, speichern und über die UI erneut öffnen.

## Reale Voraussetzungen – noch nicht automatisch vorbereitet

- Lokale, ausschließlich für diesen Benchmark bestimmte BLE-Instanz samt isolierter Testdatenbank. Keine produktiven oder fremden Entwicklungsdaten verändern.
- Zurücksetzbarer Startzustand mit Laborleitungs-Testkonto und beiden vorhandenen Regelwerken. Das Produkt STS 0–45 darf vor dem Lauf noch nicht existieren.
- Verifizierte BLE-URL und Softwareversion.
- Tatsächlich verfügbare visionfähige API-Modell-IDs und entsprechende API-Schlüssel. ChatGPT Plus oder ein Claude-Abo ist kein automatisches API-Guthaben.

Die Datenbank-Migrationen und Fixture-Skripte liegen im BLE-Projektrepository, nicht hier. Der Runner führt deshalb bewusst **keinen** automatischen DB-Reset aus.

## Installation (Windows PowerShell)

    .\scripts\setup.ps1
    .\.venv\Scripts\Activate.ps1

The setup script uses the available `python` command (Python 3.11 or later),
creates `.venv` only if it does not exist, and installs the project and
Playwright Chromium there. It does not replace local configuration or API keys.

## Vorbereitung

    python -m sqbf.cli preflight --scenario projects/ble-elva/scenarios/sts-0-45-product.json --url http://127.0.0.1:5000/

127.0.0.1:5000 ist nur ein Platzhalter – tatsächliche URL einsetzen.

Im sichtbaren Chromium-Browser mit dem isolierten Testkonto anmelden:

    python -m sqbf.cli session --url http://127.0.0.1:5000/ --output .secrets/ble-session.json

Session-Cookies sind vertraulich; .secrets und runs werden von Git ignoriert.

## Teststart

In PowerShell den API-Schlüssel der gewählten Modellplattform als Umgebungsvariable setzen. Modell-IDs im folgenden Beispiel sind Platzhalter und müssen gegen tatsächlich verfügbare API-Modelle ersetzt werden.

    $env:ANTHROPIC_API_KEY = "API_KEY_NUR_LOKAL"
    python -m sqbf.cli run --scenario projects/ble-elva/scenarios/sts-0-45-product.json --url http://127.0.0.1:5000/ --software-version BLE_COMMIT_SHA --storage-state .secrets/ble-session.json --fixture-ready --executor-provider anthropic --executor-model VERIFIED_EXECUTOR_MODEL_ID --analyst-provider anthropic --analyst-model VERIFIED_ANALYST_MODEL_ID --interactive-budget

Alternativ OPENAI_API_KEY sowie `--executor-provider openai` bzw. `--analyst-provider openai` benutzen, wenn das gewählte visionfähige Modell die Responses API mit Bildeingaben unterstützt. Ein ChatGPT- oder Claude-Abonnement stellt nicht automatisch API-Zugang oder ein Ausgabenlimit bereit.

### Modell-IDs vor dem ersten API-Run

Die Modellnamen sind bei jedem Lauf explizit anzugeben. Zum Prüfzeitpunkt 12.10.2026 nennt OpenAI `gpt-6-luna` und `gpt-6-sol` in den API-Preisinformationen. Anthropic führt `claude-sonnet-5` als aktiv; `claude-haiku-4-5-20251001` ist ebenfalls gelistet, jedoch mit angekündigtem Ruhestand ab 15.10.2026. Die im Entscheidungsprotokoll genannten IDs `claude-haiku-5-5` und `claude-sonnet-5-5` konnte ich in den offiziellen aktuellen Anthropic-Modellangaben nicht bestätigen. Die öffentliche Modellliste belegt weder Zugriff über das lokale Konto noch Provider-Kompatibilität dieses Runners. Ohne lokal gesetzten API-Schlüssel wurde kein Live-Aufruf durchgeführt und es entstehen keine API-Kosten.

--fixture-ready ist eine ausdrückliche Bestätigung durch die ausführende Person, dass isolierte Fixtures vorbereitet wurden. Es startet selbst keinen Reset. Ohne --interactive-budget stoppt der Lauf beim Budget (25 Minuten / 150 UI-Aktionen). Im interaktiven Modus wird eine Erweiterung nur durch die explizite Eingabe APPROVE <zusatz_minuten> <zusatz_aktionen> genehmigt. Kein Resume nach Prozessende in V1.

## Dateien pro Lauf

Der lokale Ordner runs/<run-id>/ enthält:
- events.json: Aktionen, Laufzustände und Benachrichtigungen (getippter Text wird nicht gespeichert)
- evidence.json: Screenshot-Index und SHA-256
- ausgewählte Screenshots als PNG
- run.json: technische Daten, Modelle, Budgets, Nutzungsdaten, Urteil
- report.md: lesbarer Ergebnisbericht

Kein automatischer SharePoint-Upload, keine Issue-Erstellung, keine Mail-Nachrichten. Die finale Model-Bewertung allein ist noch kein unabhängiger Nachweis der DB-Persistenz: dafür wird später ein separater autorisierter Oracle-Checker benötigt.

## Lokale Tests

    python -m unittest discover -s tests -v

Es ist noch kein echter BLE-Pilot durch dieses Repository ausgeführt worden. Nach einem ersten lokalen Run sind Browser-Kompatibilität, Modellverhalten und fachliche Ergebnisverifikation zu prüfen.


## Verbindlicher Testweg: ausschließlich lokal (ohne GitHub Actions)

Für das SQBF/BLE-Benchmark-MVP werden **keine GitHub Actions und keine verpflichtende Cloud-CI** eingesetzt. Der Workflow `.github/workflows/mvp-tests.yml` wurde aus dem Entwicklungsbranch entfernt.

Codex prüft nach Änderungen direkt auf dem lokalen Windows-Rechner:

    .\scripts\setup.ps1
    python -m unittest discover -s tests -v
    python -m sqbf.cli preflight --scenario projects/ble-elva/scenarios/sts-0-45-product.json

Zusätzlich gehören ein lokaler Playwright-/Chromium-Smoke-Test und, sobald die isolierte BLE-Instanz samt Testkonto und API-Zugang vorhanden ist, der echte STS-0–45-Pilot dazu.

Für jeden relevanten Änderungssatz Testdatum, Python-/Playwright-Version, Befehle, Exit-Codes, Testergebnis und ggf. lokalen Berichtspfad in PR #10 bzw. dem zuständigen GitHub-Issue dokumentieren. Keine Zugangsdaten oder sensiblen Run-Artefakte nach GitHub hochladen.

**GitHub bleibt ausschließlich für Code, Issues, Pull Requests und Nachweise zuständig.** Fehlende GitHub-Actions-Runs sind ausdrücklich kein Freigabe-Blocker. Die bekannten Anforderungen an fachlichen Persistenznachweis, Tests und Review gelten weiter; kein Merge allein wegen eines erfolgreichen Commits.

## Aktuelle PO-Priorität 12.10.2026 – Prozesse statt Normenanlage

**LAB-01 Prozessbaseline**: `scenarios/sts-0-45-product-core-v0.2.json` mit Fixture-Vertrag `fixtures/enzberg-product-core-v0.2.json` ist der neue Ersttest. Er prüft die Produktanlage und das Wiederöffnen mit existierenden fachlich belegten Referenzen; Normen/Editionen werden **nicht neu angelegt**. Fehlt eine technisch zwingende Referenz, ist das ein dokumentierter Blocker und **kein Anlass, Grenzwerte oder Editionen zu erfinden**.

Das vorherige normative Szenario `scenarios/sts-0-45-product.json` (v0.1) bleibt als **historischer, zurückgestellter** Test erhalten, aber ist kein Pflichtgate des aktuellen Prozesspilots. NORM-01 bleibt gesondertes Backlog.

### Lokal und ohne Modell-/API-Aufrufe prüfen

```powershell
python -m unittest discover -s tests -v
python -m sqbf.cli doctor --url http://127.0.0.1:5059/
python -m sqbf.cli preflight --scenario projects/ble-elva/scenarios/sts-0-45-product-core-v0.2.json --url http://127.0.0.1:5059/
```

Der `doctor` sendet nur einen lokalen GET nach `/health/ready` und startet einen kleinen lokalen Chromium-Screenshot. Er führt **keinen** KI-Aufruf, keine Datenbankänderung und keinen Produktbenchmark aus. Er prüft den deklarativen Fixture-Status und meldet das Fehlen der unabhängig geprüften DB-Baseline, der sicheren Abo-Agentenintegration und des Persistenz-Oracles offen. Ein `TECHNICAL_SMOKE_READY` ist kein fachlicher Test-PASS.

**Schutz vor Zusatzkosten:** Der aktuelle CLI-Befehl `run` verweigert ausdrücklich die bisherige `openai`-/`anthropic`-HTTP-Provider-Integration. Abonnements funktionieren **nicht** automatisch über API-Schlüssel; der unterstützte Abo-Vision-Adapter benötigt noch einen gesonderten Sicherheits-/Funktionsnachweis in #14. Das ist bewusst ein Fail-Closed-Verhalten, kein ausgeführter Agententest.
