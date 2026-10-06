# Report

Einstieg ist `main.tex`. Zitate und Literaturverzeichnis verwenden APA 7 mit Biber. Das FHNW Layout bleibt erhalten. Das Abgabedatum ist noch offen.

## Aufbau

Die Dateien sind für die Sortierung durchnummeriert. Ab `03` entspricht die Dateinummer dem Skriptkapitel. Im PDF werden die tatsächlich eingebundenen Abschnitte automatisch fortlaufend nummeriert. Beide Nummerierungen können bei ausgelassenen Themen voneinander abweichen.

| Dateien | Inhalt |
| --- | --- |
| `sections/00_zusammenfassung.tex` | Kurze Zusammenfassung |
| `sections/01_einleitung.tex` | Ausgangslage und Fragestellungen |
| `sections/02_daten.tex` | Herkunft, Bereinigung und EDA |
| `sections/03_modellierung.tex` | Hauptnetzwerk und Gewichtung |
| `sections/04_reduktion.tex` bis `sections/14_graphlets.tex` | Vorbereitete Abschnitte in Skriptreihenfolge |
| `sections/15_fazit.tex` | Fazit, Grenzen und Ausblick |
| `sections/90_eigenstaendigkeit.tex` | Erklärung und Unterschriften |
| `sections/91_anhang.tex` | Ergänzende Materialien und Hilfsmittel |
| `literature/literatur.bib` | Literaturangaben |

Zentralisierung, Link Prediction, Diffusion und Graphlets sind zunächst optional und in `main.tex` auskommentiert. Zum Aktivieren das `%` vor dem jeweiligen `\input` entfernen. Die Kapiteldateien enthalten kurze Arbeitsnotizen, die beim Schreiben ersetzt werden. `\input` vermeidet unnötige Seitenwechsel zwischen kurzen Abschnitten. Abbildungen kommen nach `graphics/`.

Der [Projektplan](PLAN_MODELLIERUNG.md) beschreibt die ausgewählten Analysen und den begrenzten Umfang. Der [Datenplan](PLAN_DATEN.md) enthält die kurze Gliederung und die geprüften Fakten zur Erhebung und Bereinigung.

Die Abbildung im Datenabschnitt wird am Ende von [01_eda.ipynb](../Notebooks/01_eda.ipynb) als `graphics/02_eda_ueberblick.pdf` exportiert.

Die Modellierung ist in [02_modellierung.ipynb](../Notebooks/02_modellierung.ipynb) umgesetzt und ausgeführt. Das Notebook enthält das bipartite Hauptmodell, seine gewichtete Projektion, das Disziplinennetzwerk und die drei vereinbarten Abbildungen. Die Netzwerkdateien sind in [data/README.md](../data/README.md) beschrieben. Der Reportabschnitt wird nach der gemeinsamen Durchsicht ausgearbeitet. Die Plots werden separat für den Report gespeichert. Der verworfene erste Entwurf bleibt unter `.archive/` lokal archiviert.

## Kompilieren und zitieren

Im Ordner `Report` ausführen:

```sh
latexmk
```

Das Ergebnis liegt unter `build/main.pdf`. `latexmk` erledigt die Durchläufe mit pdfLaTeX und Biber. Die Direktive `TeX root` verweist auch aus den einzelnen Kapiteldateien auf `main.tex`.

```tex
\textcite{henninger2024} beschreibt verschiedene Netzwerktypen.
Die Modellierung folgt dem Vorlesungsskript \parencite{henninger2024}.
```

Neue Quellen in `literature/literatur.bib` ergänzen. Im Literaturverzeichnis erscheinen die tatsächlich zitierten Quellen. Direkte Zitate erhalten eine genaue Seitenangabe.
