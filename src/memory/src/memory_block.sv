/**
 * Memory Block Module
 * 
 * A collection of memory cells forming the cache storage.
 * Supports configurable number of entries.
 */

module memory_block #(
    parameter NUM_OPERATIONS = 2,
    parameter NUM_ENTRIES = 16,
    parameter KEY_WIDTH = 16,
    parameter VALUE_WIDTH = 64
)(
    input wire clk,
    input wire rst_n,
    
    // Control signals
    input wire write_in,
    input wire read_in,
    input wire delete_in,

    // Data line input
    input wire [KEY_WIDTH-1:0] key_in,
    input wire [VALUE_WIDTH-1:0] value_in,
    //input wire [TTL_WIDTH-1:0] ttl_in,
    
    // Data line output
    //output wire [KEY_WIDTH-1:0] key_out,
    output reg [VALUE_WIDTH-1:0] value_out,
    output reg hit
    //output wire [TTL_WIDTH-1:0] ttl_out
);

    wire [KEY_WIDTH-1:0] cell_key_out [NUM_ENTRIES-1:0];
    wire [VALUE_WIDTH-1:0] cell_value_out [NUM_ENTRIES-1:0];
    wire [NUM_ENTRIES-1:0] used_entries;

    wire write_op;
    wire read_op;
    wire delete_op;
    
    // Per-cell reset: global reset OR targeted delete
    // When delete_in is active, the cell matching key_in gets its rst_n pulled low
    wire [NUM_ENTRIES-1:0] cell_rst_n;

    // Generate memory cells for memory block
    generate
        for (genvar i = 0; i < NUM_ENTRIES; i++) begin : gen_memory_cell
            // Reset this cell if global reset OR (delete requested AND this cell matches the key)
            assign cell_rst_n[i] = rst_n & ~(delete_in & used_entries[i] & (cell_key_out[i] == key_in));

            memory_cell #(
                .KEY_WIDTH(KEY_WIDTH),
                .VALUE_WIDTH(VALUE_WIDTH)
            ) temp (
                .clk(clk),
                .rst_n(cell_rst_n[i]),        // per-cell reset (low = reset)
                .write_op(write_op && !used_entries[i]),
                .key_in(key_in),
                .value_in(value_in),
                .read_op(read_op && used_entries[i]),
                .key_out(cell_key_out[i]),
                .value_out(cell_value_out[i]),
                .used_out(used_entries[i])
            );
        end
    endgenerate
    
    
    // Compare input key against all stored keys
    always_comb begin
        value_out = '0;
        hit = '0;
        for (int i = 0; i < NUM_ENTRIES; i++) begin
            if (used_entries[i] && (cell_key_out[i] == key_in)) begin
                value_out = cell_value_out[i];
                hit = '1;
            end
        end
    end

endmodule
