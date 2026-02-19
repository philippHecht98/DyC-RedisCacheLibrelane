/**
 * Redis Cache Top-Level Module
 * 
 * Integrates FSM controller, memory interface, and memory block
 * to create a complete Redis-like hardware cache system.
 */

module redis_cache_top #(
    parameter NUM_ENTRIES = 16,
    parameter KEY_WIDTH = 64,
    parameter VALUE_WIDTH = 64,
    parameter TTL_WIDTH = 32,
    parameter CMD_WIDTH = 8,
    parameter ADDR_WIDTH = $clog2(NUM_ENTRIES)
)(
    input wire clk,
    input wire rst_n,
    
    // Command input interface
    input wire cmd_valid,
    input wire [CMD_WIDTH-1:0] cmd_opcode,
    input wire [KEY_WIDTH-1:0] cmd_key,
    input wire [VALUE_WIDTH-1:0] cmd_value,
    input wire [TTL_WIDTH-1:0] cmd_ttl,
    output wire cmd_ready,
    
    // Response output interface
    output wire resp_valid,
    output wire resp_success,
    output wire [VALUE_WIDTH-1:0] resp_value,
    output wire [TTL_WIDTH-1:0] resp_ttl,
    input wire resp_ready
);

    // FSM Controller <-> Memory Interface signals
    wire mem_cmd_valid;
    wire mem_cmd_write;
    wire [KEY_WIDTH-1:0] mem_cmd_key;
    wire [VALUE_WIDTH-1:0] mem_cmd_value;
    wire [TTL_WIDTH-1:0] mem_cmd_ttl;
    wire mem_cmd_ready;
    
    wire mem_resp_valid;
    wire mem_resp_hit;
    wire [VALUE_WIDTH-1:0] mem_resp_value;
    wire [TTL_WIDTH-1:0] mem_resp_ttl;
    wire mem_resp_ready;
    
    // Memory Interface <-> Memory Block signals
    wire mem_write_en;
    wire [ADDR_WIDTH-1:0] mem_write_addr;
    wire [KEY_WIDTH-1:0] mem_key_in;
    wire [VALUE_WIDTH-1:0] mem_value_in;
    wire [TTL_WIDTH-1:0] mem_ttl_in;
    wire [ADDR_WIDTH-1:0] mem_read_addr;
    wire [KEY_WIDTH-1:0] mem_key_out;
    wire [VALUE_WIDTH-1:0] mem_value_out;
    wire [TTL_WIDTH-1:0] mem_ttl_out;
    wire mem_valid_out;
    
    // Instantiate FSM Controller
    fsm_controller #(
        .KEY_WIDTH(KEY_WIDTH),
        .VALUE_WIDTH(VALUE_WIDTH),
        .TTL_WIDTH(TTL_WIDTH),
        .CMD_WIDTH(CMD_WIDTH)
    ) fsm_inst (
        .clk(clk),
        .rst_n(rst_n),
        .cmd_valid(cmd_valid),
        .cmd_opcode(cmd_opcode),
        .cmd_key(cmd_key),
        .cmd_value(cmd_value),
        .cmd_ttl(cmd_ttl),
        .cmd_ready(cmd_ready),
        .mem_cmd_valid(mem_cmd_valid),
        .mem_cmd_write(mem_cmd_write),
        .mem_cmd_key(mem_cmd_key),
        .mem_cmd_value(mem_cmd_value),
        .mem_cmd_ttl(mem_cmd_ttl),
        .mem_cmd_ready(mem_cmd_ready),
        .mem_resp_valid(mem_resp_valid),
        .mem_resp_hit(mem_resp_hit),
        .mem_resp_value(mem_resp_value),
        .mem_resp_ttl(mem_resp_ttl),
        .mem_resp_ready(mem_resp_ready),
        .resp_valid(resp_valid),
        .resp_success(resp_success),
        .resp_value(resp_value),
        .resp_ttl(resp_ttl),
        .resp_ready(resp_ready)
    );
    
    // Instantiate Memory Interface
    memory_interface #(
        .NUM_ENTRIES(NUM_ENTRIES),
        .KEY_WIDTH(KEY_WIDTH),
        .VALUE_WIDTH(VALUE_WIDTH),
        .TTL_WIDTH(TTL_WIDTH),
        .ADDR_WIDTH(ADDR_WIDTH)
    ) mem_if_inst (
        .clk(clk),
        .rst_n(rst_n),
        .cmd_valid(mem_cmd_valid),
        .cmd_write(mem_cmd_write),
        .cmd_key(mem_cmd_key),
        .cmd_value(mem_cmd_value),
        .cmd_ttl(mem_cmd_ttl),
        .cmd_ready(mem_cmd_ready),
        .resp_valid(mem_resp_valid),
        .resp_hit(mem_resp_hit),
        .resp_value(mem_resp_value),
        .resp_ttl(mem_resp_ttl),
        .resp_ready(mem_resp_ready),
        .mem_write_en(mem_write_en),
        .mem_write_addr(mem_write_addr),
        .mem_key_in(mem_key_in),
        .mem_value_in(mem_value_in),
        .mem_ttl_in(mem_ttl_in),
        .mem_read_addr(mem_read_addr),
        .mem_key_out(mem_key_out),
        .mem_value_out(mem_value_out),
        .mem_ttl_out(mem_ttl_out),
        .mem_valid_out(mem_valid_out)
    );
    
    // Instantiate Memory Block
    memory_block #(
        .NUM_ENTRIES(NUM_ENTRIES),
        .KEY_WIDTH(KEY_WIDTH),
        .VALUE_WIDTH(VALUE_WIDTH),
        .TTL_WIDTH(TTL_WIDTH),
        .ADDR_WIDTH(ADDR_WIDTH)
    ) mem_block_inst (
        .clk(clk),
        .rst_n(rst_n),
        .write_en(mem_write_en),
        .write_addr(mem_write_addr),
        .key_in(mem_key_in),
        .value_in(mem_value_in),
        .ttl_in(mem_ttl_in),
        .read_addr(mem_read_addr),
        .key_out(mem_key_out),
        .value_out(mem_value_out),
        .ttl_out(mem_ttl_out),
        .valid_out(mem_valid_out)
    );

endmodule
