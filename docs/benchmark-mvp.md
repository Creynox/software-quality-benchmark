# SQBF V1 – Rollen- und Sicherheitsvertrag

Scope: GitHub Epic #9, BENCH-MVP-PRIORITY-001 und BENCH-MVP-AGENT-ROLES-001.

- **Deterministischer Controller:** isolierter Windows-Browser, Zielhost-Allowlist, Zeit-/Aktionsbudget, selektive Screenshots, strukturierte Aktionen und Reports.
- **Vision-Executor:** ein günstig ausgewähltes multimodales Modell; Screenshot-Eingabe, eine validierte Maus-/Tastaturaktion pro Turn. Keine DOM-Auslesung, DevTools, Backend-/DB-/Quellcodezugriffe oder vorgegebene versteckte URLs.
- **Mechanischer Checker:** Syntax und Sicherheitsgrenzen der Aktionen, Wallclock, Zähler, Evidence-Prüfsummen. Kann keinen fachlichen BLE-PASS ohne Oracle behaupten.
- **Analyst:** ein stärkeres visionfähiges Modell wertet abschließend letzten UI-Zustand und ein kompaktes Ereignisprotokoll aus. Finds sind Hypothesen und keine automatischen GitHub-Bugs.
- **Expertenreview:** nur bei Bedarf; nicht Bestandteil des ersten MVP.

## Bekannte Grenzen und Sicherheitslücken, die vor Produktion zu schließen sind

- Der letzte Screenshot kann nicht beweisen, dass Daten erfolgreich in der BLE-Datenbank persistiert sind. Urteil des Bildmodells ist nur vorläufig. Getrennte, autorisierte Oracle-Prüfung als Follow-up.
- Der Runner führt noch keinen echten Fixture-Reset aus. Test-DB und Laborleitungs-Konto müssen außerhalb der Executor-Befugnisse vorbereitet werden.
- Screenshot-Modelle verarbeiten potenziell sichtbare vertrauliche Inhalte beim API-Anbieter. Nur synthetische isolierte Testdaten, keine Secrets oder Personendaten benutzen.
- Browser-Host-Allowlist begrenzt Playwright-HTTP-Requests; Drittanbieter-CDN/SSO können deshalb scheitern. Es ist keine Netzwerk-Sandbox gegen alle denkbaren Drittkanäle.
- Nicht alle API-Modelle unterstützen Chat Completions oder Bilder in gleicher Weise; die tatsächlichen Modell-IDs/Features sind mit dem Provider zu testen.
- Bei API-Störungen, Budgetstopp oder unklaren Ergebnissen keinen fachlichen PASS behaupten. Verbräuche werden protokolliert, nicht als präzise Euro-Kosten berechnet.
- Fortsetzen nach Budgetpause ist nur innerhalb derselben laufenden Browserprozess-Sitzung implementiert; Pause über Programmneustart bleibt Follow-up.

## Nachweise bis zum MVP-GO

1. Tatsächliche isolierte BLE-Instanz, Konten und Produkt-/Regelwerks-Fixture verifiziert.
2. Startskript startet Chromium mit diesen Rollenrechten und ohne unzulässige Agenteninternazugriffe.
3. STS-0–45-Produkt und beide Normen über UI angelegt/verknüpft, anschließend sichtbar erneut geöffnet.
4. Manifest, Screenshots, Eventlog und Markdown-Bericht vorhanden; objektive Persistenz und Analystenurteil ausdrücklich getrennt.
5. Testläufe und Sicherheitsgrenzen dokumentiert, PR geprüft; ggf. Follow-ups für offene Defizite.

Die bereits beschlossenen langfristigen Governance-/Scoring-/Reminder-Anforderungen bleiben Zielbild, sind aber keine Voraussetzung für den ersten lokalen MVP-Smoke.
