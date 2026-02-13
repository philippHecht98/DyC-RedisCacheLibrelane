import os
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge
from cocotb_tools.runner import get_runner
from cocotb.triggers import ReadOnly


class UpsertTester:
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
        assert self.dut.op_succ.value == rdy_out, f"rdy_out mismatch: {self.dut.op_succ.value} != {op_succ}"
        
        

@cocotb.test()
async def test_reset_with_empty_used(dut):
    """Test: Verify controller initializes to IDLE state after reset."""
    tester = UpsertTester(dut)
    
    # Start clock
    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())
    
    dut.en.value = 0
    dut.enter.value = 0
    dut.hit.value = 0
    dut.used.value = 0
    dut.idx_in.value = 0

    # Apply reset
    await tester.reset()

    # Verify all outputs are 0 in IDLE state
    await tester.check_outputs(idx_out=1, write_out=1, select_out=0, rdy_out=1, op_succ=1)

    #await tester.wait_cycles(1)
    await FallingEdge(dut.clk)
    await tester.check_outputs(idx_out=1, write_out=1, select_out=0, rdy_out=1, op_succ=1)
   
    dut._log.info("✓ Reset test passed")


def test_upsert_runner():
    sim = os.getenv("SIM", "icarus")
    proj_path = Path(__file__).resolve().parent
    
    # Deine Verilog Datei
    sources = [
        proj_path / ".." / "src" / "ctrl_types_pkg.sv",
        proj_path / ".." / "src" / "upsert_fsm.sv"
    ]

    runner = get_runner(sim)

    #parameters = {}

    runner.build(
        sources=sources,
        hdl_toplevel="upsert_fsm",
        always=True, 
        waves=True,
        timescale=("1ns", "1ps")
    )

    runner.test(
        hdl_toplevel="upsert_fsm", 
        test_module="test_upsert_fsm",
        waves=True
    )

if __name__ == "__main__":
    test_upsert_runner()