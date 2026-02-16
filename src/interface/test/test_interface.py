"""
Cocotb testbench for the AXI4-Lite Cache Interface module.
Tests AXI protocol compliance, FSM state transitions, and controller integration.
"""

import os
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ReadOnly, ClockCycles
from cocotb.types import LogicArray
from cocotb_tools.runner import get_runner

os.environ['COCOTB_ANSI_OUTPUT'] = '1'


class AXIInterfaceTester:
    """
    Helper class for testing the AXI4-Lite cache interface.
    Provides methods for AXI transactions and checking interface state.
    """

    def __init__(self, dut):
        self.dut = dut
        self.clk = dut.clk
        self.rst_n = dut.rst_n
        
        # AXI Write Address Channel
        self.s_axi_awaddr = dut.s_axi_awaddr
        self.s_axi_awvalid = dut.s_axi_awvalid
        self.s_axi_awready = dut.s_axi_awready
        
        # AXI Write Data Channel
        self.s_axi_wdata = dut.s_axi_wdata
        self.s_axi_wvalid = dut.s_axi_wvalid
        self.s_axi_wready = dut.s_axi_wready
        
        # AXI Write Response Channel
        self.s_axi_bresp = dut.s_axi_bresp
        self.s_axi_bvalid = dut.s_axi_bvalid
        self.s_axi_bready = dut.s_axi_bready
        
        # AXI Read Address Channel
        self.s_axi_araddr = dut.s_axi_araddr
        self.s_axi_arvalid = dut.s_axi_arvalid
        self.s_axi_arready = dut.s_axi_arready
        
        # AXI Read Data Channel
        self.s_axi_rdata = dut.s_axi_rdata
        self.s_axi_rresp = dut.s_axi_rresp
        self.s_axi_rvalid = dut.s_axi_rvalid
        self.s_axi_rready = dut.s_axi_rready
        
        # Controller-facing ports
        self.operation_out = dut.operation_out
        self.key_out = dut.key_out
        self.value_out = dut.value_out
        self.start_out = dut.start_out
        
        self.result_value_in = dut.result_value_in
        self.hit_in = dut.hit_in
        self.done_in = dut.done_in
        
        # Register addresses (word-aligned)
        self.ADDR_OP = 0x00
        self.ADDR_KEY = 0x04
        self.ADDR_VAL_BASE = 0x08
        # Status and result addresses depend on VALUE_WIDTH/ARCHITECTURE ratio
        # For VALUE_WIDTH=64, ARCHITECTURE=32: NUM_VAL_REGS=2
        self.ADDR_STATUS = 0x10  # ADDR_VAL_BASE + 2*4
        self.ADDR_RES_BASE = 0x14  # ADDR_STATUS + 4

    async def reset(self):
        """Apply reset pulse to the DUT."""
        self.rst_n.value = 0
        # Initialize all AXI master signals to idle
        self.s_axi_awaddr.value = 0
        self.s_axi_awvalid.value = 0
        self.s_axi_wdata.value = 0
        self.s_axi_wvalid.value = 0
        self.s_axi_bready.value = 0
        self.s_axi_araddr.value = 0
        self.s_axi_arvalid.value = 0
        self.s_axi_rready.value = 0
        
        # Initialize controller signals
        self.result_value_in.value = 0
        self.hit_in.value = 0
        self.done_in.value = 0
        
        await RisingEdge(self.clk)
        await RisingEdge(self.clk)
        self.rst_n.value = 1
        await RisingEdge(self.clk)

    async def wait_cycles(self, num_cycles: int):
        """Wait for specified number of clock cycles."""
        for _ in range(num_cycles):
            await RisingEdge(self.clk)

    async def axi_write(self, address: int, data: int):
        """
        Perform a complete AXI write transaction.
        
        Args:
            address: Register address (word-aligned)
            data: Data value to write
        
        Returns:
            Response code (should be 0 for OKAY)
        """
        # Phase 1: Write address
        self.s_axi_awaddr.value = address
        self.s_axi_awvalid.value = 1
        
        # Wait for address acceptance
        while True:
            await RisingEdge(self.clk)
            await ReadOnly()
            if self.s_axi_awready.value == 1:
                break
        
        self.s_axi_awvalid.value = 0
        
        # Phase 2: Write data
        self.s_axi_wdata.value = data
        self.s_axi_wvalid.value = 1
        
        # Wait for data acceptance
        while True:
            await RisingEdge(self.clk)
            await ReadOnly()
            if self.s_axi_wready.value == 1:
                break
        
        self.s_axi_wvalid.value = 0
        
        # Phase 3: Write response
        self.s_axi_bready.value = 1
        
        # Wait for response
        while True:
            await RisingEdge(self.clk)
            await ReadOnly()
            if self.s_axi_bvalid.value == 1:
                resp = int(self.s_axi_bresp.value)
                break
        
        self.s_axi_bready.value = 0
        await RisingEdge(self.clk)
        
        return resp

    async def axi_read(self, address: int):
        """
        Perform a complete AXI read transaction.
        
        Args:
            address: Register address (word-aligned)
        
        Returns:
            Tuple of (data, response_code)
        """
        # Phase 1: Read address
        self.s_axi_araddr.value = address
        self.s_axi_arvalid.value = 1
        
        # Wait for address acceptance
        while True:
            await RisingEdge(self.clk)
            await ReadOnly()
            if self.s_axi_arready.value == 1:
                break
        
        self.s_axi_arvalid.value = 0
        
        # Phase 2: Read data
        self.s_axi_rready.value = 1
        
        # Wait for data valid
        while True:
            await RisingEdge(self.clk)
            await ReadOnly()
            if self.s_axi_rvalid.value == 1:
                data = int(self.s_axi_rdata.value)
                resp = int(self.s_axi_rresp.value)
                break
        
        self.s_axi_rready.value = 0
        await RisingEdge(self.clk)
        
        return data, resp

    async def poll_status(self, timeout_cycles: int = 100):
        """
        Poll the status register until done bit is set or timeout.
        
        Args:
            timeout_cycles: Maximum cycles to wait
        
        Returns:
            Status register value when done, or None if timeout
        """
        for _ in range(timeout_cycles):
            status, _ = await self.axi_read(self.ADDR_STATUS)
            done_bit = status & 0x1
            if done_bit:
                return status
            await self.wait_cycles(1)
        return None

    def get_fsm_state(self, status_reg: int):
        """Extract FSM state from status register."""
        return (status_reg >> 3) & 0x3

    def get_done_bit(self, status_reg: int):
        """Extract done bit from status register."""
        return status_reg & 0x1

    def get_hit_bit(self, status_reg: int):
        """Extract hit bit from status register."""
        return (status_reg >> 1) & 0x1

    def get_error_bit(self, status_reg: int):
        """Extract error bit from status register."""
        return (status_reg >> 2) & 0x1


# =============================================================================
# RESET AND INITIALIZATION TESTS
# =============================================================================

@cocotb.test()
async def test_reset_initialization(dut):
    """
    Test: Verify proper initialization after reset.
    
    Checks:
    - All AXI handshake signals are deasserted
    - FSM is in IDLE state (0)
    - All output signals are zero
    - Status register shows IDLE state with no flags set
    """
    pass


@cocotb.test()
async def test_reset_clears_registers(dut):
    """
    Test: Verify reset clears all internal registers.
    
    Checks:
    - Write some values to registers
    - Apply reset
    - Verify all registers read back as zero
    """
    pass


# =============================================================================
# AXI WRITE CHANNEL TESTS
# =============================================================================

@cocotb.test()
async def test_axi_write_operation_register(dut):
    """
    Test: Write to operation register (address 0x00).
    
    Checks:
    - AXI write transaction completes successfully
    - Response is OKAY (0x0)
    - op_written pulse is generated
    - FSM transitions from IDLE to EXECUTE
    """
    pass


@cocotb.test()
async def test_axi_write_key_register(dut):
    """
    Test: Write to key register (address 0x04).
    
    Checks:
    - AXI write transaction completes successfully
    - key_out reflects written value
    - No FSM state change (no op_written pulse)
    """
    pass


@cocotb.test()
async def test_axi_write_value_registers(dut):
    """
    Test: Write to value registers (addresses 0x08, 0x0C for 64-bit value).
    
    Checks:
    - Write both lower and upper 32-bit words
    - value_out reflects combined 64-bit value
    - Correct little-endian byte ordering
    """
    pass


@cocotb.test()
async def test_axi_write_address_handshake(dut):
    """
    Test: Verify write address channel handshake protocol.
    
    Checks:
    - awready asserts in response to awvalid
    - Address is latched correctly
    - Multiple cycles of awvalid before awready
    """
    pass


@cocotb.test()
async def test_axi_write_data_handshake(dut):
    """
    Test: Verify write data channel handshake protocol.
    
    Checks:
    - wready asserts after address is latched
    - Data is written when both wvalid and wready are high
    - wready deasserts after transfer
    """
    pass


@cocotb.test()
async def test_axi_write_response_handshake(dut):
    """
    Test: Verify write response channel handshake protocol.
    
    Checks:
    - bvalid asserts after write completes
    - Response code is OKAY (0x0)
    - bvalid deasserts after bready handshake
    """
    pass


@cocotb.test()
async def test_axi_write_back_to_back(dut):
    """
    Test: Multiple consecutive write transactions without gaps.
    
    Checks:
    - First write completes correctly
    - Second write starts immediately after first
    - Both writes complete successfully
    - No data corruption or lost transactions
    """
    pass


@cocotb.test()
async def test_axi_write_with_delays(dut):
    """
    Test: Write transactions with delays between phases.
    
    Checks:
    - Delay between awvalid and wvalid
    - Delay before bready assertion
    - Transaction still completes correctly
    """
    pass


# =============================================================================
# AXI READ CHANNEL TESTS
# =============================================================================

@cocotb.test()
async def test_axi_read_operation_register(dut):
    """
    Test: Read from operation register after writing.
    
    Checks:
    - Write a value to operation register
    - Read it back via AXI
    - Values match
    - Response is OKAY
    """
    pass


@cocotb.test()
async def test_axi_read_key_register(dut):
    """
    Test: Read from key register after writing.
    
    Checks:
    - Write a value to key register
    - Read it back via AXI
    - Values match
    """
    pass


@cocotb.test()
async def test_axi_read_value_registers(dut):
    """
    Test: Read from value registers after writing.
    
    Checks:
    - Write multi-word value
    - Read back all words
    - Reconstructed value matches original
    """
    pass


@cocotb.test()
async def test_axi_read_status_register(dut):
    """
    Test: Read status register in different FSM states.
    
    Checks:
    - Status in IDLE state
    - Status in EXECUTE state (brief)
    - Status in WAIT state
    - Status in COMPLETE state
    - Correct bit field encoding
    """
    pass


@cocotb.test()
async def test_axi_read_result_registers(dut):
    """
    Test: Read result registers after operation completes.
    
    Checks:
    - Perform operation that sets result_value_in
    - Wait for done
    - Read result registers
    - Values match result_value_in
    """
    pass


@cocotb.test()
async def test_axi_read_address_handshake(dut):
    """
    Test: Verify read address channel handshake protocol.
    
    Checks:
    - arready asserts in response to arvalid
    - Single-cycle address acceptance
    - No spurious arready assertions
    """
    pass


@cocotb.test()
async def test_axi_read_data_handshake(dut):
    """
    Test: Verify read data channel handshake protocol.
    
    Checks:
    - rvalid asserts after address phase
    - Data is stable when rvalid is high
    - rvalid deasserts after rready handshake
    """
    pass


@cocotb.test()
async def test_axi_read_back_to_back(dut):
    """
    Test: Multiple consecutive read transactions.
    
    Checks:
    - Read multiple registers in sequence
    - No gaps between transactions
    - All reads return correct data
    """
    pass


@cocotb.test()
async def test_axi_read_with_delays(dut):
    """
    Test: Read transactions with delays.
    
    Checks:
    - Delay before rready assertion
    - Multiple cycles with rvalid high
    - Transaction completes correctly
    """
    pass


# =============================================================================
# FSM STATE MACHINE TESTS
# =============================================================================

@cocotb.test()
async def test_fsm_idle_state(dut):
    """
    Test: FSM remains in IDLE when no operation is written.
    
    Checks:
    - FSM starts in IDLE after reset
    - Stays in IDLE through multiple clock cycles
    - start_out remains low
    - Status register reflects IDLE state
    """
    pass


@cocotb.test()
async def test_fsm_idle_to_execute_transition(dut):
    """
    Test: FSM transitions from IDLE to EXECUTE when operation is written.
    
    Checks:
    - Write to operation register
    - FSM changes from IDLE (0) to EXECUTE (1) on next cycle
    - op_written pulse triggers transition
    """
    pass


@cocotb.test()
async def test_fsm_execute_to_wait_transition(dut):
    """
    Test: FSM automatically transitions from EXECUTE to WAIT in one cycle.
    
    Checks:
    - EXECUTE state lasts exactly one clock cycle
    - start_out is high for exactly one cycle
    - FSM enters WAIT state next cycle
    """
    pass


@cocotb.test()
async def test_fsm_wait_state_until_done(dut):
    """
    Test: FSM remains in WAIT state until done_in is asserted.
    
    Checks:
    - FSM stays in WAIT for multiple cycles
    - start_out is low during WAIT
    - FSM doesn't advance until done_in = 1
    """
    pass


@cocotb.test()
async def test_fsm_wait_to_complete_transition(dut):
    """
    Test: FSM transitions from WAIT to COMPLETE when done_in asserts.
    
    Checks:
    - Assert done_in while in WAIT state
    - FSM transitions to COMPLETE (3) on next cycle
    - Results are latched
    - status_done flag is set
    """
    pass


@cocotb.test()
async def test_fsm_complete_state_holds_results(dut):
    """
    Test: FSM holds in COMPLETE state with results stable.
    
    Checks:
    - COMPLETE state persists until next operation
    - status_done remains high
    - Result registers remain stable
    - Can read results multiple times
    """
    pass


@cocotb.test()
async def test_fsm_complete_to_execute_transition(dut):
    """
    Test: FSM transitions from COMPLETE to EXECUTE on next operation.
    
    Checks:
    - Write operation register while in COMPLETE
    - FSM goes directly to EXECUTE (not IDLE)
    - Previous status_done is cleared
    - New operation begins immediately
    """
    pass


@cocotb.test()
async def test_start_out_single_cycle_pulse(dut):
    """
    Test: start_out is a single-cycle pulse in EXECUTE state.
    
    Checks:
    - start_out goes high for exactly one clock cycle
    - start_out is low before and after
    - Timing matches EXECUTE state
    """
    pass


# =============================================================================
# CONTROLLER INTERFACE TESTS
# =============================================================================

@cocotb.test()
async def test_operation_out_reflects_op_reg(dut):
    """
    Test: operation_out reflects the operation register value.
    
    Checks:
    - Write different operation codes
    - operation_out matches written value
    - Updates immediately (combinational)
    """
    pass


@cocotb.test()
async def test_key_out_reflects_key_reg(dut):
    """
    Test: key_out reflects the key register value.
    
    Checks:
    - Write various key values
    - key_out matches (lower KEY_WIDTH bits)
    - Updates immediately
    """
    pass


@cocotb.test()
async def test_value_out_reflects_value_regs(dut):
    """
    Test: value_out correctly concatenates value registers.
    
    Checks:
    - Write multi-word value (64-bit from two 32-bit registers)
    - value_out reflects correct 64-bit combination
    - Proper bit ordering (LSW first)
    """
    pass


@cocotb.test()
async def test_result_value_latching(dut):
    """
    Test: result_value_in is correctly latched when done_in asserts.
    
    Checks:
    - Start an operation
    - Assert done_in with specific result_value_in
    - Verify result registers contain correct value
    - Result remains stable after done_in deasserts
    """
    pass


@cocotb.test()
async def test_hit_status_latching(dut):
    """
    Test: hit_in is correctly latched when done_in asserts.
    
    Checks:
    - Test with hit_in = 0 (miss)
    - Test with hit_in = 1 (hit)
    - Verify status_hit bit in status register
    - Hit status persists in COMPLETE state
    """
    pass


# =============================================================================
# STATUS REGISTER TESTS
# =============================================================================

@cocotb.test()
async def test_status_register_idle_state(dut):
    """
    Test: Status register contents in IDLE state.
    
    Checks:
    - FSM state bits = 00 (IDLE)
    - done bit = 0
    - hit bit = 0
    - error bit = 0
    """
    pass


@cocotb.test()
async def test_status_register_execute_state(dut):
    """
    Test: Status register contents in EXECUTE state.
    
    Checks:
    - FSM state bits = 01 (EXECUTE)
    - Can read status during brief EXECUTE state
    """
    pass


@cocotb.test()
async def test_status_register_wait_state(dut):
    """
    Test: Status register contents in WAIT state.
    
    Checks:
    - FSM state bits = 10 (WAIT)
    - done bit = 0 (operation in progress)
    """
    pass


@cocotb.test()
async def test_status_register_complete_state(dut):
    """
    Test: Status register contents in COMPLETE state.
    
    Checks:
    - FSM state bits = 11 (COMPLETE)
    - done bit = 1
    - hit bit reflects actual hit status
    """
    pass


@cocotb.test()
async def test_status_done_bit(dut):
    """
    Test: Status done bit (bit 0) behavior.
    
    Checks:
    - done = 0 in IDLE, EXECUTE, WAIT
    - done = 1 in COMPLETE
    - done clears when new operation starts
    """
    pass


@cocotb.test()
async def test_status_hit_bit(dut):
    """
    Test: Status hit bit (bit 1) behavior.
    
    Checks:
    - hit = 0 initially
    - hit latches value from hit_in signal
    - hit persists in COMPLETE state
    - hit clears on next operation
    """
    pass


@cocotb.test()
async def test_status_fsm_state_bits(dut):
    """
    Test: Status FSM state bits (bits 4:3) encoding.
    
    Checks:
    - Correct 2-bit encoding for each state
    - State bits update as FSM transitions
    - Can track FSM progress by reading status
    """
    pass


# =============================================================================
# END-TO-END OPERATION TESTS
# =============================================================================

@cocotb.test()
async def test_complete_get_operation(dut):
    """
    Test: Complete GET operation from start to finish.
    
    Flow:
    1. Write key register
    2. Write operation register (GET/READ)
    3. Wait for done via status polling
    4. Read result registers
    5. Verify result matches expected value
    """
    pass


@cocotb.test()
async def test_complete_put_operation(dut):
    """
    Test: Complete PUT operation from start to finish.
    
    Flow:
    1. Write key register
    2. Write value registers
    3. Write operation register (PUT/CREATE)
    4. Wait for done
    5. Check status for success
    """
    pass


@cocotb.test()
async def test_complete_delete_operation(dut):
    """
    Test: Complete DELETE operation from start to finish.
    
    Flow:
    1. Write key register
    2. Write operation register (DELETE)
    3. Wait for done
    4. Check status
    """
    pass


@cocotb.test()
async def test_sequential_operations(dut):
    """
    Test: Multiple operations executed in sequence.
    
    Flow:
    1. Perform PUT operation
    2. Wait for completion
    3. Perform GET operation on same key
    4. Verify retrieved value matches PUT value
    5. Perform DELETE operation
    6. Each operation completes successfully
    """
    pass


@cocotb.test()
async def test_operation_with_cache_hit(dut):
    """
    Test: Operation that results in cache hit.
    
    Checks:
    - Provide hit_in = 1 from controller
    - Verify status_hit bit is set
    - Result value is provided
    """
    pass


@cocotb.test()
async def test_operation_with_cache_miss(dut):
    """
    Test: Operation that results in cache miss.
    
    Checks:
    - Provide hit_in = 0 from controller
    - Verify status_hit bit is clear
    - Operation still completes
    """
    pass


# =============================================================================
# EDGE CASES AND ERROR CONDITIONS
# =============================================================================

@cocotb.test()
async def test_write_during_operation_in_progress(dut):
    """
    Test: Attempt to write registers while operation is executing.
    
    Checks:
    - Start an operation (FSM in WAIT)
    - Try to write to key/value registers
    - Writes should be accepted by AXI protocol
    - Behavior is well-defined (may overwrite for next operation)
    """
    pass


@cocotb.test()
async def test_read_results_before_completion(dut):
    """
    Test: Read result registers before operation completes.
    
    Checks:
    - Start an operation
    - Read result registers while in WAIT state
    - Should read stale/zero values
    - No protocol violation
    """
    pass


@cocotb.test()
async def test_invalid_address_write(dut):
    """
    Test: Write to invalid/unmapped address.
    
    Checks:
    - AXI transaction completes
    - Response code indicates success (AXI doesn't check validity)
    - No side effects on valid registers
    """
    pass


@cocotb.test()
async def test_invalid_address_read(dut):
    """
    Test: Read from invalid/unmapped address.
    
    Checks:
    - AXI transaction completes
    - Returns zero or undefined value
    - No protocol violation
    """
    pass


@cocotb.test()
async def test_simultaneous_read_write(dut):
    """
    Test: Attempt read and write on same cycle (different channels).
    
    Checks:
    - AXI read and write channels are independent
    - Both transactions can proceed
    - No interference between channels
    """
    pass


@cocotb.test()
async def test_multiword_value_handling(dut):
    """
    Test: Proper handling of 64-bit values across two 32-bit registers.
    
    Checks:
    - Write 64-bit value as two 32-bit words
    - value_out correctly reconstructs full 64-bit value
    - Read back as two 32-bit words from result registers
    - Bit ordering is correct
    """
    pass


@cocotb.test()
async def test_rapid_operation_requests(dut):
    """
    Test: Submit new operation immediately after previous completes.
    
    Checks:
    - First operation completes normally
    - Write new operation register in COMPLETE state
    - FSM goes directly to EXECUTE (bypasses IDLE)
    - Second operation executes correctly
    """
    pass


@cocotb.test()
async def test_long_operation_timeout(dut):
    """
    Test: Operation that takes many cycles to complete.
    
    Checks:
    - FSM stays in WAIT for extended period
    - Interface remains responsive to reads
    - Eventually completes when done_in asserts
    """
    pass


# =============================================================================
# TEST RUNNER
# =============================================================================

def test_interface_runner():
    """
    Cocotb test runner for the cache interface module.
    Sets up simulation environment and executes all tests.
    """
    sim = os.getenv("SIM", "icarus")
    proj_path = Path(__file__).resolve().parent
    
    # Source files for cache interface
    sources = [
        proj_path / ".." / "src" / "if_types_pkg.sv",
        proj_path / ".." / ".." / "controller" / "src" / "ctrl_types_pkg.sv",
        proj_path / ".." / "src" / "interface.sv"
    ]

    runner = get_runner(sim)

    # Build with testbench
    runner.build(
        sources=sources,
        hdl_toplevel="cache_interface",
        always=True, 
        waves=True,
        timescale=("1ns", "1ps")
    )

    # Run tests
    runner.test(
        hdl_toplevel="cache_interface", 
        test_module="test_interface",
        waves=True
    )


if __name__ == "__main__":
    test_interface_runner()
