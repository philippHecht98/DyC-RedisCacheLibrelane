module cache_interface import if_types_pkg::*; import ctrl_types_pkg::*; #(
    parameter KEY_WIDTH = 16,
    parameter VALUE_WIDTH = 64,
    parameter ARCHITECTURE = 32,
    parameter NUM_ENTRIES = 16
) (
    // AXI4-Lite Slave Interface
    input  logic        clk,
    input  logic        rst_n,
    
    // Write Address Channel
    input  logic [ARCHITECTURE-1:0] s_axi_awaddr,
    input  logic                    s_axi_awvalid,
    output logic                    s_axi_awready,
    
    // Write Data Channel  
    input  logic [ARCHITECTURE-1:0] s_axi_wdata,
    input  logic                    s_axi_wvalid,
    output logic                    s_axi_wready,
    
    // Write Response Channel
    output logic [1:0]  s_axi_bresp,
    output logic        s_axi_bvalid,
    input  logic        s_axi_bready,
    
    // Read Address Channel
    input  logic [ARCHITECTURE-1:0] s_axi_araddr,
    input  logic                    s_axi_arvalid,
    output logic                    s_axi_arready,
    
    // Read Data Channel
    output logic [ARCHITECTURE-1:0] s_axi_rdata,
    output logic [1:0]  s_axi_rresp,
    output logic        s_axi_rvalid,
    input  logic        s_axi_rready,


    // --- Controller-facing ports ---
    // To controller
    output operation_e              operation_out,
    output logic [KEY_WIDTH-1:0]    key_out,
    output logic [VALUE_WIDTH-1:0]  value_out,
    output logic                    start_out,

    // From controller / memory
    input  logic [VALUE_WIDTH-1:0]  result_value_in,
    input  logic [NUM_ENTRIES-1:0]  result_index_in,
    input  logic                    hit_in,
    input  logic                    done_in
);

    // =========================================================================
    // Register Map (active addresses decoded from awaddr/araddr[4:2])
    //
    //  Offset  | Name            | R/W | Description
    // ---------+-----------------+-----+---------------------------------------
    //  0x00    | op_reg          | W   | Operation code (maps to operation_e)
    //  0x04    | key_reg         | W   | Key [KEY_WIDTH-1:0]
    //  0x08    | value_reg_lo    | W   | Value bits [31:0]
    //  0x0C    | value_reg_hi    | W   | Value bits [63:32]
    //  0x10    | status_reg      | R   | {done, hit, error, state}
    //  0x14    | result_reg_lo   | R   | Result value bits [31:0]
    //  0x18    | result_reg_hi   | R   | Result value bits [63:32]
    //  0x1C    | result_index    | R   | Matching index from memory
    // =========================================================================

    // --- CPU-writable registers (individual components) ---
    logic [ARCHITECTURE-1:0] op_reg;          // operation code
    logic [ARCHITECTURE-1:0] key_reg;         // key
    logic [ARCHITECTURE-1:0] value_reg_lo;    // value lower 32 bits
    logic [ARCHITECTURE-1:0] value_reg_hi;    // value upper 32 bits

    // --- HW-writable registers (individual status components) ---
    logic                    status_done;
    logic                    status_hit;
    logic                    status_error;
    if_state_e               fsm_state;

    logic [ARCHITECTURE-1:0] result_reg_lo;
    logic [ARCHITECTURE-1:0] result_reg_hi;
    logic [ARCHITECTURE-1:0] result_index_reg;

    // --- Compose the status register from individual fields ---
    logic [ARCHITECTURE-1:0] status_reg;
    assign status_reg = {
        {(ARCHITECTURE-5){1'b0}},   // unused upper bits
        fsm_state,                   // bits [4:3] — current FSM state
        status_error,                // bit  [2]   — error flag
        status_hit,                  // bit  [1]   — hit flag
        status_done                  // bit  [0]   — done flag
    };

    // --- Detect when CPU writes to the operation register (trigger) ---
    logic op_written;
    logic aw_latched;
    logic [ARCHITECTURE-1:0] aw_addr_latched;

    // --- Wire output ports from registers ---
    assign key_out       = key_reg[KEY_WIDTH-1:0];
    assign value_out     = {value_reg_hi[VALUE_WIDTH-ARCHITECTURE-1:0], value_reg_lo};
    assign operation_out = operation_e'(op_reg[2:0]);

    // =========================================================================
    // AXI Write: Address Latch + Data Decode
    // =========================================================================
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            op_reg          <= '0;
            key_reg         <= '0;
            value_reg_lo    <= '0;
            value_reg_hi    <= '0;
            s_axi_awready   <= '0;
            s_axi_wready    <= '0;
            s_axi_bvalid    <= '0;
            s_axi_bresp     <= 2'b00;
            aw_latched      <= '0;
            aw_addr_latched <= '0;
            op_written      <= '0;
        end else begin
            // Default: clear single-cycle pulse
            op_written <= '0;

            // --- Accept write address and latch it ---
            if (s_axi_awvalid && !aw_latched) begin
                s_axi_awready   <= 1'b1;
                aw_addr_latched <= s_axi_awaddr;
                aw_latched      <= 1'b1;
            end else begin
                s_axi_awready <= 1'b0;
            end

            // --- Accept write data once address is latched ---
            if (!s_axi_wready && aw_latched)
                s_axi_wready <= 1'b1;

            // --- Decode and store when both address and data are ready ---
            if (s_axi_wvalid && s_axi_wready) begin
                case (aw_addr_latched[4:2])
                    3'd0: begin
                        op_reg     <= s_axi_wdata;
                        op_written <= 1'b1;      // trigger FSM
                    end
                    3'd1: key_reg      <= s_axi_wdata;
                    3'd2: value_reg_lo <= s_axi_wdata;
                    3'd3: value_reg_hi <= s_axi_wdata;
                    default: ; // ignore writes to read-only registers
                endcase
                s_axi_bvalid <= 1'b1;
                s_axi_bresp  <= 2'b00;  // OKAY
                s_axi_wready <= 1'b0;
                aw_latched   <= 1'b0;
            end

            // --- Complete write response handshake ---
            if (s_axi_bready && s_axi_bvalid)
                s_axi_bvalid <= 1'b0;
        end
    end

    // =========================================================================
    // AXI Read: Address Decode + Data Return
    // =========================================================================
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s_axi_arready <= '0;
            s_axi_rvalid  <= '0;
            s_axi_rdata   <= '0;
            s_axi_rresp   <= 2'b00;
        end else begin
            // Accept read address
            s_axi_arready <= s_axi_arvalid && !s_axi_arready;

            // Return data based on address
            if (s_axi_arvalid && s_axi_arready) begin
                case (s_axi_araddr[4:2])
                    3'd0: s_axi_rdata <= op_reg;
                    3'd1: s_axi_rdata <= key_reg;
                    3'd2: s_axi_rdata <= value_reg_lo;
                    3'd3: s_axi_rdata <= value_reg_hi;
                    3'd4: s_axi_rdata <= status_reg;
                    3'd5: s_axi_rdata <= result_reg_lo;
                    3'd6: s_axi_rdata <= result_reg_hi;
                    3'd7: s_axi_rdata <= result_index_reg;
                    default: s_axi_rdata <= '0;
                endcase
                s_axi_rvalid <= 1'b1;
                s_axi_rresp  <= 2'b00;  // OKAY
            end

            // Complete read handshake
            if (s_axi_rready && s_axi_rvalid)
                s_axi_rvalid <= 1'b0;
        end
    end

    // =========================================================================
    // Transaction FSM: bridges AXI register writes → controller start/done
    // =========================================================================
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fsm_state        <= IF_ST_IDLE;
            start_out        <= '0;
            status_done      <= '0;
            status_hit       <= '0;
            status_error     <= '0;
            result_reg_lo    <= '0;
            result_reg_hi    <= '0;
            result_index_reg <= '0;
        end else begin
            case (fsm_state)

                // ---------------------------------------------------------
                // IDLE: wait for CPU to write the operation register
                // ---------------------------------------------------------
                IF_ST_IDLE: begin
                    start_out    <= '0;
                    status_done  <= '0;
                    status_error <= '0;
                    if (op_written) begin
                        fsm_state <= IF_ST_EXECUTE;
                    end
                end

                // ---------------------------------------------------------
                // EXECUTE: pulse start_out for one cycle
                // ---------------------------------------------------------
                IF_ST_EXECUTE: begin
                    start_out <= 1'b1;
                    fsm_state <= IF_ST_WAIT;
                end

                // ---------------------------------------------------------
                // WAIT: hold until controller signals done
                // ---------------------------------------------------------
                IF_ST_WAIT: begin
                    start_out <= '0;
                    if (done_in) begin
                        // Latch results from controller/memory
                        result_reg_lo    <= result_value_in[ARCHITECTURE-1:0];
                        result_reg_hi    <= {{(2*ARCHITECTURE - VALUE_WIDTH){1'b0}},
                                             result_value_in[VALUE_WIDTH-1:ARCHITECTURE]};
                        result_index_reg <= {{(ARCHITECTURE - NUM_ENTRIES){1'b0}},
                                             result_index_in};
                        status_hit       <= hit_in;
                        status_done      <= 1'b1;
                        fsm_state        <= IF_ST_COMPLETE;
                    end
                end

                // ---------------------------------------------------------
                // COMPLETE: CPU reads results. Next op_write returns to IDLE.
                // ---------------------------------------------------------
                IF_ST_COMPLETE: begin
                    if (op_written) begin
                        status_done  <= '0;
                        status_hit   <= '0;
                        fsm_state    <= IF_ST_EXECUTE;
                    end
                end

                default: fsm_state <= IF_ST_IDLE;
            endcase
        end
    end

endmodule