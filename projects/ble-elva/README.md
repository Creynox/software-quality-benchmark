# BLE/ELVA Blackbox Micro-Pilot V1

Erster Test: Als Laborleitung Produkt STS 0–45 in Enzberg anlegen, die vorbereiteten Regelwerke TL SoB-StB 20 und ETV-StB-BW verknüpfen, speichern und über die UI erneut öffnen.

## Reale Voraussetzungen – noch nicht automatisch vorbereitet

- Lokale, ausschließlich für diesen Benchmark bestimmte BLE-Instanz samt isolierter Testdatenbank. Keine produktiven oder fremden Entwicklungsdaten verändern.
- Zurücksetzbarer Startzustand mit Laborleitungs-Testkonto und beiden vorhandenen Regelwerken. Das Produkt STS 0–45 darf vor dem Lauf noch nicht existieren.
- Verifizierte BLE-URL und Softwareversion.
- Tatsächlich verfügbare visionfähige API-Modell-IDs und entsprechende API-Schlüssel. ChatGPT Plus oder ein Claude-Abo ist kein automatisches API-Guthaben.

Die Datenbank-Migrationen und Fixture-Skripte liegen im BLE-Projektrepository, nicht hier. Der Runner führt deshalb bewusst **keinen** automatischen DB-Reset aus.

## Installation (Windows PowerShell)

    py -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -e .
    python -m playwright install chromium

## Vorbereitung

    python -m sqbf.cli preflight --scenario projects/ble-elva/scenarios/sts-0-45-product.json --url http://127.0.0.1:5000/

127.0.0.1:5000 ist nur ein Platzhalter – tatsächliche URL einsetzen.

Im sichtbaren Chromium-Browser mit dem isolierten Testkonto anmelden:

    python -m sqbf.cli session --url http://127.0.0.1:5000/ --output .secrets/ble-session.json

Session-Cookies sind vertraulich; .secrets und runs werden von Git ignoriert.

## Teststart

In PowerShell den API-Schlüssel der gewählten Modellplattform als Umgebungsvariable setzen. Modell-IDs im folgenden Beispiel sind Platzhalter und müssen gegen tatsächlich verfügbare API-Modelle ersetzt werden.

    $env:ANTHROPIC_API_KEY = "API_KEY_NUR_LOKAL"
    python -m sqbf.cli run --scenario projects/ble-elva/scenarios/sts-0-45-product.json --url http://127.0.0.1:5000/ --storage-state .secrets/ble-session.json --fixture-ready --executor-provider anthropic --executor-model TATSAECHLICHE_HAIKU_ID --analyst-provider anthropic --analyst-model TATSAECHLICHE_SONNET_ID --interactive-budget

Alternativ OPENAI_API_KEY sowie --executor-provider openai bzw. --analyst-provider openai benutzen, wenn das gewählte visionfähige Modell Chat-Completions-Bildeingaben unterstützt.

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
