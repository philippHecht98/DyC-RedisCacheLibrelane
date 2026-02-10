/**
 * Memory Cell Module
 * 
 * Each cell contains:
 * - Key register (64-bit)
 * - Value register (64-bit)
 * - TTL timer (32-bit)
 * - Valid flag
 */

module memory_cell #(
    parameter KEY_WIDTH = 64,
    parameter VALUE_WIDTH = 64,
    parameter TTL_WIDTH = 32
)(
    input wire clk,
    input wire rst_n,
    
    // Write interface
    input wire write_en,
    input wire [KEY_WIDTH-1:0] key_in,
    input wire [VALUE_WIDTH-1:0] value_in,
    input wire [TTL_WIDTH-1:0] ttl_in,
    
    // Read interface
    output reg [KEY_WIDTH-1:0] key_out,
    output reg [VALUE_WIDTH-1:0] value_out,
    output reg [TTL_WIDTH-1:0] ttl_out,
    output reg valid
);

    // Internal registers
    reg [KEY_WIDTH-1:0] key_reg;
    reg [VALUE_WIDTH-1:0] value_reg;
    reg [TTL_WIDTH-1:0] ttl_counter;
    reg valid_reg;
    
    // Timer decrement logic
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            key_reg <= {KEY_WIDTH{1'b0}};
            value_reg <= {VALUE_WIDTH{1'b0}};
            ttl_counter <= {TTL_WIDTH{1'b0}};
            valid_reg <= 1'b0;
        end else begin
            if (write_en) begin
                // Write new data
                key_reg <= key_in;
                value_reg <= value_in;
                ttl_counter <= ttl_in;
                valid_reg <= 1'b1;
            end else if (valid_reg && ttl_counter > 0) begin
                // Decrement TTL
                ttl_counter <= ttl_counter - 1'b1;
                if (ttl_counter == 1) begin
                    // Expire the entry
                    valid_reg <= 1'b0;
                end
            end else if (valid_reg && ttl_counter == 0) begin
                // Entry expired
                valid_reg <= 1'b0;
            end
        end
    end
    
    // Output assignments
    always @(*) begin
        key_out = key_reg;
        value_out = value_reg;
        ttl_out = ttl_counter;
        valid = valid_reg;
    end

endmodule
