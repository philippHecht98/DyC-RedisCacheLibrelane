# CoCoTB Tests for Redis Cache Hardware

This directory contains CoCoTB-based tests for the Redis cache hardware design.

## Structure

```
test/
├── README.md                    # This file
├── conftest.py                  # Pytest configuration (to be implemented)
├── test_memory_cell.py          # Memory cell tests (to be implemented)
├── test_memory_block.py         # Memory block tests (to be implemented)
├── test_memory_interface.py     # Memory interface tests (to be implemented)
├── test_fsm_controller.py       # FSM controller tests (to be implemented)
└── test_top.py                  # Top-level integration tests (to be implemented)
```

## Running Tests

### Prerequisites

1. Install Python dependencies:
   ```bash
   make install
   ```

2. Install a Verilog simulator (e.g., Icarus Verilog):
   ```bash
   sudo apt-get install iverilog
   ```

### Run All Tests

```bash
make test
```

### Run Specific Tests

```bash
make test-cell    # Test memory cell
make test-block   # Test memory block
make test-fsm     # Test FSM controller
make test-top     # Test top-level module
```

## CoCoTB Test Structure

Each test file should follow this structure:

```python
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

@cocotb.test()
async def test_basic_functionality(dut):
    """Test basic functionality"""
    
    # Create clock
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())
    
    # Reset
    dut.rst_n.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    
    # Test logic here
    # ...
```

## Test Coverage

Tests should cover:
- [x] Basic functionality
- [x] Edge cases
- [x] Error conditions
- [x] Timing constraints
- [x] Protocol compliance

## Future Enhancements

- Add waveform generation for debugging
- Add code coverage analysis
- Add randomized testing
- Add protocol checkers
