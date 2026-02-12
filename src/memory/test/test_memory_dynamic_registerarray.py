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

    async def reset(self):
        """Führt einen Reset durch (Active High Reset)."""
        self.dut.rst_n.value = 0
        self.dut.write_op.value = 0
        self.dut.data_in.value = 0
        
        await RisingEdge(self.clk)
        self.dut.rst_n.value = 1  # Reset lösen
        await RisingEdge(self.clk)

    async def write(self, data: int):
        """Schreibt Daten in das Register (ohne Output zu aktivieren)."""
        await FallingEdge(self.clk)
        self.dut.write_op.value = 1
        self.dut.data_in.value = data
        
        await RisingEdge(self.clk)
        self.dut.write_op.value = 0  # Write beenden


@cocotb.test()
async def test_reset(dut):
    """Test: Reset-Verhalten überprüfen."""
    
    tester = RegisterArrayTester(dut)
    
    # Start clock
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await tester.write(0xFF)  # Vor dem Reset einen Wert schreiben, um sicherzustellen, dass Reset funktioniert

    # 1. Reset
    await tester.reset()

    await ReadOnly() 
    assert dut.data_out.value == 0, \
        f"Reset failed! Expected 0, got {hex(dut.data_out.value)}"


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

    await ReadOnly() 
    assert dut.data_out.value == test_value, \
        f"Write failed! Expected {hex(test_value)}, got {hex(dut.data_out.value)}"


    dut._log.info("✓ Write verify successful")


@cocotb.test()
async def test_write_overwrite(dut):
    """Test: Überschreiben von Daten."""
    
    tester = RegisterArrayTester(dut)
    
    # Start clock
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # 1. Reset
    await tester.reset()

    # 2. Erstes Schreiben
    first_value = 0xAA
    dut._log.info(f"Writing first value: {hex(first_value)}...")
    await tester.write(first_value)

    await ReadOnly() 
    assert dut.data_out.value == first_value, \
        f"First write failed! Expected {hex(first_value)}, got {hex(dut.data_out.value)}"
    
    # 3. Zweites Schreiben (Überschreiben)
    second_value = 0x33
    dut._log.info(f"Overwriting with second value: {hex(second_value)}...")
    await tester.write(second_value)
    await ReadOnly()
    assert dut.data_out.value == second_value, \
        f"Overwrite failed! Expected {hex(second_value)}, got {hex(dut.data_out.value)}"

    dut._log.info("✓ Overwrite verify successful")     

@cocotb.test()
async def test_data_in_without_write(dut):
    """Test: Daten an data_in anlegen, aber write_op nicht aktivieren."""
    
    tester = RegisterArrayTester(dut)
    
    # Start clock
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # 1. Reset
    await tester.reset()

    # 2. Daten anlegen ohne write_op zu aktivieren
    test_value = 0x77
    dut._log.info(f"Applying data_in value: {hex(test_value)} without write_op...")
    await FallingEdge(tester.clk)
    dut.data_in.value = test_value
    dut.write_op.value = 0  # write_op nicht aktivieren

    await RisingEdge(tester.clk)  # Auf die nächste steigende Flanke warten

    await ReadOnly() 
    assert dut.data_out.value == 0, \
        f"Expected 0 after setting data_in without write_op, got {hex(dut.data_out.value)}"


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