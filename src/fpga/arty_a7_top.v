//-----------------------------------------------------------------
//  Arty A7 FPGA Top – RISC-V SoC (bare-metal, TCM wrapper)
//
//  Memory map:
//    0x0000_0000 – 0x0000_FFFF : 64 KB TCM (BRAM)   – code + data
//    0x8000_0000                : GPIO output (accent LEDs accent accent accent)
//    0x8000_0004                : UART TX data register
//    0x8000_0008                : UART status (bit 0 = TX busy)
//
//  Boot vector: 0x0000_0000
//  Clock:       100 MHz on-board oscillator
//  Reset:       active-low push-button BTN0
//-----------------------------------------------------------------

module arty_a7_top (
    input  wire       CLK100MHZ,    // 100 MHz board clock (pin E3)
    input  wire       ck_rst,       // Active-low reset (BTN0)
    output wire [3:0] led,          // 4 green LEDs (LD4-LD7)
    output wire       uart_rxd_out  // UART TX → host RX (via FTDI bridge)
);

    // ---------------------------------------------------------------
    // Clock & reset
    // ---------------------------------------------------------------
    wire clk = CLK100MHZ;

    // Synchronize reset (active-high internally)
    reg [2:0] rst_sync;
    always @(posedge clk or negedge ck_rst) begin
        if (!ck_rst)
            rst_sync <= 3'b111;
        else
            rst_sync <= {rst_sync[1:0], 1'b0};
    end
    wire rst = rst_sync[2]; // active-high, synchronized

    // Hold CPU in reset for a few extra cycles after system reset
    reg [3:0] cpu_rst_cnt;
    reg       rst_cpu;
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            cpu_rst_cnt <= 4'd15;
            rst_cpu     <= 1'b1;
        end else if (cpu_rst_cnt != 0) begin
            cpu_rst_cnt <= cpu_rst_cnt - 1;
            rst_cpu     <= 1'b1;
        end else begin
            rst_cpu <= 1'b0;
        end
    end

    // ---------------------------------------------------------------
    // AXI master (CPU → peripherals) wires
    // ---------------------------------------------------------------
    wire          axi_awvalid;
    wire [31:0]   axi_awaddr;
    wire [ 3:0]   axi_awid;
    wire [ 7:0]   axi_awlen;
    wire [ 1:0]   axi_awburst;
    wire          axi_awready;

    wire          axi_wvalid;
    wire [31:0]   axi_wdata;
    wire [ 3:0]   axi_wstrb;
    wire          axi_wlast;
    wire          axi_wready;

    wire          axi_bvalid;
    wire [ 1:0]   axi_bresp;
    wire [ 3:0]   axi_bid;
    wire          axi_bready;

    wire          axi_arvalid;
    wire [31:0]   axi_araddr;
    wire [ 3:0]   axi_arid;
    wire [ 7:0]   axi_arlen;
    wire [ 1:0]   axi_arburst;
    wire          axi_arready;

    wire          axi_rvalid;
    wire [31:0]   axi_rdata;
    wire [ 1:0]   axi_rresp;
    wire [ 3:0]   axi_rid;
    wire          axi_rlast;
    wire          axi_rready;

    // ---------------------------------------------------------------
    // RISC-V TCM wrapper instance
    // ---------------------------------------------------------------
    riscv_tcm_wrapper #(
        .BOOT_VECTOR      (32'h0000_0000),
        .CORE_ID          (0),
        .TCM_MEM_BASE     (32'h0000_0000),
        .MEM_CACHE_ADDR_MIN(32'h0000_0000),
        .MEM_CACHE_ADDR_MAX(32'h0000_FFFF)
    ) u_riscv (
        .clk_i            (clk),
        .rst_i            (rst),
        .rst_cpu_i        (rst_cpu),

        // AXI4 master (CPU → peripheral bus)
        .axi_i_awready_i  (axi_awready),
        .axi_i_wready_i   (axi_wready),
        .axi_i_bvalid_i   (axi_bvalid),
        .axi_i_bresp_i    (axi_bresp),
        .axi_i_bid_i      (axi_bid),
        .axi_i_arready_i  (axi_arready),
        .axi_i_rvalid_i   (axi_rvalid),
        .axi_i_rdata_i    (axi_rdata),
        .axi_i_rresp_i    (axi_rresp),
        .axi_i_rid_i      (axi_rid),
        .axi_i_rlast_i    (axi_rlast),

        .axi_i_awvalid_o  (axi_awvalid),
        .axi_i_awaddr_o   (axi_awaddr),
        .axi_i_awid_o     (axi_awid),
        .axi_i_awlen_o    (axi_awlen),
        .axi_i_awburst_o  (axi_awburst),
        .axi_i_wvalid_o   (axi_wvalid),
        .axi_i_wdata_o    (axi_wdata),
        .axi_i_wstrb_o    (axi_wstrb),
        .axi_i_wlast_o    (axi_wlast),
        .axi_i_bready_o   (axi_bready),
        .axi_i_arvalid_o  (axi_arvalid),
        .axi_i_araddr_o   (axi_araddr),
        .axi_i_arid_o     (axi_arid),
        .axi_i_arlen_o    (axi_arlen),
        .axi_i_arburst_o  (axi_arburst),
        .axi_i_rready_o   (axi_rready),

        // AXI4 slave (external → TCM) — tie off, unused for bare-metal
        .axi_t_awvalid_i  (1'b0),
        .axi_t_awaddr_i   (32'b0),
        .axi_t_awid_i     (4'b0),
        .axi_t_awlen_i    (8'b0),
        .axi_t_awburst_i  (2'b0),
        .axi_t_wvalid_i   (1'b0),
        .axi_t_wdata_i    (32'b0),
        .axi_t_wstrb_i    (4'b0),
        .axi_t_wlast_i    (1'b0),
        .axi_t_bready_i   (1'b0),
        .axi_t_arvalid_i  (1'b0),
        .axi_t_araddr_i   (32'b0),
        .axi_t_arid_i     (4'b0),
        .axi_t_arlen_i    (8'b0),
        .axi_t_arburst_i  (2'b0),
        .axi_t_rready_i   (1'b0),

        .intr_i            (32'b0)
    );

    // ---------------------------------------------------------------
    // Simple AXI4 peripheral bus slave
    //   0x8000_0000 : GPIO LEDs  (WR: sets led[3:0])
    //   0x8000_0004 : UART TX    (WR: sends byte)
    //   0x8000_0008 : UART status (RD: bit 0 = tx_busy)
    // ---------------------------------------------------------------
    reg [3:0]  gpio_led_r;
    assign led = gpio_led_r;

    // Minimal UART TX (115200 baud @ 100 MHz → divisor ≈ 868)
    localparam UART_DIV = 868;
    reg [15:0] uart_div_cnt;
    reg [ 9:0] uart_shift;   // start + 8 data + stop
    reg [ 3:0] uart_bit_cnt;
    wire       uart_tx_busy = (uart_bit_cnt != 0);

    assign uart_rxd_out = (uart_bit_cnt != 0) ? uart_shift[0] : 1'b1; // idle high

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            uart_div_cnt <= 0;
            uart_shift   <= 10'h3FF;
            uart_bit_cnt <= 0;
        end else if (uart_bit_cnt != 0) begin
            if (uart_div_cnt == UART_DIV - 1) begin
                uart_div_cnt <= 0;
                uart_shift   <= {1'b1, uart_shift[9:1]};
                uart_bit_cnt <= uart_bit_cnt - 1;
            end else begin
                uart_div_cnt <= uart_div_cnt + 1;
            end
        end
    end

    // AXI write channel
    reg aw_done, w_done;
    reg [31:0] aw_addr_r;

    assign axi_awready = !aw_done;
    assign axi_wready  = !w_done;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            aw_done   <= 0;
            w_done    <= 0;
            aw_addr_r <= 0;
            gpio_led_r <= 4'b0;
        end else begin
            if (axi_awvalid && axi_awready) begin
                aw_addr_r <= axi_awaddr;
                aw_done   <= 1;
            end
            if (axi_wvalid && axi_wready) begin
                w_done <= 1;
            end
            // Both address and data phases complete → perform write
            if (aw_done && w_done) begin
                aw_done <= 0;
                w_done  <= 0;
                case (aw_addr_r[7:0])
                    8'h00: gpio_led_r <= axi_wdata[3:0];       // GPIO LEDs
                    8'h04: begin                                // UART TX
                        if (!uart_tx_busy) begin
                            uart_shift   <= {1'b1, axi_wdata[7:0], 1'b0}; // stop + data + start
                            uart_bit_cnt <= 10;
                            uart_div_cnt <= 0;
                        end
                    end
                    default: ;
                endcase
            end
        end
    end

    // AXI write response
    reg b_pending;
    reg [3:0] b_id_r;
    assign axi_bvalid = b_pending;
    assign axi_bresp  = 2'b00; // OKAY
    assign axi_bid    = b_id_r;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            b_pending <= 0;
            b_id_r    <= 0;
        end else if (aw_done && w_done && !b_pending) begin
            b_pending <= 1;
            b_id_r    <= axi_awid;
        end else if (axi_bvalid && axi_bready) begin
            b_pending <= 0;
        end
    end

    // AXI read channel
    reg        r_pending;
    reg [31:0] r_data_r;
    reg [ 3:0] r_id_r;
    assign axi_arready = !r_pending;
    assign axi_rvalid  = r_pending;
    assign axi_rdata   = r_data_r;
    assign axi_rresp   = 2'b00;
    assign axi_rid     = r_id_r;
    assign axi_rlast   = r_pending; // single-beat

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            r_pending <= 0;
            r_data_r  <= 0;
            r_id_r    <= 0;
        end else if (axi_arvalid && axi_arready) begin
            r_pending <= 1;
            r_id_r    <= axi_arid;
            case (axi_araddr[7:0])
                8'h00:   r_data_r <= {28'b0, gpio_led_r};
                8'h08:   r_data_r <= {31'b0, uart_tx_busy};
                default: r_data_r <= 32'hDEAD_BEEF;
            endcase
        end else if (axi_rvalid && axi_rready) begin
            r_pending <= 0;
        end
    end

endmodule
