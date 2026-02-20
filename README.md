# DyC-RedisCache

A Redis-like hardware acceleration design for ASIC implementation, providing high-performance key-value cache with Time-To-Live (TTL) support.

## Features

- **Hardware-accelerated cache operations** with sub-cycle response times
- **Automatic TTL management** with hardware timer countdown
- **Configurable parameters** for flexible deployment
- **Multiple Redis commands** support (SET, GET, DEL, EXPIRE)
- **Clean modular design** with well-defined interfaces

## Project Structure

```
src/
├── core/
│   └── fsm_controller.v         # FSM for command processing
├── memory/
│   ├── memory_cell.v            # Individual cache cell with TTL
│   └── memory_block.v           # Array of cache cells
├── interface/
│   └── memory_interface.v       # Memory access interface
└── redis_cache_top.v            # Top-level integration module

test/
└── README.md                    # Testing documentation (CoCoTB tests to be implemented)

docs/
├── ARCHITECTURE.md              # Detailed architecture documentation
├── BASE_MODULES.md              # Base modules implementation summary
└── SYNTHESIS.md                 # Synthesis and build guide

.github/
└── workflows/
    ├── rtl-frontend.yml         # RTL frontend pipeline (runs on push)
    └── librelane-pipeline.yml   # Full ASIC pipeline (runs on PR to main)
```

## Key Components

### 1. Memory Cell
The fundamental building block storing individual key-value pairs with TTL functionality.

### 2. Memory Block
Array of memory cells providing addressable cache storage.

### 3. Memory Interface
Handles address generation, key matching, and provides a clean interface to the memory block.

### 4. FSM Controller
Manages command execution flow and coordinates between external interface and memory subsystem.

### 5. Top-Level Integration
The `redis_cache_top` module integrates all base components into a complete system.

## Getting Started

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/philippHecht98/DyC-RedisCache.git
   cd DyC-RedisCache
   ```

2. **Set up Python environment**
   ```bash
   # Using pyenv (recommended)
   pyenv install 3.11.0
   pyenv local 3.11.0
   
   # Or create virtual environment
   make venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   make install
   ```

4. **Install Verilog simulator** (for testing)
   ```bash
   # Ubuntu/Debian
   sudo apt-get install iverilog
   
   # macOS
   brew install icarus-verilog
   ```

### Verification and Testing

Run syntax checks:
```bash
make syntax
```

Run tests (to be implemented):
```bash
make test
```

### CI/CD Pipelines

The project includes two GitHub Actions workflows:

1. **RTL Frontend Pipeline** (runs on every push)
   - Verilog syntax checking
   - Simulation with CoCoTB
   - Basic verification

2. **Librelane Full Pipeline** (runs on PR to main)
   - Complete ASIC design flow
   - Synthesis, place & route
   - Timing analysis, DRC, LVS
   - GDSII generation

See detailed architecture documentation in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Command Set

| Opcode | Command | Description |
|--------|---------|-------------|
| 0x01 | SET | Store key-value pair with TTL |
| 0x02 | GET | Retrieve value by key |
| 0x03 | DEL | Delete key-value pair |
| 0x04 | EXPIRE | Update TTL for key |

## Configuration Parameters

- `NUM_ENTRIES`: Number of cache entries (default: 16)
- `KEY_WIDTH`: Key width in bits (default: 64)
- `VALUE_WIDTH`: Value width in bits (default: 64)
- `TTL_WIDTH`: TTL counter width in bits (default: 32)

## Future Work

- **Pipeline implementation** for higher throughput
- **Comprehensive testbench suite** for validation
- Additional Redis command support
- Advanced cache replacement policies
- Multi-level cache hierarchy
- DRAM interface integration
- AXI bus compatibility