module upsert_fsm #(
    parameter NUM_ENTRIES = 16
)(
    input logic clk,
    input logic rst_n,
    
    input logic en,
    input logic enter,
    input logic hit,
    input logic [NUM_ENTRIES-1:0] used,
    input logic [NUM_ENTRIES-1:0] idx_in,
    
    output logic select_out,
    output logic write_out,
    output logic [NUM_ENTRIES-1:0] idx_out,

    output ctrl_types_pkg::sub_cmd_t cmd
);
    import ctrl_types_pkg::*;

    put_substate_e state, next_state;

    always_comb begin : control_logic
        next_state = state;
        
        select_out = 1'b0;
        write_out = 1'b0;
        idx_out = '0;
        cmd.done = 1'b0;
        cmd.error = 1'b0;


        case (state)
            
            UPSERT_ST_START: begin
                // if hit => update the value
                // if !hit && !(&used) => insert value
                // else => error

                if (hit) begin
                    // key exists
                    select_out = 1'b1;
                    write_out = 1'b1;
                    idx_out = idx_in;
                    cmd.done = 1'b1;
                    cmd.error = 1'b0;

                end else if (!hit && !(&used)) begin
                    // key doesnt exist but free space
                    // find correct free idx
                    for (int j = 0; j < NUM_ENTRIES; j++) begin
                        if (!used[j] && (idx_out == 0)) begin
                            idx_out[j] = 1'b1;
                        end
                    end
                    select_out = 1'b0;
                    write_out = 1'b1;
                    cmd.done = 1'b1;
                    cmd.error = 1'b0;

                end else begin
                    // key doesnt exist and no free space
                    select_out = 1'b0;
                    write_out = 1'b0;
                    cmd.done = 1'b0;
                    cmd.error = 1'b1;
                end
            end
            default: begin
                next_state = state; // Stay in the current state by default
            end
        endcase
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= UPSERT_ST_START;
        end else if (enter) begin
            state <= UPSERT_ST_START;
        end else if (en) begin
            state <= next_state;
        end
    end

endmodule