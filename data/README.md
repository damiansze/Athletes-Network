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

## Zentralität (Kapitel 6)

[05_zentralitaet.ipynb](../Notebooks/05_zentralitaet.ipynb) liest die bestehende
Athletenprojektion und filtert ausschliesslich Kanten mit `weight >= 2`.
Der Export `processed/networks/athlete_communities.parquet` aus Kapitel 5 wird
unverändert übernommen. Unter `processed/centrality/` entstehen:

| Datei | Inhalt |
| --- | --- |
| `actor_centralities.parquet` | Alle Knoten mit Attributen, GC-Indikator, verfügbaren Zentralitäten, Rängen und maximalen verfügbaren FINA-Punkten. Nicht berechnete Masse bleiben fehlend. |
| `rank_correlations.parquet` | Spearman-Korrelationen der verfügbaren Masse auf derselben GC-Population. |
| `performance_tests.parquet` | Einseitige monadische Permutationstests mit Effektgrösse, Stichprobengrösse, Seed und Holm-Korrektur. |
| `group_centralities.parquet` | Group Degree und harmonische Group Closeness der Profilnationen und C1–C4 auf dem gesamten Arbeitsnetz, einschliesslich Gruppengrössen. |
| `example_athletes.parquet`, `neighbor_communities.parquet` | Prüfung der vier ausgewählten Athleten und ihrer direkten Community-Nachbarschaften; bei verfügbarem Betweenness-Cache zusätzlich dessen Top-Athleten. |
| `betweenness_bridges.parquet` | Zehn höchste exakte Betweenness-Werte mit Rängen und direkten Nachbarzahlen für C1–C4 sowie übrige Communities. |
| `betweenness_run.json` | Nachweis des exakten Laufs: Methode, Graphfingerprint, Zahl der Quellen, Laufzeit und unveränderter Harmonic-Cache. |
| `analysis_metadata.json` | Lesbare Eingabefingerprints, Graphbasis, Normalisierungen, Testeinstellungen und Berechnungsstatus. Dieselben Metadaten liegen auch in den Parquet-Tabellen. |
| `cache/harmonic_exact.parquet`, `cache/betweenness_exact.parquet` | Nur tatsächlich berechnete exakte GC-Werte mit geprüften Graph- und Methodenmetadaten. Eine fehlende Datei bedeutet eine offene Berechnung. |

Im Standardlauf gilt `RECOMPUTE_EXPENSIVE = False`: Ein gültiger Cache wird
geladen, andernfalls wird das betreffende Mass sichtbar ausgelassen. Zum
gezielten Berechnen oben im Notebook `RECOMPUTE_EXPENSIVE = True` setzen und
`EXPENSIVE_MEASURES` beispielsweise auf `('betweenness',)` begrenzen. Exakte
Betweenness kann lange dauern. Anschliessend die Option wieder auf `False`
setzen und das Notebook erneut vollständig ausführen. Der Report wird dabei
nicht automatisch geändert. Die vorhandenen Degree-, Weighted-Degree- und
Eigenvector-Werte sowie die Gruppenwerte werden bei passenden Metadaten aus den
Ergebnisexporten übernommen. Die Prüfungen für Scraper und Analyse laufen aus
dem Projektverzeichnis mit `.venv/Scripts/python.exe -m pytest`.
