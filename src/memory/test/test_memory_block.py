"""
Modern cocotb 2.0 testbench for the Controller module.
Uses async/await syntax and modern pythonic patterns.
"""

import os
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge
from cocotb.types import LogicArray

from cocotb_tools.runner import get_runner
import random

os.environ['COCOTB_ANSI_OUTPUT'] = '1'


class MemoryBlockTester: 
    """
    """

    def __init__(self, dut):
        self.dut = dut
        self.clk = dut.clk
        self.rst_n = dut.rst_n

        self.index = dut.index
        self.write_op = dut.write_op
        self.select_op = dut.select_op

        self.key_in = dut.key_in
        self.value_in = dut.value_in

        self.key_out = dut.key_out
        self.value_out = dut.value_out
        
        self.used_entries = dut.used_entries


    async def reset(self):
        """Führt einen Reset durch (Active High Reset)."""
        self.rst_n.value = 0
        self.key_in.value = 0
        self.value_in.value = 0
        self.write_op.value = 0
        self.select_op.value = 0
        
        await RisingEdge(self.clk)
        self.rst_n.value = 1  # Reset lösen
        await RisingEdge(self.clk)


    async def write(self, idx: int, key: int, value: int):
        """Schreibt Daten in das Register (ohne Output zu aktivieren)."""
        await FallingEdge(self.clk)
        self.write_op.value = 1  # Write-Operation aktivieren

        self.index.value = 1 << idx   # idx=0 → 0b01, idx=1 → 0b10
        self.key_in.value = key
        self.value_in.value = value
        
        await RisingEdge(self.clk)
        self.write_op.value = 0  # Write beenden


    async def read_by_key(self, key: int):
        """Liest Daten aus dem Register (ohne Output zu aktivieren)."""
        await FallingEdge(self.clk)
        self.select_op.value = 0  # read by key
        self.key_in.value = key
        
        await RisingEdge(self.clk)
        self.select_op.value = 0  # Read beenden
        await RisingEdge(self.clk)  # Warten auf die Ausgabe
        return self.value_out.value


    async def read_by_index(self, idx: int):
        """Liest Daten aus dem Register (ohne Output zu aktivieren)."""
        await FallingEdge(self.clk)
        self.select_op.value = 1  # read by index
        self.index.value = idx
        
        await RisingEdge(self.clk)
        self.select_op.value = 0  # Read beenden
        await RisingEdge(self.clk)  # Warten auf die Ausgabe
        return self.key_out.value, self.value_out.value


    async def get_used_entries(self):
        """Liest die Anzahl der verwendeten Einträge aus."""
        await FallingEdge(self.clk)
        return bin(self.used_entries.value).count('1')


    async def get_cell_value_by_index(self, idx: int):
        """Read the value stored in a specific memory cell."""
        await FallingEdge(self.clk)
        self.index.value = idx
        await RisingEdge(self.clk)
        return self.key_out.value, self.value_out.value

    


@cocotb.test()
async def test_reset(dut):
    """Test: Reset-Verhalten überprüfen."""
    
    tester = MemoryBlockTester(dut)
    
    # Start clock
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await tester.write(0, 0xF, 0xF)  # Vor dem Reset einen Wert schreiben, um sicherzustellen, dass Reset funktioniert

    # 1. Reset
    await tester.reset()

    await RisingEdge(tester.clk) 

    # check that no line is used
    assert await tester.get_used_entries() == 0, \
        f"Reset failed! Expected 0 used entries, got {await tester.get_used_entries()}"

    # check that all cells are resetted to contain no data
    for i in range(tester.dut.NUM_ENTRIES.value):
        key, value = await tester.get_cell_value_by_index(i)
        assert key == 0, \
            f"Reset failed! Expected key 0 in cell {i}, got {hex(key)}"
        assert value == 0, \
            f"Reset failed! Expected value 0 in cell {i}, got {hex(value)}"

    # check that output of module is also set to 0
    assert tester.key_out.value == 0, \
        f"Reset failed! Expected key_out 0, got {hex(tester.key_out.value)}"
    assert tester.value_out.value == 0, \
        f"Reset failed! Expected value_out 0, got {hex(tester.value_out.value)}"


@cocotb.test()
async def test_writing_memory_block(dut):
    """Test: check if memory can write into a single cell and read it back."""

    tester = MemoryBlockTester(dut)
    
    # Start clock
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # 1. Reset
    await tester.reset()

    # 2. Schreiben
    key = random.randint(0, 15)  # Schlüssel im Bereich der Adressierung
    value = random.randint(0, 15)  # Wert im Bereich der Wertbreite
    await tester.write(0, key, value)

    # 3. Lesen und Überprüfen
    read_value = await tester.read_by_key(key)
    
    assert read_value == value, f"Expected value {value} for key {key}, but got {read_value}."


@cocotb.test()
async def test_used_entries(dut):
    """Test: check if used_entries signal correctly reflects the number of used entries."""

    tester = MemoryBlockTester(dut)
    
    # Start clock
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # 1. Reset
    await tester.reset()

    # 2. Schreiben von mehreren Einträgen
    num_entries = tester.dut.NUM_ENTRIES.value
    for i in range(num_entries):
        key = i + 1  # Schlüssel im Bereich der Adressierung
        value = (i + 1) * 2  # Wert im Bereich der Wertbreite
        await tester.write(i, key, value)

        # Überprüfen der Anzahl der verwendeten Einträge nach jedem Schreibvorgang
        used_entries = await tester.get_used_entries()
        assert used_entries == i + 1, f"Expected {i + 1} used entries after writing {i + 1} entries, but got {used_entries}."

@cocotb.test()
async def test_reading_cell_by_key(dut):
    """Test: check if we can read the value of a cell by its key."""

    tester = MemoryBlockTester(dut)
    
    # Start clock
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # 1. Reset
    await tester.reset()

    # 2. Schreiben von mehreren Einträgen
    num_entries = tester.dut.NUM_ENTRIES.value
    for i in range(num_entries):
        key = i + 1  # Schlüssel im Bereich der Adressierung
        value = (i + 1) * 2  # Wert im Bereich der Wertbreite
        await tester.write(i, key, value)

        # Lesen des Werts über den Schlüssel und Überprüfen der Korrektheit
        read_value = await tester.read_by_key(key)
        assert read_value == value, f"Expected value {value} for key {key}, but got {read_value}."

@cocotb.test()
async def test_reading_cell_by_index(dut):
    """Test: check if we can read the value of a cell by its index."""

    tester = MemoryBlockTester(dut)
    
    # Start clock
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # 1. Reset
    await tester.reset()

    # 2. Schreiben von mehreren Einträgen
    num_entries = tester.dut.NUM_ENTRIES.value
    for i in range(num_entries):
        key = i + 1  # Schlüssel im Bereich der Adressierung
        value = (i + 1) * 2  # Wert im Bereich der Wertbreite
        await tester.write(i, key, value)

        await FallingEdge(tester.clk)  # Warten auf die Stabilisierung der Werte in den Zellen

        # Lesen des Werts über den Index und Überprüfen der Korrektheit
        read_key, read_value = await tester.get_cell_value_by_index(i)
        assert read_key == key, f"Expected key {key} at index {i}, but got {read_key}."
        assert read_value == value, f"Expected value {value} at index {i}, but got {read_value}."


@cocotb.test()
async def test_reading_cell_by_select_with_input_key_matching(dut):
    """Test: check if we can read the value of a cell by its key using the select operation."""

    tester = MemoryBlockTester(dut)
    
    # Start clock
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # 1. Reset
    await tester.reset()

    # 2. Schreiben von mehreren Einträgen
    num_entries = tester.dut.NUM_ENTRIES.value
    for i in range(num_entries):
        key = i + 1  # Schlüssel im Bereich der Adressierung
        value = (i + 1) * 2  # Wert im Bereich der Wertbreite
        await tester.write(i, key, value)

    # Lesen der Zelle an der Stelle 0 über die select Operation und Überprüfen ob mit einem matchendem Schlüssel
    # Zelleninhalt vom Index übernommen wird
    dut.index.value = 0  # Index auf die erste Zelle setzen
    dut.key_in.value = 2  # Schlüssel setzen, der mit dem ersten Eintrag übereinstimmt
    dut.select_op.value = 1  # Select-Operation aktivieren
    await RisingEdge(tester.clk)  # Warten auf die Ausgabe
    
    assert tester.key_out.value == 1, f"Expected key_out 1 for select operation with matching index, but got {tester.key_out.value}."
    assert tester.value_out.value == 2, f"Expected value_out 2 for select operation with matching index, but got {tester.value_out.value}."


def test_memory_block_runner():
    sim = os.getenv("SIM", "icarus")

    proj_path = Path(__file__).resolve().parent

    sources = [proj_path / ".." / "src" / "memory_block.sv"]

    runner = get_runner(sim)

    parameters = {
        "NUM_ENTRIES": 2, 
        "KEY_WIDTH": 4, 
        "VALUE_WIDTH": 4
    }

    sources = [
        proj_path / ".." / "src" / "memory_block.sv",
        proj_path / ".." / "src" / "memory_cell.sv",
        proj_path / ".." / "src" / "memory_dynamic_registerarray.sv"
    ]

    runner.build(
        sources=sources,
        hdl_toplevel="memory_block",
        parameters=parameters,
        always=True,
        waves=True,
        timescale=("1ns", "1ps"),
    )


    runner.test(
        hdl_toplevel="memory_block", 
        test_module="test_memory_block", 
        waves=True
    )

if __name__ == "__main__":
    test_memory_block_runner()
