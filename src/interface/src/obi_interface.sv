
module obi_cache_interface #(
    parameter ARCHITECTURE = 32 // Bits per register in the interface
) (
    input logic clk, 
    input logic rst_n, 

    /*   OBI interface signals   */
    // Incoming wires from master (CPU)
    input if_types_pkg::obi_req_t obi_req,

    // Outgoing wires to master (CPU)
    output if_types_pkg::obi_rsp_t obi_resp,

    /*   Controller interface signals (simplified for now - assuming data always available)   */
    // Incoming wires from controller 
    input logic                                     ready_in,
    input logic                                     op_succ_in,
    input logic [if_types_pkg::VALUE_WIDTH-1:0]     value_in, // Data read from memory (for read operations)

    // Outgoing wires to controller
    output ctrl_types_pkg::operation_e              operation_out,
    output logic [if_types_pkg::KEY_WIDTH-1:0]      key_out,  // ACTUAL_KEY_WIDTH = ARCHITECTURE - OP_BITS
    output logic [if_types_pkg::VALUE_WIDTH-1:0]    value_out // VALUE_WIDTH = 2 * ARCHITECTURE
);

    import if_types_pkg::*;
    import ctrl_types_pkg::*;


    // =========================================================================
    // Local parameters
    // =========================================================================
    localparam TOTAL_INPUT_REGISTER_LENGTH  = VALUE_WIDTH + KEY_WIDTH + OP_WIDTH;
    localparam OPERATION_WRITE_OFFSET       = TOTAL_INPUT_REGISTER_LENGTH - OP_WIDTH; // Operation code is in the highest bits
    localparam KEY_OFFSET                   = VALUE_WIDTH; // Key is in the middle bits
    localparam VALUE_OFFSET                 = 0; // Value is in the lowest bits

    // =========================================================================
    // Internal Stuff
    // =========================================================================
    
    // State machine state
    if_types_pkg::if_state_e state, next_state;
    
    // Internal grant signal (combinational logic)
    logic internal_gnt;

    // Internal signal to indicate if the current operation is a write or read (1=write, 0=read)
    logic write_or_read_operation;

    // Registers to hold the current request data
    reg [TOTAL_INPUT_REGISTER_LENGTH-1:0] current_request;

    // wires to capture the incoming request data from always_comb
    logic [TOTAL_INPUT_REGISTER_LENGTH-1:0] current_request_wires;

    // Registers to hold the response data from controller
    reg [VALUE_WIDTH-1:0]   rdata_from_controller;
    reg                     err_from_controller;
    reg                     rvalid_from_controller;
    
    // logical wires to hold the decoded operation, key, and value from the current request
    logic [OP_WIDTH-1:0]     decoded_operation;
    logic [KEY_WIDTH-1:0]    decoded_key;
    logic [VALUE_WIDTH-1:0]  decoded_value;

    assign decoded_operation    = current_request[OPERATION_WRITE_OFFSET +: OP_WIDTH];
    assign decoded_key          = current_request[KEY_OFFSET +: KEY_WIDTH];
    assign decoded_value        = current_request[VALUE_OFFSET +: VALUE_WIDTH];

    assign operation_out = ctrl_types_pkg::operation_e'(decoded_operation); // Cast to enum type for controller output
    assign key_out = decoded_key;
    assign value_out = decoded_value;
    
    logic [ARCHITECTURE-1:0] addr_from_a_chan;
    logic [ARCHITECTURE-1:0] wdata_from_a_chan;

    logic [ARCHITECTURE-1:0] rdata_to_r_chan;
    logic                    rvalid_to_r_chan;
    logic                    err_to_r_chan;

    // initalize a channel module
    a_channel #(
        .ADDR_WIDTH(ARCHITECTURE),
        .DATA_WIDTH(ARCHITECTURE)
    ) a_chan_inst (
        .clk(clk),
        .rst_n(rst_n),
        .obi_req(obi_req),
        .internal_gnt(internal_gnt),
        .addr_out(addr_from_a_chan), // Connect to controller address input
        .wdata_out(wdata_from_a_chan), // Connect to controller write data input
        .is_write_or_read_operation(write_or_read_operation)
    );

    // initalize r channel module
    r_channel #(
        .DATA_WIDTH(ARCHITECTURE)
    ) r_chan_inst (
        .clk(clk),
        .rst_n(rst_n),
        .obi_resp(obi_resp),
        .internal_gnt(internal_gnt),
        .rvalid_in(rvalid_to_r_chan), // Connect ready signal from controller to rvalid input
        .rdata_in(rdata_to_r_chan), // Connect read data from controller to rdata input
        .err_in(err_to_r_chan) // Connect error signal from controller to err input
    );

    // =========================================================================
    // State Machine
    // =========================================================================    
    always_comb begin
        // Default values for outputs and next state
        next_state = state; 

        // Default to not granting until we determine we have a valid request to process
        internal_gnt = 1'b0; 

        // Default to holding the current request unless we capture new data
        current_request_wires = current_request; 

        rdata_to_r_chan = '0;
        err_to_r_chan = 1'b0;
        rvalid_to_r_chan = 1'b0;


        case (state)
            // Wait in idle state until master initiates a complete request
            // When master writes to the operation register, transition to processing state
            // Set internal_gnt to 1'b1 to signal that we are ready to accept a new request
            IF_ST_IDLE: begin

                // check if current operation is a read operation. If so and in idle state, 
                // we can directly grant the request and transition back to idle state
                // since we can immediatly place the r channel to the response already in the rdata_from_controller
                if (write_or_read_operation == 1'b0) begin
                    next_state          = IF_ST_IDLE;
                    internal_gnt        = 1'b1; // Grant the request since we can immediately respond to read operations without needing to wait for the controller to process the request 
                    rdata_to_r_chan     = rdata_from_controller[addr_from_a_chan +: ARCHITECTURE]; // Send read data from controller to R-channel to be sent back to master
                    rvalid_to_r_chan    = rvalid_from_controller; // Send valid signal from controller to R-channel to indicate if read data is valid
                    err_to_r_chan       = err_from_controller; // Send error signal from controller to R
                end
                else begin
                    // Capture incoming request data into current_request register
                    current_request_wires[addr_from_a_chan +: ARCHITECTURE] = wdata_from_a_chan;

                    if (decoded_operation != ctrl_types_pkg::NOOP) begin
                        internal_gnt = 1'b0; 
                        next_state        = IF_ST_PROCESS;
                    end

                    // still allow master to write the full request data into
                    // the current_request register while in idle state, 
                    // yet do not transition until the operation code is written
                    else begin
                        next_state = IF_ST_IDLE;
                        internal_gnt = 1'b1;
                    end
                end
            end

            // In the processing state, wait for the controller to 
            IF_ST_PROCESS: begin
                // If controller signals that the data on the wires is ready
                if (ready_in) begin
                    next_state      = IF_ST_COMPLETE;
                end

                // Controller is still processing request, 
                // stay in this state
                else begin
                    next_state = IF_ST_PROCESS;
                end
            end
            
            IF_ST_COMPLETE: begin
                // Clear the current request register to be ready for the next request
                current_request_wires = '0;
                rdata_to_r_chan = '0;
                err_to_r_chan = 1'b0;
                rvalid_to_r_chan = 1'b0;

                if (obi_req.rready) begin
                    next_state = IF_ST_IDLE;
                    internal_gnt = 1'b1; // Deassert grant until we have a new valid request to process
                end
                // Still waiting for master to accept response
                // stay in complete state until master is ready to accept response
                else begin
                    next_state = IF_ST_COMPLETE;
                    internal_gnt = 1'b0; // Deassert grant until current transaction is completed by master
                end
            end

            default: next_state = IF_ST_IDLE;
        endcase
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IF_ST_IDLE;
        end else begin
            state <= next_state;
        end
    end

    always_ff @(negedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rdata_from_controller <= '0;
            err_from_controller <= 1'b0;
            rvalid_from_controller <= 1'b0;
        end 
        else if (ready_in) begin
            rdata_from_controller <= value_in; // Capture read data from controller when ready signal is asserted
            err_from_controller <= ~op_succ_in; // If operation was not successful, set error signal to be sent back to master
            rvalid_from_controller <= 1'b1; // Signal that the read data from controller is valid and can be sent back to master
        end 
        else if (next_state == IF_ST_PROCESS) begin
            rdata_from_controller <= '0; // Clear read data when we start processing a new request
            err_from_controller <= 1'b0; // Clear error signal when we start processing a new request
            rvalid_from_controller <= 1'b0; // Clear valid signal when we start processing a new request
        end
    end    

    always_ff @(posedge clk or negedge rst_n) begin : blockName
        if (!rst_n) begin
            current_request <= '0;
        end else begin
            current_request <= current_request_wires;
        end
    end

endmodule