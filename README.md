# Athletes Network

Soziale Netzwerkanalyse im Schwimmsport, Projektarbeit im Modul Soziale Netzwerke. Grundlage sind die TOP100-Listen von
[swimrankings.net](https://www.swimrankings.net) mit den persönlichen Bestleistungen
von über 13'000 Athleten aus 182 Nationen. Zwei Athleten sind verbunden, wenn sie am
selben Veranstaltungstag eine ihrer Karrierebestzeiten erzielten. Auf diesem Netz
untersuchen wir Gruppen, zentrale Athleten, Zusammenhalt, Assortativität und
Link Prediction.

Die Nutzung von KI-Werkzeugen ist in `KI-Deklaration.md` dokumentiert.

## Einstieg

Am besten beginnt man mit `Source/Notebooks/00_projekt.ipynb` und liest die Notebooks der
Reihe nach. `00_projekt` und `09_fazit` enthalten nur Text und rahmen die Analysen ein.
Jedes Analyse-Notebook endet mit einem Abschnitt «Erkenntnisse». Der Report unter
`Report/build/main.pdf` enthält dieselben Inhalte als zusammenhängenden Text. Er ist eine Ergänzung zur Präsentation und muss nicht zusätzlich gelesen werden.

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

## Struktur

```
Athletes-Network/
├── Source/
│   ├── scraper/      Scraper für swimrankings.net (Selenium)
│   └── Notebooks/    Notebooks 00 bis 09 und Hilfsmodule
├── Rohdaten/         Ausgabe des Scrapers
├── Graphen/          Netzwerke als GEXF, Gephi-Projekt und Zuordnungstabellen
├── Ergebnisse/       Bereinigte Daten und gespeicherte Auswertungen der Notebooks
└── Report/           Report als PDF (build/main.pdf) mit LaTeX-Quellen
```

Rohdaten, Graphen und Ergebnisse beschreiben ihren Inhalt jeweils in einem eigenen README.

## Notebooks ausführen

Alle Notebooks sind bereits ausgeführt und zeigen ihre Ergebnisse. Wer sie neu ausführen
möchte, braucht Python 3.13 und folgende Pakete:

```bash
pip install matplotlib networkx numpy pandas pyarrow scipy jupyter
```

Die Notebooks bauen aufeinander auf und werden in der Reihenfolge 01 bis 08 ausgeführt.
Closeness und Betweenness in `05_zentralitaet.ipynb` dauern zusammen rund eine halbe
Stunde. Das Notebook lädt sie deshalb aus `Ergebnisse/centrality/cache`. Für eine
Neuberechnung oben im Notebook `RECOMPUTE_EXPENSIVE = True` setzen.

## Für die Entwicklung

Im Repository werden Rohdaten, Graphen und Ergebnisse über [Git LFS](https://git-lfs.com)
versioniert. Die Abhängigkeiten verwaltet [uv](https://docs.astral.sh/uv/), inklusive
Selenium für den Scraper und `pytest` für die Tests.

```bash
git clone https://github.com/damiansze/Athletes-Network.git
cd Athletes-Network
git lfs pull      # Daten laden, falls Git LFS erst nach dem Klonen installiert wurde
uv sync           # Abhängigkeiten installieren
uv run pytest     # Tests
make              # Report kompilieren (latexmk, pdflatex und biber nötig)
make rebuild      # Report vollständig neu bauen
```

Alle Pfade der Notebooks stehen in `Source/Notebooks/paths.py`.
