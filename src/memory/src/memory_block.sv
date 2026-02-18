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
    input logic clk,
    input logic rst_n,
    
    // Control signals
    input logic write_in,
    input logic select_by_index,
    input logic delete_in,

    // Data line input
    input logic [KEY_WIDTH-1:0] key_in,
    input logic [VALUE_WIDTH-1:0] value_in,
    input logic [NUM_ENTRIES-1:0] index_in, 
    //input logic [TTL_WIDTH-1:0] ttl_in,
    

    // Data line output
    output logic [VALUE_WIDTH-1:0] value_out,
    output logic [NUM_ENTRIES-1:0] index_out, // Indicates which cell(s) matched the key (for read/delete)
    output logic hit,
    output logic [NUM_ENTRIES-1:0] used_entries
    //output logic [TTL_WIDTH-1:0] ttl_out
);

    logic [KEY_WIDTH-1:0] cell_key_out [NUM_ENTRIES-1:0];
    logic [VALUE_WIDTH-1:0] cell_value_out [NUM_ENTRIES-1:0];
    
    // Per-cell reset: global reset OR targeted delete
    // When delete_in is active, the cell matching key_in gets its rst_n pulled low
    logic [NUM_ENTRIES-1:0] cell_rst_n;

    // Generate memory cells for memory block
    generate
        for (genvar i = 0; i < NUM_ENTRIES; i++) begin : gen_memory_cell
            // Reset this cell if global reset OR (delete requested AND this cell matches the key)
            assign cell_rst_n[i] = rst_n & ~(delete_in && index_in[i]);

            memory_cell #(
                .KEY_WIDTH(KEY_WIDTH),
                .VALUE_WIDTH(VALUE_WIDTH)
            ) temp (
                .clk(clk),
                .rst_n(cell_rst_n[i]), // per-cell reset (low = reset)
                // Write only if write_in is active AND this cell is selected by index_in
                .write_op(write_in && index_in[i]), 
                .key_in(key_in),
                .value_in(value_in),
                .key_out(cell_key_out[i]),
                .value_out(cell_value_out[i]),
                .used_out(used_entries[i])
            );
        end
    endgenerate
    
    
    // Compare input key against all stored keys
    always_comb begin
        index_out = '0; // Default to no matches
        value_out = '0;
        hit = '0;

        // If key_in is all zeros, and select_by_index is not active, 
        // treat this as a "no key" condition and do not report any matches
        if (key_in == '0 && select_by_index == 1'b0) begin
            hit = '0;
            value_out = '0;
            index_out = '0;

        // Else a key was provided, check for matches among used entries
        end else begin

            // check if select_by_index is active, if so only check the specified index
            if (select_by_index) begin
                index_out = index_in; // Pass through the index to output
                for (int i = 0; i < NUM_ENTRIES; i++) begin

                    // If this bit is set, return the corresponding cell's value
                    if (index_in[i] && used_entries[i]) begin 
                        index_out = 1 << i;
                        value_out = cell_value_out[i];
                        hit = '1;
                    end
                end 

            // otherwise check all entries for a key match
            end else begin 
                for (int i = 0; i < NUM_ENTRIES; i++) begin
                    if (used_entries[i] && (cell_key_out[i] == key_in)) begin
                        value_out = cell_value_out[i];
                        hit = '1;
                        index_out = 1 << i; // Set the corresponding bit in index_out
                    end
                end
            end
        end
    end

endmodule
