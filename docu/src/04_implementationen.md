# Implementationen

## Memory
Philipp Hecht

Wie bereits zuvor beschrieben, haben wir uns für die Implementierung eines Key-Value-Stores entschieden, der 
im Wesentlichen auf einem einfachen Speicherblock basiert. Zunächst wurde für den Speicherblock definiert,
dass er in der Lage sein soll, 

1) Schlüssel-Wert Paare zu speichern
2) Schlüssel-Wert Paare zu löschen
3) Schlüssel-Wert Paare anhand von Schlüsseln zu lesen und auszugeben

Die Implementierung wurde hierfür in weitere kleinere Submodule hierarisch unterteilt. 
Zunächst wurde eine dynamisch ansteuerbarer Speicheeinheit implementiert, worauf im Nachfolgendem eingegangen wird. Darauf aufbauend wurde eine einzelne Speicherzelle definiert, welche die übergeordnete Funktionalität 
des Speicherns von Schlüssel-Wert Paaren bereitstellt. Hierauf setzend wurde ein kleiner Controller definiert, welcher N Schlüssel-Wert Paare in einem Array von Speicherzellen verwaltet und die zuvor beschreibenenen Funktionen bereitstellt.

### Dynamic Register Array

Diese Komponente bildet die unterste Hierarchie-Ebene der Memory-Funktionalität und stellt einen einzelnen, konfigurierbaren Registerblock dar. Die Registerbreite wird durch den Parameter `LENGTH` zur Compile-Zeit definiert, wodurch eine flexible Anpassung an verschiedene Datenbreiten ermöglicht wird. Der Registerblock ist nach außen hin vollständig addressierbar durch standardisierte Steuersignale für Lese- und Schreibvorgänge.

**Funktionale Merkmale:**
- **Parametrische Registerlänge**: Die Breite des Registerblocks wird über `LENGTH` konfiguriert
- **Synchrone Schreibvorgänge**: Daten werden auf der fallenden Clock-Flanke übernommen
- **Asynchroner Reset**: Der Register wird auf 0 zurückgesetzt, wenn `rst_n` Low wird
- **Parallele Ein- und Ausgänge**: Simultaner Zugriff auf alle Bits des Registerblocks

**Implementierung:**

```systemverilog
module dynamic_register_array #(
    parameter LENGTH
)(
  ....
);

    reg [LENGTH-1:0] registers;

    always_ff @(negedge clk or negedge rst_n) begin
        if (!rst_n) begin
            registers <=  '0;
        end else if (write_op) begin
            registers <= data_in;
        end 
    end
    assign data_out = registers;
endmodule
```

Dieses Basis-Registermodul wird für jede Speicherzelle instanziiert und bildet die Grundlage für die höherrangigen Speicherfunktionen im Controller. Zur Optimierung 
des gesamten Caches beschlossen wir, dass die Registerblöcke nicht, wie üblich, auf der steigenenden Taktflanke beschrieben werden, sondern stattdessen auf der fallenden. Dadurch können wir die Daten bereits im nächsten Zyklus für Controller und die darüber ligendenden Blöcke bereitstellen, was es uns ermöglichte, die gesamte Speicherfunktionalität in nur einem Taktzyklus zu realisieren.

### Memory Cell

Die Memory Cell ist die zweite Hierarchie-Ebene und kapselt eine einzelne Speicherzelle, welche Key-Value-Pair speichert. 
Dabei nutzt sie das zuvor beschriebenen Dynamic Register Array Modul für die Speicherung des Schlüssels 
als auch des Wertes: 

```systemverilog
module memory_cell #(
    parameter KEY_WIDTH,
    parameter VALUE_WIDTH
)(
    ...
    input logic [KEY_WIDTH-1:0] key_in,
    input logic [VALUE_WIDTH-1:0] value_in,

    output logic [KEY_WIDTH-1:0] key_out,
    output logic [VALUE_WIDTH-1:0] value_out,
    output logic used_out
);
    // Key Register
    dynamic_register_array #(.LENGTH(KEY_WIDTH)) key_reg (
        ...
    );

    // Value Register
    dynamic_register_array #(.LENGTH(VALUE_WIDTH)) value_reg (
        ...
    );

    // Used-Flag: Zelle ist gültig, wenn Key ungleich 0
    assign used_out = (key_out != '0);

endmodule
```

Durch das zuvorige Implementieren des Dynamic Register, können wir innerhalb der Zelle verschiedene Bit-Längen
für die Schlüssel und Daten definieren. 

Zusätzlich wurde ein "Used-Flag" implementiert, welches anzeigt, ob die Zelle aktuell gültige Daten enthält. 
Diese Funktionalität wird für den darüber ligenenden Controller benötigt. Da hierdurch bestimmt werden kann, 
ob der Cache vollständig gefüllt ist oder ob noch freie Zellen vorhanden sind. Zunächst bestand die Idee, 
die einzelnen Schlüssel zeitlich auslaufen zu lassen (ählich zu Redis). Aufgrund von Zeitmangel, wurde diese 
Funktionalität jedoch nicht implementiert, sodass als Verkürzung die Gültigkeit eines Schlüssel-Wert-Paares 
durch das Vorhandensein eines Schlüssels (key_out != 0) definiert wurde. Gleichzeitig beschlossen wir, dass die 
Übergeordnete Verwaltungslogik, welche Zellen aktuell *frei* sind innerhalb des Controllers stattfinden soll, was die Implementierung der Memory Einheit vereinfachte. Auch wollten wir nicht den Used-Wertes einer einzelnen Zelle
über ein eigenes Register abbilden um damit auch hier eine Optimierung zu erreichen. 

### Memory Block

Der Memory Block ist die übergeordnete Kontrollschicht der einzelnen Speicherzellen. Gleichzeigit übernimmt dieser
Block die Verwaltung von Befehlen des übergeordneten Controllers, welcher im Nachfolgenden [Kapitel](#controller) 
beschrieben wird. 

Der Block instantiiert `NUM_ENTRIES` Speicherzellen und verwaltet diese als Array. Die Kontrolle über Schreib- und 
Löschvorgänge erfolgt durch gezieltes Aktivieren einzelner Zellen mittels Index-Signalen. Hierauf wird im Nachfolgendem
näher eingegangen:

#### Einfügen von Schlüssel-Wert Paaren

Das Einfügen eines Schlüssel-Wert Paares wird durch ein Signal des Controllers
ausgelöst. Zusammen mit dem Setzen des ausgewählten Indexes (Der Controller nutzt 
hierfür die *used* Signale der einzelnen Zellen (Hot-Wire)) wird die entsprechende Zelle 
aktiviert, um die Daten zu speichern. Bei der nächsten positiven Taktflanke werden 
die Daten in der Zelle gespeichert. 

Als eine Optimierung wird die Löschoperation als Sonderfall eines Schreibvorgangs 
behandelt. Das bedeutet, dass beim Löschen eines Schlüssel-Wert Paares die Zelle mit 
einem Schlüssel von 0 beschrieben wird, wodurch sie als ungültig markiert wird. 

```systemverilog
    memory_cell #(
        .KEY_WIDTH(KEY_WIDTH),
        .VALUE_WIDTH(VALUE_WIDTH)
    ) temp (
        ...
        .write_op((write_in || delete_in) && index_in[i]),
        .key_in(delete_in ? '0 : key_in),
        .value_in(delete_in ? '0 : value_in),
        ...
    );
```

#### Abrufen von Werten anhand von Schlüsseln

Für das Abrufen von Schlüssel-Wert Einträgen empfängt der Memory Block einen 
Schlüssel als Input und durchsucht alle Speicherzellen nach einer Übereinstimmung. 
Dieser Prozess findet vollständig kombinatorisch im `always_comb` Block statt und 
liefert daher im selben Taktzyklus ein Ergebnis.

Die Such-Logik vergleicht den Input-Schlüssel mit allen gespeicherten Schlüsseln und gibt den zugehörigen Wert zurück. Dies wird im `always_comb` Block durch folgende Schritte realisiert:

```systemverilog
// Schlüssel-basierter Zugriff: Alle Zellen nach Key durchsuchen
for (int i = 0; i < NUM_ENTRIES; i++) begin
    if (used_entries[i] && (cell_key_out[i] == key_in)) begin
        value_out_d = cell_value_out[i];    // Wert der gefundenen Zelle
        hit_d = '1;                          // Signalisiere erfolgreichen Match
        index_out_d = 1 << i;                // Gebe Position als One-Hot aus
    end
end
```

Bei einem erfolgreichen Match werden drei Ausgänge gesetzt:
- `value_out_d`: Der gespeicherte Wert der gefundenen Zelle
- `hit_d`: Ein Flag, das signalisiert, dass ein Match gefunden wurde
- `index_out_d`: Die Position der gefundenen Zelle im One-Hot-Encoding Format

#### Löschen von Werten anhand von Schlüsseln

Wie bereits zuvor erwähnt, wird die Löschoperation als Sonderfall eines 
Schreibprozesses behandelt. Falls der Controller ein Löschsignal sendet, wird die
gesamte Zellen auf *0* gesetzt: 

```systemverilog
    memory_cell #(
        .KEY_WIDTH(KEY_WIDTH),
        .VALUE_WIDTH(VALUE_WIDTH)
    ) temp (
        ...
        .write_op((write_in || delete_in) && index_in[i]),
        .key_in(delete_in ? '0 : key_in),
        .value_in(delete_in ? '0 : value_in),
        ...
    );
```

Nachfolgendes Architekturdiagramm zeigt den Aufbau des Memory Blockes und deren Teilkomponenten 
als auch die Signale, welche für die Interaktion mit dem übergeordneten Controller definiert 
wurden:

![Memory Block Architektur](./diagramme/Memory Block Architektur.drawio.svg)


#### Zusammenhang mit Controller

Der Memory Block wird zentral vom übergeordneten Controller orchestriert, welcher drei unterschiedliche Operationen 
(GET, UPSERT, DELETE) mittels Finite State Machines (FSMs) durchführt. Dabei laufen die Interaktionen zwischen 
Controller und Memory Block über klar definierte Steuersignale.

Im Nachfoglendem wird auf die einzelnen Operationen eingegangen. Dabei wird auf Taktzyklenebene beschreiben,
wie die einzelnen Signale den Memory Block operieren und der Datenfluss dargestellt.


**GET-Operation:**

1. **Schritt 1 - Positive Flanke**: Der Controller wechselt intern in einen *GET*-Zustand (siehe nachfolgendes 
Kapitel). Auf den Schlüssel-Input Kabeln des Memory Blocks wird der gesuchte Schlüssel für den Memory Block 
bereitgestellt. Durch die `always_comb` Logik des Memory Blockes wird dadurch sofort eine Suche nach diesem 
Schlüssel in allen Zellen durchgeführt (siehe Kombinationslogik oben). 

2. **Schritt 2 - Positive Flanke**: Sollte dabei der Schlüssel in den Zellen gefunden werden, wird an die
Ausgangssignale des Memory Blockes die Daten, ein Hit-Signal sowie der Index der gefundenen 
Zelle ausgegeben. Daraufaufsetzend, kann der Controller in der nächsten steigenden Flanke mit einem 
Ergebnis vom Memory Block rechnen. 

Falls dieser Schlüssel nicht gefunden wird, wird das Hit-Signal nicht gesetzt, wodurch der Controller in der 
nächsten steigenden Flanke erkennen kann, dass kein Treffer vorliegt. Dies verwendet der Controller anschließend für die 
Kalkulation ob der Upsert ein Update eines Eintrages oder das Einfügen eines neuen Eintrags bedeutet.


**UPSERT / DELETE -Operation:**

1. **Schritt 1 - Positive Flanke**: Der Controller wechselt zu einem *UPSERT*-Zustand. Auf den Schlüssel und Daten Kabeln
des Memory Blockes werden die entsprechenden Werte bereitgestellt. Zusätzlich wird das Steuersignal für das Einfügen bzw.
des Löschen als auch der Index für relevante Zelle gesetzt. 

2. **Schritt 2 - Negative Flanke**: Zur fallenden Flanke liegen die Schüssel und Daten Werte bereits an den Eingängen aller Zellen.
Durch die Logik des Memory Blockes wird abhängig vom gesetzten Indexes und des Schreibsignals allerdings nur an der zum Index
zugehörigen Zelle das *Schreib-Flag* angelegt. Dadurch wird nur diese Zelle die Daten in ihren Registern speichern. Im Falle einer
Löschoperation, werden an die Schlüssel und Dateneingägne der Zellen *0* angelegt. Mit der fallenden Flanke werden die Daten in der 
Zelle gespeichert bzw. gelöscht.

1. **Schritt 3 - Positive Flanke**: Der Controller kann davon ausgehen, dass die angelegten Werte in der Zelle gespeichert wurden. 
Zusätzlich wird im Falle einer Upsert-Operation über die Combinationslogik des Memory Blockes sofort ein Hit-Signal zurückgegeben. 


**Timing-Diagramm der Operationen:**

Durch dieses sorgfältig abgestimmte Timing zwischen Controller-Zustandsübergängen (positive Flanken) und Memory Block-Schreibvorgängen (negative Flanken) spart sich der Cache komplexere Handshakes als auch Wartezyklen. Nachfolgende Abbildungen zeigen zunächst die theoretische Planung als auch den simulierten Durchlauf der Taktzyklen: 

TODO: Diagramm erstellen


## Controller

### Main Controller
Luca Schmid

Der Main Controller (controller.sv) dient als Orchestrator der Operationen. Seine Hauptaufgabe besteht darin, eingehende Operationen von dem Interface entgegenzunehmen und die Ausführung an spezialisierte Sub-Controller (GET, UPSERT, DELETE) zu delegieren.

Die Architektur haben wir hierarchisch aufgebaut. Der Main Controller implementiert eine übergeordnete State Machine, die im `IDLE`-Zustand auf Anfragen wartet. Sobald eine valide Operation erkannt wird, wechselt der Controller in den entsprechenden Zustand und aktiviert das zuständige Sub-Modul.

**Schnittstelle zu Sub-Controllern**

Um die Komplexität zu kapseln, haben wir für alle Sub-Controller ein einheitliches Interface-Konzept zur Kommunikation mit dem Main Controller entworfen:

- **`en` (Enable):** Ein Signal vom Main Controller an den Sub-Controller, um dessen FSM oder Logik zu starten.
- **`enter` (Enter):** Signalisiert den Eintritt in den Zustand des Sub-Controllers. Dient zur Initialisierung der Sub-FSM.
- **`cmd` (Command/Data):** Status Signale der Sub-Controller. (Error/Done)

Dies ermöglicht es dem Main Controller, generisch auf das Ende einer Operation zu warten, ohne die internen Details der Operation kennen zu müssen.

```systemverilog
// Pseudo-Code Beispiel für die State-Wechsel vom Main Controller zu den Sub-Controllern
always_comb begin
    // Default Zuweisungen
    next_state = state;

    case (state)
        IDLE: begin
            busy = 1'b1;
            
            case (operation_in)
                    READ: begin
                        next_state = ST_GET;
                    end
                    // ... Weitere Operationen ...
            endcase
        end
        ST_GET: begin
            // ...                              Werte an Sub-Controller übergeben
            if (get_error) next_state = ST_ERR; // Error handling
            else if(get_done) begin             // Operation erfolgreich
                next_state = IDLE;
                busy = 1'b0;
            end
        end
        // ... Weitere Zustände ...
    endcase
end
```

### GET
Luca Pinnekamp

Für das Auslesen von Werten aus dem Cache haben wir die GET-Operation implementiert. Die zugehörige FSM (`get_fsm`) wird vom Main Controller aktiviert, sobald ein Lesezugriff angefordert wird.

Den Ablauf einer GET-Operation haben wir wie folgt gestaltet:

1. **Schlüsselsuche:** Um Latenzen zu minimieren, haben wir uns dazu entschieden, den zu suchenden Schlüssel nicht durch den Controller oder die `get_fsm` zu leiten. Stattdessen liegt dieser direkt am Interface an und wird von dort kontinuierlich an das Speichermodul übergeben. Das Speichermodul prüft daraufhin asynchron, ob ein entsprechender Eintrag im Cache existiert.

2. **Hit/Miss-Auswertung:** Das Speichermodul liefert ein `hit`-Signal an die `get_fsm` zurück. Da die Schlüssel und daraus resultierenden Werte direkt zwischen Interface und Memory Block übertragen werden muss die `get_fsm` lediglich die hit werte an den übergeordneten Controller bzw. das Interface weiterleiten. Zudem wird das `hit_valid` signal gesetzt um dem interface mitzuteilen, dass der Wert in das Kontrollregister übernommen werden kann. 

3. **Abschluss:** Die `get_fsm` signalisiert dem Main Controller den Abschluss der Operation (`cmd.done = 1`), woraufhin dieser den Status und aktuellen Befehl auf die Standard Werte zurücksetzt und in den Idle Zustand wechselt.

### UPSERT
Luca Schmid

Der UPSERT-Controller ("Update or Insert") ist für das Schreiben von Daten in den Cache verantwortlich. Er wurde so implementiert, dass er unabhängig vom Basistemplate agiert und die spezifische Logik für das Hinzufügen oder Aktualisieren von Key-Value-Paaren kapselt.

Die Key-Value Werte liegen direkt vom OBI-Interface am Memory-Block an. (Siehe Kapitel [Architektur](#architektur)) 
Somit steuert die Implementierung nur noch die Signale zur Verarbeitung dieser Werte im Memory-Block.

Wenn der empfangene Key-Wert bereits im Memory vorhanden ist, dann gibt der Memory-Block dem UPSERT-Controller ein positives "hit" signal und dessen "index" zurück. Wenn der Key-Wert nicht vorhanden ist liegt ein negatives "hit" signal an.
Außerdem übergibt der Memory Block die aktuell benutzen Indizes "used".

Anhand der Werte hit, idx_out und used kann in nur einem Zyklus entschieden werden, ob oder an welchem Index der anliegende Wert gespeichert werden soll:

```systemverilog
// Pseudo-Code Beispiel UPSERT
always_comb begin
    if (hit) begin
        // key existiert
        // Übergebenen Index an Memory Block übergeben

    end else if (!hit && !(&used)) begin
        // key existiert nicht, aber noch Platz im Memory
        // korrekten key finden und übergeben
        for (int j = 0; j < NUM_ENTRIES; j++) begin
            if (!used[j] && (idx_out == 0)) begin
                idx_out[j] = 1'b1;
            end
        end

    end else begin
        // key existiert nicht und kein Platz im Memory
        // Error an Main Controller übergeben
    end
```

### DELETE
Philipp Hecht

Die DELETE FSM verwaltet den Löschprozess durch drei Zustände:

1. **DEL_ST_START**: In diesem Zustand wird keine Operation ausgeführt; das Modul wartet auf die Aktivierung durch den Controller. Sobald das Modul aktiviert wird (dediziertes Steuersignal), springt die State Machine in den nächsten Zustand, um die Löschoperation einzuleiten. 

2. **DEL_ST_DELETE**: Die Statemachine behandelt das Löschen eines Schlüssels aus dem Memory Block. Aus dem eingehenden HIT-Signal wird vom Memory Block erkannt, dass der Schlüssel abgespeicher worden ist. Sollte dies der Fall sein, wird ein Löschsignal an den Memory Block gesendet, welcher, in Kombination mit dem bereits anliegendem Schlüssel, spätestens zur negativen Taktflanke vom Memory Block durchgeführt wird. 

3. **DEL_ST_ERROR**: Wenn der Memory Block keine Übereinstimmung zum zu löschenden Schlüssel findet (Hit-Signal bleibt Low), wechselt die FSM in diesen Fehlerzustand. Der Substate übermittelt an den übergeordneten Controller, dass die Löschoperation nicht erfolgreich war. 

Beide Zustände DEL_ST_DELETE und DEL_ST_ERROR wechseln zur nächsten positiven Flanke zurück in den DEL_ST_START Zustand, um die nächste Löschoperation entgegenzunehmen.

Dieses Timing ermöglicht es, dass die DELETE-Operation in nur zwei Taktzyklen abgeschlossen wird. 
Die zuvor beschriebene `always_comb`-Logik des Memory Blockes ermöglicht es direkt einen Löschvorgang abzuschließen.



## Obi interface 
Philipp Hecht

Als übergeordneten Block wurde für die Anbindung des Caches eine OBI (Open Bus Interface) Schnittstelle implementiert. Diese 
ermöglicht es, den Cache über ein standardisiertes Protokoll zu steuern. Weiteres wird im Nachfolgendem Kapitel [OBI](#obi) beschrieben.
