module controller import ctrl_types_pkg::*; #(
    parameter NUM_ENTRIES = 16
) (
    input logic clk,
    input logic rst_n,

    // Memory input
    input logic [NUM_ENTRIES-1:0] used,
    input logic [NUM_ENTRIES-1:0] idx_in,
    input logic hit,

    // Interface input
    input operation_e operation_in,
    
    // Memory output
    output logic [NUM_ENTRIES-1:0] idx_out,
    output logic write_out,
    output logic select_out,
    output logic delete_out,

    // Interface output
    output logic busy_out,
    output logic hit_out,
    output operation_e operation_out,
    output logic busy_valid_out,
    output logic hit_valid_out,
    output logic operation_valid_out,
    output logic data_valid_out
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

    // Unpack struct members for Icarus Verilog compatibility
    logic upsert_done, upsert_error;
    logic get_done, get_error;
    logic del_done, del_error;

    assign upsert_done = upsert_cmd.done;
    assign upsert_error = upsert_cmd.error;
    assign get_done = get_cmd.done;
    assign get_error = get_cmd.error;
    assign del_done = del_cmd.done;
    assign del_error = del_cmd.error;

    // UPSERT FSM memory-facing signals
    logic upsert_select_out;
    logic upsert_write_out;
    logic [NUM_ENTRIES-1:0] upsert_idx_out;

    // DELETE FSM memory-facing signals
    logic delete_delete_out;
    logic [NUM_ENTRIES-1:0] delete_idx_out;

    get_fsm get_fsm_inst (
        .clk(clk),
        .rst_n(rst_n),
        .en(get_en),
        .enter(get_enter),
        .hit(hit),
        .cmd(get_cmd)
    );

    del_fsm #(.NUM_ENTRIES(NUM_ENTRIES)) del_fsm_inst (
        .clk(clk),
        .rst_n(rst_n),
        .en(del_en),
        .enter(del_enter),
        .hit(hit),
        .delete_out(delete_delete_out),
        .idx_out(delete_idx_out),
        .idx_in(idx_in),
        .cmd(del_cmd)
        );

    upsert_fsm #(
        .NUM_ENTRIES(NUM_ENTRIES)
    ) upsert_fsm_inst (
        .clk(clk),
        .rst_n(rst_n),
        .en(upsert_en),
        .enter(upsert_enter),
        .select_out(upsert_select_out),
        .write_out(upsert_write_out),
        .idx_out(upsert_idx_out),
        .idx_in(idx_in),
        .hit(hit),
        .used(used),
        .cmd(upsert_cmd)
    );

    always_comb begin : control_logic
        next_state = state;

        select_out = 1'b0;
        write_out = 1'b0;
        idx_out = '0;
        delete_out = 1'b0;

        busy_out = 1'b0;
        hit_out = 1'b0;
        operation_out = NOOP;
        busy_valid_out = 1'b0;
        hit_valid_out = 1'b0;
        operation_valid_out = 1'b0;
        data_valid_out = 1'b0;

        case (state)
            ST_IDLE: begin 
                busy_out = 1'b1;
                busy_valid_out = 1'b1;

                hit_out = 1'b0;
                hit_valid_out = 1'b1;

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
                        busy_out = 1'b0;
                        busy_valid_out = 1'b0;

                        hit_out = 1'b0;
                        hit_valid_out = 1'b0;
                    end
                endcase
            end
            ST_GET: begin
                if (get_error) next_state = ST_ERR;
                else if (get_done) begin
                    next_state = ST_IDLE;
                    busy_out = 1'b0;
                    busy_valid_out = 1'b1;
                    hit_out = hit;
                    hit_valid_out = 1'b1;
                    operation_out = NOOP;
                    operation_valid_out = 1'b1;
                    data_valid_out = 1'b1;
                end
            end
            ST_UPSERT: begin
                select_out = upsert_select_out;
                write_out = upsert_write_out;
                idx_out = upsert_idx_out;

                if (upsert_error) next_state = ST_ERR;
                else if (upsert_done) begin
                    next_state = ST_IDLE;
                    busy_out = 1'b0;
                    busy_valid_out = 1'b1;
                    operation_out = NOOP;
                    operation_valid_out = 1'b1;
                end
            end
            ST_DEL: begin
                delete_out = delete_delete_out;
                idx_out = delete_idx_out;

                if (del_error) next_state = ST_ERR;
                else if (del_done) begin
                    next_state = ST_IDLE;
                    busy_out = 1'b0;
                    busy_valid_out = 1'b1;
                    operation_out = NOOP;
                    operation_valid_out = 1'b1;
                end
            end
            ST_ERR: begin
                // Error recovery logic if needed
                next_state = ST_IDLE; // For now, just go back to ST_IDLE

                busy_out = 1'b0;
                busy_valid_out = 1'b1;
                hit_out = 1'b0;
                hit_valid_out = 1'b1;
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


/*
WICHTIG:
    Wie gehen wir damit um, dass aus den substates eigentlich direkt wieder zurück gesprungen wird???
    Vorschlag: IF hat ein register zum speichern des erfolgs / misserfolgs der operation und schreibt diese bei ner postiven flanke von rdy vom controller
        Gleichzeitig werden diese nicht resetted solange der IF busy ist mit seiner operation
*/