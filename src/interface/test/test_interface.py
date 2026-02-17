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

os.environ['COCOTB_ANSI_OUTPUT'] = '1'


class OBIInterfaceTester:


    def __init__(self, dut):
        self.dut = dut
        self.clk = dut.clk
        self.rst_n = dut.rst_n

    async def reset(self):
        """Apply reset pulse to the DUT."""
        self.rst_n.value = 0
        
        # Initialize OBI request to idle (all zeros)
        self.obi_req_i.value = 0
        
        # Initialize controller signals
        self.result_value_in.value = 0
        self.hit_in.value = 0
        self.done_in.value = 0
        
        await RisingEdge(self.clk)
        self.rst_n.value = 1
        await RisingEdge(self.clk)


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
        
    # Check OBI response signals are deasserted (sample at readonly)
    await ReadOnly()
    rvalid, gnt, rdata, rid, err = tester.unpack_obi_rsp(dut.obi_rsp_o.value)
    assert gnt == 0, "gnt should be 0 after reset (no request)"
    assert rvalid == 0, "rvalid should be 0 after reset"
    
    # Check controller output signals are zero
    assert dut.operation_out.value == 0, "operation_out should be 0 after reset"
    assert dut.key_out.value == 0, "key_out should be 0 after reset"
    assert dut.value_out.value == 0, "value_out should be 0 after reset"
    assert dut.start_out.value == 0, "start_out should be 0 after reset"
        

    # Read status register
    status, _, err = await tester.obi_read(tester.ADDR_STATUS)
    
    # Verify no error
    assert err == 0, f"Status read should not error, got err={err}"
    
    # Extract status fields
    fsm_state = tester.get_fsm_state(status)
    done_bit = tester.get_done_bit(status)
    hit_bit = tester.get_hit_bit(status)
    error_bit = tester.get_error_bit(status)
    
    # Verify status register shows IDLE state with no flags
    assert fsm_state == 0, f"FSM should be in IDLE (0), got {fsm_state}"
    assert done_bit == 0, f"done bit should be 0, got {done_bit}"
    assert hit_bit == 0, f"hit bit should be 0, got {hit_bit}"
    assert error_bit == 0, f"error bit should be 0, got {error_bit}"
    
    dut._log.info("✓ Reset initialization test passed")


@cocotb.test()
async def test_reset_clears_registers(dut):
    """
    Test: Verify reset clears all internal registers.
    
    Checks:
    - Write some values to registers
    - Apply reset
    - Verify all registers read back as zero
    """
    tester = OBIInterfaceTester(dut)
    
    # Start clock
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    
    # Initial reset
    await tester.reset()
    
    # Write some values to registers
    dut._log.info("Writing test values to registers...")
    
    # Write to key register
    await tester.obi_write(tester.ADDR_KEY, 0x1234)
    
    # Write to value registers (64-bit value across two 32-bit registers)
    await tester.obi_write(tester.ADDR_VAL_BASE, 0xDEADBEEF)
    await tester.obi_write(tester.ADDR_VAL_BASE + 4, 0xCAFEBABE)
    
    # Write to operation register
    await tester.obi_write(tester.ADDR_OP, 0x01)  # READ operation
    
    # Verify values were written by reading them back
    key_val, _, _ = await tester.obi_read(tester.ADDR_KEY)
    assert key_val == 0x1234, f"Key should be 0x1234 before reset, got 0x{key_val:08x}"
    
    val0, _, _ = await tester.obi_read(tester.ADDR_VAL_BASE)
    assert val0 == 0xDEADBEEF, f"Value[0] should be 0xDEADBEEF before reset, got 0x{val0:08x}"
    
    dut._log.info("Test values written successfully, applying reset...")
    
    # Apply reset
    dut.rst_n.value = 0
    await tester.wait_cycles(2)
    dut.rst_n.value = 1
    await tester.wait_cycles(1)
    
    # Read back all registers and verify they are zero
    dut._log.info("Verifying registers are cleared after reset...")
    
    # Read operation register
    op_val, _, _ = await tester.obi_read(tester.ADDR_OP)
    assert op_val == 0, f"Operation register should be 0 after reset, got 0x{op_val:08x}"
    
    # Read key register
    key_val, _, _ = await tester.obi_read(tester.ADDR_KEY)
    assert key_val == 0, f"Key register should be 0 after reset, got 0x{key_val:08x}"
    
    # Read value registers
    val0, _, _ = await tester.obi_read(tester.ADDR_VAL_BASE)
    assert val0 == 0, f"Value[0] register should be 0 after reset, got 0x{val0:08x}"
    
    val1, _, _ = await tester.obi_read(tester.ADDR_VAL_BASE + 4)
    assert val1 == 0, f"Value[1] register should be 0 after reset, got 0x{val1:08x}"
    
    # Read result registers
    res0, _, _ = await tester.obi_read(tester.ADDR_RES_BASE)
    assert res0 == 0, f"Result[0] register should be 0 after reset, got 0x{res0:08x}"
    
    res1, _, _ = await tester.obi_read(tester.ADDR_RES_BASE + 4)
    assert res1 == 0, f"Result[1] register should be 0 after reset, got 0x{res1:08x}"
    
    # Read status register
    status, _, _ = await tester.obi_read(tester.ADDR_STATUS)
    fsm_state = tester.get_fsm_state(status)
    done_bit = tester.get_done_bit(status)
    
    assert fsm_state == 0, f"FSM should be in IDLE after reset, got {fsm_state}"
    assert done_bit == 0, f"Done bit should be 0 after reset, got {done_bit}"
    
    # Check controller outputs are cleared (sample at readonly)
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.operation_out.value == 0, "operation_out should be 0 after reset"
    assert dut.key_out.value == 0, "key_out should be 0 after reset"
    assert dut.value_out.value == 0, "value_out should be 0 after reset"
    assert dut.start_out.value == 0, "start_out should be 0 after reset"
    
    dut._log.info("✓ Reset clears registers test passed")


# # =============================================================================
# # OBI WRITE TRANSACTION TESTS
# # =============================================================================

# @cocotb.test()
# async def test_obi_write_operation_register(dut):
#     """
#     Test: Write to operation register (address 0x00).
    
#     Checks:
#     - OBI write transaction completes successfully
#     - gnt handshake occurs
#     - op_written pulse is generated
#     - FSM transitions from IDLE to EXECUTE
#     """
#     pass


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
        proj_path / ".." / "src" / "temp.sv", 
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
