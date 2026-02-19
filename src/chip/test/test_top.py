import os
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ReadOnly, ClockCycles
from cocotb_tools.runner import get_runner

from enum import Enum

os.environ['COCOTB_ANSI_OUTPUT'] = '1'

class OBIState(Enum):
    IDLE = 0
    PROCESS = 1
    COMPLETE = 2

class ControllerState(Enum):
    ST_IDLE = 0
    ST_GET = 1
    ST_UPSERT = 2
    ST_DEL = 3
    ST_ERR = 4


class TopTester:
    """Helper class for the Chip Top Level."""

    # Bit-field positions inside obi_req_t  (75-bit packed struct)
    _RREADY_BIT   = 0
    _REQ_BIT      = 1
    _A_OPT_BIT    = 2
    _AID_LSB      = 3   # 3 bits [5:3]
    _WDATA_LSB    = 6   # 32 bits [37:6]
    _BE_LSB       = 38  # 4 bits [41:38]
    _WE_BIT       = 42
    _ADDR_LSB     = 43  # 32 bits [74:43]

    # Bit-field positions inside obi_rsp_t (39-bit packed struct)
    _RVALID_BIT   = 0
    _GNT_BIT      = 1
    _R_OPT_BIT    = 2
    _ERR_BIT      = 3
    _RID_LSB      = 4   # 3 bits [6:4]
    _RDATA_LSB    = 7   # 32 bits [38:7]

    _VALUE_OFFSET = 0x00
    _KEY_OFFSET   = 0x40
    _OPERATION_OFFSET = 0x60

    def __init__(self, dut):
        self.dut = dut
        self.clk = dut.clk
        self.rst_n = dut.rst_n
        self.obi_req_i = dut.obi_req_i
        self.obi_resp_o = dut.obi_resp_o

        # Internal hierarchy handles for White-Box Testing
        self.u_obi = dut.u_obi
        self.u_ctrl = dut.u_ctrl
        self.u_mem = dut.u_mem

    async def reset(self):
        """Apply reset pulse."""
        self.rst_n.value = 0
        self.obi_req_i.value = 0
        await RisingEdge(self.clk)
        self.rst_n.value = 1
        await RisingEdge(self.clk)

    @staticmethod
    def split_obi_rsp(obi_resp):
        """Split a packed obi_rsp_t into individual fields.
        
        Returns: (rdata, err, rid, r_optional, gnt, rvalid)
        """
        print(f"Raw obi_resp value: {str(obi_resp)}")
        #print(f"Raw obi_resp value: 0b{int(obi_resp):039b}")
        # Convert LogicArray to integer for bitwise operations
        #val = int(obi_resp)

        try:
            val = int(obi_resp)
        except ValueError:
            val = 0
            for bit in str(obi_resp):
                val = (val << 1) | (1 if bit == '1' else 0)

        rvalid = val & 0x1
        gnt = (val >> TopTester._GNT_BIT) & 0x1
        r_optional = (val >> TopTester._R_OPT_BIT) & 0x1
        err = (val >> TopTester._ERR_BIT) & 0x1
        rid = (val >> TopTester._RID_LSB) & 0x7
        rdata = (val >> TopTester._RDATA_LSB) & 0xFFFFFFFF
        gnt = (val >> TopTester._GNT_BIT) & 0x1
        r_optional = (val >> TopTester._R_OPT_BIT) & 0x1
        err = (val >> TopTester._ERR_BIT) & 0x1
        rid = (val >> TopTester._RID_LSB) & 0x7
        rdata = (val >> TopTester._RDATA_LSB) & 0xFFFFFFFF
        return (rdata, err, rid, r_optional, gnt, rvalid)

    @staticmethod
    def build_obi_req(addr=0, we=0, be=0, wdata=0, aid=0, a_optional=0,
                      req=0, rready=0):
        """Construct the integer value of a packed obi_req_t."""
        val  = (rready   & 0x1)          << TopTester._RREADY_BIT
        val |= (req      & 0x1)          << TopTester._REQ_BIT
        val |= (a_optional & 0x1)        << TopTester._A_OPT_BIT
        val |= (aid      & 0x7)          << TopTester._AID_LSB
        val |= (wdata    & 0xFFFFFFFF)   << TopTester._WDATA_LSB
        val |= (be       & 0xF)          << TopTester._BE_LSB
        val |= (we       & 0x1)          << TopTester._WE_BIT
        val |= (addr     & 0xFFFFFFFF)   << TopTester._ADDR_LSB
        return val


    async def obi_write(self, address, data, **kwargs):
            """Perform an OBI write transaction."""
            await FallingEdge(self.clk)
            self.obi_req_i.value = self.build_obi_req(
                addr=address, wdata=data, **kwargs
            )

    async def write_set_master_data_with_handshake(self, address, data, **kwargs):
        """Perform an OBI write transaction and wait for gnt."""
        await FallingEdge(self.clk)

        kwargs['req'] = kwargs.get('req', 1)
        kwargs['we'] = kwargs.get('we', 1)

        kwargs

        self.obi_req_i.value = self.build_obi_req(
            addr=address, wdata=data, **kwargs
        )
        await RisingEdge(self.clk)  # Wait for req to be registered
        await ReadOnly()  # Wait for combinational logic to settle

        # wait one more cycle for the internal register to hold the value
        await RisingEdge(self.clk)
        await ReadOnly()  # Wait for combinational logic to settle

    def log_obi_status(self):
        """Log internal state of OBI Interface for debugging."""
        self.dut._log.info("--- OBI Interface Status ---")
        self.dut._log.info(f"State: {self.u_obi.state.value}")
        self.dut._log.info("")
        self.dut._log.info(f"Decoded Op: {self.u_obi.decoded_operation.value}")
        self.dut._log.info(f"Decoded Key: {self.u_obi.decoded_key.value}")
        self.dut._log.info(f"Decoded Val: {self.u_obi.decoded_value.value}")
        self.dut._log.info(f"Current Request: {self.u_obi.current_request.value}")
        self.dut._log.info("")
        self.dut._log.info(f"Internal_grant Val: {self.u_obi.internal_gnt.value}")
        self.dut._log.info(f"Write or Read Operation: {self.u_obi.write_or_read_operation.value}")
        self.dut._log.info(f"Ready in: {self.u_obi.ready_in.value}")
        self.dut._log.info("")
        self.dut._log.info(f"Next State: {self.u_obi.next_state.value}")
        self.dut._log.info("----------------------------\n")

    async def wait_cycles(self, num_cycles: int):
        """Wait for specified number of clock cycles."""
        for _ in range(num_cycles):
            await RisingEdge(self.clk)

@cocotb.test()
async def test_reset(dut):
    """Test: Verify reset behavior of the top module."""
    tester = TopTester(dut)
    
    # Start clock
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    
    # Apply reset
    await tester.reset()
    
    await ReadOnly()

    ####################
    # Check Obi interface
    ####################
    assert tester.u_obi.state.value == OBIState.IDLE.value, \
        f"OBI Interface FSM should be IDLE (0), got {tester.u_obi.state.value}"
    
    rdata, err, rid, r_optional, gnt, rvalid = tester.split_obi_rsp(tester.obi_resp_o.value)
    
    assert rdata == 0, f"OBI RData should be 0, got {rdata}"
    assert err == 0, f"OBI Error should be 0, got {err}"
    assert rid == 0, f"OBI Request ID should be 0, got {rid}"
    assert r_optional == 0, f"OBI ROptional should be 0, got {r_optional}"
    assert gnt == 0, f"OBI Grant should be 0, got {gnt}"
    assert rvalid == 0, f"OBI RValid should be 0, got {rvalid}"


    ####################
    # Check Controller 
    ####################
    assert tester.u_ctrl.state.value == ControllerState.ST_IDLE.value, \
        f"Controller FSM should be IDLE (0), got {tester.u_ctrl.state.value}"


    ####################
    # Check Memory
    ####################
    # check that no line is used
    assert tester.u_mem.used_entries.value == 0, \
        f"Memory should be empty (used_entries=0), got {tester.u_mem.used_entries.value}"

    # check that output of module is also set to 0
    assert tester.u_mem.hit.value == 0, \
        f"Memory hit should be 0, got {tester.u_mem.hit.value}"
    assert tester.u_mem.value_out.value == 0, \
        f"Memory value_out should be 0, got {tester.u_mem.value_out.value}"
    

    dut._log.info("✓ Reset test passed")

@cocotb.test()
async def test_insert_simple(dut):
    """Test: Insert a value into the cache and verify success."""
    tester = TopTester(dut)
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    
    await tester.reset()

    assert tester.u_obi.internal_gnt.value == 1, "Internal grant should be 1 before transaction"


    #await tester.obi_write(address=0x00, data=0x01, req=1, we=1)
    #await tester.write_set_master_data_with_handshake(address=0x00, data=0x01, req=1, we=1)

    val_lsb = 0xDEADBEEF
    val_msb = 0xCAFEBABE
    key     = 0x12345678
    op_upsert = 0x2

    # 1. Write Value LSB
    await tester.write_set_master_data_with_handshake(address=0x00, data=val_lsb)
    # 2. Write Value MSB
    await tester.write_set_master_data_with_handshake(address=0x04, data=val_msb)
    # 3. Write Key
    await tester.write_set_master_data_with_handshake(address=0x08, data=key)
    # 4. Write Opcode (triggers the operation). Set rready=1 to allow completion.
    await tester.write_set_master_data_with_handshake(address=0x0C, data=op_upsert, rready=1)
    #await tester.write_set_master_data_with_handshake(address=tester._KEY_OFFSET, data=0x01, req=1, we=1)

    assert tester.u_obi.state.value == OBIState.IDLE.value, "FSM should still be in idle as Operation register was not set"


    print(f"Done writing")
    tester.log_obi_status()

    await RisingEdge(tester.clk)
    await ReadOnly()  # Wait for combinational logic to settle
    
    tester.log_obi_status()

    await RisingEdge(tester.clk)
    await ReadOnly()  # Wait for combinational logic to settle
    
    tester.log_obi_status()

    assert tester.u_obi.internal_gnt.value == 1, "gnt should be asserted for key register write"
    
    used = tester.u_mem.used_entries.value
    assert used == 1, f"Expected 1 used entry, got {used}"
    
    dut._log.info("✓ Insert test passed")

def test_top_runner():
    sim = os.getenv("SIM", "icarus")
    
    # Assuming this file is in src/chip/test/test_top.py
    proj_path = Path(__file__).resolve().parent
    src_root = proj_path.parent.parent
    
    sources = [
        src_root / "interface" / "src" / "if_types_pkg.sv",
        src_root / "controller" / "src" / "ctrl_types_pkg.sv",
        src_root / "interface" / "src" / "obi_interface.sv",
        src_root / "interface" / "src" / "a_channel.sv",
        src_root / "interface" / "src" / "r_channel.sv",
        src_root / "controller" / "src" / "controller.sv",
        src_root / "controller" / "src" / "upsert_fsm.sv",
        src_root / "controller" / "src" / "del_fsm.sv",
        src_root / "controller" / "src" / "get_fsm.sv",
        src_root / "memory" / "src" / "memory_block.sv",
        src_root / "memory" / "src" / "memory_cell.sv",
        src_root / "memory" / "src" / "memory_dynamic_registerarray.sv",
        src_root / "chip" / "src" / "top.sv"
    ]

    include_dirs = [
        proj_path / ".." / ".." / ".." / "obi" / "include"
    ]

    params = {
        "ARCHITECTURE": "32",
        "NUM_OPERATIONS": "2",
        "NUM_ENTRIES": "16",
        "KEY_WIDTH": "32",
        "VALUE_WIDTH": "64"
    }

    runner = get_runner(sim)

    runner.build(
        sources=sources,
        hdl_toplevel="chip",
        always=True,
        waves=True,
        timescale=("1ns", "1ps"),
        parameters=params,
        includes=include_dirs
    )

    runner.test(
        hdl_toplevel="chip",
        test_module="test_top",
        waves=True
    )

if __name__ == "__main__":
    test_top_runner()
