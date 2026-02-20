"""
Modern cocotb 2.0 testbench for the Controller module.
Uses async/await syntax and modern pythonic patterns.
"""

import os
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ReadOnly
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

        self.index_out = dut.index_out
        self.write_op = dut.write_in
        self.select_by_index = dut.select_by_index
        self.delete_op = dut.delete_in

        self.index_in = dut.index_in
        self.key_in = dut.key_in
        self.value_in = dut.value_in

        self.value_out = dut.value_out
        self.hit = dut.hit
        
        self.used_entries = dut.used_entries


    async def reset(self):
        """Führt einen Reset durch (Active High Reset)."""
        self.rst_n.value = 0
        self.key_in.value = 0
        self.value_in.value = 0
        self.write_op.value = 0
        self.delete_op.value = 0
        self.select_by_index.value = 0

        await ReadOnly()
        
        await FallingEdge(self.clk)
        self.rst_n.value = 1  # Reset lösen
        await FallingEdge(self.clk)


    async def write(self, idx: int, key: int, value: int):
        """Schreibt Daten in das Register (ohne Output zu aktivieren)."""
        await RisingEdge(self.clk)
        self.write_op.value = 1  # Write-Operation aktivieren
        self.index_in.value = 1 << idx   # idx=0 → 0b01, idx=1 → 0b10

        self.key_in.value = key
        self.value_in.value = value

        await ReadOnly()

        self.dut._log.info(f"Writing key {key} with value {value} at index {idx}.")

        await FallingEdge(self.clk)

        await RisingEdge(self.clk) 
        self.write_op.value = 0  # Write beenden
        self.index_in.value = 0  # Index zurücksetzen
        self.key_in.value = 0
        self.value_in.value = 0

    async def read_by_key(self, key: int):
        """Liest Daten aus dem Register (ohne Output zu aktivieren)."""
        self.select_by_index.value = 0  # read by key
        self.key_in.value = key
        
        await RisingEdge(self.clk)
        await ReadOnly()
        return self.value_out.value



    async def get_used_entries(self):
        """Liest die Anzahl der verwendeten Einträge aus."""
        self.dut._log.info(f"Used entries bitmask: {self.used_entries.value}")
        print(f"Used entries calculation: {self.used_entries.value.count('1')} used entries.")
        return self.used_entries.value.count('1')


    async def get_all_cells(self):
        """Liest die Werte aller Zellen aus."""
        cells = []
        for i in range(self.dut.NUM_ENTRIES.value):
            value = await self.get_cell_value_by_index(i)
            cells.append(value)
        return cells


    async def get_cell_value_by_index(self, idx: int):
        """Read the value stored in a specific memory cell."""
        self.select_by_index.value = 1  # read by index
        self.index_in.value = 1 << idx
        
        await RisingEdge(self.clk)
        await ReadOnly()
        value = self.value_out.value  # capture value BEFORE clearing select

        await RisingEdge(self.clk)
        self.select_by_index.value = 0  # Read beenden
        self.index_in.value = 0
        return value


@cocotb.test()
async def test_reset(dut):
    """Test: Reset-Verhalten überprüfen."""
    
    tester = MemoryBlockTester(dut)
    
    # Start clock
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await tester.write(0, 0xF, 0xF)  # Vor dem Reset einen Wert schreiben, um sicherzustellen, dass Reset funktioniert

    # 1. Reset
    await tester.reset()

    await FallingEdge(tester.clk) 

    # check that no line is used
    assert await tester.get_used_entries() == 0, \
        f"Reset failed! Expected 0 used entries, got {await tester.get_used_entries()}"

    # check that all cells are resetted to contain no data
    for i in range(tester.dut.NUM_ENTRIES.value):
        value = await tester.get_cell_value_by_index(i)
        assert value == 0, \
            f"Reset failed! Expected value 0 in cell {i}, got {hex(value)}"

    # check that output of module is also set to 0
    assert tester.hit.value == 0, \
        f"Reset failed! Expected hit 0, got {tester.hit.value}"
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

    await RisingEdge(tester.clk)

    # 2. Schreiben
    key = random.randint(0, 15)  # Schlüssel im Bereich der Adressierung
    value = random.randint(0, 15)  # Wert im Bereich der Wertbreite

    tester.key_in.value = key
    tester.value_in.value = value
    tester.write_op.value = 1  # Write-Operation aktivieren
    tester.index_in.value = 1 << 0  # Schreiben in die erste Zelle

    await RisingEdge(tester.clk)
    await ReadOnly()  

    assert tester.hit.value == 1, f"Expected hit signal to be 1 after writing, but got {tester.hit.value}."
    assert tester.value_out.value == value, f"Expected value_out {value} after writing, but got {tester.value_out.value}."
    assert await tester.get_used_entries() == 1, f"Expected 1 used entry after writing, but got {await tester.get_used_entries()}."
    assert tester.index_out.value == 1 << 0, f"Expected index 0 after writing to the first cell, but got {tester.index_out.value}."


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

        await ReadOnly()  
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

        assert dut.hit.value == 1, f"Expected hit signal to be 1 for key {key}, but got {dut.hit.value} for idx {i}."
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


    all_cells = await tester.get_all_cells()
    print(f"All cells: {all_cells}")

    # Lesen der zellen an den Stellen über die select Operation und Überprüfen ob mit einem matchendem Schlüssel
    for i in range(num_entries):
        await FallingEdge(tester.clk)
        dut.index_in.value = 1 << i  # Index auf die Zelle setzen
        dut.select_by_index.value = 1  # Read-Operation aktivieren
        
        await RisingEdge(tester.clk)
        await ReadOnly()
        expected_value = (i + 1) * 2

        assert tester.hit.value == 1, f"Expected hit signal to be 1 for select operation with index {i}, but got {tester.hit.value}."
        assert tester.value_out.value == expected_value, f"Expected value_out {expected_value} for select operation with index {i}, but got {tester.value_out.value}."

@cocotb.test()
async def test_reading_cell_by_select_with_input_key_matching(dut):
    """Test: check if we can read the value of a cell by its key"""

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


    for i in range(num_entries):
        await FallingEdge(tester.clk)
        # Lesen der Zelle über key
        dut.index_in.value = 0  # Index auf die erste Zelle setzen
        dut.key_in.value = i + 1  # Schlüssel setzen, der mit dem ersten Eintrag übereinstimmt
        dut.select_by_index.value = 0  # Read-Operation aktivieren
        
        await RisingEdge(tester.clk)
        await ReadOnly()

        assert tester.hit.value == 1, f"Expected hit signal to be 1 for select operation with matching index, but got {tester.hit.value}."
        assert tester.value_out.value == (i + 1) * 2, f"Expected value_out {(i + 1) * 2} for select operation with matching index, but got {tester.value_out.value}."

@cocotb.test()
async def test_reading_cell_by_select_with_input_key_not_matching(dut):
    """Test: check if we can read the value of a cell by its key"""

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

    # Lesen der Zelle über key
    dut.index_in.value = 0  # Index auf die erste Zelle setzen
    dut.key_in.value = 15  # Schlüssel setzen, der mit keinem Eintrag übereinstimmt
    dut.select_by_index.value = 0  # Read-Operation aktivieren
    
    await RisingEdge(tester.clk)
    await ReadOnly()

    assert tester.hit.value == 0, f"Expected hit signal to be 0 for select operation with non-matching index, but got {tester.hit.value}."
    assert tester.value_out.value == 0, f"Expected value_out 0 for select operation with non-matching index, but got {tester.value_out.value}."


@cocotb.test()
async def test_deleting_entry(dut):
    """Test: check if we can delete an entry and that it is properly deleted."""

    tester = MemoryBlockTester(dut)
    
    # Start clock
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # 1. Reset
    await tester.reset()

    # 2. Schreiben von mehreren Einträgen
    num_entries = int(tester.dut.NUM_ENTRIES.value)
    for i in range(num_entries):
        key = i + 1  # Schlüssel im Bereich der Adressierung
        value = (i + 1) * 2  # Wert im Bereich der Wertbreite
        await tester.write(i, key, value)

    # Löschen des Eintrags an Index 0
    tester.index_in.value = 1 << 0  # Index auf die erste Zelle setzen
    tester.delete_op.value = 1  # Delete-Operation aktivieren
    
    await RisingEdge(tester.clk)
    tester.delete_op.value = 0

    # Überprüfen, dass der Eintrag gelöscht wurde
    assert await tester.get_used_entries() == num_entries - 1, f"Expected {num_entries - 1} used entries after deletion, but got {await tester.get_used_entries()}."

    value_after_delete = await tester.get_cell_value_by_index(0)
    assert value_after_delete == 0, f"Expected value 0 in cell after deletion, but got {hex(value_after_delete)}."
    assert tester.hit.value == 0, f"Expected hit signal to be 0 after deletion, but got {tester.hit.value}."


@cocotb.test()
async def test_deleting_all_entries(dut):
    """Test: check if we can delete all entries and that they are properly deleted."""

    tester = MemoryBlockTester(dut)
    
    # Start clock
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # 1. Reset
    await tester.reset()

    # 2. Schreiben von mehreren Einträgen
    num_entries = int(tester.dut.NUM_ENTRIES.value)
    for i in range(num_entries):
        key = i + 1  # Schlüssel im Bereich der Adressierung
        value = (i + 1) * 2  # Wert im Bereich der Wertbreite
        await tester.write(i, key, value)

    # Löschen aller Einträge
    for i in range(num_entries):
        tester.index_in.value = 1 << i  # Index auf die Zelle setzen
        tester.delete_op.value = 1  # Delete-Operation aktivieren
        await RisingEdge(tester.clk)
        tester.delete_op.value = 0

    # Überprüfen, dass alle Einträge gelöscht wurden
    assert await tester.get_used_entries() == 0, f"Expected 0 used entries after deleting all entries, but got {await tester.get_used_entries()}."

    for i in range(num_entries):
        value_after_delete = await tester.get_cell_value_by_index(i)
        assert value_after_delete == 0, f"Expected value 0 in cell {i} after deletion, but got {hex(value_after_delete)}."
        assert tester.hit.value == 0, f"Expected hit signal to be 0 after deletion of cell {i}, but got {tester.hit.value}."


@cocotb.test()
async def test_overwriting_entry(dut):
    """Test: check if we can overwrite an existing entry and that the new value is properly stored."""

    tester = MemoryBlockTester(dut)
    
    # Start clock
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # 1. Reset
    await tester.reset()

    # 2. Schreiben eines Eintrags
    key = 1  # Schlüssel im Bereich der Adressierung
    value = 2  # Wert im Bereich der Wertbreite
    await tester.write(0, key, value)

    # Überschreiben des Eintrags an Index 0
    new_key = 3
    new_value = 6
    await tester.write(0, new_key, new_value)

    all_cells = await tester.get_all_cells()

    print(f"Cells after overwriting: {all_cells}")

    await ReadOnly()
    # Überprüfen, dass der Eintrag überschrieben wurde
    assert await tester.get_used_entries() == 1, f"Expected 1 used entry after overwriting, but got {await tester.get_used_entries()}."

    await RisingEdge(tester.clk)
    value_after_overwrite = await tester.get_cell_value_by_index(0)
    assert value_after_overwrite == new_value, f"Expected value {new_value} in cell after overwriting, but got {hex(value_after_overwrite)}."
    assert tester.hit.value == 1, f"Expected hit signal to be 1 after overwriting, but got {tester.hit.value}."

@cocotb.test()
async def test_writing_until_full(dut):
    """Test: check if we can write entries until the memory block is full and that it correctly reflects the full state."""

    tester = MemoryBlockTester(dut)
    
    # Start clock
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # 1. Reset
    await tester.reset()

    # 2. Schreiben von Einträgen bis zum Maximum
    num_entries = int(tester.dut.NUM_ENTRIES.value)
    for i in range(num_entries):
        key = i + 1  # Schlüssel im Bereich der Adressierung
        value = (i + 1) * 2  # Wert im Bereich der Wertbreite
        await tester.write(i, key, value)

        await ReadOnly()  
        used_entries = await tester.get_used_entries()
        assert used_entries == i + 1, f"Expected {i + 1} used entries after writing {i + 1} entries, but got {used_entries}."

@cocotb.test()
async def test_persistence_of_entries(dut):
    """Test: check if entries persist correctly across multiple write and delete operations."""

    tester = MemoryBlockTester(dut)
    
    # Start clock
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await tester.reset()

    # 2. Schreiben von mehreren Einträgen
    num_entries = int(tester.dut.NUM_ENTRIES.value)
    for i in range(num_entries):
        key = i + 1  # Schlüssel im Bereich der Adressierung
        value = (i + 1) * 2  # Wert im Bereich der Wertbreite
        await tester.write(i, key, value)

    # Löschen eines Eintrags und Überprüfen der Persistenz der anderen Einträge
    tester.index_in.value = 1 << 0  # Index auf die erste Zelle setzen
    tester.delete_op.value = 1  # Delete-Operation aktivieren
    await RisingEdge(tester.clk)
    tester.delete_op.value = 0  # Delete-Operation beenden

    assert await tester.get_used_entries() == num_entries - 1, f"Expected {num_entries - 1} used entries after deletion, but got {await tester.get_used_entries()}."

    # simulate multiple clock cycles
    for _ in range(5):
        await RisingEdge(tester.clk)

    for i in range(1, num_entries):  # Überprüfen der verbleibenden Einträge (Index 1 bis num_entries-1)
        value_after_delete = await tester.get_cell_value_by_index(i)
        expected_value = (i + 1) * 2
        assert value_after_delete == expected_value, f"Expected value {expected_value} in cell {i} after deletion of cell 0, but got {hex(value_after_delete)}."
        assert tester.hit.value == 1, f"Expected hit signal to be 1 for cell {i} after deletion of cell 0, but got {tester.hit.value}."


def test_memory_block_runner():
    sim = os.getenv("SIM", "icarus")

    proj_path = Path(__file__).resolve().parent

    sources = [proj_path / ".." / "src" / "memory_block.sv"]

    runner = get_runner(sim)

    parameters = {
        "NUM_ENTRIES": 4, 
        "KEY_WIDTH": 4, 
        "VALUE_WIDTH": 8
    }

    sources = [
        proj_path / ".." / ".." / "top" / "src" / "cache_cfg_pkg.sv",
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
