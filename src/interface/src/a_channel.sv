
module a_channel #(
    parameter ADDR_WIDTH = 32,
    parameter DATA_WIDTH = 64
)
(
    input logic clk,
    input logic rst_n,
    
    // OBI interface signals
    input  if_types_pkg::obi_req_t obi_req, // OBI request from master
    
    // Internal grant signal to control when the interface can accept new requests
    // over the A-channel
    input logic internal_gnt,

     // Signal to indicate if the current operation is a write or read (1=write, 0=read)
    output logic                  is_write_or_read_operation,
    output logic [ADDR_WIDTH-1:0] addr_out, // Address output to controller
    output logic [DATA_WIDTH-1:0] wdata_out // Write data output to controller
);
    import if_types_pkg::*;

    reg                     is_write_or_read_operation_reg;
    reg [ADDR_WIDTH-1:0]    addr_reg;
    reg [DATA_WIDTH-1:0]    wdata_reg;

    // Write logic - A channel
    always_ff @(posedge clk or negedge rst_n) begin
        // reset 
        if (!rst_n) begin
            addr_reg <= '0;
            wdata_reg <= '0;
            is_write_or_read_operation_reg <= 1'b0;
        end

        else if (obi_req.req        // OBI request set to valid from master
                    && obi_req.a.we // Write enable (1=write, 0=read)
                    && internal_gnt) begin
            // Extract lower bits of wdata that match ARCHITECTURE width
            addr_reg <= obi_req.a.addr;
            wdata_reg <= obi_req.a.wdata;
            is_write_or_read_operation_reg <= 1'b1;
        end 
        else if (obi_req.req 
                    && !obi_req.a.we // Read enabled (1=write, 0=read)
                    && internal_gnt) begin
            addr_reg <= obi_req.a.addr;
            is_write_or_read_operation_reg <= 1'b0;
        end 
    end

    assign addr_out = addr_reg;
    assign wdata_out = wdata_reg;
    assign is_write_or_read_operation = is_write_or_read_operation_reg;
    

endmodule
