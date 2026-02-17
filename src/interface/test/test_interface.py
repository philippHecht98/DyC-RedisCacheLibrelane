"""
Cocotb testbench for the OBI Cache Interface module.
Tests OBI protocol compliance, FSM state transitions, and controller integration.
"""

import os
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ReadOnly, ClockCycles
from cocotb.types import LogicArray
from cocotb_tools.runner import get_runner

from enum import Enum

os.environ['COCOTB_ANSI_OUTPUT'] = '1'


class OBIState(Enum):
    IDLE = 0
    PROCESS = 1
    COMPLETE = 2

class OBIInterfaceTester:
    """
    Cocotb test helper for the OBI Cache Interface.

    obi_req_t is a packed struct (75 bits, MSB-first):
        [74:43] a.addr        (32 bits)
        [42]    a.we          (1 bit)
        [41:38] a.be          (4 bits)
        [37:6]  a.wdata       (32 bits)
        [5:3]   a.aid         (3 bits)
        [2]     a.a_optional  (1 bit)
        [1]     req           (1 bit)
        [0]     rready        (1 bit)

    obi_rsp_t is a packed struct (39 bits, MSB-first):
        [38:7]  r.rdata       (32 bits)
        [6:4]   r.rid         (3 bits)
        [3]     r.err         (1 bit)
        [2]     r.r_optional  (1 bit)
        [1]     gnt           (1 bit)
        [0]     rvalid        (1 bit)

    Verilator flattens packed structs into a single LogicArrayObject,
    so we must build / parse the integer value ourselves.
    """

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

    def __init__(self, dut):
        self.dut = dut
        self.clk = dut.clk
        self.rst_n = dut.rst_n

        self.obi_req = dut.obi_req
        self.obi_resp = dut.obi_resp

        self.ready_in = dut.ready_in
        self.op_succ_in = dut.op_succ_in
        self.value_in = dut.value_in

        self.operation_out = dut.operation_out
        self.key_out = dut.key_out
        self.value_out = dut.value_out

        self.state = dut.state
        self.next_state = dut.next_state

        self.internal_grant = dut.internal_gnt

        self.rdata_from_controller = dut.rdata_from_controller
        self.err_from_controller = dut.err_from_controller

        self.decoded_operation = dut.decoded_operation
        self.decoded_key = dut.decoded_key
        self.decoded_value = dut.decoded_value

        self.addr_from_a_chan = dut.addr_from_a_chan
        self.wdata_from_a_chan = dut.wdata_from_a_chan

        self.rdata_to_r_chan = dut.rdata_to_r_chan
        self.rvalid_to_r_chan = dut.rvalid_to_r_chan
        self.err_to_r_chan = dut.err_to_r_chan


    def pack_obi_req(self, req, addr, we, be, wdata, aid):
        """
        Pack OBI request struct fields into a 74-bit value.
        
        Args:
            req: Request valid (1 bit)
            addr: Address (32 bits)
            we: Write enable (1 bit)
            be: Byte enable (4 bits)
            wdata: Write data (32 bits)
            aid: Transaction ID (3 bits)
        
        Returns:
            74-bit packed value
        """
        # Build from LSB to MSB
        packed = 0
        packed |= (req & 0x1)                    # bit [0]
        packed |= (0 & 0x1) << 1                 # a_optional [1]
        packed |= (aid & 0x7) << 2               # aid[2:0] [4:2]
        packed |= (wdata & 0xFFFFFFFF) << 5      # wdata[31:0] [36:5]
        packed |= (be & 0xF) << 37               # be[3:0] [40:37]
        packed |= (we & 0x1) << 41               # we [41]
        packed |= (addr & 0xFFFFFFFF) << 42      # addr[31:0] [73:42]
        return packed
    
    def unpack_obi_rsp(self, rsp_value):
        """
        Unpack OBI response struct from a 39-bit value.
        
        Args:
            rsp_value: 39-bit packed response value
        
        Returns:
            Tuple of (rvalid, gnt, rdata, rid, err)
        """
        rsp = int(rsp_value)
        rvalid = (rsp >> 0) & 0x1                # bit [0]
        gnt = (rsp >> 1) & 0x1                   # bit [1]
        # r_optional at bit [2] - ignored
        err = (rsp >> 3) & 0x1                   # bit [3]
        rid = (rsp >> 4) & 0x7                   # bits [6:4]
        rdata = (rsp >> 7) & 0xFFFFFFFF          # bits [38:7]
        return (rvalid, gnt, rdata, rid, err)
    async def reset(self):
        """Apply reset pulse to the DUT."""
        self.rst_n.value = 0
        # Clear OBI request signals during reset
        self.obi_req.value = 0
        
        await RisingEdge(self.clk)
        self.rst_n.value = 1
        await RisingEdge(self.clk)


    # -----------------------------------------------------------------
    # Helpers to build / decompose the packed obi_req_t / obi_resp_t bit-vector
    # -----------------------------------------------------------------
    @staticmethod
    def build_obi_req(addr=0, we=0, be=0, wdata=0, aid=0, a_optional=0,
                      req=0, rready=0):
        """Construct the integer value of a packed obi_req_t."""
        val  = (rready   & 0x1)          << OBIInterfaceTester._RREADY_BIT
        val |= (req      & 0x1)          << OBIInterfaceTester._REQ_BIT
        val |= (a_optional & 0x1)        << OBIInterfaceTester._A_OPT_BIT
        val |= (aid      & 0x7)          << OBIInterfaceTester._AID_LSB
        val |= (wdata    & 0xFFFFFFFF)   << OBIInterfaceTester._WDATA_LSB
        val |= (be       & 0xF)          << OBIInterfaceTester._BE_LSB
        val |= (we       & 0x1)          << OBIInterfaceTester._WE_BIT
        val |= (addr     & 0xFFFFFFFF)   << OBIInterfaceTester._ADDR_LSB
        return val


    async def write_set_master_data(self, address, data, **kwargs):
        """Perform an OBI write transaction."""
        await FallingEdge(self.clk)
        self.obi_req.value = self.build_obi_req(
            addr=address, wdata=data, **kwargs
        )

    @staticmethod
    def split_obi_rsp(obi_resp):
        """Split a packed obi_rsp_t into individual fields.
        
        Returns: (rdata, err, rid, r_optional, gnt, rvalid)
        """
        print(f"Raw obi_resp value: 0b{int(obi_resp):039b}")
        # Convert LogicArray to integer for bitwise operations
        val = int(obi_resp)
        rvalid = val & 0x1
        gnt = (val >> OBIInterfaceTester._GNT_BIT) & 0x1
        r_optional = (val >> OBIInterfaceTester._R_OPT_BIT) & 0x1
        err = (val >> OBIInterfaceTester._ERR_BIT) & 0x1
        rid = (val >> OBIInterfaceTester._RID_LSB) & 0x7
        rdata = (val >> OBIInterfaceTester._RDATA_LSB) & 0xFFFFFFFF
        return (rdata, err, rid, r_optional, gnt, rvalid)

    
    async def read_obi_response(self) -> tuple[int, int, int, int, int, int]:
        """Wait for combinational logic to settle and read the OBI response.
        
        Returns: (rdata, err, rid, r_optional, gnt, rvalid)
        """
        await ReadOnly()  # Wait for combinational logic to settle
        rdata, err, rid, r_optional, gnt, rvalid = self.split_obi_rsp(self.obi_resp.value)
        return (rdata, err, rid, r_optional, gnt, rvalid)

# =============================================================================
# RESET AND INITIALIZATION TESTS
# =============================================================================

@cocotb.test()
async def test_reset_initialization(dut):
    """
    Test: Verify proper initialization after reset.
    
    Checks:
    - All OBI handshake signals are deasserted
    - FSM is in IDLE state (0)
    - All output signals are zero
    - Status register shows IDLE state with no flags set
    """
    
    tester = OBIInterfaceTester(dut)
    
    # Start clock
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    
    # Apply reset
    await tester.reset()


    # Check internal registers
    assert tester.decoded_key.value == 0, "decoded key should be 0 after reset"
    assert tester.decoded_operation.value == 0, "decoded operation should be 0 after reset"
    assert tester.decoded_value.value == 0, "decoded value should be 0 after reset"

    assert tester.addr_from_a_chan.value == 0, "Address from A-channel should be 0 after reset"
    assert tester.wdata_from_a_chan.value == 0, "Write data from A-channel should be 0 after reset"
    assert tester.rdata_to_r_chan.value == 0, "Read data to R-channel should be 0 after reset"
    assert tester.rvalid_to_r_chan.value == 0, "rvalid to R-channel should be 0 after reset"
    assert tester.err_to_r_chan.value == 0, "err to R-channel should be 0 after reset"

    
    # Check controller output signals are zero
    assert tester.operation_out.value == 0, "operation_out should be 0 after reset"
    assert tester.key_out.value == 0, "key_out should be 0 after reset"
    assert tester.value_out.value == 0, "value_out should be 0 after reset"

    # Check FSM state is IDLE
    assert tester.state.value == OBIState.IDLE.value, "FSM should be in IDLE state (0) after reset"
    assert tester.next_state.value == OBIState.IDLE.value, "Next state should also be IDLE (0) after reset"   

    # Check OBI handshake signals are deasserted
    assert tester.obi_req.value == 0, "OBI req should be 0 after reset"
    assert tester.obi_resp.value == 0, "OBI resp should be 0 after reset"

    dut._log.info("✓ Reset initialization test passed")


# =============================================================================
# OBI A Channel TRANSACTION TESTS
# =============================================================================

@cocotb.test()
async def test_obi_write_operation_standard_test(dut):
    """
    Test: Write to operation register (address 0x00).
    
    Checks:
    - OBI write transaction completes successfully
    - gnt handshake occurs
    - op_written pulse is generated
    - FSM transitions from IDLE to EXECUTE
    """
    tester = OBIInterfaceTester(dut)

    # Start clock
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    
    # Apply reset
    await tester.reset()

    # Write operation code (e.g., 0x01 for GET)
    await tester.write_set_master_data(address=0x00, data=0x01, req=1, we=1)

    await RisingEdge(tester.clk)  # Wait for req to be registered
    await ReadOnly()  # Wait for combinational logic to settle

    assert tester.addr_from_a_chan.value == 0x00, "Address from A-channel should be 0x00 for operation register"
    assert tester.wdata_from_a_chan.value == 0x01, "Write data from A-channel should be 0x01 for GET operation"

    expected_req = OBIInterfaceTester.build_obi_req(addr=0x00, wdata=0x01, we=1, req=1)
    assert tester.obi_req.value == expected_req, "OBI req packed value mismatch after write"
    assert tester.obi_resp.value == 0, "OBI resp should be 0 until transaction completes"


@cocotb.test()
async def test_obi_write_operation_without_req_set(dut):
    """
    Test: Write to operation register without setting req bit.
    
    Checks:
    - OBI write transaction does not occur (no gnt)
    - op_written pulse is not generated
    - FSM remains in IDLE state
    """
    tester = OBIInterfaceTester(dut)

    # Start clock
    clock = Clock(tester.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    
    # Apply reset
    await tester.reset()

    # Attempt to write operation code without req=1
    await tester.write_set_master_data(address=0x01, data=0x01, req=0, we=1)

    await RisingEdge(tester.clk)  # Wait for write to be registered
    await ReadOnly()  # Wait for combinational logic to settle

    assert tester.addr_from_a_chan.value == 0x00, "Address from A-channel should be 0x00 for operation register"
    assert tester.wdata_from_a_chan.value == 0x00, "Write data from A-channel should be 0x00 when req=0 (no write)"
    
    assert tester.state.value == OBIState.IDLE.value, "FSM should remain in IDLE state when req=0"
    assert tester.next_state.value == OBIState.IDLE.value, "Next state should also be IDLE when req=0"
    assert tester.obi_resp.value == 0, "OBI resp should be 0 when req=0 (no transaction)"


@cocotb.test()
async def test_obi_write_operation_with_we_zero(dut):
    """
    Test: Write to operation register with we=0 (should not write).
    
    Checks:
    - OBI write transaction does not occur (no gnt)
    - op_written pulse is not generated
    - FSM remains in IDLE state
    """
    tester = OBIInterfaceTester(dut)

    # Start clock
    clock = Clock(tester.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    
    # Apply reset
    await tester.reset()

    # Attempt to write operation code with we=0
    await tester.write_set_master_data(address=0x01, data=0x01, req=1, we=0)

    await RisingEdge(tester.clk)  # Wait for write to be registered
    await ReadOnly()  # Wait for combinational logic to settle

    assert tester.addr_from_a_chan.value == 0x00, "Address from A-channel should be 0x00 for operation register"
    assert tester.wdata_from_a_chan.value == 0x00, "Write data from A-channel should be 0x00 when we=0 (no write)"
    
    assert tester.state.value == OBIState.IDLE.value, "FSM should remain in IDLE state when we=0"
    assert tester.next_state.value == OBIState.IDLE.value, "Next state should also be IDLE when we=0"
    assert tester.obi_resp.value == 0, "OBI resp should be 0 when we=0 (no transaction)"


@cocotb.test()
async def test_obi_write_operation_without_we_and_req_set(dut):
    """
    Test: Write to operation register with req=1 but we=0 (should not write).
    
    Checks:
    - OBI write transaction does not occur (no gnt)
    - op_written pulse is not generated
    - FSM remains in IDLE state
    """
    tester = OBIInterfaceTester(dut)

    # Start clock
    clock = Clock(tester.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    
    # Apply reset
    await tester.reset()

    # Attempt to write operation code with req=1 but we=0
    await tester.write_set_master_data(address=0x01, data=0x01, req=0, we=0)

    await RisingEdge(tester.clk)  # Wait for write to be registered
    await ReadOnly()  # Wait for combinational logic to settle

    assert tester.addr_from_a_chan.value == 0x00, "Address from A-channel should be 0x00 for operation register"
    assert tester.wdata_from_a_chan.value == 0x00, "Write data from A-channel should be 0x00 when we=0 (no write)"
    
    assert tester.state.value == OBIState.IDLE.value, "FSM should remain in IDLE state when we=0 even if req=1"
    assert tester.next_state.value == OBIState.IDLE.value, "Next state should also be IDLE when we=0 even if req=1"
    assert tester.obi_resp.value == 0, "OBI resp should be 0 when we=0 (no transaction)"


@cocotb.test()
async def test_obi_write_operation_without_internal_grant_set(dut):
    """
    Test: Write to operation register with req=1 and we=1 but gnt not asserted by internal logic.
    
    Checks:
    - OBI write transaction does not complete (no gnt)
    - op_written pulse is not generated
    - FSM remains in IDLE state
    """
    tester = OBIInterfaceTester(dut)

    # Start clock
    clock = Clock(tester.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    
    # Apply reset
    await tester.reset()

    tester.state.value = OBIState.PROCESS.value # Force FSM into PROCESS state to test grant behavior
    await ReadOnly()  # Wait for state change to propagate

    # Attempt to write operation code with req=1 and we=1 but gnt not asserted
    await tester.write_set_master_data(address=0x01, data=0x01, req=1, we=1)

    await RisingEdge(tester.clk)  # Wait for write to be registered
    await ReadOnly()  # Wait for combinational logic to settle

    assert tester.addr_from_a_chan.value == 0x00, "Address from A-channel should be 0x00 for operation register"
    assert tester.wdata_from_a_chan.value == 0x00, "Write data from A-channel should be 0x00 when gnt not asserted (no write)"
    assert tester.obi_resp.value == 0, "OBI resp should be 0 when gnt not asserted (no transaction)"


# =============================================================================
# OBI R Channel TRANSACTION TESTS
# =============================================================================

# @cocotb.test()
# async def test_obi_read_operation_standard_test(dut):
#     """
#     Test: Read from operation register after writing.
    
#     Checks:
#     - Write a value to operation register
#     - Read it back via OBI
#     - Values match
#     - No error flag set
#     """
    
#     tester = OBIInterfaceTester(dut)

#     # Start clock
#     clock = Clock(tester.clk, 10, unit="ns")
#     cocotb.start_soon(clock.start())
    
#     # Apply reset
#     await tester.reset()

#     await FallingEdge(tester.clk)

#     # Force FSM into PROCESS state and provide controller inputs
#     tester.state.value = OBIState.PROCESS.value
#     tester.ready_in.value = 1  # Controller signals data ready
#     tester.rdata_from_controller.value = 0x01  # Controller provides data
#     tester.err_from_controller.value = 0  # No error

#     await ReadOnly()  # Wait for combinational logic to settle

#     assert tester.rdata_from_controller.value == 0x01, "rdata_from_controller should be 0x01 as set"
#     assert tester.err_to_r_chan.value == 0, "err_to_r_chan should be 0 as set"
#     assert tester.rvalid_to_r_chan.value == 1, "rvalid to R-channel should be 1 when data is ready"

#     await RisingEdge(tester.clk)  # r_channel registers the data on this edge

#     rdata, err, rid, r_optional, gnt, rvalid = await tester.read_obi_response()

#     assert rdata == 0x01, f"Expected rdata 0x01, got 0x{rdata:x}"
#     assert err == 0, f"Expected err 0, got {err}"
#     assert rid == 0, f"Expected rid 0, got {rid}"
#     assert r_optional == 0, f"Expected r_optional 0, got {r_optional}"



# @cocotb.test()
# async def test_obi_write_key_register(dut):
#     """
#     Test: Write to key register (address 0x04).
    
#     Checks:
#     - OBI write transaction completes successfully
#     - key_out reflects written value
#     - No FSM state change (no op_written pulse)
#     """
#     pass


# @cocotb.test()
# async def test_obi_write_value_registers(dut):
#     """
#     Test: Write to value registers (addresses 0x08, 0x0C for 64-bit value).
    
#     Checks:
#     - Write both lower and upper 32-bit words
#     - value_out reflects combined 64-bit value
#     - Correct little-endian byte ordering
#     """
#     pass


# @cocotb.test()
# async def test_obi_write_handshake(dut):
#     """
#     Test: Verify write request/grant handshake protocol.
    
#     Checks:
#     - gnt asserts in response to req
#     - Address and data are latched correctly
#     - Multiple cycles of req before gnt
#     """
#     pass


# @cocotb.test()
# async def test_obi_write_back_to_back(dut):
#     """
#     Test: Multiple consecutive write transactions without gaps.
    
#     Checks:
#     - First write completes correctly
#     - Second write starts immediately after first
#     - Both writes complete successfully
#     - No data corruption or lost transactions
#     """
#     pass


# @cocotb.test()
# async def test_obi_write_with_delays(dut):
#     """
#     Test: Write transactions with delays between requests.
    
#     Checks:
#     - Delay before asserting req again
#     - Transaction still completes correctly
#     """
#     pass


# # =============================================================================
# # OBI READ TRANSACTION TESTS
# # =============================================================================

# @cocotb.test()
# async def test_obi_read_operation_register(dut):
#     """
#     Test: Read from operation register after writing.
    
#     Checks:
#     - Write a value to operation register
#     - Read it back via OBI
#     - Values match
#     - No error flag set
#     """
#     pass


# @cocotb.test()
# async def test_obi_read_key_register(dut):
#     """
#     Test: Read from key register after writing.
    
#     Checks:
#     - Write a value to key register
#     - Read it back via OBI
#     - Values match
#     """
#     pass


# @cocotb.test()
# async def test_obi_read_value_registers(dut):
#     """
#     Test: Read from value registers after writing.
    
#     Checks:
#     - Write multi-word value
#     - Read back all words
#     - Reconstructed value matches original
#     """
#     pass


# @cocotb.test()
# async def test_obi_read_status_register(dut):
#     """
#     Test: Read status register in different FSM states.
    
#     Checks:
#     - Status in IDLE state
#     - Status in EXECUTE state (brief)
#     - Status in WAIT state
#     - Status in COMPLETE state
#     - Correct bit field encoding
#     """
#     pass


# @cocotb.test()
# async def test_obi_read_result_registers(dut):
#     """
#     Test: Read result registers after operation completes.
    
#     Checks:
#     - Perform operation that sets result_value_in
#     - Wait for done
#     - Read result registers
#     - Values match result_value_in
#     """
#     pass


# @cocotb.test()
# async def test_obi_read_handshake(dut):
#     """
#     Test: Verify read request/grant and response handshake protocol.
    
#     Checks:
#     - gnt asserts in response to req (A-channel)
#     - rvalid asserts one cycle after gnt
#     - Data is stable when rvalid is high
#     - No spurious rvalid assertions
#     """
#     pass


# @cocotb.test()
# async def test_obi_read_back_to_back(dut):
#     """
#     Test: Multiple consecutive read transactions.
    
#     Checks:
#     - Read multiple registers in sequence
#     - No gaps between transactions
#     - All reads return correct data
#     """
#     pass


# @cocotb.test()
# async def test_obi_read_with_delays(dut):
#     """
#     Test: Read transactions with delays.
    
#     Checks:
#     - Delay before next req assertion
#     - Transaction completes correctly
#     """
#     pass


# @cocotb.test()
# async def test_obi_simultaneous_operations(dut):
#     """
#     Test: OBI protocol behavior with rapid successive requests.
    
#     Checks:
#     - Can handle back-to-back requests
#     - Each transaction properly isolated
#     - Transaction IDs tracked correctly
#     """
#     pass

# # =============================================================================

# @cocotb.test()
# async def test_fsm_idle_state(dut):
#     """
#     Test: FSM remains in IDLE when no operation is written.
    
#     Checks:
#     - FSM starts in IDLE after reset
#     - Stays in IDLE through multiple clock cycles
#     - start_out remains low
#     - Status register reflects IDLE state
#     """
#     pass


# @cocotb.test()
# async def test_fsm_idle_to_execute_transition(dut):
#     """
#     Test: FSM transitions from IDLE to EXECUTE when operation is written.
    
#     Checks:
#     - Write to operation register
#     - FSM changes from IDLE (0) to EXECUTE (1) on next cycle
#     - op_written pulse triggers transition
#     """
#     pass


# @cocotb.test()
# async def test_fsm_execute_to_wait_transition(dut):
#     """
#     Test: FSM automatically transitions from EXECUTE to WAIT in one cycle.
    
#     Checks:
#     - EXECUTE state lasts exactly one clock cycle
#     - start_out is high for exactly one cycle
#     - FSM enters WAIT state next cycle
#     """
#     pass


# @cocotb.test()
# async def test_fsm_wait_state_until_done(dut):
#     """
#     Test: FSM remains in WAIT state until done_in is asserted.
    
#     Checks:
#     - FSM stays in WAIT for multiple cycles
#     - start_out is low during WAIT
#     - FSM doesn't advance until done_in = 1
#     """
#     pass


# @cocotb.test()
# async def test_fsm_wait_to_complete_transition(dut):
#     """
#     Test: FSM transitions from WAIT to COMPLETE when done_in asserts.
    
#     Checks:
#     - Assert done_in while in WAIT state
#     - FSM transitions to COMPLETE (3) on next cycle
#     - Results are latched
#     - status_done flag is set
#     """
#     pass


# @cocotb.test()
# async def test_fsm_complete_state_holds_results(dut):
#     """
#     Test: FSM holds in COMPLETE state with results stable.
    
#     Checks:
#     - COMPLETE state persists until next operation
#     - status_done remains high
#     - Result registers remain stable
#     - Can read results multiple times
#     """
#     pass


# @cocotb.test()
# async def test_fsm_complete_to_execute_transition(dut):
#     """
#     Test: FSM transitions from COMPLETE to EXECUTE on next operation.
    
#     Checks:
#     - Write operation register while in COMPLETE
#     - FSM goes directly to EXECUTE (not IDLE)
#     - Previous status_done is cleared
#     - New operation begins immediately
#     """
#     pass


# @cocotb.test()
# async def test_start_out_single_cycle_pulse(dut):
#     """
#     Test: start_out is a single-cycle pulse in EXECUTE state.
    
#     Checks:
#     - start_out goes high for exactly one clock cycle
#     - start_out is low before and after
#     - Timing matches EXECUTE state
#     """
#     pass


# # =============================================================================
# # CONTROLLER INTERFACE TESTS
# # =============================================================================

# @cocotb.test()
# async def test_operation_out_reflects_op_reg(dut):
#     """
#     Test: operation_out reflects the operation register value.
    
#     Checks:
#     - Write different operation codes
#     - operation_out matches written value
#     - Updates immediately (combinational)
#     """
#     pass


# @cocotb.test()
# async def test_key_out_reflects_key_reg(dut):
#     """
#     Test: key_out reflects the key register value.
    
#     Checks:
#     - Write various key values
#     - key_out matches (lower KEY_WIDTH bits)
#     - Updates immediately
#     """
#     pass


# @cocotb.test()
# async def test_value_out_reflects_value_regs(dut):
#     """
#     Test: value_out correctly concatenates value registers.
    
#     Checks:
#     - Write multi-word value (64-bit from two 32-bit registers)
#     - value_out reflects correct 64-bit combination
#     - Proper bit ordering (LSW first)
#     """
#     pass

# # =============================================================================

# @cocotb.test()
# async def test_result_value_latching(dut):
#     """
#     Test: result_value_in is correctly latched when done_in asserts.
    
#     Checks:
#     - Start an operation
#     - Assert done_in with specific result_value_in
#     - Verify result registers contain correct value
#     - Result remains stable after done_in deasserts
#     """
#     pass


# @cocotb.test()
# async def test_hit_status_latching(dut):
#     """
#     Test: hit_in is correctly latched when done_in asserts.
    
#     Checks:
#     - Test with hit_in = 0 (miss)
#     - Test with hit_in = 1 (hit)
#     - Verify status_hit bit in status register
#     - Hit status persists in COMPLETE state
#     """
#     pass


# # =============================================================================
# # STATUS REGISTER TESTS
# # =============================================================================

# @cocotb.test()
# async def test_status_register_idle_state(dut):
#     """
#     Test: Status register contents in IDLE state.
    
#     Checks:
#     - FSM state bits = 00 (IDLE)
#     - done bit = 0
#     - hit bit = 0
#     - error bit = 0
#     """
#     pass


# @cocotb.test()
# async def test_status_register_execute_state(dut):
#     """
#     Test: Status register contents in EXECUTE state.
    
#     Checks:
#     - FSM state bits = 01 (EXECUTE)
#     - Can read status during brief EXECUTE state
#     """
#     pass


# @cocotb.test()
# async def test_status_register_wait_state(dut):
#     """
#     Test: Status register contents in WAIT state.
    
#     Checks:
#     - FSM state bits = 10 (WAIT)
#     - done bit = 0 (operation in progress)
#     """
#     pass


# @cocotb.test()
# async def test_status_register_complete_state(dut):
#     """
#     Test: Status register contents in COMPLETE state.
    
#     Checks:
#     - FSM state bits = 11 (COMPLETE)
#     - done bit = 1
#     - hit bit reflects actual hit status
#     """
#     pass


# @cocotb.test()
# async def test_status_done_bit(dut):
#     """
#     Test: Status done bit (bit 0) behavior.
    
#     Checks:
#     - done = 0 in IDLE, EXECUTE, WAIT
#     - done = 1 in COMPLETE
#     - done clears when new operation starts
#     """
#     pass


# @cocotb.test()
# async def test_status_hit_bit(dut):
#     """
#     Test: Status hit bit (bit 1) behavior.
    
#     Checks:
#     - hit = 0 initially
#     - hit latches value from hit_in signal
#     - hit persists in COMPLETE state
#     - hit clears on next operation
#     """
#     pass


# @cocotb.test()
# async def test_status_fsm_state_bits(dut):
#     """
#     Test: Status FSM state bits (bits 4:3) encoding.
    
#     Checks:
#     - Correct 2-bit encoding for each state
#     - State bits update as FSM transitions
#     - Can track FSM progress by reading status
#     """
#     pass


# # =============================================================================
# # END-TO-END OPERATION TESTS
# # =============================================================================

# @cocotb.test()
# async def test_complete_get_operation(dut):
#     """
#     Test: Complete GET operation from start to finish.
    
#     Flow:
#     1. Write key register
#     2. Write operation register (GET/READ)
#     3. Wait for done via status polling
#     4. Read result registers
#     5. Verify result matches expected value
#     """
#     pass


# @cocotb.test()
# async def test_complete_put_operation(dut):
#     """
#     Test: Complete PUT operation from start to finish.
    
#     Flow:
#     1. Write key register
#     2. Write value registers
#     3. Write operation register (PUT/CREATE)
#     4. Wait for done
#     5. Check status for success
#     """
#     pass


# @cocotb.test()
# async def test_complete_delete_operation(dut):
#     """
#     Test: Complete DELETE operation from start to finish.
    
#     Flow:
#     1. Write key register
#     2. Write operation register (DELETE)
#     3. Wait for done
#     4. Check status
#     """
#     pass


# @cocotb.test()
# async def test_sequential_operations(dut):
#     """
#     Test: Multiple operations executed in sequence.
    
#     Flow:
#     1. Perform PUT operation
#     2. Wait for completion
#     3. Perform GET operation on same key
#     4. Verify retrieved value matches PUT value
#     5. Perform DELETE operation
#     6. Each operation completes successfully
#     """
#     pass


# @cocotb.test()
# async def test_operation_with_cache_hit(dut):
#     """
#     Test: Operation that results in cache hit.
    
#     Checks:
#     - Provide hit_in = 1 from controller
#     - Verify status_hit bit is set
#     - Result value is provided
#     """
#     pass


# @cocotb.test()
# async def test_operation_with_cache_miss(dut):
#     """
#     Test: Operation that results in cache miss.
    
#     Checks:
#     - Provide hit_in = 0 from controller
#     - Verify status_hit bit is clear
#     - Operation still completes
#     """
#     pass


# # =============================================================================
# # EDGE CASES AND ERROR CONDITIONS
# # =============================================================================

# @cocotb.test()
# async def test_write_during_operation_in_progress(dut):
#     """
#     Test: Attempt to write registers while operation is executing.
    
#     Checks:
#     - Start an operation (FSM in WAIT)
#     - Try to write to key/value registers
#     - Writes should be accepted by OBI protocol
#     - Behavior is well-defined (may overwrite for next operation)
#     """
#     pass


# @cocotb.test()
# async def test_read_results_before_completion(dut):
#     """
#     Test: Read result registers before operation completes.
    
#     Checks:
#     - Start an operation
#     - Read result registers while in WAIT state
#     - Should read stale/zero values
#     - No protocol violation
#     """
#     pass


# @cocotb.test()
# async def test_invalid_address_write(dut):
#     """
#     Test: Write to invalid/unmapped address.
    
#     Checks:
#     - OBI transaction completes
#     - No error flag set (interface doesn't check address validity)
#     - No side effects on valid registers
#     """
#     pass


# @cocotb.test()
# async def test_invalid_address_read(dut):
#     """
#     Test: Read from invalid/unmapped address.
    
#     Checks:
#     - OBI transaction completes
#     - Returns zero or undefined value
#     - No protocol violation
#     """
#     pass


# @cocotb.test()
# async def test_sequential_read_write(dut):
#     """
#     Test: Sequential read and write transactions.
    
#     Checks:
#     - OBI transactions are sequential (one at a time)
#     - Each transaction completes properly
#     - No interference between operations
#     """
#     pass


# @cocotb.test()
# async def test_multiword_value_handling(dut):
#     """
#     Test: Proper handling of 64-bit values across two 32-bit registers.
    
#     Checks:
#     - Write 64-bit value as two 32-bit words
#     - value_out correctly reconstructs full 64-bit value
#     - Read back as two 32-bit words from result registers
#     - Bit ordering is correct
#     """
#     pass


# @cocotb.test()
# async def test_rapid_operation_requests(dut):
#     """
#     Test: Submit new operation immediately after previous completes.
    
#     Checks:
#     - First operation completes normally
#     - Write new operation register in COMPLETE state
#     - FSM goes directly to EXECUTE (bypasses IDLE)
#     - Second operation executes correctly
#     """
#     pass


# @cocotb.test()
# async def test_long_operation_timeout(dut):
#     """
#     Test: Operation that takes many cycles to complete.
    
#     Checks:
#     - FSM stays in WAIT for extended period
#     - Interface remains responsive to reads
#     - Eventually completes when done_in asserts
#     """
#     pass


# =============================================================================
# TEST RUNNER
# =============================================================================

def test_interface_runner():
    """
    Cocotb test runner for the cache interface module.
    Sets up simulation environment and executes all tests.
    """
    sim = os.getenv("SIM", "verilator")
    proj_path = Path(__file__).resolve().parent 
    
    # Source files for cache interface
    sources = [
        proj_path / ".." / "src" / "if_types_pkg.sv",
        proj_path / ".." / ".." / "controller" / "src" / "ctrl_types_pkg.sv",
        proj_path / ".." / "src" / "obi_interface.sv", 
        proj_path / ".." / "src" / "a_channel.sv",
        proj_path / ".." / "src" / "r_channel.sv",
    ]

    include_dirs = [
        proj_path / ".." / ".." / ".." / "obi" / "include"
    ]

    params = {
        "ARCHITECTURE": "32",
    }

    runner = get_runner(sim)

    # Build with testbench
    runner.build(
        sources=sources,
        hdl_toplevel="obi_cache_interface",
        always=True, 
        waves=True,
        timescale=("1ns", "1ps"), 
        parameters=params, 
        includes=include_dirs
    )

    # Run tests
    runner.test(
        hdl_toplevel="obi_cache_interface", 
        test_module="test_interface",
        waves=True
    )


if __name__ == "__main__":
    test_interface_runner()
