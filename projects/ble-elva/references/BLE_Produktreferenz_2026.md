# BLE Produktreferenz 2026

**Stand:** 06.10.2026  
**Zweck:** Verbindliche Arbeitsreferenz für die weitere Modellierung des Labor- und WPK-Prozesses in BLE.  
**Quelle:** Probenahmepläne 2026 unter  
`BLE/01_Labor & Prüfungen/Prüfberichte/RG-MIN 2026/{Enzberg|Keltern|Magstadt}`

> Diese Datei dokumentiert alle in den ausgewerteten Probenahmeplänen 2026 nachgewiesenen Produkte bzw. Probenahmepositionen.  
> Sie ersetzt nicht automatisch einen vollständigen kaufmännischen Materialstamm.

## 1. Fachliche Abkürzungen

| Kürzel | Bedeutung | Status |
|---|---|---|
| STS | Schottertragschicht | bestätigt |
| HGT | Hydraulisch gebundene Tragschicht | bestätigt |
| HST | Bezeichnung im aktuellen Magstadt-Plan; Verhältnis zu HGT noch fachlich zu klären | offen |
| BS | Brechsand | bestätigt |
| Sp / SP | Splitt | bestätigt |
| MB | Mineralbeton | bestätigt |
| Bet | Beton / Beton-Gesteinskörnung im Probenahmeplan | bestätigt |
| Asph | Asphalt / Asphalt-Gesteinskörnung | bestätigt |
| Fü | Füller | bestätigt |
| MWS | Bedeutung noch nicht geklärt | offen |
| Godel | Godel Beton; Auftraggeber/Abnehmer von Magstadt, kein Bestandteil des Produktnamens | bestätigt |

## 2. Modellierungsregeln

1. **Godel wird nicht als Produktbestandteil modelliert.**  
   Beispiel: `Bet 2-8 Godel` wird als Produkt `Bet 2-8` geführt. Godel ist lediglich der Auftraggeber/Abnehmer-Kontext.

2. **MWS bleibt bis zur fachlichen Klärung als Kontextzusatz erhalten**, wird aber nicht als eigene Produktfamilie interpretiert.

3. **Produktfamilie und Körnung werden getrennt betrachtet.**  
   Beispiel: `STS` = Produktfamilie, `0-45` = Sorte/Körnung.

4. Historische bzw. operative Bezeichnungen aus den Probenahmeplänen werden zusätzlich erhalten, damit bestehende Prüfberichte weiter zugeordnet werden können.

5. Die nachfolgende Liste ist die Arbeitsgrundlage für die weitere 0-to-End-Prozessmodellierung.

---

# 3. Werk Enzberg

| Originalbezeichnung im Plan | Normalisierte Produktbezeichnung | Produktfamilie | Entnahmestelle / Hinweis |
|---|---|---|---|
| STS 0-45 | STS 0-45 | STS | Band |
| STS 0-32 | STS 0-32 | STS | Band |
| BS (wie in STS 0-45) | BS aus STS 0-45 | BS | Band |
| BS abgem | BS 0-2 abgemagert | BS | Silo; Etikett im Plan: `BS 0-2 - abgemagert` |
| BS 0-1 | BS 0-1 | BS | Silo |
| BS 1-2 | BS 1-2 | BS | Silo |
| Sp 2-8 | Sp 2-8 | Splitt | Silo |
| Sp 8-16 | Sp 8-16 | Splitt | Silo |
| Bet 2/8 | Bet 2-8 | Bet | Band |
| Bet 8-16 | Bet 8-16 | Bet | Band |
| Asph 2-16 | Asph 2-16 | Asphalt | Band |
| Asph 16-32 | Asph 16-32 | Asphalt | Band |
| Fü Abmag | Füller Abmagerung | Füller | Silo |
| Fü Kost | Fü Kost | Füller | Silo; Bedeutung `Kost` noch nicht erweitert |

**Enzberg: 14 planmäßige Produkte/Probenahmepositionen.**

---

# 4. Werk Keltern

Die 2026er Probenahmepläne wurden für mehrere Zeitpunkte gegengeprüft (u. a. Februar, April, Juni, Juli und August). Die Positionen bleiben dabei konstant.

| Originalbezeichnung im Plan | Normalisierte Produktbezeichnung | Produktfamilie | Hinweis |
|---|---|---|---|
| STS 0-45 | STS 0-45 | STS | Hauptposition |
| Sand separat (aus 0-45) | Sand separat aus STS 0-45 | Sand / Feinanteil aus STS | separate Probenahmeposition |

**Keltern: 2 nachgewiesene Produkte/Probenahmepositionen.**

---

# 5. Werk Magstadt

| Originalbezeichnung im Plan | Normalisierte Produktbezeichnung | Produktfamilie | Entnahmestelle / Kontext |
|---|---|---|---|
| STS 0-45 | STS 0-45 | STS | Band |
| STS 0-32 | STS 0-32 | STS | Band |
| HST 0-45 | HST 0-45 | HGT/HST | Band; genaue Begriffseinordnung noch offen |
| BS 0-0,5 | BS 0-0,5 | BS | Silo |
| BS 0,5-2 Godel | BS 0,5-2 | BS | Silo; Godel = Auftraggeber/Abnehmer |
| BS 0-2 MWS | BS 0-2 | BS | Band; MWS = ungeklärter Kontext |
| BS 0-1 | BS 0-1 | BS | Silo |
| BS 1-2 | BS 1-2 | BS | Silo |
| Sp 2-5 | Sp 2-5 | Splitt | Silo |
| Sp 5-8 | Sp 5-8 | Splitt | Silo |
| Sp 8-11 | Sp 8-11 | Splitt | Silo |
| Sp 11-16 | Sp 11-16 | Splitt | Silo |
| MB 2-8 | MB 2-8 | Mineralbeton | Silo |
| MB 8-16 | MB 8-16 | Mineralbeton | Silo |
| MB 16-32 | MB 16-32 | Mineralbeton | Silo |
| MB 32-45 | MB 32-45 | Mineralbeton | Silo |
| Bet 2-8 Godel | Bet 2-8 | Bet | Band; Godel = Auftraggeber/Abnehmer |
| Bet 8-16 Godel | Bet 8-16 | Bet | Band; Godel = Auftraggeber/Abnehmer |
| Bet 16-22 Godel | Bet 16-22 | Bet | Silo; Godel = Auftraggeber/Abnehmer |
| Asph 5-16 MWS | Asph 5-16 | Asphalt | Band; MWS = ungeklärter Kontext |
| Asph 16-22 MWS | Asph 16-22 | Asphalt | Silo; MWS = ungeklärter Kontext |
| Asph 22-32 MWS | Asph 22-32 | Asphalt | Silo; MWS = ungeklärter Kontext |
| Fü MB | Fü MB | Füller | Silo |
| Fü Sp MWS | Fü Sp | Füller | Silo; MWS = ungeklärter Kontext |

**Magstadt: 24 planmäßige Produkte/Probenahmepositionen.**

Besondere Regel aus dem Probenahmeplan:
- Bei `Asph 16-22 MWS` ist vermerkt, dass einmal je Fraktion genügt, wenn das Material aus demselben Silo stammt.

---

# 6. Konsolidierte Produktfamilien

## STS – Schottertragschicht
- STS 0-32
- STS 0-45

## HGT / HST – hydraulisch gebundene Tragschicht
- HST 0-45
- Verhältnis der Bezeichnungen HGT/HST noch klären

## BS – Brechsand
- BS aus STS 0-45
- BS 0-0,5
- BS 0-1
- BS 0,5-2
- BS 1-2
- BS 0-2
- BS 0-2 abgemagert

## Splitt
- Sp 2-5
- Sp 2-8
- Sp 5-8
- Sp 8-11
- Sp 8-16
- Sp 11-16

## Mineralbeton
- MB 2-8
- MB 8-16
- MB 16-32
- MB 32-45

## Beton / Bet
- Bet 2-8
- Bet 8-16
- Bet 16-22

## Asphalt
- Asph 2-16
- Asph 5-16
- Asph 16-22
- Asph 16-32
- Asph 22-32

## Füller
- Füller Abmagerung
- Fü Kost
- Fü MB
- Fü Sp

## Weitere Probenahmeposition
- Sand separat aus STS 0-45

---

# 7. Noch offene Begriffe

Diese Punkte sind bewusst **nicht geraten** und müssen bei Gelegenheit fachlich bestätigt werden:

- `MWS` – genaue Bedeutung und Rolle
- `HST` gegenüber `HGT` – Alias, alte/neue Bezeichnung oder fachlich unterschiedliche Sorte
- `Kost` in `Fü Kost`
- genaue fachliche Einordnung von `Fü MB` und `Fü Sp` über die reine Füller-Bezeichnung hinaus

Bis zur Klärung bleiben die Originalbezeichnungen vollständig erhalten.

---

# 8. Verwendung im weiteren BLE-Prozess

Für die weitere Modellierung gilt diese Datei als Ausgangspunkt für:

`Werk → Produktfamilie → Sorte/Körnung → Probenahmeplan → konkrete Probenahme → Probe → Prüfungen → Bewertung → Prüfbericht / WPK-Nachweis`

Änderungen oder neu auftauchende Produkte sollen künftig direkt in dieser Referenz ergänzt werden, statt die historischen Probenahmepläne erneut vollständig auszuwerten.