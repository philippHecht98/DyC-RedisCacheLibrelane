# Learnings und Ausblick
Ausarbeitung gemeinsam

Nachfolgend werden unsere Learnings während der Entwicklung des Caches und der zugehörigen Toolchain beschrieben. Hierbei werden sowohl Learnings bezüglich der Implementierung als auch der generellen Arbeitsweise und des Projektmanagements beschrieben.

1) Hardware Implementierungs sind aus Sicht eines Softwareentwicklers deutlich umständlicher als Software. Hardware verhält sich anders als Software und muss anders angedacht werden. 
2) Ein modularisiertes Design ermöglichte uns, die Arbeiten a) parallel zu bearbeiten und b) die Komplexität der einzelnen Module möglichst gering zu halten.
3) Selbst mit minimaler Anzahl an Featuren und mit der Idee der Erweiterung, hätten wir nicht gedacht, dass die Implementierung des Chips und die Integration in Croc so komplex sein würde.
4) Das Aufsetzen von Pipelines und Testautomatisierung über GitHub Actions ist für einen Projekt Scope von zwei Wochen zu aufwändig. Zuletzt wurden Tests als auch die Backendpipeline lokal ausgeführt. 
5) Eine Optimierung auf der unterstenen Ebene (Taktzyklen) ermöglichte uns weitgehende Optimierungen der Statemaschinen vorzunehmen, was die Komplexität des gesamten Systems deutlich reduzierte. 

Zuletzt werden weitere Funktionalitäten beschrieben, welche wir gerne umgesetzt hätten, jedoch aufgrund von Zeitmangel nicht mehr implementieren konnten: 

**DELETE Implementation refactoren. Kann auf 1 State gekürzt werden**
Nach den Optimierungen des Memory Blockes könnte die DELETE Sub FSM auf einen einzigen State gekürzt werden. Hintergrund ist, dass bereits nach der positiven Flanke die DELETE operation abhängig vom HIT Signals des bereits schon anliegenden Schlüssels exisitert sodass nur noch abhängig von diesem Signal ein DELETE durchgeführt werden muss. Dieses Signal würde vom Memory Block bereits zur fallenden Taktflanke verarbeitet werden.

**LIST Operation**

Die zunächst angedachte Funktionalität einer LIST Operation wäre für eine realitätsnahe Umsetzung vermutlich sinnvoll. Damit müsste die darauf aufbauende Applikation nicht mehr intern die eigene Schlüsselverwaltung implementieren und diese direkt über die Hardware gestalten. Angedacht wäre, dass die LIST Operation über mehrere OBI Transaktionen die jegliche Schlüssel ausliest und an die Applikation zurückgibt.

**TTL (Time To Live) Funktionalität**

Redis implementiert eine TTL Funktionalität, welche Schlüssel nach einer vorgegebenen Zeit invalidiert und löscht. Ähnliches hatten wir für unsere Implementierung angedacht. Hierzu hätten wir einen Timer mit implementiert welcher immer den kleinsten TTL Wert der aktuell im Cache befindlichen Schlüssel verwendet und nach Ablauf der Zeit den Schlüssel automatisch löscht. 

**Evaluation des Nutzen von SRAM**
Unsere Aktuelle Implementierung verwendet für den Memory Block eine Liste von einzelnen selbst definierten Registerzellen. Eine Alternative hierzu wäre die Verwendung von 
bereits fertigen Memory Blöcken. Diese bieten den Vorteil, dass sie deutlich weniger Logik und Platz aufweisen, wobei die Ansteuerung und das Überprüfen der einzelnen Zellen
auf einen *Hit* dadurch deutlich komplexer wird.