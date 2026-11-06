# Daten

Die Daten wurden Mitte 2025 mit dem Scraper unter `scraper/` von
[swimrankings.net](https://www.swimrankings.net) erhoben. Erfasst sind die TOP100-Listen
mit bis zu 100 Männern und 100 Frauen je Land sowie die persönlichen Bestleistungen
dieser Athleten.

Pro Athlet ist je Disziplin und Beckenlänge nur die schnellste Zeit der Karriere
gespeichert. Verbessert ein Athlet diese Zeit, ersetzt der neue Eintrag den früheren.
Die Daten bilden deshalb keine vollständigen Wettkampfbiografien ab.

Alle Dateien werden über Git LFS versioniert (`git lfs pull`).

## Struktur

| Ordner oder Datei | Erzeugt von | Inhalt |
| --- | --- | --- |
| `raw/athlete_data_master.csv` | `scraper/scripts/scrape.py` | Unveränderte Rohdaten mit Athletenangaben und Bestleistungen |
| `processed/athlete_data_clean.parquet` | `01_eda.ipynb` | Bereinigte Tabelle, eine Zeile pro Bestleistungseintrag |
| `processed/networks/` | `02` bis `04` | Netzwerke als GEXF (für Python und Gephi) und Zuordnungstabellen als Parquet |
| `processed/centrality/` | `05_zentralitaet.ipynb` | Zentralitäten, Tests und Zwischenspeicher der exakten Betweenness |
| `processed/zusammenhalt/` | `06_zusammenhalt.ipynb` | Kennzahlen, Nullmodell, Robustheit, Generationen |
| `processed/assortativitaet/` | `07_assortativitaet.ipynb` | Tests, lokale Werte und Attribute pro Athlet |
| `processed/link_prediction/` | `08_link_prediction.ipynb` | Datensplit, Scores und Auswertung |

## Netzwerke in `processed/networks/`

| Datei | Inhalt |
| --- | --- |
| `athlete_events.gexf` | Two-Mode-Netz aus Athleten und Veranstaltungstagen |
| `athletes.gexf` | Athletenprojektion, Kantengewicht = gemeinsame Veranstaltungstage |
| `disciplines.gexf` | Disziplinennetz, Kantengewicht = gemeinsame Athleten |
| `nations.gexf` | Nationennetz aus dem Arbeitsnetz (Global View) |
| `athlete_events.parquet`, `athlete_disciplines.parquet` | Zuordnungstabellen zu den Netzwerken |
| `athlete_communities.parquet` | Louvain- und Label-Propagation-Communities sowie k-Core je Athlet |
| `athlete_communities_gephi.csv` | Community-Zuordnung für den Import in Gephi |
| `Athletes.gephi` | Gephi-Projekt für die Abbildungen der Athletenprojektion |

Ein Veranstaltungstag ist die Kombination aus Wettkampfname, Ort, Datum und
Beckenlänge. `athlete_id` ist die ursprüngliche Kennung von swimrankings.net,
`athlete_node` die Knotenkennung in den Netzwerken. `nation` bezeichnet die beim
Scraping gewählte Länderliste, `athlete_nation` die Nation im Athletenprofil.
