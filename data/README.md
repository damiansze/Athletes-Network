# Daten

Grundlage sind die 2025 erhobenen Daten von swimrankings.net. Gespeicherte persönliche Bestleistungen bilden keine vollständigen Wettkampfbiografien ab.

## Vorhandene Dateien

| Datei | Inhalt |
| --- | --- |
| `raw/athlete_data_master.csv` | Ursprüngliche Scrapingdaten mit Athletenangaben und Bestleistungen, einschliesslich fehlender Angaben und Duplikate. |
| `processed/athlete_data_clean.parquet` | Bereinigte Leistungstabelle aus [01_eda.ipynb](../Notebooks/01_eda.ipynb). Eine Zeile entspricht einem Bestleistungseintrag. Alle Jahre bleiben enthalten. |

`athlete_id` identifiziert eine Person. `nation` bezeichnet die beim Scraping ausgewählte Länderliste, `athlete_nation` die Nation im Athletenprofil.

Wettkampfname, Ort und Beckenlänge enthalten bereits vereinheitlichte Leerzeichen. Leere Angaben und Schreibvarianten wie `UNKNOWN` sind als `Unknown` gespeichert. Diese allgemeine Bereinigung erfolgt in `01_eda.ipynb`, die Zuordnung zu Netzwerken in `02_modellierung.ipynb`.

## Dateien der Modellierung

Diese Dateien werden von [02_modellierung.ipynb](../Notebooks/02_modellierung.ipynb) unter `processed/networks/` erzeugt. Beide Modelle verwenden alle Jahre.

| Datei | Inhalt |
| --- | --- |
| `athlete_events.gexf` | Bipartites Netzwerk aus Athleten und Veranstaltungstagen. Eine Kante steht für mindestens eine gespeicherte Bestleistung an diesem Tag. |
| `athletes.gexf` | Abgeleitetes Athletennetzwerk. Das Kantengewicht zählt gemeinsame Veranstaltungstage. |
| `disciplines.gexf` | Disziplinennetzwerk mit getrennten Knoten für Kurzbahn und Langbahn. Das Kantengewicht zählt gemeinsame Athleten. |
| `athlete_events.parquet` | Eindeutige Zuordnungen zwischen Athleten und Veranstaltungstagen samt Veranstaltungsangaben. |
| `athlete_disciplines.parquet` | Eindeutige Zuordnungen zwischen Athleten und Kombinationen aus Disziplin und Beckenlänge, ohne Zwischenzeiten mit `Lap`. |

Ein Veranstaltungstag wird über Wettkampfname, Ort, Datum und Beckenlänge zugeordnet. Eine Disziplin besteht aus Strecke und Schwimmstil. Die GEXF Dateien enthalten Knoten, Kanten und Attribute für Python und Gephi. Parquet speichert die zugehörigen Tabellen.

Die Spalten `athlete_node`, `event_id` und `discipline_id` der Zuordnungstabellen entsprechen den Knotenkennungen in GEXF. `athlete_id` bleibt die ursprüngliche Personenkennung. Fehlende Knotenattribute, etwa der Verein, werden in GEXF ausgelassen.

Die Regeln zur Erstellung stehen im [Modellierungsplan](../Report/PLAN_MODELLIERUNG.md). Plots werden im Notebook angezeigt und separat für den Report gespeichert.
