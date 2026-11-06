# Rohdaten

`athlete_data_master.csv` enthält die unveränderte Ausgabe des Scrapers
(`Source/scraper/scripts/scrape.py`). Die Daten wurden Mitte 2025 von
[swimrankings.net](https://www.swimrankings.net) erhoben. Erfasst sind die TOP100-Listen
mit bis zu 100 Männern und 100 Frauen je Land sowie die persönlichen Bestleistungen
dieser Athleten.

Pro Athlet ist je Disziplin und Beckenlänge nur die schnellste Zeit der Karriere
gespeichert. Verbessert ein Athlet diese Zeit, ersetzt der neue Eintrag den früheren.
Die Daten bilden deshalb keine vollständigen Wettkampfbiografien ab.

`athlete_id` ist die Kennung von swimrankings.net. `nation` bezeichnet die beim
Scraping gewählte Länderliste, `athlete_nation` die Nation im Athletenprofil.
Bereinigt werden die Daten in `Source/Notebooks/01_eda.ipynb`.
