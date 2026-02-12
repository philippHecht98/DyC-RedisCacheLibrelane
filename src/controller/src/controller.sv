typedef enum logic [1:0]{
    NOOP = 2'b00,
    READ = 2'b01,
    WRITE = 2'b10
} operation_e;
module controller (
    input logic clk,
    input logic rst_n,
    input logic [15:0] used,
    input operation_e operation_in,

    output logic [15:0] idx_out,
    output logic write_out,
    output logic select_out,
    output logic ready_out
);
    localparam NUM_ENTRIES = 16;
    enum {IDLE, GET, PUT} state, next_state;

    always_comb begin : control_logic

        next_state = state;
        idx_out = '0;
        select_out = '0;
        write_out = '0;
        ready_out = '0;

         case (state)
            IDLE: begin 
                case (operation_in)
                    READ: begin
                        next_state = GET;
                    end
                    WRITE: begin
                        next_state = PUT;
                    end
                    default: begin
                        next_state = IDLE;
                    end
                endcase
            end
            GET: begin
                next_state = IDLE;
            end
            PUT: begin
                for (int j = 0; j < NUM_ENTRIES; j++) begin
                    if (!used[j] && (idx_out == 0)) begin
                        idx_out[j] = 1'b1;
                    end
                end
                write_out = 1'b1;
                next_state = IDLE;
            end
        endcase
    end


    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
        end else begin
            state <= next_state;
        end
    end
endmodule