
module a_channel #(
    parameter ADDRESS_WIDTH = 4, // Width of the address bus (number of address bits)
    parameter DATA_WIDTH    = 32,
    parameter ID_WIDTH      = 4  // Width of the ID field in OBI request
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
    output logic                      is_write_or_read_operation,

    // Signal to indicate that a valid operation has occurred on the A-channel (either read or write)
    output logic                      operation_happened, 
    output logic [ID_WIDTH-1:0]       aid_out, // ID output to controller
    output logic [ADDRESS_WIDTH-1:0]  addr_out, // Address output to controller
    output logic [DATA_WIDTH-1:0]     wdata_out // Write data output to controller
);
    import if_types_pkg::*;

    logic [ADDRESS_WIDTH-1:0]    offset_addr;
    // Calculate offset address by extracting lower bits
    assign offset_addr = obi_req.a.addr[ADDRESS_WIDTH-1:0];

    reg                     operation_occurred; 
    reg                     is_write_or_read_operation_reg;
    reg [ID_WIDTH-1:0]      id_reg;
    reg [ADDRESS_WIDTH-1:0] addr_reg;
    reg [DATA_WIDTH-1:0]    wdata_reg;

    // Write logic - A channel
    always_ff @(posedge clk or negedge rst_n) begin
        // reset 
        if (!rst_n) begin
            addr_reg <= '0;
            wdata_reg <= '0;
            is_write_or_read_operation_reg <= 1'b0;
            id_reg <= '0;
        end

        else if (obi_req.req        // OBI request set to valid from master
                    && obi_req.a.we // Write enable (1=write, 0=read)
                    && internal_gnt) begin
            // Extract lower bits of wdata that match ARCHITECTURE width
            addr_reg <= offset_addr; // Shift left to get actual address
            wdata_reg <= obi_req.a.wdata;
            is_write_or_read_operation_reg <= 1'b1;
            id_reg <= obi_req.a.aid;
            operation_occurred <= 1'b1; // Indicate that a valid operation has occurred on the A-channel
        end 
        else if (obi_req.req 
                    && !obi_req.a.we // Read enabled (1=write, 0=read)
                    && internal_gnt) begin
            addr_reg <= offset_addr; // Shift left to get actual address
            is_write_or_read_operation_reg <= 1'b0;
            id_reg <= obi_req.a.aid;
            operation_occurred <= 1'b1; // Indicate that a valid operation has occurred on the A-channel
        end 
        // No valid request was made, reset registers and indicate that no valid operation has occurred
        else begin 
            operation_occurred <= 1'b0; // Indicate that no valid operation has occurred on the A-channel
            addr_reg <= '0;
            wdata_reg <= '0;
            is_write_or_read_operation_reg <= 1'b0;
            id_reg <= '0;
        end
    end

    assign addr_out = addr_reg;
    assign wdata_out = wdata_reg;
    assign is_write_or_read_operation = is_write_or_read_operation_reg;
    assign aid_out = id_reg;
    assign operation_happened = operation_occurred;
    

endmodule
