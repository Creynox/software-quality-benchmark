# NSN014-Benchmark: Startseite

SQBF prüft BLE mit **46 festen Prüfpunkten** in zwölf Stufen (Probeneingang bis Prüfbericht). Jeder Lauf endet mit Punkten,
„bestanden“ oder „nicht bestanden“ je Prüfpunkt und einer Ursache für alles Offene, nur aus Zahlen und Fakten.

## Ein Lauf von A bis Z

Alle Befehle: `python -m sqbf.cli nsn014 <Schritt> --name <Lauf-Akte>` (z. B. `--name lauf-09`). Jeder Schritt hält sein Ergebnis in der
Lauf-Akte fest; `status` zeigt jederzeit die Checkliste und den nächsten Befehl.

| Schritt | Was passiert | Modell |
|---|---|---|
| `status` | Lage: Docker, wer die Ports hält, neueste Sitzungen, Provider-Probe, nächster Schritt | – |
| `prepare [--rehearse]` | die beiden Trockenläufe (und der Probelauf) in einem Ablauf; bestandene Schritte bleiben bestehen | wie die Einzelschritte |
| `dry-run` | Wegwerfkopie und skriptierter Trockenlauf mit allen echten Prüfungen | keins |
| `dry-run-faults` | dasselbe mit drei eingespielten Provider-Fehlern | keins |
| `rehearse` (optional) | Probelauf mit Claude Haiku 5.5 als Executor; zeigt, wo Aufgaben für ein Modell schwer sind | Claude, über die lokale Claude-Code-Anmeldung |
| `fixture` | frische Fixture für den Lauf, Sitzungen, Readiness | keins |
| `probe` | zwei Probe-Anfragen an den ChatGPT-Plan (12 Stunden gültig) | 2 Anfragen |
| `approve --statement "…"` | **nur mit ausdrücklicher Freigabe des PO**: genau ein Lauf, an Commit, Fixture und Budget gebunden | – |
| `run` | Readiness und genau ein Lauf, kein Retry, danach die Berichte | ChatGPT-Plan |

Ein fehlgeschlagener Schritt wird wiederholt (er legt eine neue Kopie an). Ein abgebrochener Schritt (Prozess beendet) wird beim
nächsten Start als `ABORTED` vermerkt und neu begonnen. Eine Freigabe gilt für genau einen Lauf.

Lange Schritte (`prepare`, `rehearse`, `run`: eine bis drei Stunden) startet ein Agent mit `--detach` losgelöst von seiner Sitzung,
damit deren Zeitgrenze den Lauf nicht mitnimmt (das Protokoll liegt in der Lauf-Akte; `status` zeigt den Fortschritt).

## Ergebnisse lesen

- **`bericht.html`** im Lauf-Ordner: der Bericht für Menschen (das Wichtigste, Balken je Stufe, Veränderungen, offene Punkte mit Bedeutung
  und Nutzen der Behebung, Entscheidungen mit Empfehlung, Checkliste, nächste Schritte, unten jeder Prüfpunkt mit seinen Kriterien, Begriffe).
- **`uebersicht.html`** im Ordner aller Läufe: alle Läufe mit Ergebnis, Punkten und Vergleichsgruppe.
- `scorecard.json` (für Maschinen), `punktebericht.md` (feste Fassung), `completion-report.md` (Belege für Nachprüfungen).
- Trocken- und Probeläufe liegen in der Lauf-Akte, sind gekennzeichnet und **nie Benchmark-Ergebnisse**.

## Regeln

- Kein Live-Lauf ohne ausdrückliche Freigabe des PO. Kein Eingriff in BLE-Daten oder Produktkonfiguration.
- Die Auswertung folgt der festen, versionierten [Spezifikation](../../docs/nsn014-report-spec.md); Agenten übernehmen Zahlen, sie schätzen nichts.
- Ein BLE-Fehler ist nur ein Prüfpunkt „nicht bestanden“. Beobachtungen des Reviewers bleiben unbestätigt.
- Offene und getroffene Entscheidungen stehen in [decisions.json](decisions.json).

## Einrichtung (einmal je Rechner)

1. Lokale Konfiguration `%LOCALAPPDATA%\SQBF\nsn014-pipeline.json` nach [Vorlage](pipeline.example.json) anlegen (private Pfade, nie ins Repository).
2. Docker Desktop starten (nach einem Neustart von Hand).
3. ChatGPT-Anmeldung einmal behalten: `python -m sqbf.plan_login --keep-signed-in` (7 Tage gültig).
4. Für Probeläufe: Claude Code angemeldet.

## Archiv

[Betriebsanleitung](operations.md) · [Verlauf aller Läufe](../../docs/nsn014-v04-completion-report.md) ·
[Unbestätigte Beobachtungen zu BLE](../../docs/nsn014-ble-observations.md) · [Auswertung](../../docs/nsn014-report-spec.md)
