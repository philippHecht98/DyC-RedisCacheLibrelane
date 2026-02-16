/**
 * Memory Cell Module
 * 
 * Each cell contains:
 * - Key register (8-bit)
 * - Value register (64-bit)
 * - TTL timer (32-bit)
 */

module memory_cell #(
    parameter KEY_WIDTH,
    parameter VALUE_WIDTH
    //parameter TTL_WIDTH
)(
    input logic clk,
    input logic rst_n,
    
    // Write interface
    input logic write_op,
    input logic [KEY_WIDTH-1:0] key_in,
    input logic [VALUE_WIDTH-1:0] value_in,
    //input logic [TTL_WIDTH-1:0] ttl_in,
    
    // Read interface
    input logic read_op,
    output logic [KEY_WIDTH-1:0] key_out,
    output logic [VALUE_WIDTH-1:0] value_out,
    output logic used_out // Indicates if the cell is currently used (valid)
    //output reg [TTL_WIDTH-1:0] ttl_out
);
    // initialize registers by using memory_dynamic_registerarray
    dynamic_register_array #(.LENGTH(KEY_WIDTH)) key_reg (
        .clk(clk),
        .rst_n(rst_n),
        .write_op(write_op),
        .data_in(key_in),
        .data_out(key_out)
    );

    dynamic_register_array #(.LENGTH(VALUE_WIDTH)) value_reg (
        .clk(clk),
        .rst_n(rst_n),
        .write_op(write_op),
        .data_in(value_in),
        .data_out(value_out)
    );

    dynamic_register_array #(.LENGTH(1)) used_reg (
        .clk(clk),
        .rst_n(rst_n),
        .write_op(write_op),
        .data_in(in_use),
        .data_out(used_out) 
    );

    //dynamic_register_array #(.LENGTH(TTL_WIDTH)) ttl_reg (
    //    .clk(clk),
    //    .rst_n(rst_n),
    //    .write_op(write_op ),
    //    .select_op(read_op ),
    //    .data_in(ttl_in),
    //    .data_out(ttl_out)
    //);

    assign in_use = (key_out != '0);

endmodule
