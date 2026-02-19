# Testing Guide for Redis Cache Hardware

This document provides guidelines for implementing CoCoTB tests for the Redis cache hardware design.

## Overview

The project uses **CoCoTB** (Coroutine-based Cosimulation TestBench) for hardware verification. CoCoTB allows writing testbenches in Python, providing a more flexible and productive testing environment compared to traditional SystemVerilog testbenches.

## Setup

### Prerequisites

1. **Python 3.11** (managed via pyenv)
2. **Verilog Simulator** - One of:
   - Icarus Verilog (recommended for open-source)
   - Verilator
   - ModelSim/QuestaSim
   - VCS

### Installation

```bash
# Install Python dependencies
make install

# Or manually
pip install -r requirements-dev.txt
```

## Test Structure

### Directory Layout

```
test/
├── README.md                    # This file
├── conftest.py                  # Pytest configuration
├── common/                      # Shared test utilities
│   ├── __init__.py
│   ├── drivers.py              # Bus drivers
│   ├── monitors.py             # Bus monitors
│   └── scoreboard.py           # Verification scoreboard
├── test_memory_cell.py          # Memory cell tests
├── test_memory_block.py         # Memory block tests
├── test_memory_interface.py     # Memory interface tests
├── test_fsm_controller.py       # FSM controller tests
└── test_top.py                  # Integration tests
```

## Writing Tests

### Basic Test Template

```python
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer
from cocotb.types import LogicArray

@cocotb.test()
async def test_basic_operation(dut):
    """Test basic functionality of the module"""
    
    # Create a 10ns clock (100 MHz)
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())
    
    # Reset
    dut.rst_n.value = 0
    await Timer(20, units="ns")
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    
    # Test stimulus
    dut.input_signal.value = 0x1234
    await RisingEdge(dut.clk)
    
    # Check output
    assert dut.output_signal.value == expected_value, \
        f"Expected {expected_value}, got {dut.output_signal.value}"
```

### Memory Cell Tests

Location: `test/test_memory_cell.py`

**Test Cases:**
1. Basic write and read
2. TTL countdown
3. Automatic expiration
4. Write during countdown
5. Multiple write/read cycles

```python
# Example test
@cocotb.test()
async def test_ttl_countdown(dut):
    """Verify TTL decrements each clock cycle"""
    # Implementation here
```

### Memory Block Tests

Location: `test/test_memory_block.py`

**Test Cases:**
1. Address decoding
2. Multiple cell access
3. Concurrent operations
4. Boundary conditions

### Memory Interface Tests

Location: `test/test_memory_interface.py`

**Test Cases:**
1. Hash function correctness
2. Key matching
3. Hit/miss detection
4. Ready-valid handshaking
5. State machine transitions

### FSM Controller Tests

Location: `test/test_fsm_controller.py`

**Test Cases:**
1. Command decoding (SET, GET, DEL, EXPIRE)
2. State transitions
3. Memory interface coordination
4. Error handling
5. Back-to-back commands

### Integration Tests

Location: `test/test_top.py`

**Test Cases:**
1. End-to-end SET/GET operations
2. TTL expiration scenarios
3. Cache hit/miss behavior
4. Multiple concurrent operations
5. Stress testing

## Running Tests

### Run All Tests
```bash
make test
```

### Run Specific Test Module
```bash
make test-cell    # Memory cell
make test-block   # Memory block
make test-fsm     # FSM controller
make test-top     # Top-level
```

### Run with Specific Simulator
```bash
SIM=verilator make test
SIM=icarus make test-cell
```

### Run with Coverage
```bash
pytest --cov=test --cov-report=html
```

## Test Utilities

### Drivers

Create bus drivers for input interfaces:

```python
class CommandDriver:
    """Driver for command interface"""
    
    def __init__(self, dut):
        self.dut = dut
        
    async def send_command(self, opcode, key, value, ttl):
        """Send a command to the DUT"""
        self.dut.cmd_valid.value = 1
        self.dut.cmd_opcode.value = opcode
        self.dut.cmd_key.value = key
        self.dut.cmd_value.value = value
        self.dut.cmd_ttl.value = ttl
        
        await RisingEdge(self.dut.clk)
        while not self.dut.cmd_ready.value:
            await RisingEdge(self.dut.clk)
        
        self.dut.cmd_valid.value = 0
```

### Monitors

Create monitors for output interfaces:

```python
class ResponseMonitor:
    """Monitor for response interface"""
    
    def __init__(self, dut, callback):
        self.dut = dut
        self.callback = callback
        
    async def monitor(self):
        """Monitor responses"""
        while True:
            await RisingEdge(self.dut.clk)
            if self.dut.resp_valid.value:
                response = {
                    'success': int(self.dut.resp_success.value),
                    'value': int(self.dut.resp_value.value),
                    'ttl': int(self.dut.resp_ttl.value)
                }
                self.callback(response)
```

### Scoreboard

Implement a scoreboard for checking expected vs actual results:

```python
class Scoreboard:
    """Verification scoreboard"""
    
    def __init__(self):
        self.expected = []
        self.received = []
        
    def add_expected(self, data):
        """Add expected transaction"""
        self.expected.append(data)
        
    def add_received(self, data):
        """Add received transaction"""
        self.received.append(data)
        
    def check(self):
        """Compare expected vs received"""
        assert len(self.expected) == len(self.received), \
            "Transaction count mismatch"
        
        for exp, rcv in zip(self.expected, self.received):
            assert exp == rcv, f"Mismatch: expected {exp}, got {rcv}"
```

## Debugging

### Waveform Generation

CoCoTB automatically generates VCD waveforms. View with GTKWave:

```bash
gtkwave dump.vcd
```

### Logging

Use CoCoTB's logging:

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Starting test")
logger.debug(f"Signal value: {dut.signal.value}")
```

### Print Debug Info

```python
dut._log.info("DUT state: %s", dut.state.value)
```

## Best Practices

1. **Use async/await properly** - All CoCoTB tests are coroutines
2. **Clock synchronization** - Always await clock edges
3. **Reset sequences** - Include proper reset at start of each test
4. **Assertions** - Use clear, descriptive assertion messages
5. **Randomization** - Use random inputs for robust testing
6. **Coverage** - Aim for high code and functional coverage
7. **Documentation** - Document test purpose and expected behavior

## CI/CD Integration

Tests run automatically on:
- Every push (RTL Frontend Pipeline)
- Pull requests to main (Full validation)

See `.github/workflows/rtl-frontend.yml` for CI configuration.

## References

- [CoCoTB Documentation](https://docs.cocotb.org/)
- [CoCoTB Bus Library](https://github.com/cocotb/cocotb-bus)
- [Project Architecture](../docs/ARCHITECTURE.md)
