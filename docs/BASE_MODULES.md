# Base Modules Implementation Summary

## Overview

This document summarizes the base modules implemented for the Redis-like hardware cache system. These modules form the foundation of the ASIC design.

## Module Hierarchy

```
redis_cache_top
├── fsm_controller
├── memory_interface
└── memory_block
    └── memory_cell (instantiated NUM_ENTRIES times)
```

## Module Descriptions

### 1. Memory Cell (`src/memory/memory_cell.v`)

**Purpose:** Basic storage element for key-value pairs with TTL.

**Key Features:**
- Stores 64-bit key, 64-bit value, 32-bit TTL counter
- Valid flag indicates active entry
- Automatic TTL decrement each clock cycle
- Self-invalidates when TTL reaches zero

**Interface:**
- Clock and reset inputs
- Write enable with key, value, and TTL inputs
- Read outputs for key, value, TTL, and valid status

**Behavior:**
- On write: Stores new data and sets valid flag
- Each cycle: Decrements TTL if valid and TTL > 0
- On expiry: Clears valid flag when TTL reaches zero

### 2. Memory Block (`src/memory/memory_block.v`)

**Purpose:** Array of memory cells forming the cache storage.

**Key Features:**
- Parameterized number of entries (default: 16)
- Parallel instantiation of memory cells
- Address-based read/write access
- Multiplexed output based on read address

**Interface:**
- Write interface: address, enable, and data inputs
- Read interface: address input, data outputs
- All cells share common clock and reset

**Behavior:**
- Write: Activates write_en for selected cell based on address
- Read: Multiplexes output from selected cell

### 3. Memory Interface (`src/interface/memory_interface.v`)

**Purpose:** Provides abstraction layer between controller and memory block.

**Key Features:**
- Hash function for key-to-address mapping
- Key matching for hit/miss detection
- Ready-valid handshake protocol
- State machine for command processing

**States:**
- IDLE: Wait for command
- LOOKUP: Read from memory and hash key
- WRITE: Perform write operation
- RESPOND: Send response to controller

**Hash Function:**
- XOR-folding of key bits
- Distributes keys across address space

### 4. FSM Controller (`src/core/fsm_controller.v`)

**Purpose:** Top-level command processor and coordinator.

**Key Features:**
- Decodes Redis-like commands
- Manages transaction flow
- Coordinates memory interface operations
- Generates responses

**Supported Commands:**
- SET (0x01): Store key-value-TTL
- GET (0x02): Retrieve value by key
- DEL (0x03): Delete entry (set TTL=0)
- EXPIRE (0x04): Update TTL

**States:**
- IDLE: Ready for new command
- DECODE: Interpret command opcode
- EXECUTE: Issue memory operation
- WAIT_MEM: Wait for memory response
- RESPOND: Return result to user

### 5. Top-Level Integration (`src/redis_cache_top.v`)

**Purpose:** Integrates all modules into complete system.

**Key Features:**
- Connects FSM controller to memory interface
- Connects memory interface to memory block
- Routes all signals between components
- Parameterized for easy configuration

**External Interface:**
- Command input: valid, opcode, key, value, TTL, ready
- Response output: valid, success, value, TTL, ready

## Design Philosophy

### Simplicity First
The base modules prioritize correctness and clarity over optimization. This provides:
- Easy verification
- Clear understanding of functionality
- Solid foundation for enhancements

### Parameterization
All key parameters are configurable:
- Cache size (NUM_ENTRIES)
- Data widths (KEY_WIDTH, VALUE_WIDTH, TTL_WIDTH)
- This allows flexible deployment

### Standard Interfaces
Ready-valid handshaking throughout:
- Industry-standard protocol
- Clean module boundaries
- Easy integration

### Single Clock Domain
All logic operates on one clock:
- Simplifies timing analysis
- No CDC issues
- Easier verification

## Resource Summary

For default configuration (16 entries, 64-bit key/value, 32-bit TTL):

**Memory Cells:**
- 16 cells × (64 + 64 + 32 + 1) bits = 2,576 flip-flops

**Control Logic:**
- FSM states: ~10-20 FFs
- Memory interface: ~200 FFs
- Counters and flags: ~100 FFs

**Combinational Logic:**
- Hash function: ~50 LUTs
- Key comparison: ~70 LUTs
- FSM decode: ~30 LUTs
- Multiplexers: ~200 LUTs

**Total Estimate:**
- ~2,900 flip-flops
- ~500 LUTs
- Scales linearly with NUM_ENTRIES

## Next Steps

Future enhancements will add:
1. **Pipeline architecture** - Split operation into stages
2. **Testbench suite** - Comprehensive validation
3. **Additional commands** - Extend functionality
4. **Performance optimization** - Improve throughput

The current base implementation provides a solid foundation for these additions.
