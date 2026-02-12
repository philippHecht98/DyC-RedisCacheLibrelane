module get_fsm import ctrl_types_pkg::* (
    input logic clk,
    input logic rst_n,

    input logic en,
    input logic enter
);
    get_state_e state, next_state;

    always_comb begin : control_logic
        next_state = state;

        case (state)
            // Define state transitions based on the get operation's substates and command status
            // This is a placeholder and should be replaced with actual logic based on the get operation's requirements
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