import os
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ReadOnly
from cocotb_tools.runner import get_runner
        

class TopTester:
    """Helper class for Controller."""

    def __init__(self, dut):
        self.dut = dut
        self.clk = dut.clk
        self.rst_n = dut.rst_n

        self.u_obi = dut.u_obi
        self.u_ctrl = dut.u_ctrl
        self.u_mem = dut.u_mem
    
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

def pack_obi_req(addr=0, we=0, be=0, wdata=0, req=0, aid=0, a_optional=0):
    """
    Hilfsfunktion, um das OBI Request Struct in einen flachen Bitvektor zu packen.
    Reihenfolge (MSB -> LSB): addr, we, be, wdata, aid, a_optional, req
    """
    val = addr
    val = (val << 1) | we
    val = (val << 4) | be
    val = (val << 32) | wdata
    val = (val << 1) | aid         # Falls ID_WIDTH in obi_pkg.sv anders ist, Shift anpassen!
    val = (val << 1) | a_optional
    val = (val << 1) | req
    return val

async def obi_write(dut, addr, wdata, be=0xF):
    """Hilfsfunktion für einen vollständigen OBI Write-Handshake."""
    dut.obi_req_i.value = pack_obi_req(addr=addr, we=1, be=be, wdata=wdata, req=1)
    
    # Warten auf das Grant-Signal (Handshake)
    while True:
        await RisingEdge(dut.clk)
        resp_val = int(dut.obi_resp_o.value)
        gnt_bit = (resp_val >> 1) & 1 
        if gnt_bit == 1:
            break
            
    # Request wieder auf 0 ziehen
    dut.obi_req_i.value = pack_obi_req()
    await RisingEdge(dut.clk)

async def execute_cache_operation(dut, tester, operation, key, value=0):
    """
    Führt eine Cache-Operation über das OBI-Interface aus.
    
    :param operation: String ('UPSERT', 'GET' oder 'DELETE')
    :param key: Der Schlüssel für die Operation
    :param value: Der zu schreibende Wert (wird nur bei UPSERT verwendet)
    """
    # Mapping der Operationen auf ihre numerischen Werte (aus ctrl_types_pkg.sv)
    op_map = {
        'GET': 1,
        'READ': 1,     # Ist das Gleiche
        'UPSERT': 2,
        'DELETE': 3
    }
    
    op_code = op_map.get(operation.upper())
    if op_code is None:
        raise ValueError(f"Unbekannte Operation: {operation}")

    dut._log.info(f"--- Starte Operation: {operation.upper()} | Key: {hex(key)} ---")

    # 1. Nur bei UPSERT müssen wir das Daten-Register (Value) befüllen
    if op_code == 2:
        await obi_write(dut, addr=0, wdata=value)
        
    # 2. Alle Operationen (UPSERT, GET, DELETE) benötigen den Key
    await obi_write(dut, addr=8, wdata=key)
    
    # 3. Kommando im Control-Register absetzen
    # Das Interface erwartet die Operation in den Bits [3:1], also op_code << 1
    await obi_write(dut, addr=12, wdata=(op_code << 1), be=1)
    
    # 4. Dem Controller Zeit geben, um in den jeweiligen Arbeits-State zu wechseln
    #await tester.wait_cycles(1)
    
    # 5. Warten bis der Controller wieder in IDLE (0) zurückkehrt
    # Timeout einbauen um Endlosschleifen bei FSM-Fehlern zu vermeiden
    timeout = 20
    cycles = 0
    while int(tester.u_ctrl.state.value) != 0:
        await tester.wait_cycles(1)
        cycles += 1
        if cycles > timeout:
            raise TimeoutError(f"TIMEOUT: Controller ist nach {timeout} Zyklen nicht in den IDLE State zurückgekehrt!")
            
    dut._log.info(f"Operation {operation.upper()} abgeschlossen (Dauer: {cycles} Zyklen).")

@cocotb.test()
async def test_reset(dut):
    """Test: Verify controller initializes to IDLE state after reset."""
    tester = TopTester(dut)
    
    # Start clock
    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())
    
    
    # Apply reset
    await tester.reset()
    
    # Verify state is IDLE (0)
    assert tester.u_ctrl.state.value == 0, f"State mismatch: {dut.u_ctrl.state.value} != 0 (IDLE)"
    assert tester.u_mem.used_entries.value == 0b0, f"Used mismatch: {dut.u_mem.used_entries.value} != 0 (Empty)"
   
    dut._log.info("✓ Reset test passed")

@cocotb.test()
async def test_upsert_simple(dut):
    """Test: Insert a value into the cache and verify success."""
    tester = TopTester(dut)
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    
    # 1. Reset
    await tester.reset()
    
    test_key = 0xBEEF
    test_val = 0x8765FFFF

    await execute_cache_operation(dut, tester, 'UPSERT', key=test_key, value=test_val)

    assert tester.u_mem.used_entries.value == 0b1, "Fehler: Das used-Bit für den ersten Eintrag wurde nicht gesetzt!"
    
    dut._log.info("✓ Upsert test passed")

@cocotb.test()
async def test_upsert_simple2(dut):
    """Test: Insert two values into the cache and verify success."""
    tester = TopTester(dut)
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    
    # 1. Reset
    await tester.reset()
    
    # ==========================================
    # --- ERSTER EINTRAG ---
    # ==========================================
   
    await execute_cache_operation(dut, tester, 'UPSERT', key=0x42, value=0xDEADBEEF)
    dut._log.info(f"Memory Used Entries: {tester.u_mem.used_entries.value}")
    assert tester.u_mem.used_entries.value == 0b1, f"Fehler nach Upsert 1: used={tester.u_mem.used_entries.value}"

    # ==========================================
    # --- ZWEITER EINTRAG ---
    # ==========================================
    
    await execute_cache_operation(dut, tester, 'UPSERT', key=0x99, value=0xCAFEBABE)
    dut._log.info(f"Memory Used Entries: {tester.u_mem.used_entries.value}")
    assert tester.u_mem.used_entries.value == 0b11, f"Fehler nach Upsert 2: used={tester.u_mem.used_entries.value}"
    
    dut._log.info("✓ Double Upsert test passed")

@cocotb.test()
async def test_upsert_get_delete(dut):
    """Test: Insert a value, read it, delete it, and verify it is gone."""
    tester = TopTester(dut)
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    
    # 1. Reset
    await tester.reset()
    
    test_key = 0x55
    test_val = 0x12345678

    # ==========================================
    # --- 1. EINTRAG SCHREIBEN (UPSERT) ---
    # ==========================================
    dut._log.info("1. Schreibe Eintrag...")
    await execute_cache_operation(dut, tester, 'UPSERT', key=test_key, value=test_val)
    
    dut._log.info(f"Memory Used Entries nach UPSERT: {tester.u_mem.used_entries.value}")
    assert tester.u_mem.used_entries.value == 0b1, f"Fehler nach Upsert: used={tester.u_mem.used_entries.value}"
    
    # ==========================================
    # --- 2. EINTRAG LÖSCHEN (DELETE) ---
    # ==========================================
    dut._log.info("3. Lösche Eintrag (DELETE)...")
    await execute_cache_operation(dut, tester, 'DELETE', key=test_key)
    
    dut._log.info(f"Memory Used Entries nach DELETE: {tester.u_mem.used_entries.value}")
    # Nach dem Löschen muss das used-Bit wieder auf 0 gehen
    assert tester.u_mem.used_entries.value == 0b0, f"Fehler nach Delete: used={tester.u_mem.used_entries.value} (Sollte wieder 0 sein!)"


def test_top_runner():
    #sim = os.getenv("SIM", "icarus")
    sim = "verilator"
    proj_path = Path(__file__).resolve().parent
    src_root = proj_path.parent.parent
    obi_root = src_root.parent
    
    sources = [
        obi_root / "obi" / ".bender" / "git" / "checkouts" / "common_cells-f02d7eeaa3b89547" / "src" / "cf_math_pkg.sv",
        obi_root / "obi" / "src" / "obi_pkg.sv",
        src_root / "redis_cache" / "src" / "cache_cfg_pkg.sv",
        src_root / "controller" / "src" / "ctrl_types_pkg.sv",
        src_root / "interface" / "src" / "if_types_pkg.sv",
        src_root / "interface" / "src" / "obi_interface.sv",
        src_root / "controller" / "src" / "controller.sv",
        src_root / "controller" / "src" / "upsert_fsm.sv",
        src_root / "controller" / "src" / "del_fsm.sv",
        src_root / "controller" / "src" / "get_fsm.sv",
        src_root / "memory" / "src" / "memory_block.sv",
        src_root / "memory" / "src" / "memory_cell.sv",
        src_root / "memory" / "src" / "memory_dynamic_registerarray.sv",
        src_root / "redis_cache" / "src" / "redis_cache.sv",
    ]

    

    parameters = {
        "NUM_ENTRIES": 16,
        "KEY_WIDTH": 16,
        "VALUE_WIDTH": 64
    }

    include_dirs = [
        obi_root / "obi" / "include",   # include obi/include for the if_types_pkg
    ]

    build_args = []
    if sim == "verilator":
        build_args = ["-Wno-fatal", "-Wno-lint", "-Wno-style"]
        #patch_cocotb_verilator_cpp()

    runner = get_runner(sim)

    runner.build(
        sources=sources,
        hdl_toplevel="redis_cache",
        always=True, 
        waves=True,
        timescale=("1ns", "1ps"),
        parameters=parameters,
        includes=include_dirs,
        build_args=build_args
    )

    runner.test(
        hdl_toplevel="redis_cache", 
        test_module="test_redis_cache", 
        waves=True
    )

if __name__ == "__main__":
    test_top_runner()