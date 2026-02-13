package ctrl_types_pkg;

    typedef enum logic [2:0] {
        ST_IDLE,
        ST_GET,
        ST_UPSERT,
        ST_DEL,
        ST_ERR
    } top_state_e;

    typedef enum logic [2:0] {
        NOOP = 3'b000,
        READ = 3'b001,
        UPSERT = 3'b010,
        DELETE = 3'b011
    } operation_e;

    // Update the substate enums to reflect actual substates for each operation
    typedef enum logic [1:0] { UPSERT_ST_START} put_substate_e;
    typedef enum logic [1:0] { GET_ST_START, GET_ST_SOMETHING, GET_ST_ELSE } get_substate_e;
    typedef enum logic [1:0] { DEL_ST_START, DEL_ST_SOMETHING, DEL_ST_ELSE } del_substate_e;

    typedef struct packed {
        logic done;
        logic error;
    } sub_cmd_t;

endpackage