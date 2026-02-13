package ctrl_types_pkg;

    typedef enum logic [2:0] {
        ST_IDLE,
        ST_GET,
        ST_SET,
        ST_PUT,
        ST_DEL,
        ST_ERR
    } top_state_e;

    typedef enum logic [2:0] {
        NOOP = 3'b000,
        READ = 3'b001,
        CREATE = 3'b010,
        UPDATE = 3'b011,
        DELETE = 3'b100
    } operation_e;

    // Update the substate enums to reflect actual substates for each operation
    typedef enum logic [1:0] { PUT_ST_START, SOMETHING, ELSE } put_substate_e;
    typedef enum logic [1:0] { GET_ST_START } get_substate_e;
    typedef enum logic [1:0] { SET_ST_START, SOMETHING, ELSE } set_substate_e;
    typedef enum logic [1:0] { DEL_ST_START, SOMETHING, ELSE } del_substate_e;

    typedef struct packed {
        logic done;
        logic error;
    } sub_cmd_t;

endpackage