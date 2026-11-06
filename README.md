# Athletes Network

Soziale Netzwerkanalyse im Schwimmsport, Projektarbeit im Modul Soziale Netzwerke
(FHNW, Data Science). Grundlage sind die TOP100-Listen von
[swimrankings.net](https://www.swimrankings.net) mit den persönlichen Bestleistungen
von über 13'000 Athleten aus 182 Nationen. Zwei Athleten sind verbunden, wenn sie am
selben Veranstaltungstag eine ihrer Karrierebestzeiten erzielten. Auf diesem Netz
untersuchen wir Gruppen, zentrale Athleten, Zusammenhalt, Assortativität und
Link Prediction. Die Ergebnisse stehen im Report.

## Struktur

```
Athletes-Network/
├── scraper/      Scraper für swimrankings.net (Selenium) mit Tests
├── data/         Rohdaten, bereinigte Daten und Netzwerke (Git LFS), siehe data/README.md
├── Notebooks/    Notebooks 00 bis 09, Hilfsmodule und Tests
├── Report/       LaTeX-Report, Abbildungen unter Report/graphics
└── Makefile      Baut den Report
```

## Einrichten

Voraussetzungen sind Python 3.13, [uv](https://docs.astral.sh/uv/) und
[Git LFS](https://git-lfs.com) für die Daten.

```bash
git lfs pull
uv sync
```

`uv sync` installiert alle Abhängigkeiten, inklusive `ipykernel` zum Ausführen der
Notebooks.

## Notebooks

Die Notebooks bauen aufeinander auf und werden in dieser Reihenfolge ausgeführt.
`00_projekt.ipynb` und `09_fazit.ipynb` enthalten nur Text und rahmen die Analysen ein.

| Notebook | Inhalt | Report-Kapitel |
| --- | --- | --- |
| `00_projekt.ipynb` | Thema, Daten, Fragestellungen | 1 |
| `01_eda.ipynb` | Explorative Datenanalyse und Bereinigung | 2 |
| `02_modellierung.ipynb` | Two-Mode-Netz, Athleten- und Disziplinennetz | 3 |
| `03_reduktion.ipynb` | Arbeitsnetz, Local, Global und Contextual View, Ego-Netzwerk | 4 |
| `04_communities.ipynb` | k-Core, Louvain, Label Propagation | 5 |
| `05_zentralitaet.ipynb` | Aktor- und Gruppen-Zentralität, Leistung | 6 |
| `06_zusammenhalt.ipynb` | Kennzahlen, Nullmodell, Robustheit | 7 |
| `07_assortativitaet.ipynb` | Assortativität mit Permutationstests | 8 |
| `08_link_prediction.ipynb` | Zeitliches Link-Prediction-Experiment | 9 |
| `09_fazit.ipynb` | Antworten, Grenzen, Ausblick, Reflexion | 10 |

Die exakte Betweenness in `05_zentralitaet.ipynb` dauert rund 20 Minuten. Das Notebook
lädt sie deshalb standardmässig aus `data/processed/centrality/cache`. Für eine
Neuberechnung oben im Notebook `RECOMPUTE_EXPENSIVE = True` setzen.

## Report bauen

Voraussetzung ist eine LaTeX-Installation mit `latexmk`, `pdflatex` und `biber` sowie
GNU Make. Im Projektverzeichnis:

```bash
make            # Report kompilieren
make rebuild    # vollständiger Neubau
```

Das PDF entsteht unter `Report/build/main.pdf`. Im Ordner `Report` genügt auch
`latexmk`.

## Tests

```bash
uv run pytest
```
