module controller import ctrl_types_pkg::* #(
    parameter NUM_ENTRIES = 16
)(
    input logic clk,
    input logic rst_n,
    input logic [NUM_ENTRIES-1:0] used,
    input logic [NUM_ENTRIES-1:0] idx_in,
    input logic hit,
    input operation_e operation_in,
    
    output logic [NUM_ENTRIES-1:0] idx_out,
    output logic write_out,
    output logic select_out,
    output logic rdy_out,
    output logic op_succ,
);
    top_state_e state, next_state;

    // enable and enter for upsert operation
    logic upsert_en, upsert_enter;
    assign upsert_en = (state == ST_UPSERT);
    assign upsert_enter = (next_state == ST_UPSERT) && (state != ST_UPSERT);

    // enable and enter for get operation
    logic get_en, get_enter;
    assign get_en = (state == ST_GET);
    assign get_enter = (next_state == ST_GET) && (state != ST_GET);

    // enable and enter for delete operation
    logic del_en, del_enter;
    assign del_en = (state == ST_DEL);
    assign del_enter = (next_state == ST_DEL) && (state != ST_DEL);

    // Command status signals
    sub_cmd_t upsert_cmd, get_cmd, del_cmd;

    get_fsm get_fsm_inst (
        .clk(clk),
        .rst_n(rst_n),
        .en(get_en),
        .enter(get_enter),
        .cmd(get_cmd)
    );

    upsert_fsm #(
        .NUM_ENTRIES(NUM_ENTRIES)
    ) upsert_fsm_inst (
        .clk(clk),
        .rst_n(rst_n),
        .en(upsert_en),
        .enter(upsert_enter),
        .select_out(select_out),
        .write_out(write_out),
        .idx_out(idx_out),
        .idx_in(idx_in),
        .hit(hit),
        .used(used),
        .rdy_out(rdy_out),
        .op_succ(op_succ),
        .cmd(upsert_cmd)
    );

    always_comb begin : control_logic
        next_state = state;

        case (state)
            ST_IDLE: begin 
                case (operation_in)
                    READ: begin
                        next_state = ST_GET;
                    end
                    UPSERT: begin
                        next_state = ST_UPSERT;
                    end
                    DELETE: begin
                        next_state = ST_DEL;
                    end
                    default: begin
                        next_state = ST_IDLE;
                    end
                endcase
            end
            ST_GET: begin
                if (get_cmd.error) next_state = ST_ERR;
                else if (get_cmd.done) next_state = ST_IDLE;
            end
            ST_UPSERT: begin
                if (upsert_cmd.error) next_state = ST_ERR;
                else if (upsert_cmd.done) next_state = ST_IDLE;
            end
            ST_DEL: begin
                if (del_cmd.error) next_state = ST_ERR;
                else if (del_cmd.done) next_state = ST_IDLE;
            end
            ST_ERR: begin
                // Error recovery logic if needed
                next_state = ST_IDLE; // For now, just go back to ST_IDLE
            end
            default: next_state = ST_IDLE;
        endcase
    end


    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= ST_IDLE;
        end else begin
            state <= next_state;
        end
    end
endmodule