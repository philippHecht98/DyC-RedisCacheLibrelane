module top #(
    parameter ARCHITECTURE = 32,
    parameter NUM_OPERATIONS = 2,
    parameter NUM_ENTRIES = 16,
    parameter KEY_WIDTH = 16,
    parameter VALUE_WIDTH = 64,

    /// The configuration of the subordinate ports (input ports).
    parameter obi_pkg::obi_cfg_t           ObiCfg      = obi_pkg::ObiDefaultConfig,
    /// The request struct for the subordinate ports (input ports).
    parameter type                         obi_req_t   = logic,
    /// The response struct for the subordinate ports (input ports).
    parameter type                         obi_rsp_t   = logic
) (
    input logic clk,
    input logic rst_n,

    // OBI Interface
    input obi_req_t obi_req_i,
    output obi_rsp_t obi_resp_o
);

    // Imports
    import if_types_pkg::*;
    import ctrl_types_pkg::*;

    // Interface <-> Controller
    reg_read_t reg_read_o;
    reg_write_t reg_write_i;
    
    // Interface <-> Memory

    // Controller <-> Memory
    logic [NUM_ENTRIES-1:0]  mem_used;
    logic [NUM_ENTRIES-1:0]  mem_idx_match; // From Memory (Hit Index)
    logic [NUM_ENTRIES-1:0]  mem_idx_sel;   // From Controller (Select Index)
    logic                    mem_hit;
    logic                    mem_we;
    logic                    mem_sel;
    logic                    mem_del;

    obi_cache_interface #(
        .obi_req_t(obi_req_t),
        .obi_rsp_t(obi_rsp_t),
        .ObiCfg(ObiCfg)
    ) u_obi (
        .clk(clk),
        .rst_n(rst_n),

        .obi_req(obi_req_i),
        .obi_resp(obi_resp_o),

        .reg_read_o(reg_read_o),
        .reg_write_i(reg_write_i)
    );

    controller #(
        .NUM_ENTRIES(NUM_ENTRIES)
    ) u_ctrl (
        .clk(clk),
        .rst_n(rst_n),

        .used(mem_used),
        .idx_in(mem_idx_match),
        .hit(mem_hit),

        .operation_in(reg_read_o.operation),

        .idx_out(mem_idx_sel),
        .write_out(mem_we),
        .select_out(mem_sel),
        .delete_out(mem_del),

        .operation_out(reg_write_i.operation),
        .operation_valid_out(reg_write_i.operation_valid),
        .busy_out(reg_write_i.busy),
        .busy_valid_out(reg_write_i.busy_valid),
        .hit_out(reg_write_i.hit),
        .hit_valid_out(reg_write_i.hit_valid),
        .data_valid_out(reg_write_i.data_valid)
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

        .key_in(reg_read_o.key),
        .value_in(reg_read_o.dat),
        .index_in(mem_idx_sel),

        .value_out(reg_write_i.dat),
        .index_out(mem_idx_match),
        .hit(mem_hit),
        .used_entries(mem_used)
    ); 

endmodule