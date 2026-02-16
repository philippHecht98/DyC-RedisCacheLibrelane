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
        self.delete_out = dut.delete_out
        self.cmd = dut.cmd  # packed struct: cmd[1]=done, cmd[0]=error
        self.idle = dut.idle

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
    def next_state(self):
        """Return the next FSM state as an integer."""
        return int(self.dut.next_state.value)

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
        self.enabled.value = 0
        self.enter.value = 0
        self.hit.value = 0
        self.idx_in.value = 0
        
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
        assert self.delete_out.value == 0, "delete_out should be 0"
        assert self.idx_out.value == 0, "idx_out should be 0"

@cocotb.test()
async def test_state_is_always_start_when_block_not_enabled(dut):
    """Test 0: Verify that the FSM remains in the start state when not enabled.
    When en=0, the FSM should not transition to any other state and should
    keep all outputs at their default values."""

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
        assert tester.state == del_fsm_states.DEL_ST_START.value, "FSM should remain in DEL_ST_START state when not enabled"
        await tester.check_output_signals_are_resetted()

    dut._log.info("✓ Test 0 passed: FSM remains in start state when not enabled")


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

    assert tester.state == del_fsm_states.DEL_ST_START.value, "FSM should be in DEL_ST_START state after reset"

    # Enter the FSM and enable it
    dut.en.value = 1
    dut.enter.value = 1

    await RisingEdge(dut.clk)

    # After enabling sub state switch to DEL_ST_START
    assert tester.state == del_fsm_states.DEL_ST_START.value, "FSM should be in START state after entering"
    await tester.check_output_signals_are_resetted()

    # wait for memory block to process hit and transition to DELETE
    await FallingEdge(dut.clk)

    # reset enter state after initially entering the FSM
    dut.enter.value = 0


    # Provide a hit signal in CHECK_EXISTS
    dut.hit.value = 1
    dut.idx_in.value = 0b0010  # one-hot index for cell 1

    # Wait until Start State processed hit
    await ReadOnly()


    # Jump into the next cycle of the FSM to process the hit and transition to DELETE
    await RisingEdge(dut.clk)
    await ReadOnly()

    assert tester.state == del_fsm_states.DEL_ST_DELETE.value, "FSM should still be in DELETE state after entering"
    assert tester.delete_out.value == 1, "delete_out should be 1 in DELETE state"
    assert tester.idx_out.value == 0b0010, "idx_out should reflect idx_in in DELETE state"

    # simulating now the memory block to process the delete command
    await FallingEdge(dut.clk)
    await ReadOnly()

    assert tester.cmd_done.value == 1, "cmd.done should be 1 during DELETE state"
    assert tester.cmd_error.value == 0, "cmd.error should be 0 in DELETE state"

    await RisingEdge(dut.clk)
    await ReadOnly()

    assert tester.state == del_fsm_states.DEL_ST_START.value, "FSM should be in START state after delete is processed"
    await tester.check_output_signals_are_resetted()

    dut._log.info("✓ Test 2 passed: Delete with hit transitions correctly through all states")


@cocotb.test()
async def test_delete_miss_path(dut):
    """Test 3: Verify that the FSM transitions to the error state when
    a delete operation is initiated and no hit is detected. The FSM should
    go through: START -> CHECK_EXISTS -> ERROR."""

    tester = DelFsmTester(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await tester.reset()

    assert tester.state == del_fsm_states.DEL_ST_START.value, "FSM should be in DEL_ST_START state after reset"

    # Enter the FSM and enable it
    dut.en.value = 1
    dut.enter.value = 1

    await RisingEdge(dut.clk)
    await ReadOnly()

    # After enabling sub state switch to DEL_ST_START
    assert tester.state == del_fsm_states.DEL_ST_START.value, "FSM should be in START state after entering"
    await tester.check_output_signals_are_resetted()

    # wait for memory block to process hit and transition to DELETE
    await FallingEdge(dut.clk)

    # reset enter state after initially entering the FSM
    dut.enter.value = 0


    # Provide a hit signal in CHECK_EXISTS
    dut.hit.value = 0
    dut.idx_in.value = 0b0000  # one-hot index for cell 1

    # Wait until Start State processed hit
    await ReadOnly()


    # Jump into the next cycle of the FSM to process the hit and transition to DELETE
    await RisingEdge(dut.clk)
    await ReadOnly()

    assert tester.state == del_fsm_states.DEL_ST_ERROR.value, "FSM should be in ERROR state after miss"
    assert tester.delete_out.value == 0, "delete_out should be 0 in ERROR state"
    assert tester.idx_out.value == 0b0000, "idx_out should be 0 in ERROR state"

    # simulating now the memory block to process the delete command
    await FallingEdge(dut.clk)
    await ReadOnly()

    assert tester.cmd_done.value == 0, "cmd.done should be 0 during ERROR state"
    assert tester.cmd_error.value == 1, "cmd.error should be 1 in ERROR state"

    await RisingEdge(dut.clk)
    await ReadOnly()

    assert tester.state == del_fsm_states.DEL_ST_START.value, "FSM should be in START state after delete is processed"
    await tester.check_output_signals_are_resetted()


    dut._log.info("✓ Test 3 passed: Delete without hit transitions to error state")


@cocotb.test()
async def test_outputs_per_state(dut):
    """Test 4: Verify that the outputs are correctly set in each state
    of the FSM. Checks delete_out, idx_out,
    cmd.done, and cmd.error at each transition."""

    tester = DelFsmTester(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await tester.reset()

    await FallingEdge(dut.clk)

    dut.state.value = del_fsm_states.DEL_ST_START.value    
    await ReadOnly()

    assert tester.delete_out.value == 0, "delete_out should be 0 in START state"
    assert tester.idx_out.value == 0, "idx_out should be 0 in START state"
    assert tester.cmd_done.value == 0, "cmd.done should be 0 in START state"
    assert tester.cmd_error.value == 0, "cmd.error should be 0 in START state"
    assert tester.next_state == del_fsm_states.DEL_ST_START.value, "next_state should be START when in START state"

    await FallingEdge(dut.clk)
    
    # init the next state for checking    
    dut.en.value = 1
    dut.state.value = del_fsm_states.DEL_ST_START.value
    dut.idx_in.value = 0b0100  # one-hot index for cell 2
    dut.hit.value = 1
    
    await ReadOnly()
    assert tester.next_state == del_fsm_states.DEL_ST_DELETE.value, "next_state should be DELETE when hit is detected"

    await RisingEdge(dut.clk)
    await ReadOnly()

    assert tester.delete_out.value == 1, "delete_out should be 1 in DELETE state"
    assert tester.idx_out.value == 0b0100, "idx_out should reflect idx_in in DELETE state"
    assert tester.cmd_done.value == 1, "cmd.done should be 1 in DELETE state"
    assert tester.cmd_error.value == 0, "cmd.error should be 0 in DELETE state"
    assert tester.next_state == del_fsm_states.DEL_ST_START.value, "next_state should be START after DELETE state"


    await FallingEdge(dut.clk)
    dut.state.value = del_fsm_states.DEL_ST_START.value
    dut.hit.value = 0

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert tester.state == del_fsm_states.DEL_ST_ERROR.value, "FSM should be in ERROR state after processing delete without hit"
    assert tester.next_state == del_fsm_states.DEL_ST_START.value, "next_state should be START when no hit is detected"
    assert tester.delete_out.value == 0, "delete_out should be 0 in ERROR state"
    assert tester.idx_out.value == 0b0000, "idx_out should be 0 in ERROR state"
    assert tester.cmd_done.value == 0, "cmd.done should be 0 in ERROR state"
    assert tester.cmd_error.value == 1, "cmd.error should be 1 in ERROR state"

    await RisingEdge(dut.clk)
    await ReadOnly()

    assert tester.state == del_fsm_states.DEL_ST_START.value, "FSM should be in START state after no hit"
    assert tester.cmd_done.value == 0, "cmd.done should be 0 in START state"
    assert tester.cmd_error.value == 0, "cmd.error should be 0 in START state"
    assert tester.next_state == del_fsm_states.DEL_ST_ERROR.value, "next_state should be ERROR after START state (enter is still set)"
    assert tester.delete_out.value == 0, "delete_out should be 0 in START state"
    assert tester.idx_out.value == 0b0000, "idx_out should be 0 in START state"
   
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

        await FallingEdge(dut.clk)

        # alternate between hit and miss for each iteration
        hit = iteration % 2
        dut.enter.value = 1

        dut.hit.value = hit
        dut.idx_in.value = 0b0010

        await RisingEdge(dut.clk)
        await ReadOnly()
        
        ## Start state after entering the FSM
        assert tester.state == del_fsm_states.DEL_ST_START.value, "FSM should be in START state after entering"
        await tester.check_output_signals_are_resetted(), "Outputs should be reset in START state after entering"
        
        assert tester.next_state == (del_fsm_states.DEL_ST_DELETE.value if hit else del_fsm_states.DEL_ST_ERROR.value), \
            f"Next state should be {'DELETE' if hit else 'ERROR'} when hit is {'detected' if hit else 'not detected'}"

        await FallingEdge(dut.clk)
        dut.enter.value = 0  # reset enter after initially entering the FSM
        
        await RisingEdge(dut.clk)
        await ReadOnly()

        assert tester.state == (del_fsm_states.DEL_ST_DELETE.value if hit else del_fsm_states.DEL_ST_ERROR.value), \
            f"FSM should be in {'DELETE' if hit else 'ERROR'} state after processing hit={hit}"

        assert tester.next_state == del_fsm_states.DEL_ST_START.value, "FSM should be in DEL_ST_START after processing delete or error"
        assert tester.cmd_done.value == (1 if hit else 0), f"cmd.done should be {'1' if hit else '0'} in {'DELETE' if hit else 'ERROR'} state"
        assert tester.cmd_error.value == (0 if hit else 1), f"cmd.error should be {'0' if hit else '1'} in {'DELETE' if hit else 'ERROR'} state"

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
        await tester.check_output_signals_are_resetted(), "Outputs should remain at default values when FSM is disabled"

    dut._log.info("✓ Test 6 passed: FSM is idle when not enabled")


@cocotb.test()
async def test_en_deassert_mid_operation(dut):
    """Test 7: Verify edge cases — en deasserted mid-operation freezes the
    FSM, and enter asserted mid-operation resets back to START."""

    tester = DelFsmTester(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await tester.reset()

    # Start a delete -> bring FSM to DEL_ST_DELETE
    dut.en.value = 1
    dut.enter.value = 1
    await RisingEdge(dut.clk)
    
    
    assert tester.state == del_fsm_states.DEL_ST_START.value, "FSM should be in START state after entering"
    await tester.check_output_signals_are_resetted(), "Outputs should be reset in START state after entering"

    dut.hit.value = 1
    dut.idx_in.value = 0b0001
    dut.enter.value = 0

    await ReadOnly()

    await RisingEdge(dut.clk)  # Now in DEL_ST_DELETE
    
    assert tester.state == del_fsm_states.DEL_ST_START.value, "FSM should be in START state after reset of mid-operation"

    await FallingEdge(dut.clk)

    ## setting up the FSM again for testing and disable it in the middle of the operation
    dut.enter.value = 1
    dut.en.value = 1

    dut.hit.value = 1
    dut.idx_in.value = 0b0001

    await RisingEdge(dut.clk)  # Now in DEL_ST_DELETE

    await FallingEdge(dut.clk)
    dut.en.value = 0  # Deassert enable mid-operation
    await RisingEdge(dut.clk)

    assert tester.state == del_fsm_states.DEL_ST_START.value, "FSM should remain in START state when en is deasserted mid-operation"
    await tester.check_output_signals_are_resetted(), "Outputs should be reset to default values when en is deasserted mid-operation"

    dut._log.info("✓ Test 7 passed: en deassert freezes FSM, enter mid-op resets to START")


@cocotb.test()
async def test_output_signals_each_state(dut):
    """Test 9: Verify that the FSM correctly sets the output signals for
    each state — a comprehensive check of all outputs at every state
    along the hit path."""

    tester = DelFsmTester(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await tester.reset()

    # -- START state after reset: all outputs idle --
    assert tester.state == del_fsm_states.DEL_ST_START.value, "FSM should be in START after reset"
    await tester.check_output_signals_are_resetted()

    # Enter the FSM and enable it
    dut.en.value = 1
    dut.enter.value = 1

    await RisingEdge(dut.clk)

    # Still in START (enter forces START on posedge)
    assert tester.state == del_fsm_states.DEL_ST_START.value, "FSM should be in START after entering"
    await tester.check_output_signals_are_resetted()

    await FallingEdge(dut.clk)
    dut.enter.value = 0
    dut.hit.value = 1
    dut.idx_in.value = 0b0010
    await ReadOnly()

    # -- Transition to DELETE --
    await RisingEdge(dut.clk)
    await ReadOnly()

    assert tester.state == del_fsm_states.DEL_ST_DELETE.value, "FSM should be in DELETE state"
    assert tester.delete_out.value == 1, "delete_out should be 1 in DELETE"
    assert tester.idx_out.value == 0b0010, "idx_out should match idx_in in DELETE"
    assert tester.cmd_done.value == 1, "cmd.done should be 1 in DELETE"
    assert tester.cmd_error.value == 0, "cmd.error should be 0 in DELETE"

    # -- Transition back to START --
    await RisingEdge(dut.clk)
    await ReadOnly()

    assert tester.state == del_fsm_states.DEL_ST_START.value, "FSM should return to START after DELETE"
    assert tester.delete_out.value == 0, "delete_out should be 0 in START"
    assert tester.idx_out.value == 0, "idx_out should be 0 in START"
    assert tester.cmd_done.value == 0, "cmd.done should be 0 in START"
    assert tester.cmd_error.value == 0, "cmd.error should be 0 in START"

    dut._log.info("✓ Test 9 passed: Output signals correct at each state along hit path")


@cocotb.test()
async def test_delete_out_single_cycle(dut):
    """Test 10: Verify that delete_out is only asserted for the appropriate
    duration when initiating a delete operation, and is not held longer
    than expected."""

    tester = DelFsmTester(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await tester.reset()

    # -- START: delete_out must be 0 --
    assert tester.delete_out.value == 0, "delete_out should be 0 in START before operation"

    # Enter the FSM with a hit
    dut.en.value = 1
    dut.enter.value = 1

    await RisingEdge(dut.clk)
    await ReadOnly()

    # Still START (enter forces START)
    assert tester.delete_out.value == 0, "delete_out should be 0 in START after entering"

    await FallingEdge(dut.clk)
    dut.enter.value = 0
    dut.hit.value = 1
    dut.idx_in.value = 0b0001
    await ReadOnly()

    # -- DELETE state: delete_out asserted for exactly one cycle --
    await RisingEdge(dut.clk)
    await ReadOnly()

    assert tester.state == del_fsm_states.DEL_ST_DELETE.value, "FSM should be in DELETE"
    assert tester.delete_out.value == 1, "delete_out should be 1 in DELETE state"

    # -- Back to START: delete_out must be deasserted --
    await RisingEdge(dut.clk)
    await ReadOnly()

    assert tester.state == del_fsm_states.DEL_ST_START.value, "FSM should return to START"
    assert tester.delete_out.value == 0, "delete_out should be 0 after returning to START"

    # Wait additional cycles to ensure it stays deasserted
    await FallingEdge(dut.clk)
    dut.hit.value = 0
    for _ in range(3):
        await RisingEdge(dut.clk)
        await ReadOnly()
        assert tester.delete_out.value == 0, "delete_out should remain 0 after operation completes"

    dut._log.info("✓ Test 10 passed: delete_out asserted for exactly one cycle during DELETE")


@cocotb.test()
async def test_idx_out_on_hit(dut):
    """Test 11: Verify that idx_out represents the idx_in when hit is
    detected, and is reset to 0 in the done and error states."""

    tester = DelFsmTester(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await tester.reset()

    # Test with several one-hot index values
    for idx_val in [0b0001, 0b0010, 0b0100, 0b1000]:
        # Enter FSM with hit
        await FallingEdge(dut.clk)
        dut.en.value = 1
        dut.enter.value = 1

        await RisingEdge(dut.clk)

        await FallingEdge(dut.clk)
        dut.enter.value = 0
        dut.hit.value = 1
        dut.idx_in.value = idx_val
        await ReadOnly()

        # -- DELETE state: idx_out should match idx_in --
        await RisingEdge(dut.clk)
        await ReadOnly()

        assert tester.state == del_fsm_states.DEL_ST_DELETE.value, "FSM should be in DELETE"
        assert tester.idx_out.value == idx_val, \
            f"idx_out ({tester.idx_out.value:#06b}) should match idx_in ({idx_val:#06b}) in DELETE"

        # -- Back to START: idx_out should be 0 --
        await RisingEdge(dut.clk)
        await ReadOnly()

        assert tester.state == del_fsm_states.DEL_ST_START.value, "FSM should return to START"
        assert tester.idx_out.value == 0, "idx_out should be 0 after returning to START"

    dut._log.info("✓ Test 11 passed: idx_out matches idx_in on hit and resets to 0")


@cocotb.test()
async def test_idx_out_zero_on_miss(dut):
    """Test 11a: Verify that idx_out is 0 when no hit is detected and the
    FSM transitions to the error state. The FSM should not propagate any
    invalid index values when an operation fails."""

    tester = DelFsmTester(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await tester.reset()

    # Enter FSM with miss and a non-zero idx_in that should NOT propagate
    dut.en.value = 1
    dut.enter.value = 1

    await RisingEdge(dut.clk)

    await FallingEdge(dut.clk)
    dut.enter.value = 0
    dut.hit.value = 0
    dut.idx_in.value = 0b0101  # non-zero but should not propagate on miss
    await ReadOnly()

    # -- ERROR state: idx_out must be 0 --
    await RisingEdge(dut.clk)
    await ReadOnly()

    assert tester.state == del_fsm_states.DEL_ST_ERROR.value, "FSM should be in ERROR on miss"
    assert tester.idx_out.value == 0, "idx_out should be 0 in ERROR state"
    assert tester.delete_out.value == 0, "delete_out should be 0 in ERROR state"
    assert tester.cmd_error.value == 1, "cmd.error should be 1 in ERROR state"
    assert tester.cmd_done.value == 0, "cmd.done should be 0 in ERROR state"

    # -- Back to START: idx_out still 0 --
    await RisingEdge(dut.clk)
    await ReadOnly()

    assert tester.state == del_fsm_states.DEL_ST_START.value, "FSM should return to START"
    assert tester.idx_out.value == 0, "idx_out should be 0 after ERROR"

    dut._log.info("✓ Test 11a passed: idx_out is 0 on miss, no invalid index propagation")


@cocotb.test()
async def test_idx_out_cleared_after_operation(dut):
    """Test 11c: Verify that idx_out is reset to 0 in the done and error
    states, even if a hit was detected in the previous state. Ensures
    the FSM does not propagate stale index values after completing."""

    tester = DelFsmTester(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await tester.reset()

    # -- Hit path: idx_out set in DELETE, cleared when returning to START --
    dut.en.value = 1
    dut.enter.value = 1

    await RisingEdge(dut.clk)

    await FallingEdge(dut.clk)
    dut.enter.value = 0
    dut.hit.value = 1
    dut.idx_in.value = 0b1000
    await ReadOnly()

    await RisingEdge(dut.clk)
    await ReadOnly()

    assert tester.state == del_fsm_states.DEL_ST_DELETE.value, "FSM should be in DELETE"
    assert tester.idx_out.value == 0b1000, "idx_out should be set in DELETE"

    # Transition back to START
    await RisingEdge(dut.clk)
    await ReadOnly()

    assert tester.state == del_fsm_states.DEL_ST_START.value, "FSM should return to START"
    assert tester.idx_out.value == 0, "idx_out should be cleared after DELETE completes"

    # -- Miss path: idx_out should remain 0 in ERROR despite non-zero idx_in --
    await FallingEdge(dut.clk)
    dut.enter.value = 1

    await RisingEdge(dut.clk)

    await FallingEdge(dut.clk)
    dut.enter.value = 0
    dut.hit.value = 0
    dut.idx_in.value = 0b1000  # non-zero, should not propagate
    await ReadOnly()

    await RisingEdge(dut.clk)
    await ReadOnly()

    assert tester.state == del_fsm_states.DEL_ST_ERROR.value, "FSM should be in ERROR"
    assert tester.idx_out.value == 0, "idx_out should be 0 in ERROR even with non-zero idx_in"

    # Transition back to START
    await RisingEdge(dut.clk)
    await ReadOnly()

    assert tester.state == del_fsm_states.DEL_ST_START.value, "FSM should return to START"
    assert tester.idx_out.value == 0, "idx_out should remain 0 after ERROR"

    dut._log.info("✓ Test 11c passed: idx_out cleared after operations complete")


@cocotb.test()
async def test_cmd_done_and_error_signals(dut):
    """Test 12: Verify that cmd.done is asserted only in the DONE state
    and cmd.error is asserted only in the ERROR state, and both are
    deasserted in all other states."""

    tester = DelFsmTester(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await tester.reset()

    # -- START state: both cmd.done and cmd.error should be 0 --
    assert tester.cmd_done.value == 0, "cmd.done should be 0 in START"
    assert tester.cmd_error.value == 0, "cmd.error should be 0 in START"

    # -- Hit path: cmd.done=1 only in DELETE, cmd.error=0 everywhere --
    dut.en.value = 1
    dut.enter.value = 1

    await RisingEdge(dut.clk)

    await FallingEdge(dut.clk)
    dut.enter.value = 0
    dut.hit.value = 1
    dut.idx_in.value = 0b0010
    await ReadOnly()

    await RisingEdge(dut.clk)
    await ReadOnly()

    assert tester.state == del_fsm_states.DEL_ST_DELETE.value, "FSM should be in DELETE"
    assert tester.cmd_done.value == 1, "cmd.done should be 1 in DELETE"
    assert tester.cmd_error.value == 0, "cmd.error should be 0 in DELETE"

    # Back to START: both deasserted
    await RisingEdge(dut.clk)
    await ReadOnly()

    assert tester.state == del_fsm_states.DEL_ST_START.value, "FSM should return to START"
    assert tester.cmd_done.value == 0, "cmd.done should be 0 in START after DELETE"
    assert tester.cmd_error.value == 0, "cmd.error should be 0 in START after DELETE"

    # -- Miss path: cmd.error=1 only in ERROR, cmd.done=0 everywhere --
    await FallingEdge(dut.clk)
    dut.enter.value = 1

    await RisingEdge(dut.clk)

    await FallingEdge(dut.clk)
    dut.enter.value = 0
    dut.hit.value = 0
    await ReadOnly()

    await RisingEdge(dut.clk)
    await ReadOnly()

    assert tester.state == del_fsm_states.DEL_ST_ERROR.value, "FSM should be in ERROR"
    assert tester.cmd_done.value == 0, "cmd.done should be 0 in ERROR"
    assert tester.cmd_error.value == 1, "cmd.error should be 1 in ERROR"

    # Back to START: both deasserted
    await RisingEdge(dut.clk)
    await ReadOnly()

    assert tester.state == del_fsm_states.DEL_ST_START.value, "FSM should return to START"
    assert tester.cmd_done.value == 0, "cmd.done should be 0 in START after ERROR"
    assert tester.cmd_error.value == 0, "cmd.error should be 0 in START after ERROR"

    dut._log.info("✓ Test 12 passed: cmd.done and cmd.error correct in each state")


@cocotb.test()
async def test_enter_mid_operation_resets(dut):
    """Test 13: Verify that asserting enter while in the middle of a delete
    operation resets the FSM to the start state without unintended behavior.
    All outputs should return to their idle values."""

    tester = DelFsmTester(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await tester.reset()

    # Start a delete operation to reach DELETE state
    dut.en.value = 1
    dut.enter.value = 1

    await RisingEdge(dut.clk)

    assert tester.state == del_fsm_states.DEL_ST_START.value, "FSM should be in START after entering"

    dut.hit.value = 1
    dut.idx_in.value = 0b0001
    dut.enter.value = 0
    await ReadOnly()

    await RisingEdge(dut.clk)
    await ReadOnly()

    assert tester.state == del_fsm_states.DEL_ST_DELETE.value, "FSM should be in DELETE"

    # Assert enter mid-operation to force reset to START
    await FallingEdge(dut.clk)
    dut.enter.value = 1

    await RisingEdge(dut.clk)
    await ReadOnly()

    # FSM should be forced back to START
    assert tester.state == del_fsm_states.DEL_ST_START.value, \
        "FSM should reset to START when enter is asserted mid-operation"
    await tester.check_output_signals_are_resetted()

    # Also test enter during ERROR state
    await FallingEdge(dut.clk)
    dut.enter.value = 0
    dut.hit.value = 0

    await RisingEdge(dut.clk)
    await ReadOnly()

    assert tester.state == del_fsm_states.DEL_ST_ERROR.value, "FSM should be in ERROR"

    # Assert enter mid-error
    await FallingEdge(dut.clk)
    dut.enter.value = 1

    await RisingEdge(dut.clk)
    await ReadOnly()

    assert tester.state == del_fsm_states.DEL_ST_START.value, \
        "FSM should reset to START when enter is asserted during ERROR"
    await tester.check_output_signals_are_resetted()

    dut._log.info("✓ Test 13 passed: enter mid-operation resets FSM to START with idle outputs")



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
    test_del_fsm_runner();