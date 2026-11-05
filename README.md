# Athletes-Network

## Report bauen

Voraussetzungen sind GNU Make und eine LaTeX-Installation mit `latexmk`,
`pdflatex` und `biber` im PATH.

Im Projektverzeichnis oder im Ordner `Report`:

```powershell
make
```

Das PDF entsteht unter `Report/build/main.pdf`. `latexmk` führt die benötigten
LaTeX- und Literaturdurchläufe automatisch aus und baut nur bei Änderungen neu.
Für einen vollständigen Neubau:

```powershell
make rebuild
```
