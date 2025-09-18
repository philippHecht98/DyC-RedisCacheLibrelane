module spm_chip_sg13g2 (
  input logic clk_pad,
  input logic rst_pad,
  input logic x_pad,
  input logic [31:0] a_pad,
  output logic y_pad
); 

  logic clk, rst;
  logic x;
  logic [31:0] a;
  logic y;

  spm #(.bits(32)) i_spm
  (
    .clk,
    .rst,
    .x,
    .a,
    .y
  );

endmodule
