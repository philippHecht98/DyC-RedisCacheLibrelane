import os
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge
from cocotb_tools.runner import get_runner
from cocotb.triggers import ReadOnly

class GetFSMTest:
    """Helper class for GET FSM."""

    def __init__(self, dut):
        self.dut = dut
        self.clk = dut.clk
        self.rst_n = dut.rst_n
        self.hit = dut.hit
        self.cmd = dut.cmd
    
    async def reset(self):
        """Apply reset pulse."""
        self.rst_n.value = 0
        await RisingEdge(self.clk)
        self.rst_n.value = 1
        await RisingEdge(self.clk)

@cocotb.test()
async def test_fsm_hit(dut):
    """Test case for FSM hit scenario."""
    fsm_test = GetFSMTest(dut)

    # Start clock
    clock = Clock(fsm_test.clk, 10, unit="us")
    cocotb.start_soon(clock.start())

    await fsm_test.reset()

    # Simulate a hit scenario
    fsm_test.hit.value = 1
    await RisingEdge(fsm_test.clk)

    # Check if FSM transitions to the expected state
    await ReadOnly()
    assert int(fsm_test.cmd.value) == 2, "FSM did not set correct command for hit scenario"
    assert (int(fsm_test.cmd.value) & 1) == 0, "FSM set error command"

@cocotb.test()
async def test_fsm_miss(dut):
    """Test case for FSM miss scenario."""
    fsm_test = GetFSMTest(dut)

    # Start clock
    clock = Clock(fsm_test.clk, 10, unit="us")
    cocotb.start_soon(clock.start())

    await fsm_test.reset()

    # Simulate a miss scenario
    fsm_test.hit.value = 0
    await RisingEdge(fsm_test.clk)

    # Check if FSM transitions to the expected state
    await ReadOnly()
    assert int(fsm_test.cmd.value) == 2, "FSM did not set correct command for miss scenario"
    assert (int(fsm_test.cmd.value) & 1) == 0, "FSM set error command"

def test_get_fsm_runner():
    sim = os.getenv("SIM", "icarus")
    proj_path = Path(__file__).resolve().parent
    
    # Deine Verilog Datei
    sources = [proj_path / ".." / "src" / "ctrl_types_pkg.sv",
               proj_path / ".." / "src" / "get_fsm.sv"]

    runner = get_runner(sim)

    #parameters = {}

    runner.build(
        sources=sources,
        hdl_toplevel="get_fsm",
        always=True, 
        waves=True,
        timescale=("1ns", "1ps")
    )

    runner.test(
        hdl_toplevel="get_fsm", 
        test_module="test_get_fsm",
        waves=True
    )

if __name__ == "__main__":
    test_get_fsm_runner()