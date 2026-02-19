
module r_channel #(
    parameter DATA_WIDTH = 64,
    parameter ID_WIDTH   = 4  // Width of the ID field in OBI request
)
(
    input logic clk,
    input logic rst_n,
    
    // OBI interface signals
    output if_types_pkg::obi_rsp_t obi_resp, // OBI response to master
    
    // Valid signal from main module indicating that the read data from the 
    //controller is valid and can be sent back to the master
    input logic                     rvalid_in,
    input logic [DATA_WIDTH-1:0]    rdata_in, // Read data from controller to be sent back to master
    input logic                     err_in, // Error signal from controller to be sent back to master
    input logic [ID_WIDTH-1:0]      rid_in // ID signal from controller to be sent back to master
);
    import if_types_pkg::*;

    reg [DATA_WIDTH-1:0] rdata_reg;
    reg                  rvalid_reg;
    reg                  err_reg;
    reg [ID_WIDTH-1:0]  id_reg;

     // Output OBI response signals

    // Read logic - R channel
    always_ff @(posedge clk or negedge rst_n) begin
        // reset 
        if (!rst_n) begin
            rdata_reg <= '0;
            rvalid_reg <= 1'b0;
            err_reg <= 1'b0;
            id_reg <= '0;
        end

        // Read data from controller if valid
        else if (rvalid_in) begin 
            // Extract lower bits of wdata that match ARCHITECTURE width
            rdata_reg <= rdata_in;
            rvalid_reg <= rvalid_in;
            err_reg <= err_in;
            id_reg <= rid_in;
        end
    end

    assign obi_resp.r.rdata    = rdata_reg; // Data captured from controller
    assign obi_resp.rvalid     = rvalid_reg; // Valid signal from controller
    assign obi_resp.r.err      = err_reg; // Error signal from controller
    assign obi_resp.r.rid       = id_reg; // ID signal from controller

endmodule
