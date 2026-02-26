# OBI

## Einleitung und Motivation
Philipp Hecht

Die ursprüngliche Idee war es, den Cache über *Custom-Commands* innerhalb einer RISC-V CPU anzusteuern. Hierrüber wäre es somit möglich gewesen, 
die Cache Operationen direkt als Assembler Instruktionen zu implementieren. Auf Empfehlung des Lehrpersonals, wurde die Entscheidung getroffen, die 
Anbindung des Caches über Memory Mapping zu realisieren. Als mögliche Protokolle hierfür fanden wir das AXI als auch das OBI (Open Bus Interface)
Protokoll. Nach ersten Versuchen zur Implementierung des AXI Protokolls, entschieden wir uns auf Anraten des Lehrpersonals für die Implementierung
des OBI Protokolles, da dieses bereits als vorgefertiges Projekt bereits (vgl. Kapitel Croc) vorliegt. 

Architekturell entschlossen wir uns, den OBI Slave nicht direkt in den Cache Controller zu implementieren sondern stattdessen, diesen als 
separates Modul aufzusetzten. Dies ermöglichte uns einerseits die aktuelle Implementierung des Caches nicht zu verändern. Der Cache erhält weiterhin 
die gleichen Signale wie zuvor, was die Komplexität der Implementierung reduzierte. Andererseits ermöglichte eine separate Implementierung dediziertes
Testen und Debugging des OBI Slaves. 

## OBI Protokoll
Luca Schmid

### Register

Mit dem OBI Protokoll ermöglichen wir der CPU über Memory Mapping direkt mit dem Controller zu kommunizieren. Hierfür definierten wir 3 Registertypen,
die über das OBI Protokoll angesprochen werden können:

|        | Daten    | Schlüssel | Op-Code |
| ------ | -------- | ---------- | ------------ |
| Größe  | 64 (8 Bytes) | 32 (4 Bytes) | 32 (4 Bytes) |
| Offset | 0        | 8          | 12            |

Die Größe der Register ist in der cache_cfg_pkg konfigurierbar. Die Offset Werte leiten sich aus den den Größen der Key und Value Register Modulo 32 ab.
In den OBI Nachrichten wird die Speicheraddresse(Basis + Offset) mitgegeben. Über dieses Offset werden die Daten in die richtigen Register geschrieben bzw. können darüber ausgelesen werden. 

### OBI Request

Über einen OBI Request sendet die Applikation (Master) Daten an den Cache. Hierfür sieht das OBI Protokoll eine bestimmte Struktur der Nachricht vor. 
Nachfolgende Tablle beschreibt die für den Cache relevanten Felder des OBI Requests:

| Feld in obi_req_t | Bit-Breite    | Beschreibung |
| ---------         | ----------    | ------------ |
| addr              | 32            | Adresse von der CPU an der die Daten geschrieben werden sollen |
| we                | 1             | Write Enable: 1 führt einen Schreiben aus, 0 führt ein Lesen aus |
| wdata             | 32            | Write Data: Die Daten, die am Offset der Addresse eingeschrieben werden sollen |
| aid               | 1             | Address ID: Eine ID für die Transaktion |
| req               | 1             | Request: Das Handshake-Signal, welches der Master zum Start einer Transaktion sendet |

Eine OBI Transkation besteht dabei immer aus einem OBI Request, sowie der zugehörigen Response.

TODO: Philipp rausgeschmissene Bits als Sternchen markieren


### OBI Response

Die OBI Response wird von der Hardware an den Master versendet. Hierrüber können die Werte des angefragten Register an die Applikation zurückgegeben werden.
Nachfolgende Tablle beschreibt die für den Cache relevanten Felder des OBI Responses:

| Feld in obi_rsp_t | Bit-Breite    | Beschreibung |
| ---------         | ----------    | ------------ |
| rdata             | 32            | Read Data: Daten, die vom Cache zurück an die Applikation versendet werden |
| rid               | 1             | Response ID: Spiegelt die aid aus dem Request wider, um Antworten zuzuordnen |
| err               | 1             | Error: Einfaches Flag Signal, welches der Applikation andeutet, dass die Ausführung nicht erfolgreich war |
| gnt               | 1             | Grant: Handshake-Signal mit dem der Slave bestätigt, dass er die Anfrage verarbeitet hat |
| rvalid            | 1             | Response Valid: Wird 1, wenn die zurückgegebenen Daten in r.rdata gültig sind. |

## Implementierung des OBI Slaves
Philipp Hecht


Zunächst versuchten wir, den OBI Slave eigenständig zu implementieren. Vorwegnehmend war diese Weg zur Implementierung nicht erfolgreich. Dennoch soll hier
der Weg zur erfolgreichen Implementierung beschrieben werden, um damit das generelle Konzept hinter unserer Implementierung zu verdeutlichen: 

Die Risc-V CPU kommuniziert über Memory Mapping mit dem Cache. Hierfür werden die OBI Requests und Responses über die entsprechenden Signale gesendet.
Der vom Croc bereitgestellte RISC-V Core arbeitet dabei auf einer 32-Bit Architektur, weshalb die Datenbreite eines einezelnen OBI Requests bzw. Response 
auf 32 Bit limitiert ist. Gleichzeitig arbeitet der Cache mit einer Datenlänge, welche höher als die 32 Bit ist. Dies stellte die erste Herausforderung 
für die Interface Implementierung dar. 

Aus Sicht des OBI Protokolles, wird dieses Problem darüber gelöst, dass mehrere, hintereianderliegende Adressen für die gesamte Datenübertragung genutzt werden. 
Es ist dann Aufgabe der Applikation die Daten entsprechend über mehrere Aufrufe an die zugehörigen Register zu schreiben (siehe hierzu das Kapitel [C Lib](#c-lib)). 

Pseudo Code hierfür würde in etwa wie folgt aussehen:

```c
void upsert_to_cache(uint32_t base_address, uint64_t data, uint32_t key) {
    // Aufteilen der 64-Bit Daten in zwei 32-Bit Teile
    uint32_t lower_data = (uint32_t)(data & 0xFFFFFFFF);
    uint32_t upper_data = (uint32_t)((data >> 32) & 0xFFFFFFFF);  

    write_to_obi(base_address, lower_data);
    write_to_obi(base_address + 4, upper_data);
    write_to_obi(base_address + 8, key);
    write_to_obi(base_address + 12, OP_CODE_UPSERT);    
}
```

Darauf aufbauend muss das OBI Interface Modul über einen State Machine arbeiten, um eingehende OBI Transaktionen zu verarbeiten und die entsprechenden Daten in ein 
temporäres Register zu schreiben. Als *Go* für das Übermitteln der Daten an den Cache Controller definierten wir, dass sobald der Master den Operationscode über das 
entsprechende Register schreibt, die Daten an den Cache Controller weitergeleitet werden. Die State Machine hatte dabei die folgenden Zustände:

- IDLE: In diesem Zustand wartet die State Machine auf einen OBI Request. Sobald ein Operationscode über das entsprechende Register geschrieben wird, übermittelt das
Interface die Daten an den Controller und wechselt in einen WAIT_FOR_CONTROLLER Zustand.

- WAIT_FOR_CONTROLLER: In diesem Zustand wartet die State Machine auf eine Rückmeldung des Cache Controllers. Sobald der Controller die Daten verarbeitet hat, wechselt die State Machine zurück in den IDLE Zustand und ist bereit für die nächste Transaktion. Während dieser Phase blockiert die State Machine weitere OBI Requests und setzt `rvalid` auf 0, um der Applikation mitzuteilen, dass die Daten noch nicht zurückgegeben werden können.

- COMPLETE: In diesem Zustand werden die Daten an die Applikation zurückgegeben. Sobald die Daten zurückgegeben wurden, wechselt die State Machine zurück in den IDLE Zustand.

Es zeigte sich jedoch, dass diese Art der Implementierung nicht sonderbar kombinierbar mit dem Ablauf des OBI Protokolles einhergehend war. Erste Implementierungen blockierten dabei die gesamte OBI Crossbar und blockierten damit nicht nur den Cache als auch die CPU selbst (vermutlich). 

Nach Absprache mit dem Lehrpersonal überarbeiteten wir die Implementierung dahingehend um, dass die Statemaschine nicht mehr über einen internen Zustandsautomaten verfügt, 
sondern *OBI nativ* jegliche Anfragen immer annimmt und direkt darauf reagiert. Das Interface *blockiert* nicht mehr während der Verarbeitung einer Anfrage, sondern nimmt 
direkt die nächste Anfrage an. Hierdurch reduziert sich die Komplexität des OBI Interfaces. Gleichzeitig ist es damit Aufgabe des Masters die Anfragen in sequenzieller 
Reihenfolge zu stellen. Das Lesen von Daten während der Controller noch mit der Verarbeitung einer vorherigen Anfrage beschäftigt ist, führt zu fehlerhaften Daten.

### Aktuelle Implementierung
Luca Pinnekamp

Die finale Architektur des OBI-Interfaces ist stark an die Implementierung des UART OBI Interfaces aus dem Croc SoC angelehnt. Sie realisiert eine direkte Register-Schnittstelle, die als Bindeglied fungiert und von zwei Seiten unabhängig aktualisiert werden kann:

- **Updates durch die CPU (OBI-Seite):** 
  Die CPU schreibt über reguläre OBI-Requests in die Register. Das Interface decodiert die Zieladresse und aktualisiert das entsprechende 32-Bit-Wort im `DAT`-, `KEY`- oder `CTR`-Register. Dabei werden die Byte-Enable-Signale (`be`) des OBI-Protokolls respektiert, sodass auch einzelne Bytes innerhalb eines Wortes gezielt beschrieben werden können (Auch wenn dies hier nicht unbedingt nötig ist). Eine Änderung der Operation im `CTR`-Register löst dabei die eigentliche Operation im Cache-Controller aus.
  
- **Updates durch den Cache-Controller (Interne Seite):** 
  Die aktuellen Werte der Register werden kontinuierlich über interne Signale `reg_read_o` (`dat`, `key`, `operation`) an den Controller ausgegeben. Der Cache-Controller meldet Ergebnisse über dedizierte interne Signale `reg_write_i` (`dat`, `busy`, `hit`, `operation`) an das Interface zurück. Jedes Feld verfügt über ein eigenes Valid-Signal (`data_valid`, `busy_valid`, `hit_valid`, `operation_valid`), welches bestimmt, ob der entsprechende Wert im Register aktualisiert werden soll. Bei einem erfolgreichen `GET`-Befehl setzt der Controller beispielsweise `data_valid` auf 1 und überschreibt das `DAT`-Register mit dem gefundenen Wert aus dem Cache. Gleichzeitig werden die Status-Bits über `hit_valid` und `busy_valid` im `CTR`-Register aktualisiert.

Durch diese beidseitige Aktualisierung dient das Interface als reiner Datenspeicher. Die Synchronisation erfolgt ausschließlich über die Software, welche das `busy`-Bit auslesen muss, um festzustellen, wann der Controller seine Updates abgeschlossen hat.
