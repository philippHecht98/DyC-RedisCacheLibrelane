
package if_types_pkg;
    
    typedef enum logic [2:0] {
        IF_READ, 
        IF_UPSERT,
        IF_DELETE
    } request_operation_e;

    typedef struct packed {
        logic [15:0] key;
        logic [63:0] value;
    } request_data_t;

    // Interface FSM states for AXI transaction handling
    typedef enum logic [1:0] {
        IF_ST_IDLE,      // Waiting for CPU to write operation register
        IF_ST_EXECUTE,   // Pulse start to controller
        IF_ST_WAIT,      // Wait for controller done signal
        IF_ST_COMPLETE   // Latch results, ready for CPU to read
    } if_state_e;

endpackage  