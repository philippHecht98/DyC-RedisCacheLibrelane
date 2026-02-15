import os
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge
from cocotb_tools.runner import get_runner
from cocotb.triggers import ReadOnly


class ControllerTester:
    """Helper class for Controller."""

    def __init__(self, dut):
        self.dut = dut
        self.clk = dut.clk
        self.rst_n = dut.rst_n
    
    async def reset(self):
        """Apply reset pulse."""
        self.rst_n.value = 0
        await RisingEdge(self.clk)
        self.rst_n.value = 1
        await RisingEdge(self.clk)
    
    async def wait_cycles(self, num_cycles: int):
        """Wait for specified number of clock cycles."""
        for _ in range(num_cycles):
            await RisingEdge(self.clk)
    
    async def write(self, cycles: int = 1):
        """..."""
        
    async def check_outputs(self, idx_out, write_out, select_out, ready_out):
        """Check outputs against expected values."""
        await ReadOnly()
        assert self.dut.idx_out.value == idx_out, f"idx_out mismatch: {self.dut.idx_out.value} != {idx_out}"
        assert self.dut.write_out.value == write_out, f"write_out mismatch: {self.dut.write_out.value} != {write_out}"
        assert self.dut.select_out.value == select_out, f"select_out mismatch: {self.dut.select_out.value} != {select_out}"
        assert self.dut.ready_out.value == ready_out, f"ready_out mismatch: {self.dut.ready_out.value} != {ready_out}"
        
        

@cocotb.test()
async def test_reset(dut):
    """Test: Verify controller initializes to IDLE state after reset."""
    tester = ControllerTester(dut)
    
    # Start clock
    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())
    
    dut.operation_in.value = 0
    dut.used.value = 0
    # Apply reset
    await tester.reset()

    # Verify all outputs are 0 in IDLE state
    await tester.check_outputs(idx_out=0, write_out=0, select_out=0, ready_out=0)

    await tester.wait_cycles(1)
    await tester.check_outputs(idx_out=0, write_out=0, select_out=0, ready_out=0)

   
    dut._log.info("✓ Reset test passed")
    
    
@cocotb.test()
async def test_idle_noop_operation(dut):
    """Test: Verify controller stays in IDLE if no operation."""
    tester = ControllerTester(dut)
    
    # Start clock
    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())
    
    dut.operation_in.value = 0
    dut.used.value = 0
    # Apply reset
    await tester.reset()

    dut.operation_in.value = 0  # NOOP

    await tester.wait_cycles(1)

    await tester.check_outputs(idx_out=0, write_out=0, select_out=0, ready_out=0)
    assert dut.state.value == 0, f"State mismatch: {dut.state.value} != 0 (IDLE)"

    dut._log.info("✓ IDLE no operation test passed")


@cocotb.test()
async def test_write_operation(dut):
    """Test: Switch to the PUT state and find the correct index in used."""
    tester = ControllerTester(dut)
    
    # Start clock
    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())
    
    dut.operation_in.value = 0
    dut.used.value = 0
    # Apply reset
    await tester.reset()

    dut.operation_in.value = 2  # WRITE

    dut.used.value = 0b1100010010010111

    await RisingEdge(dut.clk)

    await tester.check_outputs(idx_out=8, write_out=1, select_out=0, ready_out=0)
    assert dut.state.value == 2, f"State mismatch: {dut.state.value} != 2 (PUT)"

    await RisingEdge(dut.clk)

    dut.operation_in.value = 0  # NOOP
    await RisingEdge(dut.clk)
    assert dut.state.value == 0, f"State mismatch: {dut.state.value} != 0 (IDLE)"

    dut._log.info("✓ Write operation test passed")

@cocotb.test()
async def test_read_operation(dut):
    """Test: Verify controller switches from IDLE to GET state when Operation is READ."""
    tester = ControllerTester(dut)
    
    # Start clock
    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())
    
    dut.operation_in.value = 0
    dut.used.value = 0
    # Apply reset
    await tester.reset()

    dut.operation_in.value = 1  # READ
    dut.used.value = 0

    await RisingEdge(dut.clk)

    await tester.check_outputs(idx_out=0, write_out=0, select_out=0, ready_out=0)
    assert dut.state.value == 1, f"State mismatch: {dut.state.value} != 1 (GET)"

    await RisingEdge(dut.clk)
    
    dut.operation_in.value = 0  # NOOP
    await RisingEdge(dut.clk)
    assert dut.state.value == 0, f"State mismatch: {dut.state.value} != 0 (IDLE)"

    dut._log.info("✓ Read operation test passed")


def test_controller_runner():
    sim = os.getenv("SIM", "icarus")
    proj_path = Path(__file__).resolve().parent
    
    # Deine Verilog Datei
    sources = [proj_path / ".." / "src" / "controller.sv"]

    runner = get_runner(sim)

    #parameters = {}

    runner.build(
        sources=sources,
        hdl_toplevel="controller",
        always=True, 
        waves=True,
        timescale=("1ns", "1ps")
    )

    runner.test(
        hdl_toplevel="controller", 
        test_module="test_controller",
        waves=True
    )

if __name__ == "__main__":
    test_controller_runner()