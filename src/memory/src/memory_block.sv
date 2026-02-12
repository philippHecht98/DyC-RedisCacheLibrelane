/**
 * Memory Block Module
 * 
 * A collection of memory cells forming the cache storage.
 * Supports configurable number of entries.
 */

typedef enum operations logic [1:0] {
    GET = 2'b01,
    PUT = 2'b10
} operations;

module memory_block #(
    parameter NUM_ENTRIES = 16,
    parameter KEY_WIDTH = 16,
    parameter VALUE_WIDTH = 64
)(
    input logic clk,
    input logic rst_n,
    
    // Control signals
    input operation operation_input,

    // Data line input
    input logic [KEY_WIDTH-1:0] key_in,
    input logic [VALUE_WIDTH-1:0] value_in,
    //input logic [TTL_WIDTH-1:0] ttl_in,
    
    // Data line output
    //output logic [KEY_WIDTH-1:0] key_out,
    output reg [VALUE_WIDTH-1:0] value_out,
    output reg hit
    //output logic [TTL_WIDTH-1:0] ttl_out
);

    logic [KEY_WIDTH-1:0] cell_key_out [NUM_ENTRIES-1:0];
    logic [VALUE_WIDTH-1:0] cell_value_out [NUM_ENTRIES-1:0];
    logic [NUM_ENTRIES-1:0] used_entries;
    logic [NUM_ENTRIES-1:0] cell_write_en;
    logic write_op;
    logic read_op;


    // Decode operation input
    always_comb begin
        write_op = '0;
        read_op = '0;
        case (operation_input)
            GET: read_op = 1'b1;
            PUT: write_op = 1'b1;
            default: begin
                write_op = '0;
                read_op = '0;
            end
        endcase
    end

    // Priority encoder: enable write only for the first unused cell
    always_comb begin
        cell_write_en = '0;
        if (write_op) begin
            for (int j = 0; j < NUM_ENTRIES; j++) begin
                if (!used_entries[j] && (cell_write_en == '0)) begin
                    cell_write_en[j] = 1'b1;
                end
            end
        end
    end

    
    // Generate memory cells for memory block
    generate
        for (genvar i = 0; i < NUM_ENTRIES; i++) begin : gen_memory_cell
            memory_cell #(
                .KEY_WIDTH(KEY_WIDTH),
                .VALUE_WIDTH(VALUE_WIDTH)
            ) temp (
                .clk(clk),
                .rst_n(rst_n),
                .write_op(cell_write_en[i]), // Write to first free cell only
                .key_in(key_in),
                .value_in(value_in),
                //.ttl_in(ttl_in),
                .read_op(read_op && used_entries[i]), // Read from selected cell
                .key_out(cell_key_out[i]),
                .value_out(cell_value_out[i]),
                .used_out(used_entries[i]) // Track which cells are used
                //.ttl_out(cell_ttl_out[i])
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
