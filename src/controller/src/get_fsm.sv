module get_fsm (
    // management inputs
    input logic clk,
    input logic rst_n,

    input logic en,
    input logic enter,

    // logic inputs
    input logic hit,

    // management outputs
    output ctrl_types_pkg::sub_cmd_t cmd,

    // logic outputs
    output logic rdy_out,
    output logic op_succ
);
    import ctrl_types_pkg::*;

    get_substate_e state, next_state;

    always_comb begin : control_logic
        next_state = state;
        cmd = '0;
        rdy_out = '0;
        op_succ = '0;

        case (state)
            GET_ST_START: begin
                rdy_out = hit;
                op_succ = 1'b1;

                cmd.done = 1'b1;
            end
            default: begin
                next_state = state; // Stay in the current state by default
            end
        endcase
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= GET_ST_START;
        end else if (enter) begin
            state <= GET_ST_START;
        end else if (en) begin
            state <= next_state;
        end
    end

endmodule