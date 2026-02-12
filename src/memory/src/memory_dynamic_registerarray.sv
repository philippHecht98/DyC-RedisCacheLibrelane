
module dynamic_register_array #(
    parameter LENGTH
)(
    input logic clk,
    input logic rst_n,
    input logic write_op,
    input logic select_op,
    input logic [LENGTH-1:0] data_in,
    output logic [LENGTH-1:0] data_out
);

    reg [LENGTH-1:0] registers;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            registers <=  '0;
        end else if (write_op) begin
            registers <= data_in;
        end 
    end

    assign data_out = registers;

endmodule