# Quick Start Guide

This guide will help you get started with the Redis Cache Hardware project.

## Prerequisites

- Python 3.11
- Git
- A Verilog simulator (Icarus Verilog recommended)

## Setup

### 1. Clone and Enter Directory

```bash
git clone https://github.com/philippHecht98/DyC-RedisCache.git
cd DyC-RedisCache
```

### 2. Set Up Python Environment

**Using pyenv (recommended):**
```bash
pyenv install 3.11.0
pyenv local 3.11.0
```

**Or create a virtual environment:**
```bash
make venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
make install
```

### 4. Install Simulator

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install iverilog gtkwave
```

**macOS:**
```bash
brew install icarus-verilog gtkwave
```

## Verify Installation

Check Verilog syntax:
```bash
make syntax
```

Expected output:
```
Checking Verilog syntax...
Checking src/memory/memory_cell.v...
Checking src/memory/memory_block.v...
...
All Verilog files passed syntax check
```

## Project Structure

```
src/                    # Verilog source files
├── core/              # FSM controller
├── interface/         # Memory interface
├── memory/            # Memory cells and blocks
└── redis_cache_top.v  # Top-level module

test/                  # CoCoTB tests (to be implemented)
docs/                  # Documentation
.github/workflows/     # CI/CD pipelines
```

## Development Workflow

### 1. Make Changes to RTL

Edit files in `src/` directory.

### 2. Check Syntax

```bash
make syntax
```

### 3. Run Tests (when implemented)

```bash
make test
```

### 4. Format Code (Python tests)

```bash
make format
```

### 5. Commit and Push

```bash
git add .
git commit -m "Your changes"
git push
```

The RTL Frontend pipeline will automatically run on push.

## Makefile Targets

```bash
make help          # Show all available targets
make install       # Install Python dependencies
make venv          # Create virtual environment
make syntax        # Check Verilog syntax
make test          # Run all tests
make test-cell     # Test memory cell
make test-block    # Test memory block
make test-fsm      # Test FSM controller
make test-top      # Test top-level module
make lint          # Run Python linting
make format        # Format Python code
make clean         # Clean build artifacts
```

## Running Tests

Tests use CoCoTB framework. Basic structure:

```python
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

@cocotb.test()
async def test_example(dut):
    """Test description"""
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())
    
    # Reset
    dut.rst_n.value = 0
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    
    # Test logic here
```

See [docs/TESTING.md](docs/TESTING.md) for detailed testing guide.

## CI/CD Pipelines

### RTL Frontend (runs on every push)
- Syntax checking
- Simulation
- Verification
- View: `.github/workflows/rtl-frontend.yml`

### Librelane Pipeline (runs on PR to main)
- Full ASIC design flow
- Synthesis → GDSII
- View: `.github/workflows/librelane-pipeline.yml`

See [docs/CICD.md](docs/CICD.md) for detailed CI/CD documentation.

## Design Overview

The Redis cache hardware implements a key-value store with TTL (Time-To-Live) support:

### Modules

1. **Memory Cell** (`src/memory/memory_cell.v`)
   - Stores key, value, and TTL
   - Automatic TTL countdown
   - Self-invalidation on expiry

2. **Memory Block** (`src/memory/memory_block.v`)
   - Array of memory cells
   - Address-based access

3. **Memory Interface** (`src/interface/memory_interface.v`)
   - Hash function for key mapping
   - Hit/miss detection

4. **FSM Controller** (`src/core/fsm_controller.v`)
   - Command processing (SET, GET, DEL, EXPIRE)
   - State machine control

5. **Top-Level** (`src/redis_cache_top.v`)
   - Integrates all modules

### Commands

| Opcode | Command | Description |
|--------|---------|-------------|
| 0x01   | SET     | Store key-value with TTL |
| 0x02   | GET     | Retrieve value by key |
| 0x03   | DEL     | Delete entry |
| 0x04   | EXPIRE  | Update TTL |

## Documentation

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - Design architecture
- [BASE_MODULES.md](docs/BASE_MODULES.md) - Module implementation details
- [SYNTHESIS.md](docs/SYNTHESIS.md) - Synthesis guide
- [TESTING.md](docs/TESTING.md) - Testing framework
- [CICD.md](docs/CICD.md) - CI/CD pipelines

## Getting Help

1. Check documentation in `docs/`
2. Review examples in test files
3. Check GitHub Issues
4. See Makefile for available commands

## Next Steps

1. **Implement Tests**: Add CoCoTB tests in `test/`
2. **Configure PDK**: Set up Process Design Kit for librelane
3. **Add Constraints**: Define timing constraints
4. **Optimize**: Profile and optimize design

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and checks
5. Submit a pull request

## License

[Add license information]

## Contact

[Add contact information]
