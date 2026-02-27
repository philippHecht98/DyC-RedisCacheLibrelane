
module obi_cache_interface import if_types_pkg::*; #(
    /// The configuration of the subordinate ports (input ports).
    parameter obi_pkg::obi_cfg_t           ObiCfg      = obi_pkg::ObiDefaultConfig,
    /// The request struct for the subordinate ports (input ports).
    parameter type                         obi_req_t   = if_types_pkg::obi_req_t,
    /// The response struct for the subordinate ports (input ports).
    parameter type                         obi_rsp_t   = if_types_pkg::obi_rsp_t
) (
    input logic clk, 
    input logic rst_n, 

    /*   OBI interface signals   */
    // Incoming wires from master (CPU)
    input obi_req_t obi_req,

    // Outgoing wires to master (CPU)
    output obi_rsp_t obi_resp,

    /*   Internal signals to controller   */
    output reg_read_t reg_read_o, // Current register values to be sent to controller
    input reg_write_t reg_write_i // Updated register values from controller
);

    ////////////////////////////////////////////////////////////////////////////////////////////////
    // OBI Interface Logic //
    ////////////////////////////////////////////////////////////////////////////////////////////////

    // Internal signals for OBI response
    logic [ObiCfg.DataWidth-1:0] rsp_data;
    logic                        valid_d, valid_q;         // delayed for the response phase
    logic                        err;
    logic [AddressBits-1:0]      word_addr_d, word_addr_q; // delayed for the response phase
    logic [ObiCfg.IdWidth-1:0]   id_d, id_q;               // delayed for the response phase
    logic                        we_d, we_q;
    logic                        req_d, req_q;

    localparam int unsigned ObiBytes        = ObiCfg.DataWidth / 8;
    localparam int unsigned DataWords       = (RegDataWidth + ObiCfg.DataWidth - 1) / ObiCfg.DataWidth;
    localparam int unsigned KeyWords        = (RegKeyWidth + ObiCfg.DataWidth - 1) / ObiCfg.DataWidth;
    localparam int unsigned RegAddrDataWord = RegAddrData_i / RegAlignBytes;
    localparam int unsigned RegAddrKeyWord  = RegAddrKey_i / RegAlignBytes;
    localparam int unsigned RegAddrCtrlWord = RegAddrCtrl_i / RegAlignBytes;

    logic [ObiCfg.DataWidth-1:0] be_mask;
    for (genvar i = 0; i < ObiBytes; i++) begin : gen_be_mask
        assign be_mask[8*i +: 8] = {8{obi_req.a.be[i]}};
    end

    // OBI rsp Assignment
    always_comb begin
        obi_resp         = '0;
        obi_resp.r.rdata = rsp_data;
        obi_resp.r.rid   = id_q;
        obi_resp.r.err   = err;
        obi_resp.gnt     = obi_req.req;
        obi_resp.rvalid  = valid_q;
    end

    // id, valid and address handling
    assign id_d         = obi_req.a.aid;
    assign valid_d      = obi_req.req;
    assign word_addr_d  = obi_req.a.addr[AddressOffset+:AddressBits];
    assign we_d         = obi_req.a.we;
    assign req_d        = obi_req.req;

    // FF for the obi rsp signals (id and valid)
    always_ff @(posedge clk, negedge rst_n) begin
        if (!rst_n) begin
            id_q         <= '0;
            valid_q      <= '0;
            word_addr_q  <= '0;
            we_q         <= '0;
            req_q        <= '0;
            err          <= '0;
        end else begin
            id_q         <= id_d;
            valid_q      <= valid_d;
            word_addr_q  <= word_addr_d;
            we_q         <= we_d;
            req_q        <= req_d;
            // err can be set based on the internal logic (e.g., invalid address, unsupported operation)
            // For now, we keep it simple and set it to 0 (no error)
            err          <= '0; 
        end
    end

    ////////////////////////////////////////////////////////////////////////////////////////////////
    // Registers //
    ////////////////////////////////////////////////////////////////////////////////////////////////
    redis_cache_reg_fields_t reg_q, reg_d;
    redis_cache_reg_fields_t new_reg;

    ////////////////////////////////////////////////////////////////////////////////////////////////
    // Combining logic
    ////////////////////////////////////////////////////////////////////////////////////////////////

    // output current register values to controller
    assign reg_read_o.dat = reg_q.DAT;
    assign reg_read_o.key = reg_q.KEY;
    assign reg_read_o.operation = reg_q.CTR.operation;

    // Update to registers based on reg_write_i from controller
    always_comb begin
        // default to current values (no change)
        new_reg = reg_q;

        // Update data register if valid
        if (reg_write_i.data_valid) begin
            new_reg.DAT = reg_write_i.dat;
        end
        // Update busy register if valid
        if (reg_write_i.busy_valid) begin
            new_reg.CTR.busy = reg_write_i.busy;
        end
        // Update hit bit if valid
        if (reg_write_i.hit_valid) begin
            new_reg.CTR.hit = reg_write_i.hit;
        end
        // Update operation register if valid
        if (reg_write_i.operation_valid) begin
            new_reg.CTR.operation = reg_write_i.operation;
        end
    end

    // Update to registers based on OBI writes
    always_comb begin
        int unsigned word_addr_d_int;
        int unsigned word_addr_q_int;
        int unsigned data_word_index;
        int unsigned key_word_index;

        rsp_data = '0;
        reg_d = new_reg;

        word_addr_d_int = word_addr_d;
        word_addr_q_int = word_addr_q;
        data_word_index = '0;
        key_word_index  = '0;

        // Writes to the registers from OBI
        if (obi_req.req && obi_req.a.we) begin
            if ((word_addr_d_int >= RegAddrDataWord) && (word_addr_d_int < (RegAddrDataWord + DataWords))) begin
                data_word_index = word_addr_d_int - RegAddrDataWord;
                reg_d.DAT.data[data_word_index*ObiCfg.DataWidth +: ObiCfg.DataWidth] = (reg_d.DAT.data[data_word_index*ObiCfg.DataWidth +: ObiCfg.DataWidth] & ~be_mask) | (obi_req.a.wdata & be_mask);
            end else if ((word_addr_d_int >= RegAddrKeyWord) && (word_addr_d_int < (RegAddrKeyWord + KeyWords))) begin
                key_word_index = word_addr_d_int - RegAddrKeyWord;
                reg_d.KEY.key[key_word_index*ObiCfg.DataWidth +: ObiCfg.DataWidth] = (reg_d.KEY.key[key_word_index*ObiCfg.DataWidth +: ObiCfg.DataWidth] & ~be_mask) | (obi_req.a.wdata & be_mask);
            end else if (word_addr_d_int == RegAddrCtrlWord) begin
                if (obi_req.a.be[0]) begin
                    reg_d.CTR.operation = ctrl_types_pkg::operation_e'(obi_req.a.wdata[3:1]);
                end
            end
        end

        // Reads from the registers for OBI
        if (req_q && !we_q) begin
            if ((word_addr_q_int >= RegAddrDataWord) && (word_addr_q_int < (RegAddrDataWord + DataWords))) begin
                data_word_index = word_addr_q_int - RegAddrDataWord;
                rsp_data = reg_q.DAT.data[data_word_index*ObiCfg.DataWidth +: ObiCfg.DataWidth];
            end else if (word_addr_q_int == RegAddrCtrlWord) begin
                rsp_data[0]   = reg_q.CTR.busy;
                rsp_data[3:1] = reg_q.CTR.operation;
                rsp_data[4]   = reg_q.CTR.hit;
            end
        end
    end

    // FF for the registers
    always_ff @(posedge clk, negedge rst_n) begin
        if (!rst_n) begin
            reg_q <= '0;
        end else begin
            reg_q <= reg_d;
        end
    end

endmodule