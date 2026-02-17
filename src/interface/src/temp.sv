
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
    output logic gnt, // Grant signal to master indicating interface is ready to accept request

    /*   Controller interface signals   */
    output ctrl_types_pkg::operation_e operation_out,
    output logic [ACTUAL_KEY_WIDTH-1:0] key_out,
    output logic [VALUE_WIDTH-1:0] value_out,
    input logic ready_in,
    input logic op_succ_in
);

    import if_types_pkg::*;
    import croc_pkg::*;
    import ctrl_types_pkg::*;

    // Calculate the number of bits needed for operation encoding
    localparam OP_BITS = 3; // operation_e uses logic [2:0]
    localparam KEY_WIDTH = ARCHITECTURE;
    localparam ACTUAL_KEY_WIDTH = ARCHITECTURE - OP_BITS;
    localparam VALUE_WIDTH = 2 * ARCHITECTURE;

    // State machine state
    if_types_pkg::if_state_e state, next_state;

    // Store controller output in registers to hold until master is ready
    reg [VALUE_WIDTH-1:0] result_value_in_from_ctrl_reg; // Register to hold the result from the memory block
    reg op_succ_reg; // Register to hold the operation success status

    // Register to hold the operation type extracted from the address
    ctrl_types_pkg::operation_e operation_in_from_master_reg; 
    reg [KEY_WIDTH-1:0] key_in_from_master_reg; // Register to hold the incomming key
    reg [VALUE_WIDTH-1:0] value_in_from_master_reg; // Register to hold the incomming value

    // Extract operation from MSBs and key from remaining LSBs of address
    logic [OP_BITS-1:0] addr_operation = obi_req.obi_master_addr[ARCHITECTURE-1 : ARCHITECTURE-OP_BITS];
    logic [ACTUAL_KEY_WIDTH-1:0] addr_key = obi_req.obi_master_addr[ACTUAL_KEY_WIDTH-1 : 0];

    // Write logic
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            value_in_from_master_reg <= 'd0;
            key_in_from_master_reg <= 'd0;
            operation_in_from_master_reg <= NOOP;
        end 
        // check for write is enabled and master is requesting to write
        else if (obi_req.obi_master_request && obi_req.obi_master_write_enabled) begin
            
            // capture the incoming request data when the current state is idle 
            if (state == IF_ST_IDLE) begin
                value_in_from_master_reg <= obi_req.obi_master_wdata;
                key_in_from_master_reg <= addr_key;
                operation_in_from_master_reg <= addr_operation;
            end 
        end
    end

    // Read logic
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            obi_resp.obi_slave_response_data <= 'd0;

        // check for read request from master
        else if (obi_req.obi_master_request && !obi_req.obi_master_write_enabled) begin
            
            // capture the response data from the controller and return it to the master
            if (state == IF_ST_COMPLETE) begin
                obi_resp.obi_slave_response_data <= result_value_in_from_ctrl_reg;
                obi_resp.obi_slave_response_valid <= 1'b1;
            end else begin
                obi_resp.obi_slave_response_data <= 'd0; // Clear response data when not in complete state
            end
        end
    end

    /* Controller interaction */
    // Assign operation output from the extracted and registered operation
    assign operation_out = operation_in_from_master_reg;
    assign key_out = key_in_from_master_reg;
    assign value_out = value_in_from_master_reg;

    // STATE MACHINE
    // Cominbational logic for the next state
    always_comb begin
        next_state = state;
        gnt = 1'b0; // Default to not granting
        case (state)
            /*
                In the idle state, we wait for a valid request from the master
                When obi_master_request is set to 1 the cpu marks the current
                data in the interface as valid and ready to be processed by the controller
            */
            IF_ST_IDLE: begin
                if (obi_req.obi_master_request && ready_in) begin

                    next_state = IF_ST_WAIT;
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

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            result_value_in_from_ctrl_reg <= 'd0;
            op_succ_reg <= 1'b0;
        end else begin
            if (state == IF_ST_COMPLETE) begin
                result_value_in_from_ctrl_reg <= obi_resp.obi_slave_response_data;
                op_succ_reg <= op_succ_in;
            end
            else begin
                result_value_in_from_ctrl_reg <= '0; // Hold the value until the next operation
                op_succ_reg <= 1'b0; // Hold the status until the next operation
            end
        end
    end

endmodule