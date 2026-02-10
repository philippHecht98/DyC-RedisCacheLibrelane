/**
 * FSM Controller Module
 * 
 * Finite State Machine controller for processing Redis-like commands.
 * Handles key-value-TTL line passing and command execution.
 */

module fsm_controller #(
    parameter KEY_WIDTH = 64,
    parameter VALUE_WIDTH = 64,
    parameter TTL_WIDTH = 32,
    parameter CMD_WIDTH = 8
)(
    input wire clk,
    input wire rst_n,
    
    // Input command interface
    input wire cmd_valid,
    input wire [CMD_WIDTH-1:0] cmd_opcode,
    input wire [KEY_WIDTH-1:0] cmd_key,
    input wire [VALUE_WIDTH-1:0] cmd_value,
    input wire [TTL_WIDTH-1:0] cmd_ttl,
    output reg cmd_ready,
    
    // Memory interface command output
    output reg mem_cmd_valid,
    output reg mem_cmd_write,
    output reg [KEY_WIDTH-1:0] mem_cmd_key,
    output reg [VALUE_WIDTH-1:0] mem_cmd_value,
    output reg [TTL_WIDTH-1:0] mem_cmd_ttl,
    input wire mem_cmd_ready,
    
    // Memory interface response input
    input wire mem_resp_valid,
    input wire mem_resp_hit,
    input wire [VALUE_WIDTH-1:0] mem_resp_value,
    input wire [TTL_WIDTH-1:0] mem_resp_ttl,
    output reg mem_resp_ready,
    
    // Output response interface
    output reg resp_valid,
    output reg resp_success,
    output reg [VALUE_WIDTH-1:0] resp_value,
    output reg [TTL_WIDTH-1:0] resp_ttl,
    input wire resp_ready
);

    // Command opcodes
    localparam CMD_SET = 8'h01;  // Set key-value with TTL
    localparam CMD_GET = 8'h02;  // Get value by key
    localparam CMD_DEL = 8'h03;  // Delete key
    localparam CMD_EXPIRE = 8'h04;  // Update TTL for key
    
    // FSM states
    localparam IDLE = 3'b000;
    localparam DECODE = 3'b001;
    localparam EXECUTE = 3'b010;
    localparam WAIT_MEM = 3'b011;
    localparam RESPOND = 3'b100;
    
    reg [2:0] state, next_state;
    reg [CMD_WIDTH-1:0] current_opcode;
    reg [KEY_WIDTH-1:0] current_key;
    reg [VALUE_WIDTH-1:0] current_value;
    reg [TTL_WIDTH-1:0] current_ttl;
    
    // State register
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
        end else begin
            state <= next_state;
        end
    end
    
    // Next state logic
    always @(*) begin
        next_state = state;
        case (state)
            IDLE: begin
                if (cmd_valid) begin
                    next_state = DECODE;
                end
            end
            DECODE: begin
                next_state = EXECUTE;
            end
            EXECUTE: begin
                if (mem_cmd_ready) begin
                    next_state = WAIT_MEM;
                end
            end
            WAIT_MEM: begin
                if (mem_resp_valid) begin
                    next_state = RESPOND;
                end
            end
            RESPOND: begin
                if (resp_ready) begin
                    next_state = IDLE;
                end
            end
            default: next_state = IDLE;
        endcase
    end
    
    // Output and control logic
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cmd_ready <= 1'b1;
            mem_cmd_valid <= 1'b0;
            mem_cmd_write <= 1'b0;
            mem_cmd_key <= {KEY_WIDTH{1'b0}};
            mem_cmd_value <= {VALUE_WIDTH{1'b0}};
            mem_cmd_ttl <= {TTL_WIDTH{1'b0}};
            mem_resp_ready <= 1'b0;
            resp_valid <= 1'b0;
            resp_success <= 1'b0;
            resp_value <= {VALUE_WIDTH{1'b0}};
            resp_ttl <= {TTL_WIDTH{1'b0}};
            current_opcode <= {CMD_WIDTH{1'b0}};
            current_key <= {KEY_WIDTH{1'b0}};
            current_value <= {VALUE_WIDTH{1'b0}};
            current_ttl <= {TTL_WIDTH{1'b0}};
        end else begin
            case (state)
                IDLE: begin
                    cmd_ready <= 1'b1;
                    mem_cmd_valid <= 1'b0;
                    mem_resp_ready <= 1'b0;
                    resp_valid <= 1'b0;
                    if (cmd_valid) begin
                        // Latch command inputs
                        current_opcode <= cmd_opcode;
                        current_key <= cmd_key;
                        current_value <= cmd_value;
                        current_ttl <= cmd_ttl;
                        cmd_ready <= 1'b0;
                    end
                end
                
                DECODE: begin
                    // Decode command - prepare memory operation
                    case (current_opcode)
                        CMD_SET: begin
                            mem_cmd_write <= 1'b1;
                            mem_cmd_key <= current_key;
                            mem_cmd_value <= current_value;
                            mem_cmd_ttl <= current_ttl;
                        end
                        CMD_GET: begin
                            mem_cmd_write <= 1'b0;
                            mem_cmd_key <= current_key;
                            mem_cmd_value <= {VALUE_WIDTH{1'b0}};
                            mem_cmd_ttl <= {TTL_WIDTH{1'b0}};
                        end
                        CMD_DEL: begin
                            mem_cmd_write <= 1'b1;
                            mem_cmd_key <= current_key;
                            mem_cmd_value <= {VALUE_WIDTH{1'b0}};
                            mem_cmd_ttl <= {TTL_WIDTH{1'b0}};  // TTL=0 means delete
                        end
                        CMD_EXPIRE: begin
                            mem_cmd_write <= 1'b1;
                            mem_cmd_key <= current_key;
                            mem_cmd_value <= {VALUE_WIDTH{1'b0}};  // Keep existing value
                            mem_cmd_ttl <= current_ttl;
                        end
                        default: begin
                            mem_cmd_write <= 1'b0;
                            mem_cmd_key <= {KEY_WIDTH{1'b0}};
                            mem_cmd_value <= {VALUE_WIDTH{1'b0}};
                            mem_cmd_ttl <= {TTL_WIDTH{1'b0}};
                        end
                    endcase
                end
                
                EXECUTE: begin
                    // Issue command to memory interface
                    mem_cmd_valid <= 1'b1;
                    if (mem_cmd_ready) begin
                        mem_cmd_valid <= 1'b0;
                        mem_resp_ready <= 1'b1;
                    end
                end
                
                WAIT_MEM: begin
                    if (mem_resp_valid) begin
                        // Capture response
                        resp_success <= mem_resp_hit;
                        resp_value <= mem_resp_value;
                        resp_ttl <= mem_resp_ttl;
                        mem_resp_ready <= 1'b0;
                    end
                end
                
                RESPOND: begin
                    // Send response to user
                    resp_valid <= 1'b1;
                    if (resp_ready) begin
                        resp_valid <= 1'b0;
                        cmd_ready <= 1'b1;
                    end
                end
            endcase
        end
    end

endmodule
