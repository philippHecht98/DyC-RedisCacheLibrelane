# Cache Interface Module

## Overview

The cache interface module bridges the CPU bus to the internal Redis cache controller. It provides a memory-mapped register interface that allows software to issue cache operations (READ, CREATE, UPDATE, DELETE) and read back results.

Two interface variants are provided:

| File | Bus Protocol | Use Case |
|---|---|---|
| `interface.sv` | AXI4-Lite | Generic SoC integration |
| `interface_croc.sv` | OBI (v1.6) | CROC RISC-V SoC integration |

## Register Map

Both variants share the same register layout (32-bit word-addressed):

| Offset | Name | R/W | Description |
|--------|------|-----|-------------|
| `0x00` | `op_reg` | W | Operation code (NOOP=0, READ=1, CREATE=2, UPDATE=3, DELETE=4) |
| `0x04` | `key_reg` | W | Cache key (lower KEY_WIDTH bits used) |
| `0x08` | `value_regs[0]` | W | Value bits [31:0] |
| `0x0C` | `value_regs[1]` | W | Value bits [63:32] *(only if VALUE_WIDTH > 32)* |
| `0x10` | `status_reg` | R | `{fsm_state[4:3], error[2], hit[1], done[0]}` |
| `0x14` | `result_regs[0]` | R | Result bits [31:0] |
| `0x18` | `result_regs[1]` | R | Result bits [63:32] *(only if VALUE_WIDTH > 32)* |

## Software Operation Flow

1. Write the key to `key_reg` (offset `0x04`)
2. For write operations: write value word(s) to `value_regs` (offset `0x08`+)
3. Write the operation code to `op_reg` (offset `0x00`) — **this triggers execution**
4. Poll `status_reg` (offset `0x10`) until `done` bit (bit 0) is set
5. Read `result_regs` (offset `0x14`+) for the result value

---

## Integrating with CROC

The [CROC SoC](https://github.com/pulp-platform/croc) provides a **User Domain** specifically designed for custom peripherals. The cache interface connects as an OBI subordinate in this domain.

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│  CROC SoC (croc_soc.sv)                                │
│                                                         │
│  ┌──────────┐    ┌───────────┐    ┌──────────────────┐  │
│  │ CVE2     │    │  OBI      │    │  User Domain     │  │
│  │ RISC-V   ├───►│  Crossbar ├───►│  (user_domain.sv)│  │
│  │ Core     │    │  (xbar)   │    │                  │  │
│  └──────────┘    └───────────┘    │  ┌─────────────┐ │  │
│                                   │  │ OBI Demux   │ │  │
│                                   │  └──────┬──────┘ │  │
│                                   │         │        │  │
│                                   │  ┌──────▼──────┐ │  │
│                                   │  │ cache_      │ │  │
│                                   │  │ interface_  │ │  │
│                                   │  │ croc        │ │  │
│                                   │  └──────┬──────┘ │  │
│                                   │         │        │  │
│                                   │  ┌──────▼──────┐ │  │
│                                   │  │ Redis Cache │ │  │
│                                   │  │ Controller  │ │  │
│                                   │  └─────────────┘ │  │
│                                   └──────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Step 1: Replace the Placeholder in `user_domain.sv`

CROC's `rtl/user_domain.sv` has a placeholder `obi_err_sbr` labeled `i_your_design_goes_here`. Replace it with the cache interface and controller:

```systemverilog
// In user_domain.sv — replace the placeholder obi_err_sbr with:

// Wires between interface and controller
operation_e              cache_operation;
logic [15:0]             cache_key;
logic [63:0]             cache_value;
logic                    cache_start;
logic [63:0]             cache_result;
logic                    cache_hit;
logic                    cache_done;

cache_interface_croc #(
    .KEY_WIDTH    ( 16 ),
    .VALUE_WIDTH  ( 64 ),
    .ARCHITECTURE ( 32 )
) i_cache_interface (
    .clk_i          ( clk_i                ),
    .rst_ni         ( rst_ni               ),

    // OBI subordinate port (from CROC crossbar)
    .obi_req_i      ( user_design_obi_req  ),
    .obi_rsp_o      ( user_design_obi_rsp  ),

    // Controller-facing ports
    .operation_out  ( cache_operation       ),
    .key_out        ( cache_key             ),
    .value_out      ( cache_value           ),
    .start_out      ( cache_start           ),
    .result_value_in( cache_result          ),
    .hit_in         ( cache_hit             ),
    .done_in        ( cache_done            )
);

// Instantiate the cache controller
controller i_cache_ctrl (
    .clk            ( clk_i            ),
    .rst_n          ( rst_ni           ),
    .operation_in   ( cache_operation  ),
    .key_in         ( cache_key        ),
    .value_in       ( cache_value      ),
    .start_in       ( cache_start      ),
    .result_value   ( cache_result     ),
    .hit            ( cache_hit        ),
    .done           ( cache_done       )
);
```

### Step 2: Address Map Configuration

The cache interface is accessible in the **User Domain** address range. By default in CROC, this is:

| Region | Start Address | End Address |
|--------|---------------|-------------|
| User Domain | `0x2000_0000` | `0x8000_0000` |

The `user_pkg.sv` maps the first subordinate (`UserDesign`) to the full user region. The cache registers will be at:

| Register | Address |
|----------|---------|
| `op_reg` | `0x2000_0000` |
| `key_reg` | `0x2000_0004` |
| `value_regs[0]` | `0x2000_0008` |
| `value_regs[1]` | `0x2000_000C` |
| `status_reg` | `0x2000_0010` |
| `result_regs[0]` | `0x2000_0014` |
| `result_regs[1]` | `0x2000_0018` |

If you want a custom base address (e.g., `0x2000_1000`), edit `user_pkg.sv`:

```systemverilog
localparam croc_pkg::addr_map_rule_t [0:0] user_addr_map = '{
    '{ idx: UserDesign,
       start_addr: croc_pkg::UserBaseAddr + 32'h0000_1000,
       end_addr:   croc_pkg::UserBaseAddr + 32'h0000_2000 }
};
```

### Step 3: C Software Access

From the RISC-V core running on CROC, access the cache via memory-mapped I/O:

```c
#include <stdint.h>

#define CACHE_BASE      0x20000000

#define CACHE_OP        (*(volatile uint32_t *)(CACHE_BASE + 0x00))
#define CACHE_KEY       (*(volatile uint32_t *)(CACHE_BASE + 0x04))
#define CACHE_VAL0      (*(volatile uint32_t *)(CACHE_BASE + 0x08))
#define CACHE_VAL1      (*(volatile uint32_t *)(CACHE_BASE + 0x0C))
#define CACHE_STATUS    (*(volatile uint32_t *)(CACHE_BASE + 0x10))
#define CACHE_RES0      (*(volatile uint32_t *)(CACHE_BASE + 0x14))
#define CACHE_RES1      (*(volatile uint32_t *)(CACHE_BASE + 0x18))

// Operation codes (from ctrl_types_pkg)
#define OP_NOOP   0
#define OP_READ   1
#define OP_CREATE 2
#define OP_UPDATE 3
#define OP_DELETE 4

// Status register bits
#define STATUS_DONE  (1 << 0)
#define STATUS_HIT   (1 << 1)
#define STATUS_ERROR (1 << 2)

static inline void cache_wait_done(void) {
    while (!(CACHE_STATUS & STATUS_DONE));
}

// Example: PUT a 64-bit value
void cache_put(uint16_t key, uint64_t value) {
    CACHE_KEY  = key;
    CACHE_VAL0 = (uint32_t)(value);
    CACHE_VAL1 = (uint32_t)(value >> 32);
    CACHE_OP   = OP_CREATE;       // triggers execution
    cache_wait_done();
}

// Example: GET a 64-bit value
uint64_t cache_get(uint16_t key, int *hit) {
    CACHE_KEY = key;
    CACHE_OP  = OP_READ;          // triggers execution
    cache_wait_done();

    *hit = (CACHE_STATUS & STATUS_HIT) ? 1 : 0;
    return ((uint64_t)CACHE_RES1 << 32) | CACHE_RES0;
}
```

### Step 4: File Dependencies

Add these source files to your build (Bender.yml, Makefile, or Flist):

```
# Packages (must be compiled first)
src/interface/src/if_types_pkg.sv
src/controller/src/ctrl_types_pkg.sv

# CROC OBI interface
src/interface/src/interface_croc.sv

# Controller + memory
src/controller/src/controller.sv
src/memory/src/memory_block.sv
```

### OBI vs AXI4-Lite: Key Differences

| Feature | AXI4-Lite (`interface.sv`) | OBI (`interface_croc.sv`) |
|---------|---------------------------|--------------------------|
| Handshake | 5 independent channels (AW, W, B, AR, R) | 2 phases: A (req/gnt) + R (rvalid) |
| Write | Separate address + data phases | Single req with addr + wdata together |
| Read | Separate address + data phases | Single req, response next cycle |
| Complexity | Higher (multi-channel state machine) | Lower (simple req/gnt + 1-cycle response) |
| Backpressure | Per-channel ready/valid | gnt controls A channel |
| Use case | ARM-based SoCs, generic | RISC-V (CROC, PULP Platform) |
