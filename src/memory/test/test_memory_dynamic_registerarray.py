import os
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge
from cocotb_tools.runner import get_runner
from cocotb.triggers import ReadOnly


class RegisterArrayTester:
    """Helper class for Dynamic Register Array testing."""

    def __init__(self, dut):
        self.dut = dut
        self.clk = dut.clk

    @cocotb.before_test()
    async def reset(self):
        """Führt einen Reset durch (Active High Reset)."""
        self.dut.rst_n.value = 1
        self.dut.write_op.value = 0
        self.dut.select_op.value = 0
        self.dut.data_in.value = 0
        
        await RisingEdge(self.clk)
        self.dut.rst_n.value = 0  # Reset lösen
        await RisingEdge(self.clk)

    async def write(self, data: int):
        """Schreibt Daten in das Register (ohne Output zu aktivieren)."""
        await FallingEdge(self.clk)
        self.dut.write_op.value = 1
        self.dut.data_in.value = data
        
        await RisingEdge(self.clk)
        self.dut.write_op.value = 0  # Write beenden

    async def set_select(self, enable: bool):
        """Aktiviert oder deaktiviert den Ausgang (Tristate Steuerung)."""
        await FallingEdge(self.clk)
        self.dut.select_op.value = 1 if enable else 0
        await RisingEdge(self.clk)

@cocotb.test()
async def test_write_simple(dut):
    """Test: Nur Schreiben und überprüfen."""
    
    tester = RegisterArrayTester(dut)
    
    # Start clock
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # 1. Reset
    await tester.reset()

    # 2. Schreiben
    test_value = 0x55
    dut._log.info(f"Writing value: {hex(test_value)}...")
    await tester.write(test_value)

    # 3. Überprüfung
    # Damit wir sehen, ob es gespeichert wurde, müssen wir kurz select anmachen
    dut.select_op.value = 1
    await ReadOnly() # Warten bis Simulator Signale aktualisiert hat

    assert dut.data_out.value == test_value, \
        f"Write failed! Expected {hex(test_value)}, got {hex(dut.data_out.value)}"
    
    dut._log.info("✓ Write verify successful")
    
    


def test_register_runner():
    sim = os.getenv("SIM", "icarus")
    proj_path = Path(__file__).resolve().parent
    
    # Deine Verilog Datei
    sources = [proj_path / ".." / "src" / "memory_dynamic_registerarray.sv"]

    runner = get_runner(sim)
    
    # WICHTIG: Parameter für die Breite setzen (z.B. 8 Bit)
    parameters = {"LENGTH": 8}

    runner.build(
        sources=sources,
        hdl_toplevel="dynamic_register_array",
        parameters=parameters,
        always=True, 
        waves=True,
        timescale=("1ns", "1ps")
    )

    runner.test(
        hdl_toplevel="dynamic_register_array", 
        test_module="test_memory_dynamic_registerarray", # Name dieser Datei
        waves=True
    )

if __name__ == "__main__":
    test_register_runner()