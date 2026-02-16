import os
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ReadOnly
from cocotb_tools.runner import get_runner


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
        
    async def check_outputs(self, idx_out, write_out, select_out, rdy_out, op_succ):
        """Check outputs against expected values."""
        await ReadOnly()
        assert self.dut.idx_out.value == idx_out, f"idx_out mismatch: {self.dut.idx_out.value} != {idx_out}"
        assert self.dut.write_out.value == write_out, f"write_out mismatch: {self.dut.write_out.value} != {write_out}"
        assert self.dut.select_out.value == select_out, f"select_out mismatch: {self.dut.select_out.value} != {select_out}"
        assert self.dut.rdy_out.value == rdy_out, f"rdy_out mismatch: {self.dut.rdy_out.value} != {rdy_out}"
        assert self.dut.op_succ.value == op_succ, f"op_succ mismatch: {self.dut.op_succ.value} != {op_succ}"
        

@cocotb.test()
async def test_reset(dut):
    """Test: Verify controller initializes to IDLE state after reset."""
    tester = ControllerTester(dut)
    
    # Start clock
    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())
    
    # Initialize inputs
    dut.used.value = 0
    dut.idx_in.value = 0
    dut.hit.value = 0
    dut.operation_in.value = 0 #NOOP
    
    # Apply reset
    await tester.reset()

    # Verify all outputs are 0 in IDLE state
    await tester.check_outputs(idx_out=0, write_out=0, select_out=0, rdy_out=0, op_succ=0)
    
    # Verify state is IDLE (0)
    assert dut.state.value == 0, f"State mismatch: {dut.state.value} != 0 (IDLE)"

   
    dut._log.info("✓ Reset test passed")


def test_controller_runner():
    sim = os.getenv("SIM", "icarus")
    proj_path = Path(__file__).resolve().parent
    src_path = proj_path / ".." / "src"
    
    # Deine Verilog Datei
    sources = [
        src_path / "ctrl_types_pkg.sv",
        src_path / "get_fsm.sv",
        src_path / "upsert_fsm.sv",
        src_path / "controller.sv"
    ]

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