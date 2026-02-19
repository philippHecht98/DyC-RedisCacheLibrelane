

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
    output logic delete_out,                     // 1 = signal memory to delete the cell
    output logic [NUM_ENTRIES-1:0] idx_out,      // One-hot index of the cell to operate on


    // Status back to parent FSM
    output ctrl_types_pkg::sub_cmd_t cmd
);
    import ctrl_types_pkg::*;

    ctrl_types_pkg::del_substate_e state, next_state;

    logic idle; // Not active

    // Registered copy of the hit index, captured in CHECK_EXISTS

    // ---------------------------------------------------------------
    // Combinational: next-state logic + output logic
    // ---------------------------------------------------------------
    always_comb begin
        idle = (en == 0 && enter == 0);
        next_state = state;
        delete_out = 1'b0;
        idx_out    = '0;
        cmd        = '0;

        case (state)

            // ----------------------------------------------------------
            // DEL_ST_START – Entry point.
            // Ask the memory block to search for the key (get_by_key).
            // Outputs: select=0 (key-based lookup), write=0, idx=0.
            // On the next negative clock edge the memory block will
            // evaluate key_in and provide hit / hit_idx combinationally.
            // ----------------------------------------------------------
            DEL_ST_START: begin
                delete_out = 1'b0;
                idx_out    = '0;


                cmd.done   = 1'b0;
                cmd.error  = 1'b0;

                // directly transistion to Delete / Error state as the result of the hit is 
                // set after the negative edge of the clock 
                if (idle) begin
                    next_state = DEL_ST_START; // Stay in START if not active
                end else if (hit) begin
                    next_state = ctrl_types_pkg::DEL_ST_DELETE;
                end else begin
                    next_state = ctrl_types_pkg::DEL_ST_ERROR;
                end
            end

            // ----------------------------------------------------------
            // DEL_ST_DELETE – Erase the cell.
            // Set delete_out to 1 to indicate a delete operation
            // Outputs: write=0, delete_out=1, idx=saved_idx (one-hot index of the cell to delete)
            // ----------------------------------------------------------
            DEL_ST_DELETE: begin
                delete_out  = 1'b1;
                idx_out     = idx_in; // Use the index from the hit result to target the delete
                cmd.done    = 1'b1; // Signal completion to parent FSM

                // directly transistion back to the START state to be ready for the next operation
                next_state = ctrl_types_pkg::DEL_ST_START;
            end

            // ----------------------------------------------------------
            // DEL_ST_ERROR – Key not found.
            // Signal cmd.error=1 so the parent FSM can handle the error.
            // ----------------------------------------------------------
            DEL_ST_ERROR: begin
                delete_out  = 1'b0;
                idx_out     = '0;
                cmd.error   = 1'b1;
                next_state = DEL_ST_START; // Ready for the next operation
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
        end else if (enter) begin
            state     <= DEL_ST_START;
        end else if (en) begin
            state <= next_state;
        end
    end
endmodule