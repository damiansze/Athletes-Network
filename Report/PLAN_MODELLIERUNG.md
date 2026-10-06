# Kompakter Projektplan

Ziel ist eine nachvollziehbare Anwendung der Netzwerkanalyse im Umfang eines Moduls mit 4 Credits. Das [Bewertungsraster](../Infos/Bewertungsraster-1753184609.xlsx) verlangt sinnvolle Vielfalt, korrekte Anwendung und Interpretation. Eine vollständige Bearbeitung des Skripts ist dafür nicht nötig.

Wir arbeiten in Skriptreihenfolge weiter und dokumentieren nur Methoden, die eine konkrete Frage beantworten. Pro Analyse reichen Fragestellung, Vorgehen, ein aussagekräftiges Ergebnis und dessen Einordnung. Technische Details und zusätzliche Prüfungen bleiben im Notebook. Die Dateien für alle Kapitel dienen der Orientierung und verpflichten nicht zur Aufnahme in den Report.

## Kapitel 3: Gemeinsam abgestimmter Modellierungsplan

**Stand:** Das Notebook ist gemäss diesem Plan umgesetzt und vollständig ausgeführt. Die drei Netzwerke, beide Zuordnungstabellen und alle drei Notebookabbildungen liegen vor. Die exportierten Zuordnungen und sämtliche Kantengewichte wurden unabhängig geprüft. Als Nächstes folgt die gemeinsame Durchsicht des Notebooks. Der Reportabschnitt wird anschliessend ausgearbeitet. Die Ideen für spätere Kapitel bleiben vorläufig. Der verworfene erste Entwurf bleibt lokal archiviert.

### Vereinbarte Modelle

Das Hauptmodell untersucht, welche Athleten über gemeinsame Veranstaltungstage ihrer gespeicherten Bestleistungen verbunden sind. Das zusätzliche Disziplinennetzwerk zeigt, welche Disziplinen bei denselben Athleten vorkommen.

| Darstellung | Knoten | Bedeutung einer Kante | Gewicht |
| --- | --- | --- | --- |
| Bipartites Hauptmodell | Athleten und Veranstaltungstage | Für den Athleten ist an diesem Veranstaltungstag mindestens eine Bestleistung gespeichert | Eine Verbindung je Athlet und Veranstaltungstag |
| Abgeleitetes Athletennetzwerk | Athleten | Beide Athleten haben mindestens einen gemeinsamen Veranstaltungstag in ihren Bestleistungseinträgen | Anzahl verschiedener gemeinsamer Veranstaltungstage |
| Zusätzliches Disziplinennetzwerk | Kombinationen aus Disziplin und Beckenlänge | Mindestens ein Athlet hat Bestleistungen in beiden Kombinationen | Anzahl verschiedener gemeinsamer Athleten |

Alle Darstellungen sind ungerichtet und fassen die vorhandenen Jahre statisch zusammen. Die beiden abgeleiteten Netzwerke sind gewichtet. Eine Verbindung im Hauptmodell belegt einen gemeinsamen Veranstaltungskontext. Eine persönliche Bekanntschaft oder ein direkter Wettkampf gegeneinander lässt sich daraus nicht ableiten.

### Vereinbarte Datengrundlage und Zuordnung

1. **Alle Jahre.** Ausgangspunkt ist `data/processed/athlete_data_clean.parquet`. Es wird kein Zeitfilter gesetzt.
2. **Gemeinsames Hauptnetzwerk.** Männer und Frauen werden gemeinsam betrachtet. Das Geschlecht bleibt als Knotenattribut verfügbar.
3. **Veranstaltungstag.** Gespeicherter Wettkampfname, Ort, Datum und Beckenlänge bilden die Zuordnung. Leistungen an unterschiedlichen Tagen derselben mehrtägigen Veranstaltung erzeugen allein keine gemeinsame Verbindung.
4. **Gekürzte Namen.** Identische Kürzungen wie `...` bleiben enthalten. Konkrete Mehrdeutigkeiten werden geprüft. Verschiedene Namen am selben Tag rechtfertigen allein keinen Ausschluss.
5. **Athletenkennung.** Personen werden über `athlete_id` erkannt. Ein Auftreten in mehreren Länderlisten darf keine zusätzlichen Personen oder mehrfach gezählten Verbindungen erzeugen.
6. **Zwischenzeiten mit `Lap`.** Im Hauptmodell bleiben sie als Beleg für einen Veranstaltungstag enthalten. Im Disziplinennetzwerk werden sie ausgeschlossen, damit Zwischenzeiten keine eigenen Disziplinknoten bilden.
7. **Fehlende Veranstaltungsangaben.** Für die Zuordnung zu Veranstaltungstagen müssen Wettkampfname, Ort, Datum und Beckenlänge vorhanden sein. Leere Angaben und `Unknown` unabhängig von der Grossschreibung gelten als fehlend. Die aktuell betroffenen 854 Einträge, rund 0,3 Prozent der Daten, werden für diese Zuordnung nicht verwendet. Andere Einträge derselben Athleten bleiben verwendbar. Die bereinigte Datendatei bleibt erhalten. Für das Disziplinennetzwerk gelten weiterhin dessen eigene Regeln, insbesondere der Ausschluss von `Lap`.
8. **Athleten ohne zuordenbaren Veranstaltungstag.** Die aktuell sechs betroffenen Athleten werden beim Aufbau des Hauptmodells ausgelassen und im Datenumfang mit dem Grund dokumentiert. Athleten mit mindestens einem gültigen Veranstaltungstag bleiben im bipartiten Hauptmodell und in der Projektion enthalten, auch wenn in der Projektion keine Verbindung zu anderen Athleten entsteht. Diese Regel betrifft ausschliesslich das Hauptmodell.
9. **Seltene Disziplinen.** Alle vorhandenen Kombinationen aus Disziplin und Beckenlänge ohne `Lap` bleiben im Disziplinennetzwerk enthalten. Es wird kein Häufigkeitsfilter angewendet. Aktuell sind das 78 Kombinationen, davon 29 mit weniger als zehn Athleten. Die Anzahl verschiedener Athleten je Kombination wird ausgewiesen.

### Vereinbarte Transformationen

**Athletennetzwerk:** Gewichtete Projektion des bipartiten Netzwerks auf die Athleten, entsprechend Kapitel 3.2.3 des Skripts, Seite 38. Für jedes Athletenpaar werden die gemeinsamen Veranstaltungstage gezählt. Drei gemeinsame Tage ergeben Gewicht 3. Mehrere Leistungen am selben Tag ergeben zunächst nur eine Verbindung zwischen Athlet und Veranstaltungstag. Die Projektion enthält eine Kante pro verbundenem Athletenpaar und keine Verbindungen einer Person zu sich selbst.

**Disziplinennetzwerk:** Eine Disziplin besteht aus Strecke und Schwimmstil. Zusammen mit der Beckenlänge ergibt sie einen Knoten. Beispielsweise bilden 100 m Freistil auf 25 m Bahn und 100 m Freistil auf 50 m Bahn zwei eigene Knoten. Pro Athlet wird jede solche Kombination einmal berücksichtigt. Die gewichtete Projektion einer Zuordnung von Athleten zu diesen Kombinationen zählt anschliessend die gemeinsamen Athleten. 500 gemeinsame Athleten ergeben Gewicht 500. Ihre Bestleistungen können aus unterschiedlichen Veranstaltungen und Jahren stammen.

Für beide Projektionen ist die einfache Zählung vereinbart. Newman und Jaccard sind keine Bestandteile der bisher beschlossenen Modellierung.

### Vereinbarte Abbildungen

Für Kapitel 3 sind drei Darstellungen vorgesehen. Sie werden direkt im Notebook erzeugt und angezeigt. Die Übernahme in den Report erfolgt später separat.

1. **Hauptmodell und Projektion.** Ein kleiner gemeinsamer Ausschnitt zeigt das bipartite Netzwerk und seine gewichtete Projektion nebeneinander. Dadurch lassen sich die Entstehung der Kanten und ihre Gewichte nachvollziehen.
2. **Gesamtansicht des Athletennetzwerks.** Zusätzlich wird das vollständige abgeleitete Athletennetzwerk dargestellt. Dazu gehören auch isolierte Athleten, die nach den vereinbarten Regeln zum Netzwerk gehören. Die Gesamtansicht dient dem Überblick über die Struktur.
3. **Disziplinennetzwerk.** Möglichst alle 78 Kombinationen darstellen. Falls die vollständige Darstellung nicht lesbar ist, einen klar bezeichneten Ausschnitt verwenden.

Die vollständigen Netzwerke werden unabhängig von den gezeigten Ausschnitten gespeichert. Auch die statische Gesamtansicht entsteht zunächst im Notebook. Anschliessend kann Gephi ergänzend zum interaktiven Erkunden oder Verfeinern der Darstellung verwendet werden. Über diesen zusätzlichen Einsatz wird anhand der Notebookergebnisse entschieden.

### Vereinbarte Arbeitsweise im Notebook

Hauptmodell und Disziplinennetzwerk stehen gemeinsam in `Notebooks/02_modellierung.ipynb`. Zuerst wird dieses Notebook erstellt und gemeinsam durchgesehen. Der Reportabschnitt wird erst anschliessend auf Grundlage der besprochenen Ergebnisse ausgearbeitet.

Der Code soll klar strukturiert und von oben nach unten ausführbar sein. Aussagekräftige Namen, überschaubare Zellen und wenige gezielte Hilfsfunktionen halten ihn nachvollziehbar. Funktionen werden dort eingesetzt, wo sie Wiederholungen vermeiden oder einen komplexeren Schritt verständlich zusammenfassen. Unnötige Abstraktionen und wiederholter Code werden vermieden.

Markdown und Kommentare erklären knapp, warum ein Schritt nötig ist und wie wichtige Ergebnisse zu verstehen sind. Offensichtlicher Code wird nicht nacherzählt. Die EDA wird nicht wiederholt. Wenige aussagekräftige Tabellen und Beispiele genügen.

Alle Plots werden als Notebookausgaben angezeigt. Der Notebookcode enthält keine automatischen Bildexporte und keine Schreibzugriffe auf `Report/graphics/`. Die Abbildungen speichert das Projektteam manuell. Alternativ kann der Assistent sie später bei der Reportausarbeitung separat ablegen, ohne dafür Exportcode in das Modellierungsnotebook einzubauen. Das Speichern der Netzwerkdaten und Zuordnungstabellen ist davon getrennt.

### Vereinbarte technische Umsetzung

Die Modellierung und das Speichern der Netzwerkdaten erfolgen im Notebook. Eine kurze `data/README.md` erklärt die vorhandenen Daten und die erzeugten Netzwerkdateien.

| Aufgabe | Vorgesehener Ort oder Werkzeug |
| --- | --- |
| Einlesen und Zuordnungen aufbereiten | Python mit pandas in `Notebooks/02_modellierung.ipynb` |
| Netzwerke erstellen und prüfen | NetworkX im selben Notebook |
| Abbildungen erzeugen | Alle drei statischen Darstellungen mit Matplotlib direkt im Notebook |
| Gesamtansicht anordnen | Gewichtetes Federlayout von NetworkX mit SciPy, festem Zufallsstart und begrenzter Iterationszahl |
| Netzwerke und zugehörige Tabellen speichern | GEXF für die drei Netzwerke und Parquet für die Zuordnungstabellen unter `data/processed/networks/` |
| Datendateien dokumentieren | Kurze Übersicht in `data/README.md` |
| Modellierung im Report beschreiben | Nach gemeinsamer Durchsicht des Notebooks in `Report/sections/03_modellierung.tex` |
| Abbildungen für den Report übernehmen | Später manuell nach `Report/graphics/` oder separat durch den Assistenten, ohne Bildexportcode im Notebook |
| Später optional interaktiv erkunden | Die gespeicherten Netzwerke in Gephi öffnen |

Das Notebook beginnt mit einer kurzen Übersicht zu Fragestellungen, Daten, Knoten, Kanten, Gewichten und Ablauf. Die gemeinsame EDA Datei bleibt die Datengrundlage. Zusätzliche Zuordnungen und nötige Ausschlüsse für einzelne Modelle werden im Modellierungsnotebook nachvollziehbar dokumentiert.

Athleten erhalten Name, Geschlecht, Profilnation, Geburtsjahr und Verein als Attribute. Fehlende Attribute bleiben als fehlend erkennbar. Veranstaltungstage erhalten Wettkampfname, Ort, Datum und Beckenlänge. Disziplinknoten erhalten Strecke, Schwimmstil, Beckenlänge und die Anzahl verschiedener zugehöriger Athleten. Die TOP100 Platzierung steht nicht zur Verfügung.

Die Ausgabedateien heissen `athlete_events.gexf`, `athletes.gexf` und `disciplines.gexf`. Die Zuordnungen werden als `athlete_events.parquet` und `athlete_disciplines.parquet` gespeichert. Ihre Bedeutung ist in [data/README.md](../data/README.md) beschrieben.

### Geplanter Aufbau des Notebooks

1. **Überblick.** Beide Fragestellungen und die drei Darstellungen knapp definieren. Direkt erklären, was die Knoten, Kanten und Gewichte bedeuten.
2. **Datengrundlage und Zuordnungen.** Bereinigte Daten laden und die vereinbarten Regeln anwenden. Eindeutige Zuordnungen zwischen Athleten, Veranstaltungstagen und Disziplinen vorbereiten. Verwendete und ausgeschlossene Einträge kurz ausweisen.
3. **Hauptmodell und Projektion.** Das bipartite Netzwerk erstellen und durch die gewichtete Projektion das Athletennetzwerk ableiten. Eine konkrete Verbindung anhand ihrer gemeinsamen Veranstaltungstage erklären.
4. **Disziplinennetzwerk.** Kombinationen aus Disziplin und Beckenlänge bilden und gemeinsame Athleten zählen. Auch hier ein konkretes Kantengewicht nachvollziehen.
5. **Prüfung und Übersicht.** An wenigen echten Beispielen Zuordnungen und Gewichte prüfen. Sicherstellen, dass wiederholte Leistungen und mehrfach erfasste Personen keine Mehrfachzählung erzeugen. Eine kompakte Tabelle zeigt Knotenanzahl, Kantenanzahl und verwendeten Datenumfang.
6. **Abbildungen.** Die drei vereinbarten Darstellungen im Notebook zeigen: einen Ausschnitt des bipartiten Hauptmodells samt Projektion, die statische Gesamtansicht des Athletennetzwerks und das Disziplinennetzwerk. Die Darstellungen kurz einordnen.
7. **Netzwerkdaten speichern und Abschluss.** Netzwerke und Zuordnungstabellen für die weitere Arbeit speichern. Die Plots bleiben als Notebookausgaben sichtbar. Ein kurzes Fazit erklärt, welche Beziehungen nun abgebildet werden und welche Grenzen bestehen.

Für die späteren Kapitel können die gespeicherten Netzwerke wieder eingelesen werden. Nach Abschluss des Modellierungsnotebooks folgt zunächst die gemeinsame Durchsicht.

Kapitel 3 behandelt die begründete Modellwahl, Erstellung und Prüfung. Der Report fasst diese Punkte knapp zusammen und nutzt die drei vereinbarten Darstellungen zur Erklärung. Communities, Zentralitäten und weitere Auswertungen folgen in den späteren Kapiteln. Das Disziplinennetzwerk ergänzt das Hauptmodell mit einer zweiten Perspektive. Der Umfang seiner späteren Auswertung wird noch konkretisiert.

Weitere Anpassungen aus der gemeinsamen Durchsicht werden in diesem Plan festgehalten. Ein möglicher zusätzlicher Einsatz von Gephi wird anhand der Notebookergebnisse entschieden.

## Anschliessende Auswahl aus Kapitel 4 bis 14

Diese Ideen bleiben vorläufig. Ihre konkrete Umsetzung wird anhand der erstellten Netzwerke festgelegt.

| Skriptkapitel | Vorgesehener Beitrag |
| --- | --- |
| 4 Reduktion | Einen begründeten Ausschnitt festlegen und die verbleibende Datenmenge nennen. Weitere Filter nur bei Bedarf. |
| 5 Communities | Ein Verfahren, beispielsweise Louvain, anwenden und wenige Gruppen fachlich anhand von Profilnation oder Disziplinen einordnen. |
| 6 Zentralität | Degree und Betweenness als Vernetzung und Vermittlung vergleichen. Für Betweenness zunächst ungewichtete Wege verwenden. Häufigkeitsgewichte sind keine Entfernungen. |
| 7 Zentralisierung | Optional. Nur bei einem zusätzlichen Erkenntnisgewinn durch den Vergleich passender Teilnetze. |
| 8 Netzwerkmetriken | Eine kompakte Übersicht zu Grösse, Zusammenhangskomponenten, Dichte und Clustering. Durch die Projektion entstehen bereits Dreiecke, die entsprechend einzuordnen sind. |
| 9 Konnektivität | Kleiner kreativer Robustheitsvergleich: zentrale gegenüber gleich vielen zufälligen Athleten entfernen und die Veränderung der grössten Komponente beobachten. Zufallsentnahmen wiederholen. |
| 10 Korrelation | Eine Frage untersuchen: Sind Athleten derselben Profilnation im beobachteten Graphen stärker verbunden? Dafür Assortativität verwenden. |
| 11 Inferenzstatistik | Dieselbe Frage mit einem begründeten Permutationstest vertiefen. Nullmodell, Effekt und Unsicherheit erklären. Auswahlverzerrungen und mögliche gemeinsame Wettkampfangebote berücksichtigen. |
| 12 Link Prediction | Zunächst auslassen. Die Bestleistungsdaten bieten nur eine eingeschränkte Grundlage für eine historische Vorhersageprüfung. |
| 13 Diffusion | Zunächst auslassen. Es gibt keine beobachteten Übertragungsprozesse. |
| 14 Graphlets | Zunächst auslassen. Der Zusatznutzen rechtfertigt für den geplanten Umfang keinen eigenen Schwerpunkt. |

Das **Disziplinennetzwerk** ist als Ergänzung für Kapitel 3 vereinbart. Für die späteren Kapitel bietet sich ein ausgewählter Vergleich an, beispielsweise bei den Communities. Ein vollständiger zweiter Analysedurchlauf ist bisher nicht vorgesehen. Zwischenzeiten mit `Lap` bleiben dabei ausgeschlossen.

Die kreative Vielfalt kommt damit aus zwei überschaubaren Erweiterungen: dem Wechsel der Perspektive auf Disziplinen und dem Robustheitsvergleich. Eine klare Interpretation dieser Ergebnisse hat Vorrang vor weiteren Algorithmen. Die Auswahl kann beim Arbeiten angepasst werden, wenn sich eine Frage als unergiebig erweist.

## Arbeitsweise und Report

Aufbereitung, Berechnungen, Prüfungen und Abbildungen erfolgen im Notebook. Gephi kann anschliessend ergänzend genutzt werden. Für Kapitel 3 wird zuerst das Notebook gemeinsam durchgesehen und danach der kurze Reportabschnitt geschrieben. Die Abbildungen werden separat übernommen. Für Datenbeschaffung und EDA gilt der separate [Datenplan](PLAN_DATEN.md).

Die Dateinummern unter `sections/` folgen ab `03` dem Skript. Die fertigen Reportabschnitte werden unabhängig davon automatisch fortlaufend nummeriert. Optionale Abschnitte sind in `main.tex` auskommentiert. Zum Abschluss genügen ein kurzes Fazit, konkrete Grenzen und ein Ausblick.
