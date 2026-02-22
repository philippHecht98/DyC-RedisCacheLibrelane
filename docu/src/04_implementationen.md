# Implementationen

## Memory (Philipp)

## Controller

### Main Controller (Luca S, Luca P)

Der Main Controller (controller.sv) dient als Orchestrator der Operationen. Seine Hauptaufgabe besteht darin, eingehende Operationen von dem Interface entgegenzunehmen und die Ausführung an spezialisierte Sub-Controller (GET, UPSERT, DELETE) zu delegieren.

Die Architektur ist hierarchisch aufgebaut. Der Main Controller implementiert eine übergeordnete State Machine, die im `IDLE`-Zustand auf Anfragen wartet. Sobald eine valide Operation erkannt wird, wechselt der Controller in den entsprechenden Zustand und aktiviert das zuständige Sub-Modul.

**Schnittstelle zu Sub-Controllern**

Um die Komplexität zu kapseln, verfügen alle Sub-Controller über ein einheitliches Interface-Konzept zur Kommunikation mit dem Main Controller:

- **`en` (Enable):** Ein Signal vom Main Controller an den Sub-Controller, um dessen FSM oder Logik zu starten.
- **`cmd` (Command/Data):** Status Signale der Sub-Controller. (Error/Done)
- **`enter` (Enter):** Signalisiert den Eintritt in den Zustand des Sub-Controllers. Dient zur Initialisierung der Sub-FSM.

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

### GET (Luca P)

### UPSERT (Luca S)

Der UPSERT-Controller ("Update or Insert") ist für das Schreiben von Daten in den Cache verantwortlich. Er wurde so implementiert, dass er unabhängig vom Basistemplate agiert und die spezifische Logik für das Hinzufügen oder Aktualisieren von Key-Value-Paaren kapselt.

Die Key-Value Werte liegen direkt vom OBI-Interface am Memory-Block an. (Siehe Kapitel Architektur) 
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

### DELETE (Philipp)

## Obi interface 
TODO: Verlinkung auf obi.md für Protokoll beschreibung