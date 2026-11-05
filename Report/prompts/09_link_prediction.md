# KI-Unterstützung für Kapitel 9

Datum der Bearbeitung: 2026-11-05
Hilfsmittel: Codex von OpenAI

Codex unterstützt die Implementierung, Analysevalidierung, Visualisierungen sowie den Textentwurf und die Korrektur von Kapitel 9. Die Deklaration bezieht sich ausschliesslich auf die Link-Prediction-Analyse und ihre ergänzenden Dateien.

## Originalauftrag

Der folgende Block enthält den unveränderten UTF-8-Inhalt des vom Projektteam eingefügten Aufgabenprompts.

<!-- BEGIN ORIGINAL PROMPT -->
Implementiere die Link-Prediction-Analyse für Kapitel 9 unseres FHNW-Projekts **Athletes Network** im bestehenden Repository `C:\FHNW\san\Athletes-Network`.

Ziel ist ein vollständig reproduzierbares Jupyter Notebook mit validierten Ergebnissen, aussagekräftigen Visualisierungen und einem fertig ausgearbeiteten LaTeX-Reportkapitel.

## 1. Projektkontext prüfen

Lies zuerst die relevanten Dateien und halte dich an die vorhandene Projektstruktur:

- `Notebooks/02_modellierung.ipynb`
- `Notebooks/03_reduktion.ipynb`
- `Notebooks/06_zusammenhalt.ipynb`
- Bestehende Community- und Assortativitätsanalysen
- `Report/sections/` inklusive Kapitel 4 bis 8
- `Report/main.tex`
- `pyproject.toml`

Überprüfe auch die letzten Änderungen im Repository. Mein Teamkollege hat seine Arbeit bereits gepusht.

**Wichtig:** Vorhandene Notebooks, Resultate und Reportkapitel nicht unnötig verändern oder überschreiben. Verwende dieselben Konventionen für Grafiken, Tabellen, deutsche Texte und Datenablagen wie bisher.

## 2. Versuchsaufbau

Erstelle `Notebooks/08_link_prediction.ipynb`.

Verwende `data/processed/networks/athlete_events.parquet` mit den Spalten `athlete_node`, `event_id` und `best_date`.

Die Untersuchung orientiert sich an Kapitel 12.2 des SAN-Skripts und dem Experiment von Liben-Nowell und Kleinberg.

### Zeitliche Aufteilung

- Training: Veranstaltungstage 2016–2019
- Test: Veranstaltungstage 2021–2025
- 2020 vollständig ausschliessen
- Kern: Athleten mit mindestens drei verschiedenen Veranstaltungstagen in beiden Zeiträumen

Berechne diese Aufteilung selbst und überprüfe folgende vorläufigen Zahlen:

| Kennzahl | Erwartet |
|---|---:|
| Athleten im Kern | 3'017 |
| Trainingskanten innerhalb des Kerns | 50'792 |
| Kandidatenpaare | 4'498'844 |
| Neue Testkanten | 121'753 |
| Zufallspräzision | ca. 2,7 % |

Diese Zahlen dienen ausschliesslich als Validierung. Verwende die tatsächlich berechneten Werte und untersuche eventuelle Abweichungen.

### Netzwerkmodell

Erzeuge die Athletenprojektion aus den Veranstaltungstagen 2016–2019. Verwende dabei ein Mindestgewicht von 1, weil jede beobachtete gemeinsame Teilnahme als bestehende Verbindung zählt.

Die Trainingsprojektion umfasst alle im Trainingszeitraum beobachteten Athleten, nicht nur die 3'017 Kernathleten.

Berechne die Scores ausschliesslich für bislang unverbundene Kernathletenpaare, verwende für ihre Nachbarschaften aber das gesamte Trainingsnetz.

Die Testkanten entstehen unabhängig aus den Veranstaltungstagen 2021–2025.

Achte auf eindeutige Veranstaltungstage, korrekte Datumsgrenzen, Duplikate und konsistente Athletenkennungen.

Eine neue Kante ist eine Verbindung, die im Trainingsgraphen fehlt und im Testgraphen vorkommt. Sie ist nicht zwingend die erste historische Begegnung überhaupt.

## 3. Link-Prediction-Verfahren

Implementiere und vergleiche:

**Netzwerkbasierte Verfahren**

1. Common Neighbours
2. Adamic-Adar
3. Preferential Attachment
4. Soundarajan-Hopcroft

**Attributbasierte Faustregeln**

5. Gleiche Profilnation
6. Ähnliches Geburtsjahr
7. Kombination aus gleicher Profilnation und Geburtsjahrnähe

Berechne Common Neighbours und Adamic-Adar ungewichtet auf dem Trainingsgraphen. Preferential Attachment verwendet das Produkt der ungewichteten Knotengrade.

Für Soundarajan-Hopcroft müssen die Communities mit Louvain **ausschliesslich auf dem Trainingsgraphen** neu berechnet werden. Verwende einen festen Seed.

Die Community-Zuordnungen aus Kapitel 5 dürfen nicht übernommen werden, da sie Testdaten enthalten.

Die Nation und das Geburtsjahr stammen aus `data/processed/assortativitaet/athlete_attributes.parquet`.

Behandle fehlende Nationen und Geburtsjahre explizit. Zwei fehlende Nationen dürfen nicht als gleiche Nation zählen. Beachte auch, dass die Profilnation aus dem Datenstand 2025 stammt und sich historisch verändert haben könnte. Dokumentiere diese Einschränkung.

Die kombinierte Faustregel sortiert zuerst nach gleicher Nation und innerhalb dieser Gruppen nach kleinerem Jahrgangsunterschied.

## 4. Effiziente Implementierung

Bei ungefähr 4,5 Millionen Kandidatenpaaren sind einzelne NetworkX-Aufrufe pro Knotenpaar nicht sinnvoll.

Verwende deshalb `scipy.sparse` und NumPy.

Für die Kernathleten mit Adjazenzzeilen `A_K` und sämtlichen Trainingsknoten als Spalten:

- Common Neighbours: `A_K @ A_K.T`
- Adamic-Adar: `A_K @ diag(1 / ln(degree)) @ A_K.T`
- Preferential Attachment: äusseres Produkt der Knotengrade
- Soundarajan-Hopcroft: Common Neighbours plus Bonus für gemeinsame Nachbarn innerhalb der Community, sofern beide Kandidaten derselben Community angehören

Beim Soundarajan-Hopcroft-Bonus besonders auf die korrekte Community-Zugehörigkeit aller drei beteiligten Knoten achten.

Schliesse danach bereits bestehende Trainingskanten und Selbstverbindungen aus.

Vermeide unnötige dichte Matrizen und übermässigen Speicherverbrauch. Berechne die Scores effizient und möglichst vektorisiert.

Validiere die Formeln auf kleinen Testgraphen gegen die entsprechenden NetworkX-Funktionen. Füge automatisierte Tests für die Score-Berechnung, Kandidatenfilterung, zeitliche Aufteilung und Evaluation hinzu.

## 5. Evaluation

Wende die Evaluation aus SAN Kapitel 12.2 an.

Für jedes Verfahren:

1. Alle Kandidatenpaare nach Score absteigend sortieren.
2. Gleichstände reproduzierbar mit einem festen Zufallsseed auflösen.
3. Die ersten K = |E_new| Kandidaten auswählen.
4. Berechnen, welcher Anteil tatsächlich zu den neuen Testkanten gehört.
5. Präzision durch die erwartete Zufallspräzision teilen.

Die Hauptkennzahl ist damit der **Verbesserungsfaktor gegenüber Zufall**.

Verwende dieselbe Kandidatenmenge und dieselben Testkanten für sämtliche Verfahren.

Dokumentiere den Umgang mit Gleichständen und untersuche bei stark gebundenen Scores deren Einfluss anhand mehrerer Seeds.

Erstelle ausserdem einen Vergleich der absoluten Präzision.

Optional eine Robustheitsanalyse durchführen, bei der eine neue Testkante mindestens zwei gemeinsame Veranstaltungstage voraussetzt. Erwartet werden ungefähr 32'636 solcher Kanten. Verwende dafür eine separat ausgewiesene Zufallsbasis und K-Auswahl.

### Methodische Einschränkung der Kernpopulation

Die Auswahl von Athleten mit mindestens drei Veranstaltungstagen in beiden Zeiträumen verwendet Informationen aus dem Testzeitraum.

Das ist für eine retrospektive Evaluation zulässig, stellt aber keine vollständig prospektive Vorhersage dar.

Kennzeichne die Hauptanalyse deshalb als retrospektiven Vergleich einer im Nachhinein definierten aktiven Athletenpopulation.

Falls mit vertretbarem Aufwand möglich, ergänze eine Robustheitsanalyse mit einer Kernpopulation, die ausschliesslich anhand der Trainingsaktivität bestimmt wird. Vergleiche die Ergebnisse und erläutere einen möglichen Selektionsbias.

Für sämtliche Score-Berechnungen dürfen niemals Testkanten, spätere Communities oder Leistungswerte aus dem Testzeitraum verwendet werden.

## 6. Ergebnisse und Visualisierungen

Speichere die reproduzierbaren Resultate unter:

`data/processed/link_prediction/`

Erstelle geeignete Grafiken unter:

`Report/graphics/09_*.pdf`

Mindestens eine Hauptgrafik soll die sieben Verfahren als Balkendiagramm darstellen.

- Y-Achse: Faktor gegenüber Zufall
- X-Achse: Verfahren
- Netzwerkverfahren und Faustregeln visuell unterscheiden
- Zufallsbaseline bei Faktor 1
- Werte nachvollziehbar beschriften
- Keine überflüssigen Dekorationen

Ergänze eine kompakte Ergebnistabelle mit absoluter Precision@K, Verbesserungsfaktor und gegebenenfalls Robustheitsergebnissen.

Keine Werte erfinden. Alle Resultate müssen aus dem Notebook reproduzierbar sein.

## 7. Reportkapitel 9

Erstelle oder ergänze:

`Report/sections/09_link_prediction.tex`

mit dem Label:

`sec:link_prediction`

Prüfe die Einbindung in `Report/main.tex`, ohne andere Kapitel zu beschädigen.

Umfang ungefähr 1,5 bis 2 Seiten.

### Inhalt

**Versuchsaufbau**

Kurze Beschreibung von Trainingszeitraum, Testzeitraum, Kandidatenmenge, Auswahl der Kernathleten und Evaluationsmethode.

Begründe, weshalb hier Gewicht ≥ 1 verwendet wird, während frühere Analysen das Arbeitsnetz mit Gewicht ≥ 2 untersuchen.

**Ergebnisse**

Kompakte Tabelle zum Versuchsaufbau und eine zentrale Abbildung zum Vergleich der Verfahren.

**Interpretation**

Beantworte die Leitfrage, ob Netzwerkverfahren die attributbasierten Faustregeln übertreffen.

Stelle dabei einen Bezug zu bestehenden Kapiteln her:

- Kapitel 5: Bringen die Community-Informationen beim Soundarajan-Hopcroft-Verfahren einen Mehrwert?
- Kapitel 6: Welche Rolle spielt die Vernetzung zentraler Athleten?
- Kapitel 7: Sind wiederholte gemeinsame Veranstaltungstage für die Link Prediction relevant?
- Kapitel 8: Wie schneiden Nation und Jahrgang als Prädiktoren ab? Berücksichtige die dort beobachtete starke Jahrgangs-Assortativität und Degree-Assortativität.

Übernimm Zahlen aus den früheren Kapiteln nur, wenn sie im aktuellen Repository tatsächlich bestätigt sind.

**Grenzen**

Besprich die begrenzte Aussagekraft der Daten:

- Es sind nur gespeicherte persönliche Bestleistungen vorhanden.
- Frühere Bestleistungen können durch spätere Verbesserungen aus dem Quellenbestand verschwinden.
- Die Kernpopulation ist anhand beider Zeiträume selektiert.
- Das Jahr 2025 ist nicht vollständig enthalten.
- Die Projektion gemeinsamer Veranstaltungstage kann künstlich dichte Strukturen erzeugen.
- Vorhergesagte Kanten stehen für gemeinsame Veranstaltungskontexte und nicht für Freundschaften.

## 8. Schreibstil des Reports

Orientiere dich an den bestehenden Kapiteln 4–8.

- Kurze, natürliche deutsche Sätze.
- Keine Doppelpunkte, Strichpunkte oder Gedankenstriche im Fliesstext.
- Begriff „Giant Component“ verwenden, wenn relevant.
- Keine internen Prozessdetails wie Cache-Dateien, Laufzeiten oder Testabläufe im Report.
- Keine Verweise auf einzelne Notebooks im Fliesstext.
- Abbildungen mit `[H]` direkt im passenden Abschnitt.
- Bildunterschriften erklären alle Farben, Achsen und relevanten Linien.
- Keine Spekulationen als nachgewiesene Tatsachen darstellen.
- Ergebnisse im Kontext des Schwimmsports interpretieren.
- Keine Wiederholung ausführlicher Methodenerklärungen aus früheren Kapiteln.

## 9. Qualitätssicherung und Abschluss

Führe das Notebook vollständig aus und prüfe:

- Reproduzierbare Ergebnisse
- Korrekte Kandidaten- und Kantenmengen
- Kein Data Leakage bei den Vorhersagescores
- Übereinstimmung der implementierten Link-Prediction-Formeln mit NetworkX auf Testgraphen
- Deterministische Tie-Breaking-Logik
- Korrekte Evaluation und Zufallsbaseline
- Konsistenz zum bisherigen Report
- Erfolgreicher LaTeX-Build und visuelle Kontrolle der Abbildungen

Dokumentiere die verwendeten KI-Hilfsmittel und den Aufgabenprompt entsprechend den bestehenden Projektkonventionen.

Verwende die bereits vorhandene Projektstruktur und füge nur notwendige Dateien hinzu.

**Kein Commit und kein Push ohne meine Freigabe.**

Gib mir am Ende eine kurze Zusammenfassung mit:

- Geänderten und neu erstellten Dateien
- Bestätigten Kennzahlen zum Datensplit
- Precision@K und Verbesserungsfaktor aller Verfahren
- Wichtigsten Erkenntnissen
- Offenen Problemen und eventuellen methodischen Einschränkungen
- Status des Reportkapitels und der Tests
<!-- END ORIGINAL PROMPT -->

## Quellenprüfung und Abgrenzung

Die methodischen Vorgaben zur zeitlichen Aufteilung und Evaluation stammen aus dem obigen Nutzerauftrag. Das Originalpaper von David Liben-Nowell und Jon Kleinberg wurde ergänzend geprüft. Der gelesene [Autorenvorabdruck von 2004](https://www.cs.cornell.edu/home/kleinber/link-pred.pdf) beschreibt den aktiven Kern aus beiden Zeiträumen und die Evaluation der ersten K Vorhersagen mit K gleich der Zahl neuer Testkanten. Die [endgültige Veröffentlichung von 2007](https://doi.org/10.1002/asi.20591) ist im Literaturverzeichnis erfasst.

Die Soundarajan-Hopcroft-Formel wurde anhand der [offiziellen NetworkX-Dokumentation](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.link_prediction.cn_soundarajan_hopcroft.html) geprüft. Der Bonus setzt dieselbe Community für beide Kandidaten und den gemeinsamen Nachbarn voraus.

Das SAN-Skript war im lokalen Projektverzeichnis und unter dessen Elternverzeichnis nicht verfügbar. Kapitel 12.2 des Skripts wurde deshalb nicht im Original gelesen. Die Bezugnahme darauf folgt dem Nutzerauftrag und wird nicht als unabhängige Prüfung des Skripttexts ausgegeben.
