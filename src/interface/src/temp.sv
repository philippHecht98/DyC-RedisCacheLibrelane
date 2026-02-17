
module obi_cache_interface #(
    parameter ARCHITECTURE = 64 // Bits per register in the interface
) (
    input logic clk, 
    input logic rst_n, 

    /*   OBI interface signals   */

    // Incoming wires from master (CPU)
    input croc_pkg::obi_request_t obi_req,
    input logic rready, // Indicates master is ready to accept response

    // Outgoing wires to master (CPU)
    output croc_pkg::obi_response_t obi_resp,
    output logic gnt, // Grant signal to master indicating interface accepted the request

    /*   Controller interface signals (simplified for now - assuming data always available)   */
    output ctrl_types_pkg::operation_e operation_out,
    output logic [ARCHITECTURE - 3 - 1:0] key_out,  // ACTUAL_KEY_WIDTH = ARCHITECTURE - OP_BITS
    output logic [2 * ARCHITECTURE - 1:0] value_out, // VALUE_WIDTH = 2 * ARCHITECTURE
    input logic ready_in,
    input logic op_succ_in
);

    import if_types_pkg::*;
    import croc_pkg::*;
    import ctrl_types_pkg::*;

    // =========================================================================
    // Parameter Calculations
    // =========================================================================
    // Calculate the number of bits needed for operation encoding
    localparam OP_BITS = 3; // operation_e uses logic [2:0] (NOOP, READ, UPSERT, DELETE)
    localparam KEY_WIDTH = ARCHITECTURE;
    localparam ACTUAL_KEY_WIDTH = ARCHITECTURE - OP_BITS; // Key width after removing operation bits
    localparam VALUE_WIDTH = 2 * ARCHITECTURE; // Value is twice the architecture width

    // =========================================================================
    // Internal Registers
    // =========================================================================
    
    // State machine state
    if_types_pkg::if_state_e state, next_state;

    // Registers to hold the incoming request from master (CPU-writable)
    ctrl_types_pkg::operation_e operation_in_from_master_reg; // Operation type extracted from address MSBs
    reg [ACTUAL_KEY_WIDTH-1:0] key_in_from_master_reg; // Key extracted from address LSBs
    reg [VALUE_WIDTH-1:0] value_in_from_master_reg; // Value from write data

    // Registers to hold results for read responses (simplified - assume always available)
    reg [VALUE_WIDTH-1:0] result_value_reg; // Result data to return for read operations
    reg op_succ_reg; // Operation success status

    // OBI protocol tracking registers
    logic req_accepted_q; // Tracks if a request was accepted in previous cycle (for rvalid timing)
    logic req_is_read_q;  // Tracks if accepted request was a read operation

    // =========================================================================
    // Address Decoding - Extract operation and key from address
    // =========================================================================
    // Address format: [MSB bits = operation (3 bits)] [LSB bits = key (ACTUAL_KEY_WIDTH bits)]
    logic [OP_BITS-1:0] addr_operation;
    logic [ACTUAL_KEY_WIDTH-1:0] addr_key;
    
    assign addr_operation = obi_req.obi_master_addr[ARCHITECTURE-1 : ARCHITECTURE-OP_BITS];
    assign addr_key = obi_req.obi_master_addr[ACTUAL_KEY_WIDTH-1 : 0];

    // =========================================================================
    // OBI A-Channel: Request Acceptance and Register Write Logic
    // =========================================================================
    // Capture incoming write requests when interface is ready (IDLE state)
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            // Reset all incoming request registers
            value_in_from_master_reg <= 'd0;
            key_in_from_master_reg <= 'd0;
            operation_in_from_master_reg <= NOOP;
        end 
        // Check if master is making a write request and we're granting it
        else if (obi_req.obi_master_request && gnt && obi_req.obi_master_write_enabled) begin
            // Capture the write data from master
            value_in_from_master_reg <= obi_req.obi_master_wdata;
            // Extract and store the key from address LSBs
            key_in_from_master_reg <= addr_key;
            // Extract and store the operation from address MSBs with proper type casting
            operation_in_from_master_reg <= ctrl_types_pkg::operation_e'(addr_operation);
        end
    end

    // =========================================================================
    // OBI Protocol Tracking - Request Handshake and Response Timing
    // =========================================================================
    // Track accepted requests for proper R-channel timing (rvalid should be 1 cycle after gnt)
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            req_accepted_q <= 1'b0;
            req_is_read_q <= 1'b0;
        end else begin
            // Request is accepted when both req and gnt are high
            req_accepted_q <= obi_req.obi_master_request && gnt;
            // Track if it was a read operation (write_enabled = 0)
            req_is_read_q <= obi_req.obi_master_request && gnt && !obi_req.obi_master_write_enabled;
        end
    end

    // =========================================================================
    // OBI R-Channel: Read Response Logic
    // =========================================================================
    // Response is valid one cycle after request acceptance (OBI protocol requirement)
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            obi_resp.obi_slave_response_data <= 'd0;
            obi_resp.obi_slave_response_valid <= 1'b0;
            obi_resp.obi_slave_response_error <= 1'b0;
        end else begin
            // Assert rvalid one cycle after accepting a request
            obi_resp.obi_slave_response_valid <= req_accepted_q;
            
            // For read operations, return the result data
            if (req_is_read_q) begin
                obi_resp.obi_slave_response_data <= result_value_reg;
            end else begin
                // For write operations, response data can be don't care (return 0)
                obi_resp.obi_slave_response_data <= 'd0;
            end
            
            // No errors for now (simplified)
            obi_resp.obi_slave_response_error <= 1'b0;
        end
    end

    // =========================================================================
    // Controller Interface Outputs
    // =========================================================================
    // Forward the registered request data to controller
    assign operation_out = operation_in_from_master_reg; // Operation type (READ, UPSERT, DELETE)
    assign key_out = key_in_from_master_reg;             // Key value
    assign value_out = value_in_from_master_reg;         // Value data

    // =========================================================================
    // FSM: Interface State Machine (Simplified - assuming data always ready)
    // =========================================================================
    // Combinational logic for next state and grant signal
    always_comb begin
        // Default values
        next_state = state;
        gnt = 1'b0;
        
        case (state)
            // IDLE: Wait for incoming request from master
            IF_ST_IDLE: begin
                // Accept request if master is requesting and controller is ready
                if (obi_req.obi_master_request && ready_in) begin
                    gnt = 1'b1;  // Grant the request (handshake with master)
                    next_state = IF_ST_WAIT; // Move to execute to process the request
                end else begin
                    gnt = 1'b0;  // Not ready to accept
                    next_state = IF_ST_IDLE; // Stay in idle
                end
            end

            // WAIT: Waiting for controller to finish (unused in simplified version)
            IF_ST_WAIT: begin
                // This state would wait for done_in signal from controller
                // For now, immediately go to complete
                next_state = IF_ST_COMPLETE;
                gnt = 1'b0;
            end

            // COMPLETE: Operation finished, results available for read
            IF_ST_COMPLETE: begin
                // Return to IDLE to accept next request
                next_state = IF_ST_IDLE;
                gnt = 1'b0;
            end

            // Default case: return to IDLE
            default: begin
                next_state = IF_ST_IDLE;
                gnt = 1'b0;
            end
        endcase
    end

    // =========================================================================
    // FSM: State Register
    // =========================================================================
    // Sequential logic for state transitions
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            state <= IF_ST_IDLE; // Reset to IDLE state
        else
            state <= next_state; // Update to next state
    end

    // =========================================================================
    // Result Data Management (Simplified - assume data always available)
    // =========================================================================
    // Store result data from controller for read responses
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            result_value_reg <= 'd0;
            op_succ_reg <= 1'b0;
        end else begin
            // For simplified version, we can store dummy data or echo back the value
            // In full implementation, this would capture actual controller results
            if (state == IF_ST_WAIT) begin
                // Simplified: echo back the written value as the result
                // In real implementation: result_value_reg <= actual_controller_result
                result_value_reg <= value_in_from_master_reg;
                op_succ_reg <= op_succ_in; // Assume success from controller input
            end
        end
    end

endmodule