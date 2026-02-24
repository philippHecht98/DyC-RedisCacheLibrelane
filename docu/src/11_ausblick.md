# Ausblick / Zusätzliche Funktionalitäten (Alle)

Nachfolgend werden weitere Funktionalitäten beschrieben, welche wir gerne umgesetzt hätten, jedoch aufgrund von Zeitmangel nicht mehr implementieren konnten: 

**DELETE Implementation refactoren. Kann auf 1 State gekürzt werden**
Nach den Optimierungen des Memory Blockes könnte die DELETE Sub FSM auf einen einzigen State gekürzt werden. Hintergrund ist, dass bereits nach der positiven Flanke die DELETE operation abhängig vom HIT Signals des bereits schon anliegenden Schlüssels exisitert sodass nur noch abhängig von diesem Signal ein DELETE durchgeführt werden muss. Dieses Signal würde vom Memory Block bereits zur fallenden Taktflanke verarbeitet werden.

**LIST Operation**

Die zunächst angedachte Funktionalität einer LIST Operation wäre für eine realitätsnahe Umsetzung vermutlich sinnvoll. Damit müsste die darauf aufbauende Applikation nicht mehr intern die eigene Schlüsselverwaltung implementieren und diese direkt über die Hardware gestalten. Angedacht wäre, dass die LIST Operation über mehrere OBI Transaktionen die jegliche Schlüssel ausliest und an die Applikation zurückgibt.

**TTL (Time To Live) Funktionalität**

Redis implementiert eine TTL Funktionalität, welche Schlüssel nach einer vorgegebenen Zeit invalidiert und löscht. Ähnliches hatten wir für unsere Implementierung angedacht. Hierzu hätten wir einen Timer mit implementiert welcher immer den kleinsten TTL Wert der aktuell im Cache befindlichen Schlüssel verwendet und nach Ablauf der Zeit den Schlüssel automatisch löscht. 

