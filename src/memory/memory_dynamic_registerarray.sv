
module dynamic_register_array #(
    parameter LENGTH
)(
    input wire clk,
    input wire rst,
    input wire write_op,
    input wire select_op,
    input wire [LENGTH-1:0] data_in,
    output wire [LENGTH-1:0] data_out
);

    reg [LENGTH-1:0] registers;

    always_ff @(posedge clk) begin
        if (rst) begin
            registers <=  '0;
        end else if (write_op) begin
            registers <= data_in;
        end 
    end

    assign data_out = select_op ? registers : 'z;

endmodule