# BLE Laborprozess 0→End – Fachliches Arbeitsmodell v0.2

**Stand:** 06.10.2026  
**Zweck:** Verbindliche Arbeitsreferenz für die weitere BLE-Prozessmodellierung.

## 1. Grundprinzip

Der Laborprozess läuft **batch-orientiert**, nicht „eine Probe vollständig von Anfang bis Ende“.

Eine Probe kann in mehrere Teilproben zerlegt werden, z. B. für:
- Siebung
- Trocknen/Waschen
- Kornform
- Kochversuch/Sonnenbrand
- Teilsiebung
- Sandäquivalent (SÄ)
- Rückstellprobe

Alle Teilproben müssen dauerhaft auf die ursprüngliche Probe zurückführbar bleiben.

## 2. Wöchentlicher Zyklus

1. Ein Probenahmeplan wird normalerweise einmal pro Woche erstellt, meist zusammen mit bzw. nach Abgabe der letzten Prüfberichte.
2. Der Probenahmeplan legt Werk, Produkte/Sorten und die vorgesehenen Prüfungen bzw. Prüfrotation fest.
3. Heute dient die Probenahmeplan-Nummer als grobe gemeinsame Probennummer, z. B. Plan 42.
4. Zukünftig bleibt die Plan-Nummer als Prüfserien-/Batch-ID erhalten; jede einzelne Probe erhält zusätzlich eine eindeutige Datenbank-ID.

## 3. Probenahme im Werk und Transport

Die im Probenahmeplan vorgesehenen Materialien werden im Werk entnommen, in Eimern bereitgestellt und anschließend durch Personal ins Labor gebracht.

Jeder Eimer enthält einen Probenzettel mit mindestens:
- Werk/Ursprung
- Produkt/Sorte
- Datum

Beispiele:
- `Magstadt – STS 0-45 – 08.10.2026`
- `Enzberg – Beton 2-8 – 08.10.2026`

## 4. Typische Eingangsmengen

Ein Eimer enthält typischerweise ca. **15–20 kg**.

### Gemische
Beispiele: STS, HGT/HST  
Typisch: **3 Eimer à 15–20 kg**, also ca. 45–60 kg Gesamtmaterial.

### Einzelkörnungen
Beispiele: Beton 2-8, Beton 8-16, Splittfraktionen  
Typisch: **1 Eimer à 15–20 kg**.

### Brechsand und Füller
Typisch ebenfalls **1 Eimer à 15–20 kg**.

Ausnahmen sind möglich, ändern aber den grundsätzlichen Prozess nicht.

## 5. Probeneingang im Labor

Die Eimer werden anhand der Probenzettel identifiziert und sortiert.

Zukünftig soll BLE prüfen können:
- welche Proben laut Probenahmeplan erwartet werden,
- welche eingegangen sind,
- welche fehlen,
- welche eindeutig identifiziert sind.

## 6. Aufbereitung von Gemischen

Gemische aus mehreren Eimern werden fachgerecht probegeteilt und zu einer repräsentativen Laborprobe zusammengeführt.

Typische Laborprobenmassen:
- 0-32: ca. 16–18 kg
- 0-45: ca. 18–20 kg

Die tatsächliche Menge richtet sich nach:
- Norm,
- Feuchte,
- Materialzustand,
- benötigten Folgeprüfungen,
- zusätzlichen oder doppelten Entnahmen.

Die endgültige Menge entscheidet der Mitarbeiter fachlich.

## 7. Erste Teilprobenbildung

### Einzelkörnungen
Normalerweise entstehen zunächst:
- Teilprobe für die direkte Siebprüfung
- Teilprobe für Trocknen/Waschen

### Brechsand und Füller
Hier erfolgt zunächst keine separate direkte Siebprobe.

Ablauf:
`Trocknen → Wiegen → Waschen/Abschlämmen → erneut trocknen → wiegen → teilen → sieben`

Der Vorbereitungsschritt ist erst abgeschlossen, wenn alle vorgesehenen Proben entsprechend aufgeteilt wurden.

## 8. Gemische sieben

Gemische werden einzeln über den passenden Siebturm gesiebt.

Dabei können weitere Teilproben entstehen:
- Kornform
- Kochversuch/Sonnenbrand
- Teilsiebung
- Sandäquivalent

Nicht jede Probe benötigt jede Prüfung.

## 9. Teilsiebung

Für die Teilsiebung wird während der Gemischsiebung ein definierter Feinanteil separiert.

Typische Trennpunkte:
- < 5,6 mm
- < 4 mm

Der genaue Trennpunkt ist produkt-/normabhängig.

Diese Teilprobe kommt anschließend in den Trocknungsprozess.

## 10. Sandäquivalent (SÄ)

SÄ = **Sandäquivalent**.

Aus dem Feinanteil wird eine normgerechte Materialmenge entnommen und separat für das SÄ-Verfahren bereitgestellt.

## 11. Arbeits-Batches

Teilproben werden nach ihrem nächsten Arbeitsschritt gesammelt.

Typische Batches:
- Trocknungs-Batch
- Kornform-Batch
- Kochversuch-/Sonnenbrand-Batch
- SÄ-Batch

Der Kochversuch kann von einer anderen Person durchgeführt werden.

## 12. Prüfsteuerung / Prüfrotation

Heute wird über Excel-Ausdrucke bzw. Tabellen festgelegt, welche Prüfungen aktuell anstehen.

Beispiel:
Wenn bei Asphalt in der aktuellen Runde Kornform (KF) vorgesehen ist, werden die entsprechenden Unterlagen und Teilproben vorbereitet.

Die Entscheidung ergibt sich aus:
- definierter Prüfrotation,
- Probenahmeplan,
- Kundenabsprache bei Sonderfällen.

### Zielzustand BLE
Die UI soll aus `Werk + Produkt + Prüfplan/Rotation + Kundenanforderung` automatisch ableiten:
- welche Prüfungen erforderlich sind,
- welche Teilproben benötigt werden,
- welche Arbeitsschritte entstehen,
- wann die Prüfung fällig ist.

Sonder- und Zusatzprüfungen müssen weiterhin manuell ergänzt werden können.

## 13. Erster Trocknungslauf

Aktueller Arbeitswert:
- ca. **120 °C**
- ca. **4 Stunden aktive Trocknung**
- danach weitere Trocknungs-/Abkühl-/Wartezeit, insgesamt häufig etwa 10 Stunden bzw. bis zum nächsten Arbeitstag

Die verbindlichen Werte richten sich nach der jeweiligen Norm und müssen später prüfverfahrensbezogen hinterlegt werden.

## 14. Einzelkörnungen sieben

Die Einzelkörnungen werden gesiebt.

Dabei können weitere Teilproben für:
- Kornform
- Kochversuch/Sonnenbrand

entstehen.

Diese werden zu den bereits bestehenden Prüf-Batches gelegt.

## 15. Kochversuch / Sonnenbrand

Wenn alle vorgesehenen Kochversuchsproben vorbereitet sind, werden sie gemeinsam nach dem entsprechenden Verfahren angesetzt.

Während der Kochversuch läuft, werden parallel andere Arbeiten durchgeführt.

## 16. Kornform parallel prüfen

Nach dem Ansetzen des Kochversuchs werden typischerweise die gesammelten Kornformproben bearbeitet.

Die Ergebnisse werden pro ursprünglicher Probe dokumentiert.

## 17. Kochversuch auswerten

Nach Abschluss des Koch-/Sonnenbrandverfahrens und der notwendigen Folgebehandlung werden die Teilproben nach Norm ausgewertet und der Ursprungsprobe zugeordnet.

## 18. Trocknen – Wiegen – Waschen

Nach dem ersten Trocknungslauf:
1. jede Probe einzeln wiegen,
2. Trockengewicht dokumentieren,
3. einzeln waschen/abschlämmen,
4. erneut in den Trockenschrank geben.

## 19. Zweiter Trocknungslauf

Nach erneutem Trocknen wird wieder gewogen und dokumentiert.

### Grobe Einzelkörnungen
Bei Material mit D > ca. 2 mm wurde die eigentliche Siebung bereits separat durchgeführt. Das Material aus diesem Trocknen-/Waschen-Pfad kann nach Erfüllung der Prüfanforderung verworfen werden.

### Brechsand und Füller
Diese feinen Proben werden nach Trocknen und Waschen in **zwei repräsentative Teilmengen** geteilt.

Beide Teilmengen werden separat gesiebt:
- Siebung 1
- Siebung 2

Beide Ergebnisse gehören zur selben Ursprungsprobe.

## 20. SÄ-Prüfung

Die vorbereiteten Sandäquivalent-Proben werden nach dem vorgesehenen Prüfverfahren bearbeitet und dokumentiert.

## 21. Vollständigkeitskontrolle

Eine Probe gilt erst als vollständig geprüft, wenn alle für sie vorgesehenen Prüfpfade abgeschlossen sind.

Mögliche Prüfpfade:
- Siebung
- Trocknen/Waschen
- Teilsiebung
- Kornform
- Kochversuch/Sonnenbrand
- Sandäquivalent

## 22. Ergebnisprüfung und Freigabe

Heute erfolgen Eingabe, Prüfung und Excel-Pflege meist durch denselben Prüfer in einem Arbeitsgang.

### Zielzustand BLE
Künftig:
`Ergebnis erfasst → fachlich geprüft → Laborleiter-Freigabe → berichtsfähig`

Ein endgültiger Prüfbericht darf erst nach der erforderlichen Freigabe versendet werden.

## 23. Auffällige Ergebnisse / Wiederholungsprüfung

Bei Auffälligkeiten wird zunächst unterschieden, ob eher ein Prüf-/Mitarbeiterfehler oder ein tatsächlicher Produkt-/Werksfehler vorliegt.

### Möglicher Prüf-/Mitarbeiterfehler
Nur den kleinsten fachlich notwendigen Teil wiederholen.

Beispiel:
Kornform zweifelhaft → neue Kornform-Teilprobe entnehmen → nur Kornform wiederholen.

### Zweifel an kompletter Sieblinie
Rückstellprobe verwenden und Gegenprüfung durchführen.

### Bestätigter Werks-/Produktfehler
- Abweichung dokumentieren
- im Prüfbericht ausweisen
- ggf. einfache Abhilfemaßnahme empfehlen

### Wiederkehrender Fehler
- Rezeptur untersuchen
- Ursache bewerten
- ggf. Rezeptanpassung vorschlagen

## 24. Rückstellproben

Die Aufbewahrungsdauer ist auftraggeberabhängig.

Beim aktuell betrachteten Ablauf bleibt die Rückstellprobe bis zur nächsten neuen Probenserie erhalten; dann kann die vorherige Rückstellprobe entsorgt werden.

Andere Auftraggeber können z. B. **1 Jahr** Aufbewahrung verlangen.

### Zielzustand BLE
Aufbewahrungsregeln müssen konfigurierbar sein, mindestens nach:
- Auftraggeber
- Prüfvertrag/WPK-Regel
- ggf. Produkt/Prüfart

BLE sollte `Rückstellprobe aufbewahren bis` führen.

## 25. Ergebnisübertragung und Prüfbericht

Nach Abschluss aller Prüfungen werden die Ergebnisse heute in Excel-Tabellen übertragen, zusammengeführt und bewertet.

Danach werden Prüfberichte/Ergebnisse an den Auftraggeber gesendet.

Langfristig soll BLE diese Auswertung und Berichterstattung strukturiert übernehmen.

## 26. Neuer Zyklus

Mit bzw. nach Abgabe der Prüfberichte wird der nächste Probenahmeplan erstellt.

Damit beginnt die nächste Prüfserie.

---

# 27. Gesamtprozess

`Prüfrotation/Kundenanforderung`
→ `Probenahmeplan`
→ `Probenahme im Werk`
→ `Transport`
→ `Probeneingang`
→ `Laborprobe / Probeteilung`
→ `Teilproben`
→ `Arbeits-Batches`
→ `Siebung / Trocknung / Kornform / Kochversuch / SÄ`
→ `Vollständigkeitskontrolle`
→ `Ergebnisprüfung`
→ `ggf. Wiederholungsprüfung`
→ `Laborleiter-Freigabe`
→ `Prüfbericht`
→ `Versand`
→ `Rückstellprobe`
→ `neuer Probenahmeplan`

---

# 28. Zentrale BLE-Datenobjekte

- Probenahmeplan / Prüfserie
- Probe
- Eingangseinheit / Eimer
- Laborprobe
- Teilprobe
- Prüfauftrag
- Arbeitsbatch
- Prüfergebnis
- Wiederholungsprüfung
- Rückstellprobe
- Freigabe
- Prüfbericht

## Zentrale Software-Regeln

1. Probenahmeplan-Nummer und Probe-ID müssen getrennt werden.
2. Jede Probe erhält künftig eine eindeutige Datenbank-ID.
3. Eine Probe kann aus mehreren Eimern bestehen.
4. Eine Probe kann mehrere Teilproben und parallele Prüfpfade besitzen.
5. Teilproben müssen immer auf die Ursprungsprobe zurückführbar sein.
6. Gleiche Arbeitsschritte mehrerer Proben müssen als Batch bearbeitbar sein.
7. Prüfpflichten ergeben sich aus Produkt, Rotation und Kundenanforderungen.
8. Normwerte sind Regeln, aber begründete fachliche Abweichungen müssen möglich sein.
9. Wiederholungsprüfungen sollen nur den kleinsten erforderlichen Umfang neu prüfen.
10. Rückstellfristen sind auftraggeberabhängig.
11. Abschluss erfordert Vollständigkeit aller Pflichtprüfungen.
12. Endgültiger Bericht erfordert zukünftig Laborleiter-Freigabe.

---

# 29. Noch offene Detailpunkte

- vollständige Prüfrotationsmatrix je Produkt
- konkrete Prüfungen je Produkt/Körnung
- Normmengen der Teilproben
- Siebtürme/Siebfolgen je Produkt
- genaue Teilsiebungsregeln
- Kornformregeln
- Kochversuchs-/Sonnenbrandregeln
- genaue SÄ-Regeln
- verbindliche Trocknungsparameter je Prüfverfahren
- Umgang mit fehlenden/falsch beschrifteten Proben
- Umgang mit zu geringer Probenmenge
- Statusmodell während der Bearbeitung
- Freigabe-/Korrekturlogik
- Berichtsgenerierung und Versand
- Entsorgungs-/Rückstellprobenprozess

Diese Punkte werden schrittweise ergänzt, bis der reale Laborprozess vollständig ohne implizites Erfahrungswissen modelliert ist.