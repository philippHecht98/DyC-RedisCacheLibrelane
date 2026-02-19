
module obi_cache_interface #(
    parameter ARCHITECTURE = 32, // Bits per register in the interface
    parameter ID_WIDTH = 3 // Width of the ID field in OBI request
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
    localparam ADDRESS_WIDTH                = $clog2(TOTAL_INPUT_REGISTER_LENGTH >> 3); // Assuming 8-byte alignment


    // =========================================================================
    // Internal Stuff
    // =========================================================================
    
    // State machine state
    if_types_pkg::if_state_e state, next_state;
    
    // Internal grant signal (combinational logic)
    logic internal_gnt;

    // Internal signal to indicate if the current operation is a write or read (1=write, 0=read)
    logic write_or_read_operation;

    // reg to hold the current request id
    reg [ID_WIDTH-1:0]      current_request_id;
    logic [ID_WIDTH-1:0]    current_request_id_wires;

    // Registers to hold the current request data
    reg [TOTAL_INPUT_REGISTER_LENGTH-1:0] current_request;
    logic [TOTAL_INPUT_REGISTER_LENGTH-1:0] current_request_wires;

    // Registers to hold the response data from controller
    reg [VALUE_WIDTH-1:0]   rdata_from_controller;
    reg                     err_from_controller;
    reg                     rvalid_from_controller;
    
    // logical wires to hold the decoded operation, key, and value from the current request
    logic [OP_WIDTH-1:0]     decoded_operation;
    logic [KEY_WIDTH-1:0]    decoded_key;
    logic [VALUE_WIDTH-1:0]  decoded_value;

    assign decoded_operation    = current_request_wires[OPERATION_WRITE_OFFSET +: OP_WIDTH];
    assign decoded_key          = current_request_wires[KEY_OFFSET +: KEY_WIDTH];
    assign decoded_value        = current_request_wires[VALUE_OFFSET +: VALUE_WIDTH];

    assign operation_out = ctrl_types_pkg::operation_e'(decoded_operation); // Cast to enum type for controller output
    assign key_out = decoded_key;
    assign value_out = decoded_value;
    
    // Signal to indicate that a valid operation has occurred on the A-channel (either read or write)
    logic                     operation_happened; 
    logic [ID_WIDTH-1:0]      rid_from_a_chan;
    logic [ADDRESS_WIDTH-1:0] addr_from_a_chan;
    logic [ARCHITECTURE-1:0]  wdata_from_a_chan;

    // Bit position index (byte address * 8 to convert to bit offset)
    logic [$clog2(TOTAL_INPUT_REGISTER_LENGTH)-1:0] bit_offset;
    assign bit_offset = addr_from_a_chan << 3; // Multiply by 8 (shift left by 3)

    logic [ID_WIDTH-1:0]     rid_to_r_chan;
    logic [ARCHITECTURE-1:0] rdata_to_r_chan;
    logic                    rvalid_to_r_chan;
    logic                    err_to_r_chan;

    // initalize a channel module
    a_channel #(
        .ADDRESS_WIDTH(ADDRESS_WIDTH),
        .DATA_WIDTH(ARCHITECTURE),
        .ID_WIDTH(ID_WIDTH)
    ) a_chan_inst (
        .clk(clk),
        .rst_n(rst_n),
        .obi_req(obi_req),
        .internal_gnt(internal_gnt),
        .addr_out(addr_from_a_chan), // Connect to controller address input
        .wdata_out(wdata_from_a_chan), // Connect to controller write data input
        .is_write_or_read_operation(write_or_read_operation),
        .aid_out(rid_from_a_chan),
        .operation_happened(operation_happened)
    );

    // initalize r channel module
    r_channel #(
        .DATA_WIDTH(ARCHITECTURE),
        .ID_WIDTH(ID_WIDTH)
    ) r_chan_inst (
        .clk(clk),
        .rst_n(rst_n),
        .obi_resp(obi_resp),
        .rvalid_in(rvalid_to_r_chan), // Connect ready signal from controller to rvalid input
        .rdata_in(rdata_to_r_chan), // Connect read data from controller to rdata input
        .rid_in(current_request_id), // Connect current request ID to rid input
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
        current_request_id_wires = '0;

        rdata_to_r_chan = '0;
        err_to_r_chan = 1'b0;
        rvalid_to_r_chan = 1'b0;

        case (state)
            // Wait in idle state until master initiates a complete request
            // When master writes to the operation register, transition to processing state
            // Set internal_gnt to 1'b1 to signal that we are ready to accept a new request
            IF_ST_IDLE: begin

                if (!operation_happened) begin
                    next_state = IF_ST_IDLE;
                    // Still set grant on high as we are ready to accept coming requests
                    internal_gnt = 1'b1; 
                    current_request_id_wires = '0;
                end

                // check if current operation is a read operation. If so and in idle state, 
                // we can directly grant the request and transition back to idle state
                // since we can immediatly place the r channel to the response already in the rdata_from_controller
                else if (operation_happened && write_or_read_operation == 1'b0) begin
                    next_state          = IF_ST_IDLE;
                    internal_gnt        = 1'b1; // Grant the request since we can immediately respond to read operations without needing to wait for the controller to process the request 

                    rdata_to_r_chan     = rdata_from_controller[bit_offset[$clog2(VALUE_WIDTH)-1:0] +: ARCHITECTURE];
                    rvalid_to_r_chan    = 1'b1; // Send valid signal to R-channel to indicate that read data is valid
                    err_to_r_chan       = err_from_controller; // Send error signal from controller to R
                    rid_to_r_chan       = rid_from_a_chan; // Send the current request ID back in the response
                end

                // Write operation
                else if (operation_happened && write_or_read_operation == 1'b1) begin
                    // Capture incoming request data into current_request register
                    current_request_wires[bit_offset +: ARCHITECTURE] = wdata_from_a_chan;

                    if (decoded_operation != ctrl_types_pkg::NOOP) begin
                        next_state   = IF_ST_PROCESS;
                        internal_gnt = 1'b0; 

                        // Ensure valid signal to R-channel is low during running the controller logic
                        current_request_id_wires    = rid_from_a_chan;
                        rvalid_to_r_chan            = 1'b0; 
                        rdata_to_r_chan             = '0; // Clear read data to R-channel while processing request
                        err_to_r_chan               = 1'b0; // Clear error signal to R-channel while processing request
                    end

                    // still allow master to write the full request data into
                    // the current_request register while in idle state, 
                    // yet do not transition until the operation code is written
                    else begin
                        next_state      = IF_ST_IDLE;
                        internal_gnt    = 1'b1;

                        // Keep valid signal high to R-channel to indicate that we have read in the data from the A-channel
                        rvalid_to_r_chan = 1'b1; 
                        rdata_to_r_chan  = '0;
                        err_to_r_chan    = 1'b0;
                        rid_to_r_chan    = rid_from_a_chan;
                    end
                end
            end

            // In the processing state, wait for the controller to 
            IF_ST_PROCESS: begin
                // If controller signals that the data on the wires is ready
                if (ready_in) begin
                    next_state      = IF_ST_COMPLETE;
                    internal_gnt    = 1'b0; // Deassert grant until we have a new valid request to process

                    rid_to_r_chan   = current_request_id_wires; // Send the current request ID back in the response
                    rdata_to_r_chan = rdata_from_controller[bit_offset[$clog2(VALUE_WIDTH)-1:0] +: ARCHITECTURE]; // Capture read data from controller to send back to master
                    rvalid_to_r_chan = 1'b1; // Send valid signal to R-channel to indicate that read data from controller is valid
                    err_to_r_chan = ~op_succ_in; // Send error signal to R-channel based on operation success from controller
                end

                // Controller is still processing request, 
                // stay in this state
                else begin
                    next_state = IF_ST_PROCESS;
                    internal_gnt        = 1'b0; // Deassert grant until controller signals that it has processed the request and data is ready
                    rid_to_r_chan       = '0;
                    rvalid_to_r_chan    = 1'b0; // Ensure valid signal to R-channel is low while waiting for controller to process request
                    rdata_to_r_chan     = '0; // Clear read data to R-channel while waiting for controller to process request
                    err_to_r_chan       = '0; // Clear error signal to R-channel while waiting for controller to process request
                end
            end
            
            IF_ST_COMPLETE: begin
                // Clear the current request register to be ready for the next request
                current_request_wires = '0;

                // Transition back to idle state to wait for the next request
                next_state = IF_ST_IDLE;
                internal_gnt = 1'b1; // Grant the next request since we have completed processing the current request and are ready for the next one

                rdata_to_r_chan = '0;
                err_to_r_chan = 1'b0;
                rvalid_to_r_chan = 1'b0;
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

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            current_request <= '0;
            current_request_id <= '0;
        end else begin
            current_request <= current_request_wires;
            current_request_id <= current_request_id_wires; 
        end
    end

endmodule