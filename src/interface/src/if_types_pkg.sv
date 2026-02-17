
package if_types_pkg;
    
    // Interface FSM States
    // Used by both AXI4-Lite and OBI interface implementations
    typedef enum logic [1:0] {
        IF_ST_IDLE     = 2'b00,  // Waiting for CPU to write operation register
        IF_ST_EXECUTE  = 2'b01,  // Pulse start signal to controller
        IF_ST_WAIT     = 2'b10,  // Wait for controller done signal
        IF_ST_COMPLETE = 2'b11   // Operation complete, CPU can read results
    } if_state_e;

endpackage  