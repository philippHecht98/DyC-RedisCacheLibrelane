/**
 * Memory Interface Module
 * 
 * Provides an interface for interacting with the memory block.
 * Handles address generation and data routing.
 */

module memory_interface #(
    parameter NUM_ENTRIES = 16,
    parameter KEY_WIDTH = 64,
    parameter VALUE_WIDTH = 64,
    parameter TTL_WIDTH = 32,
    parameter ADDR_WIDTH = $clog2(NUM_ENTRIES)
)(
    input wire clk,
    input wire rst_n,
    
    // Command interface
    input wire cmd_valid,
    input wire cmd_write,  // 1 = write, 0 = read
    input wire [KEY_WIDTH-1:0] cmd_key,
    input wire [VALUE_WIDTH-1:0] cmd_value,
    input wire [TTL_WIDTH-1:0] cmd_ttl,
    output reg cmd_ready,
    
    // Response interface
    output reg resp_valid,
    output reg resp_hit,
    output reg [VALUE_WIDTH-1:0] resp_value,
    output reg [TTL_WIDTH-1:0] resp_ttl,
    input wire resp_ready,
    
    // Memory block interface
    output reg mem_write_en,
    output reg [ADDR_WIDTH-1:0] mem_write_addr,
    output reg [KEY_WIDTH-1:0] mem_key_in,
    output reg [VALUE_WIDTH-1:0] mem_value_in,
    output reg [TTL_WIDTH-1:0] mem_ttl_in,
    output reg [ADDR_WIDTH-1:0] mem_read_addr,
    input wire [KEY_WIDTH-1:0] mem_key_out,
    input wire [VALUE_WIDTH-1:0] mem_value_out,
    input wire [TTL_WIDTH-1:0] mem_ttl_out,
    input wire mem_valid_out
);

    // Hash function to generate address from key
    // Simple hash: XOR folding
    function [ADDR_WIDTH-1:0] hash_key;
        input [KEY_WIDTH-1:0] key;
        integer j;
        reg [ADDR_WIDTH-1:0] hash;
        begin
            hash = {ADDR_WIDTH{1'b0}};
            for (j = 0; j < KEY_WIDTH/ADDR_WIDTH; j = j + 1) begin
                hash = hash ^ key[j*ADDR_WIDTH +: ADDR_WIDTH];
            end
            hash_key = hash;
        end
    endfunction
    
    // State machine states
    localparam IDLE = 2'b00;
    localparam LOOKUP = 2'b01;
    localparam WRITE = 2'b10;
    localparam RESPOND = 2'b11;
    
    reg [1:0] state, next_state;
    reg [ADDR_WIDTH-1:0] target_addr;
    reg [KEY_WIDTH-1:0] lookup_key;
    reg key_match;
    
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
                    next_state = LOOKUP;
                end
            end
            LOOKUP: begin
                next_state = cmd_write ? WRITE : RESPOND;
            end
            WRITE: begin
                next_state = RESPOND;
            end
            RESPOND: begin
                if (resp_ready) begin
                    next_state = IDLE;
                end
            end
        endcase
    end
    
    // Output logic
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cmd_ready <= 1'b1;
            resp_valid <= 1'b0;
            resp_hit <= 1'b0;
            resp_value <= {VALUE_WIDTH{1'b0}};
            resp_ttl <= {TTL_WIDTH{1'b0}};
            mem_write_en <= 1'b0;
            mem_write_addr <= {ADDR_WIDTH{1'b0}};
            mem_key_in <= {KEY_WIDTH{1'b0}};
            mem_value_in <= {VALUE_WIDTH{1'b0}};
            mem_ttl_in <= {TTL_WIDTH{1'b0}};
            mem_read_addr <= {ADDR_WIDTH{1'b0}};
            target_addr <= {ADDR_WIDTH{1'b0}};
            lookup_key <= {KEY_WIDTH{1'b0}};
            key_match <= 1'b0;
        end else begin
            case (state)
                IDLE: begin
                    cmd_ready <= 1'b1;
                    resp_valid <= 1'b0;
                    mem_write_en <= 1'b0;
                    if (cmd_valid) begin
                        target_addr <= hash_key(cmd_key);
                        mem_read_addr <= hash_key(cmd_key);
                        lookup_key <= cmd_key;
                        cmd_ready <= 1'b0;
                    end
                end
                LOOKUP: begin
                    // Check if key matches
                    key_match <= (mem_key_out == lookup_key) && mem_valid_out;
                    if (cmd_write) begin
                        // Prepare write
                        mem_write_addr <= target_addr;
                        mem_key_in <= cmd_key;
                        mem_value_in <= cmd_value;
                        mem_ttl_in <= cmd_ttl;
                    end
                end
                WRITE: begin
                    // Perform write
                    mem_write_en <= 1'b1;
                    resp_valid <= 1'b1;
                    resp_hit <= 1'b1;  // Write always succeeds
                    resp_value <= cmd_value;
                    resp_ttl <= cmd_ttl;
                end
                RESPOND: begin
                    mem_write_en <= 1'b0;
                    if (!resp_valid) begin
                        // For read operations
                        resp_valid <= 1'b1;
                        resp_hit <= key_match;
                        resp_value <= key_match ? mem_value_out : {VALUE_WIDTH{1'b0}};
                        resp_ttl <= key_match ? mem_ttl_out : {TTL_WIDTH{1'b0}};
                    end
                    if (resp_ready) begin
                        resp_valid <= 1'b0;
                        cmd_ready <= 1'b1;
                    end
                end
            endcase
        end
    end

endmodule
