# Redis Cache Hardware Acceleration - Architecture Documentation

## Overview

This repository contains a Redis-like hardware acceleration design targeting ASIC implementation. The design provides a high-performance key-value cache with Time-To-Live (TTL) support, suitable for hardware acceleration of Redis operations.

## System Architecture

### Base Modules

The design is built from the following core building blocks:

1. **Memory Cell** (`src/memory/memory_cell.v`)
   - Basic building block of the cache
   - Contains:
     - Key register (64-bit configurable)
     - Value register (64-bit configurable)
     - TTL timer (32-bit configurable)
     - Valid flag
   - Automatic TTL decrement on each clock cycle
   - Automatic invalidation when TTL expires

2. **Memory Block** (`src/memory/memory_block.v`)
   - Array of memory cells forming the cache storage
   - Configurable number of entries (default: 16)
   - Parallel instantiation of memory cells
   - Unified read/write interface with address decoding
   - Multiplexed read output based on address

3. **Memory Interface** (`src/interface/memory_interface.v`)
   - Abstracts memory access operations
   - Implements hash function for key-to-address mapping
   - Handles key matching and hit/miss detection
   - Provides ready-valid handshake protocol
   - State machine for command processing (IDLE, LOOKUP, WRITE, RESPOND)

4. **FSM Controller** (`src/core/fsm_controller.v`)
   - Finite State Machine for command processing
   - Decodes and executes Redis-like commands
   - Manages command flow and response generation
   - Supported commands:
     - `SET` (0x01): Store key-value pair with TTL
     - `GET` (0x02): Retrieve value by key
     - `DEL` (0x03): Delete key-value pair
     - `EXPIRE` (0x04): Update TTL for existing key
   - State machine: IDLE → DECODE → EXECUTE → WAIT_MEM → RESPOND

### Top-Level Integration

**Redis Cache Top Module** (`src/redis_cache_top.v`)
- Integrates FSM controller, memory interface, and memory block
- Provides complete Redis-like cache functionality
- Single command execution at a time
- Simple control flow suitable for initial implementation

## Key Features

- **Configurable Parameters**:
  - Number of cache entries
  - Key width (default: 64-bit)
  - Value width (default: 64-bit)
  - TTL width (default: 32-bit)

- **Hardware-Efficient Design**:
  - Simple hash function for key distribution
  - Parallel TTL countdown across all entries
  - Minimal control logic overhead

- **Standard Interfaces**:
  - Ready-valid handshake protocol
  - Synchronous reset (active-low)
  - Single clock domain operation

## Design Parameters

```verilog
NUM_ENTRIES   = 16      // Number of cache entries
KEY_WIDTH     = 64      // Key width in bits
VALUE_WIDTH   = 64      // Value width in bits
TTL_WIDTH     = 32      // TTL counter width in bits
CMD_WIDTH     = 8       // Command opcode width in bits
```

## Interface Specifications

### Command Input Interface
- `cmd_valid`: Command valid signal
- `cmd_opcode[7:0]`: Operation code
- `cmd_key[63:0]`: Key value
- `cmd_value[63:0]`: Data value (for writes)
- `cmd_ttl[31:0]`: Time-to-live value
- `cmd_ready`: System ready to accept commands

### Response Output Interface
- `resp_valid`: Response valid signal
- `resp_success`: Operation success indicator
- `resp_value[63:0]`: Retrieved value (for reads)
- `resp_ttl[31:0]`: Remaining TTL
- `resp_ready`: Consumer ready to accept response

## Usage Example

```verilog
redis_cache_top #(
    .NUM_ENTRIES(16),
    .KEY_WIDTH(64),
    .VALUE_WIDTH(64),
    .TTL_WIDTH(32)
) cache_inst (
    .clk(clk),
    .rst_n(rst_n),
    .cmd_valid(cmd_valid),
    .cmd_opcode(cmd_opcode),
    .cmd_key(cmd_key),
    .cmd_value(cmd_value),
    .cmd_ttl(cmd_ttl),
    .cmd_ready(cmd_ready),
    .resp_valid(resp_valid),
    .resp_success(resp_success),
    .resp_value(resp_value),
    .resp_ttl(resp_ttl),
    .resp_ready(resp_ready)
);
```

## Future Enhancements

The following features are planned for future development:

- **Pipeline Architecture**: 3-stage pipeline for improved throughput
  - Stage 1: Command input buffering
  - Stage 2: Address calculation  
  - Stage 3: Memory access
- **Testing Infrastructure**: Comprehensive testbenches for validation
- Additional Redis commands (INCR, DECR, APPEND, etc.)
- Multi-port memory for concurrent read/write
- Cache replacement policies (LRU, LFU)
- DRAM interface for larger capacity
- AXI bus interface for SoC integration
