/**
 * Memory Block Module
 * 
 * A collection of memory cells forming the cache storage.
 * Supports configurable number of entries.
 */

module memory_block #(
    parameter NUM_ENTRIES = 16,
    parameter KEY_WIDTH = 16,
    parameter VALUE_WIDTH = 64
)(
    // basic inputs
    input logic clk,
    input logic rst_n,
    
    // inputs from controller for interacting with memory block
    input logic [NUM_ENTRIES-1:0] index,
    input logic write_op,
    input logic select_op,

    // Data line input
    input logic [KEY_WIDTH-1:0] key_in,
    input logic [VALUE_WIDTH-1:0] value_in,
    //input logic [TTL_WIDTH-1:0] ttl_in,
    
    // Data line output
    output logic [KEY_WIDTH-1:0] key_out,
    output logic [VALUE_WIDTH-1:0] value_out,
    output logic [NUM_ENTRIES-1:0] used_entries

    //output logic [TTL_WIDTH-1:0] ttl_out
);
    
    // internal wires from idv. memory cell to memory block
    // use them for returning the value by the comparator
    logic [KEY_WIDTH-1:0] cell_key_out [NUM_ENTRIES-1:0];
    logic [VALUE_WIDTH-1:0] cell_value_out [NUM_ENTRIES-1:0];
    logic [NUM_ENTRIES-1:0] cell_used_out;

    // Generate memory cells for memory block
    generate
        for (genvar i = 0; i < NUM_ENTRIES; i++) begin : gen_memory_cell
            memory_cell #(
                .KEY_WIDTH(KEY_WIDTH),
                .VALUE_WIDTH(VALUE_WIDTH)
            ) temp (
                .clk(clk),
                .rst_n(rst_n),
                .write_op(write_op && index[i] == 1'b1), // Write to first free cell only
                .key_in(key_in),
                .value_in(value_in),
                //.ttl_in(ttl_in),
                .read_op(select_op && index[i] == 1'b1), // Read from selected cell
                .key_out(cell_key_out[i]),
                .value_out(cell_value_out[i]),
                .used_out(cell_used_out[i]) // Track which cells are used
                //.ttl_out(cell_ttl_out[i])
            );
        end
    endgenerate
    
    
    // return value of selected cell
    // for this either return the value of the selected cell
    // or search by the key and return the value of the first cell that matches the key
    always_comb begin
        value_out = '0;
        key_out = '0;
        if (select_op) begin
            key_out = cell_key_out[index];
            value_out = cell_value_out[index]; 
        end
        else begin
            for (int i = 0; i < NUM_ENTRIES; i++) begin
                if ((cell_key_out[i] == key_in)) begin
                    key_out = cell_key_out[i];
                    value_out = cell_value_out[i];
                end
            end
        end
    end

    assign used_entries = cell_used_out;
    
endmodule
