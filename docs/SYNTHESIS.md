# Redis Cache Hardware - Synthesis Guide

## Overview

This document provides guidance for synthesizing the Redis cache hardware design for ASIC or FPGA targets.

## Design Files

The core design consists of the following Verilog files (in compilation order):

1. `src/memory/memory_cell.v` - Individual cache cell with TTL
2. `src/memory/memory_block.v` - Array of cache cells  
3. `src/interface/memory_interface.v` - Memory access interface
4. `src/core/fsm_controller.v` - Command processing FSM
5. `src/redis_cache_top.v` - Top-level integration module

## Synthesis for FPGA (Xilinx Vivado)

### Create Project via GUI

1. Open Vivado
2. Create new RTL project
3. Add all source files from `src/` directory in the order listed above
4. Set `redis_cache_top` as the top module
5. Select target FPGA device
6. Run Synthesis
7. Review reports for timing, utilization, and power

### Synthesis via TCL Script

```tcl
# Read design files
read_verilog src/memory/memory_cell.v
read_verilog src/memory/memory_block.v
read_verilog src/interface/memory_interface.v
read_verilog src/core/fsm_controller.v
read_verilog src/redis_cache_top.v

# Set top module
set_top redis_cache_top

# Synthesize for target device (example: Artix-7)
synth_design -top redis_cache_top -part xc7a35tcpg236-1

# Generate reports
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
report_power -file power.rpt

# Write outputs
write_checkpoint -force post_synth.dcp
```

## Synthesis for ASIC (Synopsys Design Compiler)

### Basic Synthesis Script

```tcl
# Set target library
set target_library "your_tech_library.db"
set link_library "* $target_library"

# Read design files
read_verilog src/memory/memory_cell.v
read_verilog src/memory/memory_block.v
read_verilog src/interface/memory_interface.v
read_verilog src/core/fsm_controller.v
read_verilog src/redis_cache_top.v

# Set current design
current_design redis_cache_top

# Link design
link

# Apply constraints (example)
create_clock -name clk -period 10 [get_ports clk]
set_input_delay -clock clk 2 [all_inputs]
set_output_delay -clock clk 2 [all_outputs]

# Compile
compile_ultra

# Generate reports
report_area > area.rpt
report_timing > timing.rpt
report_power > power.rpt
report_qor > qor.rpt

# Write outputs
write -format verilog -hierarchy -output synthesized_redis_cache.v
write_sdc redis_cache_constraints.sdc
```

## Design Parameters

The design is parameterized and can be configured for different sizes:

```verilog
redis_cache_top #(
    .NUM_ENTRIES(16),      // Number of cache entries (default: 16)
    .KEY_WIDTH(64),        // Key width in bits (default: 64)
    .VALUE_WIDTH(64),      // Value width in bits (default: 64)
    .TTL_WIDTH(32),        // TTL counter width (default: 32)
    .CMD_WIDTH(8)          // Command opcode width (default: 8)
) instance_name (
    // Port connections...
);
```

## Timing Considerations

### Critical Paths

Likely critical paths to analyze:
1. Hash function calculation in `memory_interface.v`
2. Key comparison logic in `memory_interface.v`
3. FSM state transitions in `fsm_controller.v`
4. TTL decrement logic in `memory_cell.v`

### Clock Constraints

Recommended starting clock period: 10ns (100 MHz)

Adjust based on technology and timing analysis results.

### Reset Strategy

The design uses active-low asynchronous reset (`rst_n`). Ensure proper reset distribution in your target technology.

## Resource Utilization Estimates

For a 16-entry cache with 64-bit keys and values:

**Registers:** ~2000-3000 flip-flops
- Memory cells: ~2560 FFs (16 entries × 160 bits)
- Control logic: ~500 FFs

**Combinational Logic:** ~1000-2000 LUTs
- Hash function
- Key comparison
- FSM logic
- Multiplexers

**Memory:** Can be implemented with:
- Distributed RAM (registers)
- Block RAM (if available and beneficial)

## Verification Recommendations

Before tape-out or FPGA programming:

1. Run lint checks (e.g., with Synopsys SpyGlass or Cadence HAL)
2. Verify all paths meet timing constraints
3. Check for clock domain crossing issues (design is single-clock)
4. Review power estimates
5. Perform equivalence checking between RTL and gate-level netlists

## Future Enhancements

When implementing pipeline architecture:
- Add pipeline registers between stages
- Balance logic depth across stages
- Consider retiming optimizations
- Re-analyze timing with pipelined structure
