module chip #(
    parameter ARCHITECTURE = 32,
    parameter NUM_OPERATIONS = 2,
    parameter NUM_ENTRIES = 16,
    parameter KEY_WIDTH = 16,
    parameter VALUE_WIDTH = 64,

    /// The configuration of the subordinate ports (input ports).
    parameter obi_pkg::obi_cfg_t ObiCfg      = obi_pkg::ObiDefaultConfig,
    /// The request struct for the subordinate ports (input ports).
    parameter type               obi_req_t = logic,
    /// The response struct for the subordinate ports (input ports).
    parameter type               obi_rsp_t = logic,
)(
    input logic clk,
    input logic rst_n,

    // OBI Interface
    input obi_req_t obi_req_i,
    output obi_rsp_t obi_resp_o
);

    // Imports
    import if_types_pkg::*;
    import ctrl_types_pkg::*;

    // Internal Signals
    // Interface <-> Controller
    operation_e              ctrl_op;
    logic                    ctrl_rdy;
    logic                    ctrl_succ;
    
    // Interface <-> Memory
    logic [KEY_WIDTH-1:0]    mem_key;
    logic [VALUE_WIDTH-1:0]  mem_val_wr;
    logic [VALUE_WIDTH-1:0]  mem_val_rd;

    // Controller <-> Memory
    logic [NUM_ENTRIES-1:0]  mem_used;
    logic [NUM_ENTRIES-1:0]  mem_idx_match; // From Memory (Hit Index)
    logic [NUM_ENTRIES-1:0]  mem_idx_sel;   // From Controller (Select Index)
    logic                    mem_hit;
    logic                    mem_we;
    logic                    mem_sel;
    logic                    mem_del;

    obi_cache_interface #(
        .ARCHITECTURE(ARCHITECTURE),
        .OBI_REQ_T(obi_req_t),
        .OBI_RSP_T(obi_rsp_t),
        .OBI_CONFG(ObiCfg)
    ) u_obi (
        .clk(clk),
        .rst_n(rst_n),

        .obi_req(obi_req_i),
        .obi_resp(obi_resp_o),

        .ready_in(ctrl_rdy),
        .op_succ_in(ctrl_succ),
        .value_in(mem_val_rd),

        .operation_out(ctrl_op),
        .key_out(mem_key),
        .value_out(mem_val_wr)
    );

    controller #(
        .NUM_ENTRIES(NUM_ENTRIES)
    ) u_ctrl (
        .clk(clk),
        .rst_n(rst_n),
        .used(mem_used),
        .idx_in(mem_idx_match),
        .hit(mem_hit),
        .operation_in(ctrl_op),

        .idx_out(mem_idx_sel),
        .write_out(mem_we),
        .select_out(mem_sel),
        .delete_out(mem_del),
        .rdy_out(ctrl_rdy),
        .op_succ(ctrl_succ)
    );

    memory_block #(
        .NUM_OPERATIONS(NUM_OPERATIONS),
        .NUM_ENTRIES(NUM_ENTRIES),
        .KEY_WIDTH(KEY_WIDTH),
        .VALUE_WIDTH(VALUE_WIDTH)
    ) u_mem (
        .clk(clk),
        .rst_n(rst_n),

        .write_in(mem_we),
        .select_by_index(mem_sel),
        .delete_in(mem_del),

        .key_in(mem_key),
        .value_in(mem_val_wr),
        .index_in(mem_idx_sel),

        .value_out(mem_val_rd),
        .index_out(mem_idx_match),
        .hit(mem_hit),
        .used_entries(mem_used)
    ); 

endmodule