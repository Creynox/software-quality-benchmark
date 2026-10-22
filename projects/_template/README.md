# __PROJECT_NAME__ – SQBF-Projektprofil (leere Vorlage)

Dieses Projekt wurde aus der versionierten SQBF-Vorlage 1.0 erstellt.
Es enthält ABSICHTLICH **keine** gültige Software-URL, Identitäten, Rollen,
Testdatensätze, Normen, geheimen Zugangsdaten oder vorhandenen Run-Ergebnisse.

## Vor dem ersten Preflight ausfüllen

1. project.json: Anwendung und Projektmetadaten prüfen.
2. scenarios/first-task.json: UI-URL, Rolle, konkrete Benutzeraufgabe,
   messbare sichtbare Erwartungen, Zeit-/Aktionsbudget festlegen.
3. fixtures/first-task.json: getrennte Testumgebung, nicht-destruktive
   reproduzierbare Vorbereitung, unabhängige Prüfung und sicheren Reset
   dokumentieren. Fixture-Bereitstellung erfolgt AUSSERHALB des UI-Executors.
4. Gültigen lokal installierten Modell-API-Zugang und expliziten Softwarestand
   des Zielsystems prüfen. Keine Secrets ins Repository.
5. Erst nach überprüfter Fixture-Isolation die Runner-Freigabe erteilen.

## Prüfen (nach Konfiguration)

    python -m sqbf.cli preflight --scenario projects/__PROJECT_SLUG__/scenarios/first-task.json --url http://SET_REAL_LOCAL_UI_URL/

Nur Beispiel: die URL muss bewusst durch den tatsächlichen isolierten
Anwendungsendpunkt ersetzt werden. Unveränderte Platzhalter sind nicht startbar.

## Regeln

- SQBF Core bleibt hersteller- und projektneutral.
- Browser-Executor sieht nur zulässige Screenshots/Benutzeraktionen.
- Sichtbare Erfolge und unabhängige Datenpersistenz getrennt bewerten.
- Run-Nachweise werden lokal und außerhalb von Git gespeichert.
- Ohne lokale Tests kein GO. Keine GitHub Actions.
