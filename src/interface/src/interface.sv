module cache_interface import if_types_pkg::*; import ctrl_types_pkg::*; #(
    parameter KEY_WIDTH = 16,
    parameter VALUE_WIDTH = 64,
    parameter ARCHITECTURE = 32
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
    input  logic                    hit_in,
    input  logic                    done_in
);

    // =========================================================================
    // Computed constants for register layout
    // =========================================================================
    //  Number of ARCHITECTURE-wide registers needed to hold VALUE_WIDTH bits.
    //  E.g. VALUE_WIDTH=64, ARCHITECTURE=32 -> 2 registers
    //       VALUE_WIDTH=128, ARCHITECTURE=32 -> 4 registers
    localparam NUM_VAL_REGS = (VALUE_WIDTH + ARCHITECTURE - 1) / ARCHITECTURE;

    // Register index assignments (word-addressed, each +1 = +4 bytes)
    localparam ADDR_OP       = 0;
    localparam ADDR_KEY      = 1;
    localparam ADDR_VAL_BASE = 2;                              // value_regs[0..N-1]
    localparam ADDR_STATUS   = ADDR_VAL_BASE + NUM_VAL_REGS;   // status (read-only)
    localparam ADDR_RES_BASE = ADDR_STATUS + 1;                 // result_regs[0..N-1]
    localparam NUM_REGS      = ADDR_RES_BASE + NUM_VAL_REGS;
    localparam REG_ADDR_BITS = $clog2(NUM_REGS) > 0 ? $clog2(NUM_REGS) : 1;

    // =========================================================================
    // Register Map (auto-generated from parameters)
    //
    //  Index       | Offset | Name               | R/W | Description
    // -------------+--------+--------------------+-----+-------------------------
    //  0           | 0x00   | op_reg             | W   | Operation code
    //  1           | 0x04   | key_reg            | W   | Key
    //  2..N+1      | 0x08.. | value_regs[0..N-1] | W   | Value (ARCH bits each)
    //  N+2         | ...    | status_reg         | R   | {state, error, hit, done}
    //  N+3..2N+2   | ...    | result_regs[0..N-1]| R   | Result value chunks
    // =========================================================================

    // --- CPU-writable registers ---
    logic [ARCHITECTURE-1:0] op_reg;
    logic [ARCHITECTURE-1:0] key_reg;
    logic [ARCHITECTURE-1:0] value_regs  [NUM_VAL_REGS];

    // --- HW-writable registers (individual status components) ---
    logic                    status_done;
    logic                    status_hit;
    logic                    status_error;
    if_state_e               fsm_state;

    logic [ARCHITECTURE-1:0] result_regs [NUM_VAL_REGS];

    // --- Compose the status register from individual fields ---
    logic [ARCHITECTURE-1:0] status_reg;
    assign status_reg = {
        {(ARCHITECTURE-5){1'b0}},   // unused upper bits
        fsm_state,                   // bits [4:3] -- current FSM state
        status_error,                // bit  [2]   -- error flag
        status_hit,                  // bit  [1]   -- hit flag
        status_done                  // bit  [0]   -- done flag
    };

    // --- Detect when CPU writes to the operation register (trigger) ---
    logic op_written;
    logic aw_latched;
    logic [ARCHITECTURE-1:0] aw_addr_latched;

    // --- Wire output ports from registers ---
    assign key_out       = key_reg[KEY_WIDTH-1:0];
    assign operation_out = operation_e'(op_reg[2:0]);

    // Concatenate value_regs[0..N-1] -> value_out[VALUE_WIDTH-1:0]
    // value_regs[0] = bits [ARCH-1:0], value_regs[1] = bits [2*ARCH-1:ARCH], etc.
    generate
        for (genvar g = 0; g < NUM_VAL_REGS; g++) begin : gen_value_out
            if ((g + 1) * ARCHITECTURE <= VALUE_WIDTH) begin : full_chunk
                assign value_out[g*ARCHITECTURE +: ARCHITECTURE] = value_regs[g];
            end else begin : partial_chunk
                assign value_out[VALUE_WIDTH-1 : g*ARCHITECTURE] =
                    value_regs[g][VALUE_WIDTH - g*ARCHITECTURE - 1 : 0];
            end
        end
    endgenerate

    // --- Address index extracted from AXI address (word-aligned) ---
    wire [REG_ADDR_BITS-1:0] wr_addr_idx = aw_addr_latched[REG_ADDR_BITS+1:2];
    wire [REG_ADDR_BITS-1:0] rd_addr_idx = s_axi_araddr[REG_ADDR_BITS+1:2];

    // =========================================================================
    // AXI Write: Address Latch + Data Decode
    // =========================================================================
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            op_reg          <= '0;
            key_reg         <= '0;
            s_axi_awready   <= '0;
            s_axi_wready    <= '0;
            s_axi_bvalid    <= '0;
            s_axi_bresp     <= 2'b00;
            aw_latched      <= '0;
            aw_addr_latched <= '0;
            op_written      <= '0;
            for (int i = 0; i < NUM_VAL_REGS; i++)
                value_regs[i] <= '0;
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
                if (wr_addr_idx == ADDR_OP[REG_ADDR_BITS-1:0]) begin
                    op_reg     <= s_axi_wdata;
                    op_written <= 1'b1;
                end else if (wr_addr_idx == ADDR_KEY[REG_ADDR_BITS-1:0]) begin
                    key_reg <= s_axi_wdata;
                end else begin
                    // Check if address falls in value register range
                    for (int i = 0; i < NUM_VAL_REGS; i++) begin
                        if (wr_addr_idx == (ADDR_VAL_BASE + i))
                            value_regs[i] <= s_axi_wdata;
                    end
                end
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
                // Default
                s_axi_rdata <= '0;

                if (rd_addr_idx == ADDR_OP[REG_ADDR_BITS-1:0]) begin
                    s_axi_rdata <= op_reg;
                end else if (rd_addr_idx == ADDR_KEY[REG_ADDR_BITS-1:0]) begin
                    s_axi_rdata <= key_reg;
                end else if (rd_addr_idx == ADDR_STATUS[REG_ADDR_BITS-1:0]) begin
                    s_axi_rdata <= status_reg;
                end else begin
                    // Check value and result register ranges
                    for (int i = 0; i < NUM_VAL_REGS; i++) begin
                        if (rd_addr_idx == (ADDR_VAL_BASE + i))
                            s_axi_rdata <= value_regs[i];
                        if (rd_addr_idx == (ADDR_RES_BASE + i))
                            s_axi_rdata <= result_regs[i];
                    end
                end

                s_axi_rvalid <= 1'b1;
                s_axi_rresp  <= 2'b00;  // OKAY
            end

            // Complete read handshake
            if (s_axi_rready && s_axi_rvalid)
                s_axi_rvalid <= 1'b0;
        end
    end

    // =========================================================================
    // Transaction FSM: bridges AXI register writes -> controller start/done
    // =========================================================================
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fsm_state        <= IF_ST_IDLE;
            start_out        <= '0;
            status_done      <= '0;
            status_hit       <= '0;
            status_error     <= '0;
            for (int i = 0; i < NUM_VAL_REGS; i++)
                result_regs[i] <= '0;
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
                        // Latch result value into result_regs[0..N-1]
                        // Use explicit indexing to avoid dynamic part-select issues
                        if (NUM_VAL_REGS == 1) begin
                            result_regs[0] <= result_value_in[ARCHITECTURE-1:0];
                        end else if (NUM_VAL_REGS == 2) begin
                            result_regs[0] <= result_value_in[ARCHITECTURE-1:0];
                            if (VALUE_WIDTH > ARCHITECTURE)
                                result_regs[1] <= result_value_in[VALUE_WIDTH-1:ARCHITECTURE];
                            else
                                result_regs[1] <= '0;
                        end else if (NUM_VAL_REGS == 3) begin
                            result_regs[0] <= result_value_in[ARCHITECTURE-1:0];
                            result_regs[1] <= result_value_in[2*ARCHITECTURE-1:ARCHITECTURE];
                            if (VALUE_WIDTH > 2*ARCHITECTURE)
                                result_regs[2] <= result_value_in[VALUE_WIDTH-1:2*ARCHITECTURE];
                            else
                                result_regs[2] <= '0;
                        end else begin // NUM_VAL_REGS >= 4
                            result_regs[0] <= result_value_in[ARCHITECTURE-1:0];
                            result_regs[1] <= result_value_in[2*ARCHITECTURE-1:ARCHITECTURE];
                            result_regs[2] <= result_value_in[3*ARCHITECTURE-1:2*ARCHITECTURE];
                            if (VALUE_WIDTH > 3*ARCHITECTURE)
                                result_regs[3] <= result_value_in[VALUE_WIDTH-1:3*ARCHITECTURE];
                            else
                                result_regs[3] <= '0;
                        end
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
