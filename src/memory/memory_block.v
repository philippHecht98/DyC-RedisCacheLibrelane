/**
 * Memory Block Module
 * 
 * A collection of memory cells forming the cache storage.
 * Supports configurable number of entries.
 */

module memory_block #(
    parameter NUM_ENTRIES = 16,
    parameter KEY_WIDTH = 64,
    parameter VALUE_WIDTH = 64,
    parameter TTL_WIDTH = 32,
    parameter ADDR_WIDTH = $clog2(NUM_ENTRIES)
)(
    input wire clk,
    input wire rst_n,
    
    // Write interface
    input wire write_en,
    input wire [ADDR_WIDTH-1:0] write_addr,
    input wire [KEY_WIDTH-1:0] key_in,
    input wire [VALUE_WIDTH-1:0] value_in,
    input wire [TTL_WIDTH-1:0] ttl_in,
    
    // Read interface
    input wire [ADDR_WIDTH-1:0] read_addr,
    output wire [KEY_WIDTH-1:0] key_out,
    output wire [VALUE_WIDTH-1:0] value_out,
    output wire [TTL_WIDTH-1:0] ttl_out,
    output wire valid_out
);

    // Wire arrays for cell connections
    wire [KEY_WIDTH-1:0] cell_key_out [NUM_ENTRIES-1:0];
    wire [VALUE_WIDTH-1:0] cell_value_out [NUM_ENTRIES-1:0];
    wire [TTL_WIDTH-1:0] cell_ttl_out [NUM_ENTRIES-1:0];
    wire cell_valid [NUM_ENTRIES-1:0];
    
    // Generate memory cells
    genvar i;
    generate
        for (i = 0; i < NUM_ENTRIES; i = i + 1) begin : gen_cells
            wire cell_write_en;
            assign cell_write_en = write_en && (write_addr == i);
            
            memory_cell #(
                .KEY_WIDTH(KEY_WIDTH),
                .VALUE_WIDTH(VALUE_WIDTH),
                .TTL_WIDTH(TTL_WIDTH)
            ) cell_inst (
                .clk(clk),
                .rst_n(rst_n),
                .write_en(cell_write_en),
                .key_in(key_in),
                .value_in(value_in),
                .ttl_in(ttl_in),
                .key_out(cell_key_out[i]),
                .value_out(cell_value_out[i]),
                .ttl_out(cell_ttl_out[i]),
                .valid(cell_valid[i])
            );
        end
    endgenerate
    
    // Read multiplexer
    assign key_out = cell_key_out[read_addr];
    assign value_out = cell_value_out[read_addr];
    assign ttl_out = cell_ttl_out[read_addr];
    assign valid_out = cell_valid[read_addr];

endmodule
