
module obi_cache_interface #(
    parameter ARCHITECTURE = 64 // Bits per register in the interface
) (
    input logic clk, 
    input logic rst_n, 

    /*   OBI interface signals   */

    // Incoming wires from master
    input croc_pkg::obi_request_t obi_req,
    input logic rready, // Indicates master is ready to accept response

    // Outgoing wires to master
    output croc_pkg::obi_response_t obi_resp,
    output logic gnt // Grant signal to master indicating interface is ready to accept request



    /*   Controller interface signals   */
    
    
)

    import if_types_pkg::*;
    import croc_pkg::*;

    localparam KEY_WIDTH = ARCHITECTURE;
    localparam VALUE_WIDTH = 2 * ARCHITECTURE;

    // State machine state
    if_types_pkg::if_state_e state, next_state;

    logic [KEY_WIDTH-1:0] key_reg; // Register to hold the key for the cache operation
    logic [VALUE_WIDTH-1:0] value_reg; // Register to hold the value

    // Write logic
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            value_reg <= 'd0;
        else if (obi_req.obi_master_write_enabled) begin
            key_reg <= obi_req.obi_master_addr; // Assuming address encodes the key for simplicity
            value_reg <= obi_req.obi_master_wdata;
        end
    end

    // Read logic
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            obi_resp.obi_slave_response_data <= 'd0;
        else if (!obi_req.obi_master_write_enabled) begin
            // For simplicity, we just return the value_reg for any read request
            obi_resp.obi_slave_response_data <= value_reg;
        end
    end

    // STATE MACHINE
    // Cominbational logic for the next state
    always_comb begin
        next_state = state;
        gnt = 1'b0; // Default to not granting
        case (state)
            /*
                In the idle state, we wait for a valid request from the master
                When obi_master_valid is set to 1 the cpu marks the current
                data in the interface as valid and ready to be processed by the controller
            */
            IF_ST_IDLE: begin
                if (obi_req.obi_master_valid) begin
                    next_state = IF_ST_EXECUTE;
                    gnt = 1'b1;
                end
                // Master is not finished yet with setting the current request
                else begin
                    next_state = IF_ST_IDLE;
                    gnt = 1'b0;
                end
            end


            /*
                In the execute state, the request gets forwarded to the controller
                and the interface waits for the master to be ready to accept the response (rready)
            */
            IF_ST_EXECUTE: begin
                if (rready) begin
                    next_state = IF_ST_IDLE;
                    gnt = 1'b0;
                end else begin
                    gnt = 1'b1;
                end
            end

            default: begin
                next_state = IF_ST_IDLE;
                gnt = 1'b0;
            end
        endcase
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            state <= IF_ST_IDLE;
        else
            state <= next_state;
    end

endmodule