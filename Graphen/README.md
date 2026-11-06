# Graphen

Die Netzwerke liegen als GEXF vor und lassen sich mit NetworkX und Gephi öffnen.

| Datei | Erzeugt von | Inhalt |
| --- | --- | --- |
| `athlete_events.gexf` | `02_modellierung.ipynb` | Two-Mode-Netz aus Athleten und Veranstaltungstagen |
| `athletes.gexf` | `02_modellierung.ipynb` | Athletenprojektion, Kantengewicht = gemeinsame Veranstaltungstage |
| `disciplines.gexf` | `02_modellierung.ipynb` | Disziplinennetz, Kantengewicht = gemeinsame Athleten |
| `athlete_events.parquet`, `athlete_disciplines.parquet` | `02_modellierung.ipynb` | Zuordnungstabellen zu den Netzwerken |
| `nations.gexf` | `03_reduktion.ipynb` | Nationennetz aus dem Arbeitsnetz (Global View) |
| `athlete_communities.parquet` | `04_communities.ipynb` | Louvain- und Label-Propagation-Communities sowie k-Core je Athlet |
| `athlete_communities_gephi.csv` | `04_communities.ipynb` | Community-Zuordnung für den Import in Gephi |
| `Athletes.gephi` | Gephi | Projekt für die Abbildungen der Athletenprojektion |

Ein Veranstaltungstag ist die Kombination aus Wettkampfname, Ort, Datum und
Beckenlänge. `athlete_node` ist die Knotenkennung in den Netzwerken, `athlete_id` die
ursprüngliche Kennung von swimrankings.net.
