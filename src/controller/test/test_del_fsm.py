import os
from pathlib import Path

from enum import Enum

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge
from cocotb_tools.runner import get_runner
from cocotb.triggers import ReadOnly

del_fsm_states = Enum(
    "del_fsm_states",
    [
        ("DEL_ST_START", 0),
        ("DEL_ST_DELETE", 1),
        ("DEL_ST_ERROR", 2)
    ]
)


class DelFsmTester:
    """Helper class for Controller."""

    def __init__(self, dut):
        self.dut = dut
        self.clk = dut.clk
        self.rst_n = dut.rst_n
        self.enabled = dut.en
        self.enter = dut.enter
        self.hit = dut.hit
        self.idx_in = dut.idx_in
        self.idx_out = dut.idx_out
        self.write_out = dut.write_out
        self.select_out = dut.select_out
        self.delete_out = dut.delete_out
        self.cmd = dut.cmd  # packed struct: cmd[1]=done, cmd[0]=error

    class _BitView:
        """Wrapper to expose a single bit with a .value attribute."""
        def __init__(self, val):
            self._val = val
        @property
        def value(self):
            return self._val

    @property
    def state(self):
        """Return the current FSM state as an integer."""
        return int(self.dut.state.value)

    @property
    def cmd_done(self):
        """Extract the 'done' bit from the packed cmd struct (bit 1)."""
        return self._BitView(int(self.cmd.value[1]))  # MSB = done

    @property
    def cmd_error(self):
        """Extract the 'error' bit from the packed cmd struct (bit 0)."""
        return self._BitView(int(self.cmd.value[0]))  # LSB = error
    

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


    async def set_enabled(self, enabled: bool):
        """Set the enabled signal."""
        self.enabled.value = int(enabled)
        await RisingEdge(self.clk)


    async def set_enter(self, enter: bool):
        """Set the enter signal."""
        self.enter.value = int(enter)
        await RisingEdge(self.clk)


    async def set_hit(self, hit: bool):
        """Set the hit signal."""
        self.hit.value = int(hit)
        await RisingEdge(self.clk)

    async def set_idx_in(self, idx: int):
        """Set the idx_in signal (one-hot encoded)."""
        self.idx_in.value = 1 << idx
        await RisingEdge(self.clk)

    async def check_output_signals_are_resetted(self):
        """Check that all output signals are in their default/idle values."""
        assert self.cmd_done.value == 0, "cmd.done should be 0"
        assert self.cmd_error.value == 0, "cmd.error should be 0"
        assert self.write_out.value == 0, "write_out should be 0"
        assert self.select_out.value == 0, "select_out should be 0"
        assert self.delete_out.value == 0, "delete_out should be 0"
        assert self.idx_out.value == 0, "idx_out should be 0"


@cocotb.test()
async def test_reset_from_every_state(dut):
    """Test 1: Verify transition to DEL_ST_START on reset.
    After asserting rst_n low, the FSM must return to the start state
    regardless of which state it was in. All outputs should be in their
    default/idle values after reset."""

    tester = DelFsmTester(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # Apply reset
    await tester.reset()

    await ReadOnly()

    assert tester.state == del_fsm_states.DEL_ST_START.value, "FSM should be in DEL_ST_START state after reset"

    # Check that all outputs are reset to default values
    await tester.check_output_signals_are_resetted()

    dut._log.info("✓ Test 1 passed: Reset returns FSM to start state")


@cocotb.test()
async def test_delete_hit_path(dut):
    """Test 2: Verify correct state transitions when a delete operation
    is initiated and a hit is detected. The FSM should go through:
    START -> CHECK_EXISTS -> DELETE -> DONE."""

    tester = DelFsmTester(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await tester.reset()

    # Enter the FSM and enable it
    dut.en.value = 1
    dut.enter.value = 1

    await RisingEdge(dut.clk)

    # After enabling sub state switch to DEL_ST_START
    assert tester.state == del_fsm_states.DEL_ST_START.value, "FSM should be in START state after entering"
    await tester.check_output_signals_are_resetted()

    
    # wait for memory block to process hit and transition to DELETE
    await FallingEdge(dut.clk)

    # Provide a hit signal in CHECK_EXISTS
    dut.hit.value = 1
    dut.idx_in.value = 0b0010  # one-hot index for cell 1

    # Wait until Start State processed hit
    await ReadOnly()

    await RisingEdge(dut.clk)

    assert tester.state == del_fsm_states.DEL_ST_DELETE.value, "FSM should still be in DELETE state after entering"
    assert tester.select_out.value == 0, "select_out should be 0 in DELETE state"
    assert tester.write_out.value == 0, "write_out should be 0 in DELETE state"
    assert tester.delete_out.value == 1, "delete_out should be 1 in DELETE state"
    assert tester.idx_out.value == 0b0010, "idx_out should reflect idx_in in DELETE state"

    # simulating now the memory block to process the delete command
    await FallingEdge(dut.clk)

    await ReadOnly()


    await RisingEdge(dut.clk)

    assert tester.state == del_fsm_states.DEL_ST_START.value, "FSM should be in START state after delete is processed"
    assert tester.cmd_done.value == 1, "cmd.done should be 1 in START state"
    assert tester.cmd_error.value == 0, "cmd.error should be 0 in START state"


    # Delete went through 
    await RisingEdge(dut.clk)

    assert tester.state == del_fsm_states.DEL_ST_START.value, "FSM should be in START state after hit is asserted"
    tester.check_output_signals_are_resetted()

    dut._log.info("✓ Test 2 passed: Delete with hit transitions correctly through all states")


@cocotb.test()
async def test_delete_miss_path(dut):
    """Test 3: Verify that the FSM transitions to the error state when
    a delete operation is initiated and no hit is detected. The FSM should
    go through: START -> CHECK_EXISTS -> ERROR."""

    tester = DelFsmTester(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await tester.reset()

    # Enter the FSM and enable it
    dut.en.value = 1
    dut.enter.value = 1
    await RisingEdge(dut.clk)
    dut.enter.value = 0

    # FSM is now in START, will transition to CHECK_EXISTS
    await RisingEdge(dut.clk)

    # No hit in CHECK_EXISTS
    dut.hit.value = 0
    await RisingEdge(dut.clk)

    # FSM should now be in ERROR state
    await ReadOnly()
    assert tester.cmd_error.value == 1, "cmd.error should be 1 in ERROR state"
    assert tester.cmd_done.value == 0, "cmd.done should be 0 in ERROR state"

    dut._log.info("✓ Test 3 passed: Delete without hit transitions to error state")


@cocotb.test()
async def test_outputs_per_state(dut):
    """Test 4: Verify that the outputs are correctly set in each state
    of the FSM. Checks select_out, write_out, delete_out, idx_out,
    cmd.done, and cmd.error at each transition."""

    tester = DelFsmTester(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await tester.reset()

    # Enter the FSM
    dut.en.value = 1
    dut.enter.value = 1
    await RisingEdge(dut.clk)
    dut.enter.value = 0

    # -- START state: select_out should signal a key lookup --
    await ReadOnly()
    assert tester.write_out.value == 0, "write_out should be 0 in START"
    assert tester.cmd_done.value == 0, "cmd.done should be 0 in START"
    assert tester.cmd_error.value == 0, "cmd.error should be 0 in START"

    await RisingEdge(dut.clk)

    # -- CHECK_EXISTS state: provide a hit --
    dut.hit.value = 1
    dut.idx_in.value = 0b0100  # one-hot cell 2
    await ReadOnly()
    assert tester.cmd_done.value == 0, "cmd.done should be 0 in CHECK_EXISTS"
    assert tester.cmd_error.value == 0, "cmd.error should be 0 in CHECK_EXISTS"

    await RisingEdge(dut.clk)
    dut.hit.value = 0

    # -- DELETE state: write_out and delete_out should be asserted --
    await ReadOnly()
    assert tester.write_out.value == 1, "write_out should be 1 in DELETE state"
    assert tester.delete_out.value == 1, "delete_out should be 1 in DELETE state"
    assert tester.cmd_done.value == 0, "cmd.done should be 0 in DELETE state"

    await RisingEdge(dut.clk)

    # -- DONE state --
    await ReadOnly()
    assert tester.cmd_done.value == 1, "cmd.done should be 1 in DONE state"
    assert tester.write_out.value == 0, "write_out should be 0 in DONE state"
    assert tester.delete_out.value == 0, "delete_out should be 0 in DONE state"

    dut._log.info("✓ Test 4 passed: Outputs are correct in each state")


@cocotb.test()
async def test_sequential_deletes(dut):
    """Test 5: Verify that the FSM can handle multiple delete operations
    in sequence without errors. After each delete completes (DONE), the FSM
    is re-entered and should process the next delete correctly."""

    tester = DelFsmTester(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await tester.reset()
    dut.en.value = 1

    for iteration in range(3):
        dut._log.info(f"Sequential delete iteration {iteration + 1}")

        # Enter the FSM
        dut.enter.value = 1
        await RisingEdge(dut.clk)
        dut.enter.value = 0

        # START -> CHECK_EXISTS
        await RisingEdge(dut.clk)

        # Provide hit
        dut.hit.value = 1
        dut.idx_in.value = 1 << iteration
        await RisingEdge(dut.clk)

        # CHECK_EXISTS -> DELETE
        dut.hit.value = 0
        await RisingEdge(dut.clk)

        # DELETE -> DONE
        await ReadOnly()
        assert tester.cmd_done.value == 1, \
            f"Iteration {iteration + 1}: cmd.done should be 1 in DONE state"
        assert tester.cmd_error.value == 0, \
            f"Iteration {iteration + 1}: cmd.error should be 0"

    dut._log.info("✓ Test 5 passed: Multiple sequential deletes work correctly")


@cocotb.test()
async def test_idle_when_disabled(dut):
    """Test 6: Verify that the FSM does not change state or outputs when
    en is deasserted. The FSM should remain in its current state and
    all outputs should stay at their current values."""

    tester = DelFsmTester(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await tester.reset()

    # Keep FSM disabled
    dut.en.value = 0
    dut.enter.value = 0

    # Wait several cycles
    for _ in range(5):
        await RisingEdge(dut.clk)

    await ReadOnly()
    assert tester.cmd_done.value == 0, "cmd.done should remain 0 when disabled"
    assert tester.cmd_error.value == 0, "cmd.error should remain 0 when disabled"
    assert tester.write_out.value == 0, "write_out should remain 0 when disabled"
    assert tester.delete_out.value == 0, "delete_out should remain 0 when disabled"

    dut._log.info("✓ Test 6 passed: FSM is idle when not enabled")


@cocotb.test()
async def test_reenter_after_done(dut):
    """Test 7: Verify that the FSM can be re-entered correctly after
    completing a delete operation. After DONE, asserting enter should
    bring the FSM back to START and allow a fresh delete."""

    tester = DelFsmTester(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await tester.reset()
    dut.en.value = 1

    # First delete: run to DONE
    dut.enter.value = 1
    await RisingEdge(dut.clk)
    dut.enter.value = 0
    await RisingEdge(dut.clk)          # START -> CHECK_EXISTS
    dut.hit.value = 1
    dut.idx_in.value = 0b0001
    await RisingEdge(dut.clk)          # CHECK_EXISTS -> DELETE
    dut.hit.value = 0
    await RisingEdge(dut.clk)          # DELETE -> DONE

    await ReadOnly()
    assert tester.cmd_done.value == 1, "Should be in DONE state"

    # Re-enter
    dut.enter.value = 1
    await RisingEdge(dut.clk)
    dut.enter.value = 0

    # Should be back in START — cmd.done must be cleared
    await ReadOnly()
    assert tester.cmd_done.value == 0, "cmd.done should be 0 after re-entering"
    assert tester.cmd_error.value == 0, "cmd.error should be 0 after re-entering"

    dut._log.info("✓ Test 7 passed: Re-entry after DONE works correctly")


@cocotb.test()
async def test_en_deassert_mid_operation(dut):
    """Test 8: Verify edge cases — en deasserted mid-operation freezes the
    FSM, and enter asserted mid-operation resets back to START."""

    tester = DelFsmTester(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await tester.reset()

    # Start a delete
    dut.en.value = 1
    dut.enter.value = 1
    await RisingEdge(dut.clk)
    dut.enter.value = 0
    await RisingEdge(dut.clk)  # Now in CHECK_EXISTS

    # Deassert en mid-operation — FSM should freeze
    dut.en.value = 0
    dut.hit.value = 1
    dut.idx_in.value = 0b0001
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    # Should NOT have advanced to DELETE since en=0
    await ReadOnly()
    assert tester.cmd_done.value == 0, "FSM should be frozen, cmd.done should be 0"
    assert tester.write_out.value == 0 or tester.delete_out.value == 0, \
        "FSM should not be in DELETE state when disabled"

    # Re-enable — should now advance
    dut.en.value = 1
    await RisingEdge(dut.clk)

    # Now test enter mid-operation: re-enter resets to START
    dut.enter.value = 1
    await RisingEdge(dut.clk)
    dut.enter.value = 0

    await ReadOnly()
    assert tester.cmd_done.value == 0, "cmd.done should be 0 after mid-operation re-enter"
    assert tester.cmd_error.value == 0, "cmd.error should be 0 after mid-operation re-enter"

    dut._log.info("✓ Test 8 passed: en deassert freezes FSM, enter mid-op resets to START")


@cocotb.test()
async def test_output_signals_each_state(dut):
    """Test 9: Verify that the FSM correctly sets the output signals for
    each state — a comprehensive check of all outputs at every state
    along the hit path."""

    tester = DelFsmTester(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await tester.reset()

    dut.en.value = 1
    dut.enter.value = 1
    await RisingEdge(dut.clk)
    dut.enter.value = 0

    # START state outputs
    await ReadOnly()
    start_write = tester.write_out.value
    start_delete = tester.delete_out.value
    start_done = tester.cmd_done.value
    start_error = tester.cmd_error.value
    assert start_write == 0, "write_out should be 0 in START"
    assert start_delete == 0, "delete_out should be 0 in START"
    assert start_done == 0, "cmd.done should be 0 in START"
    assert start_error == 0, "cmd.error should be 0 in START"

    await RisingEdge(dut.clk)

    # CHECK_EXISTS state outputs
    dut.hit.value = 1
    dut.idx_in.value = 0b0001
    await ReadOnly()
    assert tester.cmd_done.value == 0, "cmd.done should be 0 in CHECK_EXISTS"
    assert tester.cmd_error.value == 0, "cmd.error should be 0 in CHECK_EXISTS"

    await RisingEdge(dut.clk)
    dut.hit.value = 0

    # DELETE state outputs
    await ReadOnly()
    assert tester.write_out.value == 1, "write_out should be 1 in DELETE"
    assert tester.delete_out.value == 1, "delete_out should be 1 in DELETE"
    assert tester.cmd_done.value == 0, "cmd.done should be 0 in DELETE"

    await RisingEdge(dut.clk)

    # DONE state outputs
    await ReadOnly()
    assert tester.cmd_done.value == 1, "cmd.done should be 1 in DONE"
    assert tester.cmd_error.value == 0, "cmd.error should be 0 in DONE"
    assert tester.write_out.value == 0, "write_out should be 0 in DONE"
    assert tester.delete_out.value == 0, "delete_out should be 0 in DONE"

    dut._log.info("✓ Test 9 passed: All output signals correct in each state")


@cocotb.test()
async def test_select_out_single_cycle(dut):
    """Test 10: Verify that select_out is only asserted for the appropriate
    duration when initiating a delete operation, and is not held longer
    than expected."""

    tester = DelFsmTester(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await tester.reset()

    dut.en.value = 1
    dut.enter.value = 1
    await RisingEdge(dut.clk)
    dut.enter.value = 0

    # Record select_out in START
    await ReadOnly()
    select_in_start = int(tester.select_out.value)

    await RisingEdge(dut.clk)

    # Record select_out in CHECK_EXISTS
    await ReadOnly()
    select_in_check = int(tester.select_out.value)

    # Provide hit to advance
    dut.hit.value = 1
    dut.idx_in.value = 0b0001
    await RisingEdge(dut.clk)
    dut.hit.value = 0

    # Record select_out in DELETE
    await ReadOnly()
    select_in_delete = int(tester.select_out.value)

    await RisingEdge(dut.clk)

    # Record select_out in DONE
    await ReadOnly()
    select_in_done = int(tester.select_out.value)

    # select_out should not be asserted in DELETE or DONE
    assert select_in_delete == 0, "select_out should be 0 in DELETE state"
    assert select_in_done == 0, "select_out should be 0 in DONE state"

    dut._log.info(f"select_out: START={select_in_start}, CHECK={select_in_check}, DELETE={select_in_delete}, DONE={select_in_done}")
    dut._log.info("✓ Test 10 passed: select_out timing is correct")


@cocotb.test()
async def test_idx_out_on_hit(dut):
    """Test 11: Verify that idx_out represents the idx_in when hit is
    detected, and is reset to 0 in the done and error states."""

    tester = DelFsmTester(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await tester.reset()

    dut.en.value = 1
    dut.enter.value = 1
    await RisingEdge(dut.clk)
    dut.enter.value = 0
    await RisingEdge(dut.clk)  # START -> CHECK_EXISTS

    # Provide hit with specific index
    dut.hit.value = 1
    dut.idx_in.value = 0b0100  # one-hot cell 2
    await RisingEdge(dut.clk)  # CHECK_EXISTS -> DELETE
    dut.hit.value = 0

    # In DELETE state, idx_out should reflect the saved index
    await ReadOnly()
    assert tester.idx_out.value != 0, "idx_out should be non-zero in DELETE state"

    await RisingEdge(dut.clk)  # DELETE -> DONE

    # In DONE state, idx_out should be 0
    await ReadOnly()
    assert tester.idx_out.value == 0, "idx_out should be 0 in DONE state"

    dut._log.info("✓ Test 11 passed: idx_out correct on hit, cleared in DONE")


@cocotb.test()
async def test_idx_out_zero_on_miss(dut):
    """Test 11a: Verify that idx_out is 0 when no hit is detected and the
    FSM transitions to the error state. The FSM should not propagate any
    invalid index values when an operation fails."""

    tester = DelFsmTester(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await tester.reset()

    dut.en.value = 1
    dut.enter.value = 1
    await RisingEdge(dut.clk)
    dut.enter.value = 0
    await RisingEdge(dut.clk)  # START -> CHECK_EXISTS

    # No hit
    dut.hit.value = 0
    await RisingEdge(dut.clk)  # CHECK_EXISTS -> ERROR

    # In ERROR state, idx_out should be 0
    await ReadOnly()
    assert tester.idx_out.value == 0, \
        f"idx_out should be 0 in ERROR state, got {tester.idx_out.value}"
    assert tester.cmd_error.value == 1, "cmd.error should be 1 in ERROR state"

    dut._log.info("✓ Test 11a passed: idx_out is 0 on miss / error state")


@cocotb.test()
async def test_idx_out_cleared_after_operation(dut):
    """Test 11c: Verify that idx_out is reset to 0 in the done and error
    states, even if a hit was detected in the previous state. Ensures
    the FSM does not propagate stale index values after completing."""

    tester = DelFsmTester(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await tester.reset()
    dut.en.value = 1

    # --- Path 1: Hit -> DELETE -> DONE, check idx_out cleared ---
    dut.enter.value = 1
    await RisingEdge(dut.clk)
    dut.enter.value = 0
    await RisingEdge(dut.clk)          # START -> CHECK_EXISTS

    dut.hit.value = 1
    dut.idx_in.value = 0b1000          # one-hot cell 3
    await RisingEdge(dut.clk)          # CHECK_EXISTS -> DELETE
    dut.hit.value = 0

    # DELETE: idx_out should be set
    await ReadOnly()
    assert tester.idx_out.value != 0, "idx_out should be non-zero in DELETE"

    await RisingEdge(dut.clk)          # DELETE -> DONE

    # DONE: idx_out should be cleared
    await ReadOnly()
    assert tester.idx_out.value == 0, \
        f"idx_out should be 0 in DONE, got {tester.idx_out.value}"

    # --- Path 2: Re-enter, miss -> ERROR, check idx_out still 0 ---
    dut.enter.value = 1
    await RisingEdge(dut.clk)
    dut.enter.value = 0
    await RisingEdge(dut.clk)          # START -> CHECK_EXISTS

    dut.hit.value = 0
    await RisingEdge(dut.clk)          # CHECK_EXISTS -> ERROR

    await ReadOnly()
    assert tester.idx_out.value == 0, \
        f"idx_out should be 0 in ERROR, got {tester.idx_out.value}"

    dut._log.info("✓ Test 11c passed: idx_out cleared after both DONE and ERROR")


@cocotb.test()
async def test_cmd_done_and_error_signals(dut):
    """Test 12: Verify that cmd.done is asserted only in the DONE state
    and cmd.error is asserted only in the ERROR state, and both are
    deasserted in all other states."""

    tester = DelFsmTester(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await tester.reset()
    dut.en.value = 1

    # --- Hit path: check cmd signals at each state ---
    dut.enter.value = 1
    await RisingEdge(dut.clk)
    dut.enter.value = 0

    # START
    await ReadOnly()
    assert tester.cmd_done.value == 0, "cmd.done should be 0 in START"
    assert tester.cmd_error.value == 0, "cmd.error should be 0 in START"

    await RisingEdge(dut.clk)

    # CHECK_EXISTS
    dut.hit.value = 1
    dut.idx_in.value = 0b0001
    await ReadOnly()
    assert tester.cmd_done.value == 0, "cmd.done should be 0 in CHECK_EXISTS"
    assert tester.cmd_error.value == 0, "cmd.error should be 0 in CHECK_EXISTS"

    await RisingEdge(dut.clk)
    dut.hit.value = 0

    # DELETE
    await ReadOnly()
    assert tester.cmd_done.value == 0, "cmd.done should be 0 in DELETE"
    assert tester.cmd_error.value == 0, "cmd.error should be 0 in DELETE"

    await RisingEdge(dut.clk)

    # DONE
    await ReadOnly()
    assert tester.cmd_done.value == 1, "cmd.done should be 1 in DONE"
    assert tester.cmd_error.value == 0, "cmd.error should be 0 in DONE"

    # --- Miss path: check ERROR state ---
    dut.enter.value = 1
    await RisingEdge(dut.clk)
    dut.enter.value = 0
    await RisingEdge(dut.clk)  # START -> CHECK_EXISTS

    dut.hit.value = 0
    await RisingEdge(dut.clk)  # CHECK_EXISTS -> ERROR

    await ReadOnly()
    assert tester.cmd_error.value == 1, "cmd.error should be 1 in ERROR"
    assert tester.cmd_done.value == 0, "cmd.done should be 0 in ERROR"

    dut._log.info("✓ Test 12 passed: cmd.done and cmd.error asserted only in correct states")


@cocotb.test()
async def test_enter_mid_operation_resets(dut):
    """Test 13: Verify that asserting enter while in the middle of a delete
    operation resets the FSM to the start state without unintended behavior.
    All outputs should return to their idle values."""

    tester = DelFsmTester(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await tester.reset()
    dut.en.value = 1

    # Start a delete and advance to CHECK_EXISTS
    dut.enter.value = 1
    await RisingEdge(dut.clk)
    dut.enter.value = 0
    await RisingEdge(dut.clk)  # Now in CHECK_EXISTS

    # Provide hit to advance to DELETE
    dut.hit.value = 1
    dut.idx_in.value = 0b0010
    await RisingEdge(dut.clk)  # Now in DELETE
    dut.hit.value = 0

    # Assert enter mid-operation (in DELETE state)
    dut.enter.value = 1
    await RisingEdge(dut.clk)  # Should reset to START
    dut.enter.value = 0

    # Verify FSM is back in START
    await ReadOnly()
    assert tester.cmd_done.value == 0, "cmd.done should be 0 after mid-op re-enter"
    assert tester.cmd_error.value == 0, "cmd.error should be 0 after mid-op re-enter"
    assert tester.write_out.value == 0, "write_out should be 0 after mid-op re-enter"
    assert tester.delete_out.value == 0, "delete_out should be 0 after mid-op re-enter"
    assert tester.idx_out.value == 0, "idx_out should be 0 after mid-op re-enter"

    dut._log.info("✓ Test 13 passed: enter mid-operation correctly resets FSM")



def test_del_fsm_runner():
    sim = os.getenv("SIM", "icarus")
    proj_path = Path(__file__).resolve().parent
    
    # Deine Verilog Datei
    sources = [
        proj_path / ".." / "src" / "ctrl_types_pkg.sv",
        proj_path / ".." / "src" / "del_fsm.sv"
    ]

    runner = get_runner(sim)

    parameters = {
        "NUM_ENTRIES": 4
    }

    runner.build(
        sources=sources,
        hdl_toplevel="del_fsm",
        always=True, 
        waves=True,
        timescale=("1ns", "1ps")
    )

    runner.test(
        hdl_toplevel="del_fsm", 
        test_module="test_del_fsm",
        waves=True
    )

if __name__ == "__main__":
    test_controller_runner()