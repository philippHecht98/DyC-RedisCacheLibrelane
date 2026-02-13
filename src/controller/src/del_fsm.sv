

module del_fsm #(
    parameter NUM_ENTRIES = 16
)(
    input logic clk,
    input logic rst_n,

    // Control from parent FSM
    input logic en,                              // FSM is active (state == ST_DEL)
    input logic enter,                           // First cycle entering ST_DEL

    // Feedback from memory block
    input logic hit,                             // Memory reports a key match
    input logic [NUM_ENTRIES-1:0] idx_in,        // Index of the matched cell (one-hot)

    // Commands to memory block
    output logic select_out,                     // 1 = trigger key lookup in memory
    output logic write_out,                      // 1 = write to memory (used for zeroing the cell)
    output logic delete_out,                     // 1 = signal memory to delete the cell
    output logic [NUM_ENTRIES-1:0] idx_out,      // One-hot index of the cell to operate on


    // Status back to parent FSM
    output ctrl_types_pkg::sub_cmd_t cmd
);
    import ctrl_types_pkg::*;

    ctrl_types_pkg::del_substate_e state, next_state;

    // Registered copy of the hit index, captured in CHECK_EXISTS
    logic [NUM_ENTRIES-1:0] saved_idx;

    // ---------------------------------------------------------------
    // Combinational: next-state logic + output logic
    // ---------------------------------------------------------------
    always_comb begin
        next_state = state;
        cmd.done   = 1'b0;
        cmd.error  = 1'b0;
        select_out = 1'b0;
        write_out  = 1'b0;
        delete_out = 1'b0;
        idx_out    = '0;

        case (state)

            // ----------------------------------------------------------
            // DEL_ST_START – Entry point.
            // Ask the memory block to search for the key (get_by_key).
            // Outputs: select=0 (key-based lookup), write=0, idx=0.
            // On the next negative clock edge the memory block will
            // evaluate key_in and provide hit / hit_idx combinationally.
            // ----------------------------------------------------------
            DEL_ST_START: begin
                select_out = 1'b0;   // key-based lookup (not index-based)
                write_out  = 1'b0;
                idx_out    = '0;
                delete_out = 1'b0;
                next_state = DEL_ST_CHECK_EXISTS;
            end

            // ----------------------------------------------------------
            // DEL_ST_CHECK_EXISTS – Read the hit result from memory.
            // If HIT  → save the index and proceed to ST_DEL_DELETE.
            // If !HIT → the key does not exist; go to ST_DEL_ERROR.

            // This is only a temporary state inbetween the two flanks of the clock
            // calculates the next state based on the negative edge of the clock
            // ----------------------------------------------------------
            DEL_ST_CHECK_EXISTS: begin
                if (hit) begin
                    next_state = ctrl_types_pkg::ST_DEL_DELETE;
                end else begin
                    next_state = ctrl_types_pkg::ST_DEL_ERROR;
                end
            end

            // ----------------------------------------------------------
            // ST_DEL_DELETE – Erase the cell.
            // Set delete_out to 1 to indicate a delete operation
            // Outputs: write=0, delete_out=1, idx=saved_idx (one-hot index of the cell to delete)

            // ----------------------------------------------------------
            ST_DEL_DELETE: begin
                select_out = 1'b0;
                write_out  = 1'b0;
                delete_out = 1'b1;
                idx_out    = idx_in; // Use the index from the hit result to target the delete
                next_state = ctrl_types_pkg::ST_DEL_DONE;
            end

            // ----------------------------------------------------------
            // ST_DEL_DONE – Deletion complete.
            // Signal cmd.done=1 so the parent FSM returns to ST_IDLE.
            // ----------------------------------------------------------
            ST_DEL_DONE: begin
                write_out  = 1'b0;
                select_out = 1'b0;
                delete_out = 1'b0;
                idx_out    = '0;
                cmd.done = 1'b1;
            end

            // ----------------------------------------------------------
            // ST_DEL_ERROR – Key not found.
            // Signal cmd.error=1 so the parent FSM can handle the error.
            // ----------------------------------------------------------
            ST_DEL_ERROR: begin
                write_out  = 1'b0;
                select_out = 1'b0;
                delete_out = 1'b0;
                idx_out    = '0;
                cmd.error = 1'b1;
            end

            default: next_state = DEL_ST_START;
        endcase
    end

    // ---------------------------------------------------------------
    // Sequential: state register + saved index
    // ---------------------------------------------------------------
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state     <= DEL_ST_START;
            saved_idx <= '0;
        end else if (enter) begin
            state     <= DEL_ST_START;
            saved_idx <= '0;
        end else if (en) begin
            state <= next_state;
            // Capture the hit index when transitioning out of CHECK_EXISTS
            if (state == DEL_ST_CHECK_EXISTS && hit)
                saved_idx <= idx_in;
        end
    end
endmodule