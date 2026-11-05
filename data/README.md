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

## Link Prediction (Kapitel 9)

[08_link_prediction.ipynb](../Notebooks/08_link_prediction.ipynb) verwendet die
vorhandenen Veranstaltungstag-Zuordnungen aus `processed/networks/athlete_events.parquet`
und ausschliesslich `nation` und `birth_year` aus
`processed/assortativitaet/athlete_attributes.parquet`. Training sind die Jahre
2016 bis 2019, Test die Jahre 2021 bis 2025. Das Jahr 2020 bleibt ausgeschlossen.
Das letzte tatsächlich vorhandene Testdatum ist der 8. April 2025.

Die ungewichtete Trainingsprojektion enthält alle Trainingsathleten und bereits
Kanten ab einem gemeinsamen Veranstaltungstag. Die Hauptpopulation verlangt
mindestens drei verschiedene `event_id` in beiden Zeiträumen und ist damit
retrospektiv definiert. Sie enthält 3'017 Athleten, 50'792 interne Trainingskanten,
4'498'844 Kandidaten und 121'753 neue Testkanten. Ihre Zufallspräzision beträgt
2,7063 %. Nachbarschaften und neu berechnete Louvain-Communities verwenden nur
das vollständige Trainingsnetz. Die Communities aus Kapitel 5 werden nicht geladen.

Unter `processed/link_prediction/` entstehen:

| Datei | Inhalt |
| --- | --- |
| `candidate_scores.parquet` | Alle Hauptkandidaten mit sieben Scores und Zahl gemeinsamer Testtage. `core_i < core_j` sind Positionen im nach Athletenkennung sortierten Hauptkern. |
| `training_nodes.parquet` | Alle Trainingsathleten, ihre Kennung, `train_index`, ungewichteter Trainingsgrad, Trainingscommunity `T…`, Profilnation und Jahrgang. `core_index` verbindet die Hauptkandidaten mit Athletenkennungen, bei Nichtmitgliedern ist er −1. `train_days` und `test_days` dienen der dokumentierten Populationsauswahl, nicht als Scores. |
| `evaluation.parquet` | Precision@K, Treffer, Zufallsbasis, Verbesserungsfaktor und Cutoff-Gleichstände für alle sieben Verfahren und drei Szenarien bei Seed 42. |
| `tie_sensitivity.parquet` | Hauptanalyse und wiederholte Testverbindungen mit zehn Tie-Breaking-Seeds von 42 bis 51. Die Spannweite beschreibt nur Scoregleichstände. |
| `split_summary.parquet`, `period_summary.parquet` | Populationen, Kandidaten und Zielkanten sowie Athleten, Veranstaltungstage und tatsächliche Datumsgrenzen je Zeitraum. |
| `analysis_metadata.json` | Eingabe- und Implementierungshashes, Paketversionen, Seeds, Trainingsgraph, Louvain-Einstellungen, Scoredefinitionen und methodische Grenzen. |

Die Szenarien sind `main`, `repeated_test` mit mindestens zwei gemeinsamen Testtagen
und `training_only` mit mindestens drei Trainingstagen unabhängig von späterer
Aktivität. Jedes Szenario hat sein eigenes `K = Anzahl neuer Testkanten` und seine
eigene Zufallsbasis. Innerhalb eines Szenarios verwenden alle Verfahren dieselben
Kandidaten, Zielkanten und zufälligen Prioritäten für Scoregleichstände.

Die Profilnation stammt aus dem Datenstand 2025 und muss nicht der historischen
Nation entsprechen. Zwei fehlende Nationen zählen nie als gleich. Fehlende
Jahrgänge stehen hinter allen bekannten Jahrgangsdifferenzen. Die Kombination
ordnet zuerst nach gleicher Nation und innerhalb beider Gruppen nach Jahrgangsnähe.
Neue Testkanten sind im Trainingsfenster nicht vorhanden. Sie können vor 2016 oder
im ausgeschlossenen Jahr 2020 bereits existiert haben.

Ein vollständiger Notebooklauf berechnet diese Analyse erneut mit sparse
Matrixprodukten und aktualisiert nur ihre Exporte sowie `Report/graphics/09_*.pdf`.
Die anderen Notebooks werden nicht ausgeführt. Die Hauptscores werden dauerhaft
gespeichert, die grössere Training-only-Variante wird durch Eingaben, Algorithmus,
Einstellungen und aggregierte Ergebnisse reproduzierbar gehalten. Tests laufen
gemeinsam mit den bestehenden Tests über `.venv/Scripts/python.exe -m pytest`.
KI-Deklaration und Originalauftrag stehen im Reportanhang und unter
[`Report/prompts/09_link_prediction.md`](../Report/prompts/09_link_prediction.md).
