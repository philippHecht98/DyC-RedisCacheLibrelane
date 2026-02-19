# AXI4-Lite Timing Diagrams for Cache Interface

This document shows clock-level timing for the AXI4-Lite interface implementation in `src/interface/src/interface.sv`.

## AXI Write Transaction (Single Register Write)

```
Clock Cycle:      0    1    2    3    4    5    6    7
                ┌────┬────┬────┬────┬────┬────┬────┬────┐
clk             │  __│█████│____│█████│____│█████│____│█████
                └────┴────┴────┴────┴────┴────┴────┴────┘

AW Channel (Write Address):
awaddr          ──────<0x00>────────────────────────────────  // Address latched in cycle 1
awvalid         ────██████████──────────────────────────────  // Master asserts valid
awready         ────────────██████──────────────────────────  // Slave accepts (cycle 2)

W Channel (Write Data):
wdata           ──────────<0x01>────────────────────────────  // Data presented
wvalid          ──────────██████████────────────────────────  // Master asserts valid
wready          ────────────────██████──────────────────────  // Slave accepts (cycle 3)

B Channel (Write Response):
bresp           ──────────────────<00>────<XX>──────────────  // OKAY response
bvalid          ──────────────────██████████────────────────  // Slave asserts valid (cycle 4)
bready          ──────────────────────██████────────────────  // Master ready (cycle 5)

Internal Signals:
aw_latched      ────────────████████████────────────────────  // Address latched in cycle 2
op_written      ────────────────────██──────────────────────  // Pulse when write completes
```

### Detailed Behavior:

1. **Cycle 0-1**: Master presents write address (0x00 for operation register)
2. **Cycle 2**: Slave accepts address (`awready`), latches it internally
3. **Cycle 2-3**: Master presents write data, slave asserts `wready`
4. **Cycle 3**: Both valid signals high → write completes, data stored in `op_reg`
5. **Cycle 4**: Slave responds with `bvalid` (response = OKAY)
6. **Cycle 5**: Master accepts response with `bready`, transaction complete
7. **Cycle 3-4**: `op_written` pulse triggers FSM state transition

---

## AXI Read Transaction (Single Register Read)

```
Clock Cycle:      0    1    2    3    4    5    6
                ┌────┬────┬────┬────┬────┬────┬────┐
clk             │  __│█████│____│█████│____│█████│____
                └────┴────┴────┴────┴────┴────┴────┘

AR Channel (Read Address):
araddr          ──────<0x0C>────────────────────────  // Status register address
arvalid         ────██████████──────────────────────  // Master asserts valid
arready         ────────────██████──────────────────  // Slave accepts (cycle 2)

R Channel (Read Data):
rdata           ──────────────<0x09>────<XX>────────  // Status value returned
rresp           ──────────────<00>──────<XX>────────  // OKAY response
rvalid          ──────────────██████████────────────  // Slave asserts valid (cycle 3)
rready          ──────────────────██████────────────  // Master ready (cycle 4)
```

### Detailed Behavior:

1. **Cycle 1**: Master presents read address (0x0C for status register)
2. **Cycle 2**: Slave accepts address with `arready`
3. **Cycle 3**: Slave looks up register value and presents on `rdata`, asserts `rvalid`
4. **Cycle 4**: Master accepts data with `rready`, read transaction complete

**Key Point**: Read is faster (4 cycles) because there's no separate response channel.

---

## Complete Cache Operation Flow

```
Clock Cycle:      0    1    2    3    4    5    6    7    8    9   10   11   12
                ┌────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┐
clk             │  __│█████│____│█████│____│█████│____│█████│____│█████│____│█████│____
                └────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┘

FSM State:
fsm_state       ──<IDLE>──────────<EXEC><WAIT──────────────────────────><COMP>──────
                                                                         

CPU Writes OP:  ──────<Write AXI Transaction>──────
op_written      ────────────────────██──────────────────────────────────────────────

Controller Interface:
start_out       ──────────────────────────██────────────────────────────────────────  // 1 cycle pulse
done_in         ──────────────────────────────────────────────────────██────────────  // Controller done
hit_in          ──────────────────────────────────────────────────────<1>────────────
result_value_in ──────────────────────────────────────────────────────<DATA>─────────

Status Register:
status_done     ────────────────────────────────────────────────────────████████████  // Set when complete
status_hit      ────────────────────────────────────────────────────────████████████  // Latched hit result
```

### FSM State Transitions:

1. **IDLE (Cycles 0-3)**: Waiting for CPU to write operation register
2. **Write Transaction (Cycles 1-5)**: AXI write to operation register completes
3. **Cycle 4**: `op_written` pulse triggers state change
4. **EXECUTE (Cycle 5)**: FSM pulses `start_out` for one cycle to controller
5. **WAIT (Cycles 6-10)**: Waiting for controller to complete cache operation
6. **Cycle 11**: Controller asserts `done_in`, results latched into result registers
7. **COMPLETE (Cycle 12+)**: Results available, CPU can read status/results
8. **Next Operation**: Another write to operation register returns to EXECUTE

---

## AXI Protocol Key Principles

### 1. Handshake Protocol
Every AXI channel uses a **valid/ready handshake**:
- **Valid**: Asserted by the source when data is available
- **Ready**: Asserted by the destination when it can accept data
- **Transfer occurs**: When both `valid` AND `ready` are HIGH on the same clock edge

### 2. Independent Channels
- Write address, write data, and write response are independent
- Can be optimized: data can arrive before/after address
- This implementation latches address first, then accepts data

### 3. Response Codes
- `2'b00` (OKAY): Normal success
- `2'b01` (EXOKAY): Exclusive access okay
- `2'b10` (SLVERR): Slave error
- `2'b11` (DECERR): Decode error

### 4. This Implementation's Approach
- **Sequential write**: Address must be latched before data accepted (simpler logic)
- **Pipelined read**: Single-cycle address lookup
- **Register-triggered**: Writing to operation register triggers cache controller
- **Polling-based**: Software polls status register for completion

---

## Register Map Overview

| Address | Name            | Access | Description                              |
|---------|-----------------|--------|------------------------------------------|
| 0x00    | op_reg          | W      | Operation code (triggers transaction)    |
| 0x04    | key_reg         | W      | Cache key                                |
| 0x08+   | value_regs[N]   | W      | Value data (multi-word)                  |
| varies  | status_reg      | R      | {fsm_state[1:0], error, hit, done}       |
| varies  | result_regs[N]  | R      | Result value from cache (multi-word)     |
| varies  | result_index    | R      | Matching cache entry index               |

**Note**: Register addresses scale based on VALUE_WIDTH and ARCHITECTURE parameters.

---

## Timing Constraints

### Setup Time Requirements:
- Master must hold `awaddr` stable when `awvalid` is asserted
- Master must hold `wdata` stable when `wvalid` is asserted
- Slave must hold `rdata` stable when `rvalid` is asserted

### Hold Time Requirements:
- Signals must remain stable after clock edge until `ready` signal seen

### Latency:
- **Write**: 5-6 cycles (AW → W → B handshakes)
- **Read**: 4 cycles (AR → R handshake)
- **Cache Operation**: Variable (depends on cache controller + memory access time)

