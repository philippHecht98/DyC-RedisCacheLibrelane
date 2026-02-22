# Tests

## Allgemeines Testkonzept

Um die korrekte Funktionalität der Module sicherzustellen, haben wir Frontend-Tests mittels **Cocotb** (Coroutine Co-simulation Testbench) durchgeführt. Es wurden Tests für die einzelnen Memory Module, die Controller und Sub-Controller und auf Top-Ebene End-To-End Tests implementiert.

Als Simulator verwenden wir **Verilator** oder **Icarus Verilog**. Die Tests werden lokal oder über die CI/CD-Pipelines ausgeführt.

In den Modul-Tests mussten keine externen Packages integriert werden. Es konnte der Icarus-Verilog Simulator zur Durchführung der Tests verwendet werden.
Bei dem Top-Level End-To-End Test mussten OBI-Packages für das OBI-Protokoll integriert werden, welche Structs beinhalten. 
Zur Verarbeitung dieser Packages wurde der komplextere Simulator Verilator verwendet.

## End-to-End Test (`test_redis_cache.py`)

Der zentrale Bestandteil der Verifikation ist der Top-Level-Test `test_redis_cache.py`. Dieser Test instanziiert das Modul `redis_cache`, in dem alle Sub-Komponenten (`obi_interface`, `controller`, `memory_block`) bereits miteinander verbunden sind.

Dieser Test stellt einen **End-to-End (Integrationstest)** dar. 
Es werden ausschließlich Daten über das OBI-Interface mit dem OBI-Bus verschickt und empfangen und geprüft, ob die darunterliegenden Module sich richtig verhalten.

### Funktionsweise

Die Python-Testbench fungiert hierbei als OBI-Master (z.B. eine CPU). Sie sendet OBI-Requests (Adressen, Daten, Kontrollsignale) an das Interface und wertet die Responses aus.

Der Ablauf einer Operation im Test spiegelt exakt den Ablauf wider, den ein Software-Treiber auf der echten Hardware durchführen würde:

1.  **Daten schreiben:** Key und Value werden an die entsprechenden Register-Adressen des Interfaces gesendet.
2.  **Kommando senden:** Der Opcode (GET, UPSERT, DELETE) wird in das Control-Register geschrieben.
3.  **Warten:** Die Testbench wartet, bis der Controller den `IDLE`-Zustand verlässt und nach Abschluss der Operation wieder dorthin zurückkehrt.
4.  **Verifikation:** Das Ergebnis (z.B. gelesene Daten oder Status-Bits) wird überprüft.

### Code-Beispiel: Ausführen einer Operation

Die Hilfsfunktion `execute_cache_operation` in der Testbench abstrahiert das Setzen der Register:

```python
async def execute_cache_operation(dut, tester, operation, key, value=0):
    # 1. Value Register schreiben (nur bei UPSERT nötig)
    if operation == 'UPSERT':
        await obi_write(dut, addr=0, wdata=value)
        
    # 2. Key Register schreiben (Adresse 8)
    await obi_write(dut, addr=8, wdata=key)
    
    # 3. Kommando im Control-Register absetzen (Adresse 12)
    # Opcode wird geshiftet, da Bits [3:1] für Opcode genutzt werden
    op_code = get_opcode(operation)
    await obi_write(dut, addr=12, wdata=(op_code << 1), be=1)
    
    # 4. Warten bis Controller fertig ist (Polling auf State 0/IDLE)
    while int(tester.u_ctrl.state.value) != 0:
        await tester.wait_cycles(1)
```

Die Hilfsfunktion `obi_write` ersellt die OBI Nachricht und führt den Handshake durch.

```python
async def obi_write(dut, addr, wdata, be=0xF):
    dut.obi_req_i.value = pack_obi_req(addr=addr, we=1, be=be, wdata=wdata, req=1)

    # Warten auf das Grant-Signal (Handshake)
    while True:
        await RisingEdge(dut.clk)
        resp_val = int(dut.obi_resp_o.value)
        gnt_bit = (resp_val >> 1) & 1 
        if gnt_bit == 1:
            break
            
    # Request wieder auf 0 ziehen
    dut.obi_req_i.value = pack_obi_req()
    await RisingEdge(dut.clk)

```

### Analyse

Die während der tests aufgezeichneten Informationen Signale werden aufgezeichnet und können im Nachgang analysiert werden.
Folgende Grafik zeigt die aufgezeichneten Signale eines Upserts in einen leeren Cache.

TODO: Bild hinzufügen