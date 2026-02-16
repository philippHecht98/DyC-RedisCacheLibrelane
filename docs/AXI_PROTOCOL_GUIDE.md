# AXI4-Lite Protocol Implementation - Complete Guide

This guide explains the AXI4-Lite slave interface implementation in [src/interface/src/interface.sv](../src/interface/src/interface.sv).

---

## Table of Contents
1. [What is AXI4-Lite?](#what-is-axi4-lite)
2. [High-Level Architecture](#high-level-architecture)
3. [AXI Protocol Fundamentals](#axi-protocol-fundamentals)
4. [Register Map](#register-map)
5. [Write Transaction Flow](#write-transaction-flow)
6. [Read Transaction Flow](#read-transaction-flow)
7. [FSM Operation](#fsm-operation)
8. [Complete Operation Example](#complete-operation-example)
9. [Timing Diagrams](#timing-diagrams)

---

## What is AXI4-Lite?

**AXI4-Lite** is a simplified version of ARM's Advanced eXtensible Interface (AXI) protocol designed for simple memory-mapped register access. It removes the burst capabilities of full AXI, making it ideal for control registers and status/configuration interfaces.

### Key Characteristics:
- **Memory-mapped**: Registers appear at specific memory addresses
- **Single transfers only**: No burst transactions (always 1 data transfer per address)
- **Fixed 32-bit or 64-bit data width**: This implementation uses `ARCHITECTURE` parameter (typically 32)
- **Five independent channels**: Separate paths for different transaction phases
- **Handshake protocol**: Every channel uses valid/ready signaling

---

## High-Level Architecture

```
┌─────────────┐         ┌──────────────────┐         ┌─────────────────┐
│  AXI Master │◄───────►│  Cache Interface │◄───────►│ Cache Controller│
│    (CPU)    │   AXI   │      (This       │  Custom │   & Memory      │
│             │  Slave  │      Module)     │  Logic  │                 │
└─────────────┘         └──────────────────┘         └─────────────────┘

CPU side:              Interface:                     Controller side:
- 5 AXI channels       - Register map                 - start_out
- Read/write access    - Write decode logic           - operation_out
- Memory addresses     - Read mux logic               - key_out, value_out
                       - Transaction FSM              - done_in, hit_in
                                                      - result_value_in
```

---

## AXI Protocol Fundamentals

### The Five Independent Channels

AXI4-Lite separates write and read operations into independent channels that can operate concurrently:

#### Write Operation (3 channels):
1. **Write Address (AW)**: Master → Slave
   - `awaddr`: Target register address
   - `awvalid`, `awready`: Handshake signals

2. **Write Data (W)**: Master → Slave
   - `wdata`: Data to write
   - `wvalid`, `wready`: Handshake signals

3. **Write Response (B)**: Slave → Master
   - `bresp`: Response code (OKAY, SLVERR, etc.)
   - `bvalid`, `bready`: Handshake signals

#### Read Operation (2 channels):
4. **Read Address (AR)**: Master → Slave
   - `araddr`: Target register address
   - `arvalid`, `arready`: Handshake signals

5. **Read Data (R)**: Slave → Master
   - `rdata`: Data read from register
   - `rresp`: Response code
   - `rvalid`, `rready`: Handshake signals

### Handshake Protocol

Every channel uses a **two-way handshake**:

```
        Master                         Slave
          │                             │
          │─────── valid = 1 ────────►  │
          │                             │
          │◄─────── ready = 1 ──────────│
          │                             │
          ▼                             ▼
    Transfer occurs when BOTH valid AND ready are HIGH
```

**Rules:**
- Valid can be asserted before ready
- Ready can be asserted before valid
- Transfer happens on clock edge when both are HIGH
- Source must hold data stable while valid is asserted
- Destination must accept data when ready is asserted

---

## Register Map

The module dynamically generates a register map based on parameters:
- `KEY_WIDTH`: Width of cache keys
- `VALUE_WIDTH`: Width of cache values (can span multiple registers)
- `ARCHITECTURE`: Register width (typically 32 bits)

### Register Layout

| Address | Register          | Access | Bits | Description                                    |
|---------|-------------------|--------|------|------------------------------------------------|
| 0x00    | `op_reg`          | W      | [2:0]| Operation code (GET=0, PUT=1, DEL=2)          |
| 0x04    | `key_reg`         | W      | [KEY_WIDTH-1:0] | Cache key                           |
| 0x08    | `value_regs[0]`   | W      | [31:0] | Value bits [31:0]                            |
| 0x0C    | `value_regs[1]`   | W      | [31:0] | Value bits [63:32] (if VALUE_WIDTH > 32)     |
| ...     | ...               | W      | ...  | Additional value registers as needed           |
| varies  | `status_reg`      | R      | [4:0]| {fsm_state[1:0], error, hit, done}            |
| varies  | `result_regs[0]`  | R      | [31:0] | Result bits [31:0]                            |
| varies  | `result_regs[1]`  | R      | [31:0] | Result bits [63:32] (if VALUE_WIDTH > 32)     |
| ...     | ...               | R      | ...  | Additional result registers                    |

### Status Register Breakdown

```
Bit [4:3] - fsm_state:
    00 = IF_ST_IDLE      (waiting for operation)
    01 = IF_ST_EXECUTE   (starting operation)
    10 = IF_ST_WAIT      (operation in progress)
    11 = IF_ST_COMPLETE  (operation done, results ready)

Bit [2] - status_error:  Error occurred during operation
Bit [1] - status_hit:    Cache hit (for GET operations)
Bit [0] - status_done:   Operation complete (ready to read results)
```

---

## Write Transaction Flow

### Clock-Level Sequence

```
Cycle:    1         2         3         4         5
        ┌─────┬─────┬─────┬─────┬─────┐
clk     │  ↑  │  ↑  │  ↑  │  ↑  │  ↑  │
        └─────┴─────┴─────┴─────┴─────┘

Master presents      Slave        Write       Slave      Master
write address     accepts addr   completes   responds   accepts
    (awvalid)       (awready)    (wvalid &    (bvalid)   (bready)
                                  wready)
```

### Detailed Steps

1. **Master drives address** (Cycle 1):
   - Asserts `awvalid = 1`
   - Presents `awaddr` (e.g., 0x00 for operation register)

2. **Slave latches address** (Cycle 2):
   - Sees `awvalid = 1`, asserts `awready = 1`
   - Internally latches `awaddr` into `aw_addr_latched`
   - Sets `aw_latched = 1` flag

3. **Master drives data** (Cycles 2-3):
   - Presents `wdata` (e.g., operation code)
   - Asserts `wvalid = 1`

4. **Slave accepts data** (Cycle 3):
   - Sees `aw_latched = 1`, asserts `wready = 1`
   - When both `wvalid` and `wready` are HIGH:
     - Decodes address and writes data to target register
     - If writing to `op_reg` (address 0x00), pulses `op_written = 1`

5. **Slave sends response** (Cycle 4):
   - Asserts `bvalid = 1`
   - Sets `bresp = 2'b00` (OKAY)

6. **Master acknowledges** (Cycle 5):
   - Asserts `bready = 1`
   - Transaction complete, slave deasserts `bvalid`

### Key Implementation Details

```systemverilog
// Address latching (prevents race conditions)
if (s_axi_awvalid && !aw_latched) begin
    s_axi_awready   <= 1'b1;
    aw_addr_latched <= s_axi_awaddr;  // Latch address
    aw_latched      <= 1'b1;          // Remember we latched it
end

// Data write (only when address is latched)
if (s_axi_wvalid && s_axi_wready) begin
    if (wr_addr_idx == ADDR_OP) begin
        op_reg     <= s_axi_wdata;
        op_written <= 1'b1;  // Pulse to FSM
    end
    // ... other register writes ...
end
```

---

## Read Transaction Flow

### Clock-Level Sequence

```
Cycle:    1         2         3         4
        ┌─────┬─────┬─────┬─────┐
clk     │  ↑  │  ↑  │  ↑  │  ↑  │
        └─────┴─────┴─────┴─────┘

Master presents    Slave      Slave       Master
read address     accepts    responds    accepts
  (arvalid)      (arready)   (rvalid)    (rready)
                            + rdata
```

### Detailed Steps

1. **Master drives address** (Cycle 1):
   - Asserts `arvalid = 1`
   - Presents `araddr` (e.g., address of status register)

2. **Slave accepts address** (Cycle 2):
   - Sees `arvalid = 1`, asserts `arready = 1`
   - Decodes address immediately (combinational logic)

3. **Slave responds with data** (Cycle 3):
   - Multiplexes correct register onto `rdata` based on decoded address
   - Asserts `rvalid = 1`
   - Sets `rresp = 2'b00` (OKAY)

4. **Master accepts data** (Cycle 4):
   - Asserts `rready = 1`
   - Samples `rdata`
   - Transaction complete

### Key Implementation Details

```systemverilog
// Single-cycle address decode and response
if (s_axi_arvalid && s_axi_arready) begin
    if (rd_addr_idx == ADDR_STATUS)
        s_axi_rdata <= status_reg;
    // ... check other registers ...
    
    s_axi_rvalid <= 1'b1;
    s_axi_rresp  <= 2'b00;
end
```

**Performance Note**: Read is faster than write (4 cycles vs 6 cycles) because there's no separate response channel.

---

## FSM Operation

The Transaction FSM bridges AXI register writes to controller operations.

### State Diagram

See [axi_fsm_states.mermaid](axi_fsm_states.mermaid) for visual diagram.

### State Descriptions

#### 1. IF_ST_IDLE (2'b00)
**Purpose**: Wait for CPU to initiate an operation

**Behavior**:
- `start_out = 0`
- `status_done = 0`
- Monitors `op_written` signal

**Transition**:
- When `op_written = 1` → **IF_ST_EXECUTE**

**Code**:
```systemverilog
IF_ST_IDLE: begin
    start_out    <= '0;
    status_done  <= '0;
    if (op_written)
        fsm_state <= IF_ST_EXECUTE;
end
```

---

#### 2. IF_ST_EXECUTE (2'b01)
**Purpose**: Trigger the cache controller

**Behavior**:
- Pulses `start_out = 1` for exactly **one clock cycle**
- Signals controller to begin operation using current register values

**Transition**:
- Unconditional (next cycle) → **IF_ST_WAIT**

**Code**:
```systemverilog
IF_ST_EXECUTE: begin
    start_out <= 1'b1;  // Single-cycle pulse
    fsm_state <= IF_ST_WAIT;
end
```

**Critical**: This is a single-cycle state that provides a clean edge-triggered start signal.

---

#### 3. IF_ST_WAIT (2'b10)
**Purpose**: Wait for cache controller to complete operation

**Behavior**:
- `start_out = 0` (pulse ended)
- Controller performs:
  - Memory access (tag array, data array)
  - Tag comparison
  - Data retrieval (on hit)
  - Cache line allocation (on miss for PUT)

**Transition**:
- When `done_in = 1` → **IF_ST_COMPLETE**

**Code**:
```systemverilog
IF_ST_WAIT: begin
    start_out <= '0;
    if (done_in) begin
        // Latch results from controller
        for (int i = 0; i < NUM_VAL_REGS; i++)
            result_regs[i] <= result_value_in[...];
        status_hit       <= hit_in;
        status_done      <= 1'b1;
        fsm_state        <= IF_ST_COMPLETE;
    end
end
```

---

#### 4. IF_ST_COMPLETE (2'b11)
**Purpose**: Hold results until CPU reads them

**Behavior**:
- `status_done = 1` (CPU can see operation is complete)
- All result registers stable and readable:
  - `result_regs[]` contains cache data
  - `status_hit` indicates hit/miss

**Transition**:
- When `op_written = 1` (CPU starts next operation) → **IF_ST_EXECUTE**

**Code**:
```systemverilog
IF_ST_COMPLETE: begin
    if (op_written) begin
        status_done  <= '0;
        status_hit   <= '0;
        fsm_state    <= IF_ST_EXECUTE;
    end
end
```

**Design Choice**: CPU can immediately start a new operation by writing to `op_reg`, bypassing IDLE state.

---

## Complete Operation Example

Let's trace a **GET operation** (read from cache) from start to finish.

### Phase 1: Setup Key (3-6 cycles)

```
CPU → AXI Write to key_reg (0x04):
  1. awaddr=0x04, awvalid=1
  2. awready=1 (slave accepts address)
  3. wdata=0x1234, wvalid=1
  4. wready=1, write completes
  5. bvalid=1, bresp=OKAY
  6. bready=1, transaction done

Result: key_reg = 0x1234
```

### Phase 2: Trigger Operation (6 cycles)

```
CPU → AXI Write to op_reg (0x00):
  1. awaddr=0x00, awvalid=1
  2. awready=1
  3. wdata=0x00 (GET), wvalid=1
  4. wready=1, write completes
     → op_written = 1 (pulse)
     → FSM: IDLE → EXECUTE
  5. bvalid=1
  6. bready=1

Result: op_reg = 0x00, operation_out = GET
```

### Phase 3: Controller Execution (Variable)

```
Cycle N:   FSM in EXECUTE state
           start_out = 1 (pulse to controller)
           FSM → WAIT

Cycle N+1: Controller begins operation
           - Hashes key (0x1234)
           - Accesses tag memory
           - Compares tags
           - Reads data array (if hit)

Cycle N+X: Controller completes
           done_in = 1
           hit_in = 1 (assuming cache hit)
           result_value_in = 0xDEADBEEF_CAFEBABE

           FSM latches results:
           result_regs[0] = 0xCAFEBABE
           result_regs[1] = 0xDEADBEEF
           status_hit = 1
           status_done = 1
           FSM → COMPLETE
```

### Phase 4: Poll for Completion

```
CPU → AXI Read from status_reg:
  Loop:
    1. araddr=STATUS_ADDR, arvalid=1
    2. arready=1
    3. rdata=status_reg, rvalid=1
       Read bits: done=1, hit=1, fsm_state=COMPLETE
    4. rready=1, transaction done
    
    Check: Is done bit set? YES → Exit loop
```

### Phase 5: Read Results (4 cycles per register)

```
CPU → AXI Read from result_regs[0]:
  1. araddr=RESULT_BASE, arvalid=1
  2. arready=1
  3. rdata=0xCAFEBABE, rvalid=1
  4. rready=1

CPU → AXI Read from result_regs[1]:
  1. araddr=RESULT_BASE+4, arvalid=1
  2. arready=1
  3. rdata=0xDEADBEEF, rvalid=1
  4. rready=1

Reconstructed value: 0xDEADBEEF_CAFEBABE
```

---

## Timing Diagrams

For detailed clock-level timing diagrams, see:
- [AXI_TIMING_DIAGRAMS.md](AXI_TIMING_DIAGRAMS.md) - ASCII timing diagrams
- [axi_timing_sequence.mermaid](axi_timing_sequence.mermaid) - Visual sequence diagram
- [axi_fsm_states.mermaid](axi_fsm_states.mermaid) - FSM state diagram

---

## Design Decisions & Trade-offs

### 1. Sequential Write Address/Data

**Choice**: Address must be latched before data is accepted.

**Pros**:
- Simpler logic
- No address/data race conditions
- Easier to verify

**Cons**:
- Slightly higher latency (but AXI4-Lite allows this)
- Can't overlap address and data channels

**Alternative**: Full AXI allows address/data to arrive in any order, requiring more complex buffering.

---

### 2. Polling-Based Completion

**Choice**: CPU polls `status_reg` until `done` bit is set.

**Pros**:
- Simple hardware (no interrupt controller needed)
- CPU has full control of timing
- Works in any system (interrupts not required)

**Cons**:
- CPU wastes cycles polling
- Higher software latency

**Alternative**: Add interrupt output (`irq_out`) asserted when `done_in` arrives. Would require additional interrupt controller integration.

---

### 3. Single-Cycle Start Pulse

**Choice**: `start_out` is HIGH for exactly one clock cycle.

**Pros**:
- Clean edge-triggered semantics for controller
- No ambiguity about when operation starts
- Controller doesn't need to track "busy" state

**Cons**:
- Requires EXECUTE state (can't pulse directly from IDLE)

**Alternative**: Level-triggered `start_out`, held HIGH until `done_in`. More complex (controller must ignore `start_out` while busy).

---

### 4. Direct Register Mapping

**Choice**: CPU-writable registers (`op_reg`, `key_reg`, `value_regs`) are directly wired to controller.

**Pros**:
- Zero-latency data propagation
- Simple, easy to debug

**Cons**:
- Registers can change while controller is busy (if software misbehaves)

**Mitigation**: Well-defined software protocol (don't write registers during operation). Could add register locking in future.

---

## Performance Analysis

### Latency Breakdown (assuming 32-bit data, 100 MHz clock)

| Phase | Operation | Cycles | Time @ 100MHz |
|-------|-----------|--------|---------------|
| 1 | Write key register | 6 | 60 ns |
| 2 | Write value registers (N words) | 6N | 60N ns |
| 3 | Write operation register | 6 | 60 ns |
| 4 | Controller execution | Variable | Depends on cache |
| 5 | Poll status (assume 2 reads) | 8 | 80 ns |
| 6 | Read results (N words) | 4N | 40N ns |
| 7 | Read metadata | 4 | 40 ns |

**Total AXI overhead**: ~24 + 10N cycles (ignoring controller time)

**Example** (64-bit value = N=2):
- AXI overhead: 44 cycles = 440 ns @ 100 MHz
- Controller time: ~5-20 cycles (depending on cache implementation)
- **Total**: ~50-65 cycles = 500-650 ns

**Bottleneck**: Usually cache memory access, not AXI interface.

---

## Common Pitfalls & Debugging Tips

### 1. Handshake Violations

**Problem**: Master assumes slave is always ready, writes data without checking `wready`.

**Symptom**: Data lost, silent failures.

**Fix**: Always check both `valid` AND `ready` before assuming transfer occurred.

---

### 2. Address Alignment

**Problem**: Writing to unaligned address (e.g., 0x01 instead of 0x00).

**Symptom**: Write appears to succeed, but wrong register is updated.

**Fix**: This implementation uses word addressing (`addr[31:2]`), ignoring lower 2 bits. Software must ensure 4-byte alignment.

---

### 3. Read-After-Write Hazard

**Problem**: Reading status register immediately after writing operation register.

**Symptom**: Reads stale data (done=0 from previous operation).

**Fix**: Allow at least 1 cycle for FSM to transition. Better: poll until state changes.

---

### 4. Value Register Ordering

**Problem**: Multi-word values written in wrong order.

**Symptom**: Value appears byte-swapped or mangled.

**Fix**: 
- `value_regs[0]` = bits [31:0] (LSW)
- `value_regs[1]` = bits [63:32] (MSW)
- Software must write LSW first, then MSW

---

### 5. FSM Stuck in WAIT

**Problem**: Controller never asserts `done_in`.

**Symptom**: Status register shows state=WAIT forever.

**Debug**:
1. Check controller is receiving `start_out` pulse
2. Verify controller's internal FSM isn't stuck
3. Check memory interface isn't deadlocked
4. Add timeout in software

---

## Extending the Interface

### Adding Interrupts

To add interrupt support:

1. **Add output port**:
   ```systemverilog
   output logic irq_out
   ```

2. **Assert in FSM**:
   ```systemverilog
   IF_ST_WAIT: begin
       if (done_in) begin
           irq_out <= 1'b1;  // Interrupt CPU
           // ... latch results ...
       end
   end
   ```

3. **Clear on status read**:
   ```systemverilog
   if (s_axi_arvalid && rd_addr_idx == ADDR_STATUS)
       irq_out <= 1'b0;  // Reading status clears interrupt
   ```

---

### Adding Write Strobes

AXI4-Lite supports byte-level write strobes (`wstrb`) for partial register updates:

1. **Add input port**:
   ```systemverilog
   input logic [ARCHITECTURE/8-1:0] s_axi_wstrb
   ```

2. **Use in decode**:
   ```systemverilog
   if (s_axi_wvalid && s_axi_wready) begin
       for (int i = 0; i < ARCHITECTURE/8; i++) begin
           if (s_axi_wstrb[i])
               op_reg[i*8 +: 8] <= s_axi_wdata[i*8 +: 8];
       end
   end
   ```

---

### Adding More Registers

To add a new register (e.g., `timeout_reg`):

1. **Update local parameters**:
   ```systemverilog
   localparam ADDR_TIMEOUT = ADDR_RES_IDX + 1;
   localparam NUM_REGS = ADDR_TIMEOUT + 1;
   ```

2. **Declare register**:
   ```systemverilog
   logic [ARCHITECTURE-1:0] timeout_reg;
   ```

3. **Add to write decode**:
   ```systemverilog
   if (wr_addr_idx == ADDR_TIMEOUT)
       timeout_reg <= s_axi_wdata;
   ```

4. **Add to read mux**:
   ```systemverilog
   if (rd_addr_idx == ADDR_TIMEOUT)
       s_axi_rdata <= timeout_reg;
   ```

---

## Conclusion

This AXI4-Lite implementation provides a clean, memory-mapped interface between a CPU and a cache controller. Key features:

✅ **Standard protocol**: Compatible with any AXI4-Lite master  
✅ **Parameterized**: Scales with cache size and data widths  
✅ **Simple FSM**: Clear operation sequencing  
✅ **Low latency**: Minimal overhead beyond memory access  
✅ **Easy to extend**: Add registers, interrupts, or DMA

The design prioritizes **simplicity and correctness** over maximum performance, making it ideal for embedded systems where ease of verification is critical.

---

## References

- [ARM AMBA AXI Protocol Specification](https://developer.arm.com/architectures/system-architectures/amba)
- [AXI_TIMING_DIAGRAMS.md](AXI_TIMING_DIAGRAMS.md) - Detailed timing waveforms
- [interface.sv](../src/interface/src/interface.sv) - Source code
- [ARCHITECTURE.md](ARCHITECTURE.md) - Overall system architecture

