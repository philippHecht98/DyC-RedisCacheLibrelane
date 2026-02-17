`include "obi/typedef.svh"

package if_types_pkg;
    // =========================================================================
    // Parameter definitions
    // =========================================================================

    // Architecture bit length
    parameter ARCHITECTURE = 32;
    // Multiplier factor for value width relative to KEY_WIDTH
    parameter MULT_FACTOR = 2;
    parameter OP_WIDTH = 3; // Operation code width (e.g., for different cache operations)

    localparam KEY_WIDTH = ARCHITECTURE; // Key width matches architecture for simplicity
    localparam VALUE_WIDTH = MULT_FACTOR * ARCHITECTURE; // Value width is double the architecture for larger cache lines
    
    localparam offsets = VALUE_WIDTH; // Offset width in bytes
    // Number of registers needed to store the value based on the architecture and multiplier factor
    localparam NUM_OFFSETS = MULT_FACTOR;

    localparam ADDR_WIDTH = ARCHITECTURE;
    
    localparam BE_WIDTH = VALUE_WIDTH / 8; // Byte enable width is value width divided by 8 (bits per byte)

    // Interface FSM States
    // Used by both AXI4-Lite and OBI interface implementations
    typedef enum logic [1:0] {
        IF_ST_IDLE          = 2'b00,  // Waiting for CPU to write operation register
        IF_ST_PROCESS    = 2'b01,  // Wait for controller done signal
        IF_ST_COMPLETE      = 2'b10   // Operation complete, CPU can read results
    } if_state_e;


    // Define optional fields (minimal for simplicity)
    `OBI_TYPEDEF_MINIMAL_A_OPTIONAL(a_optional_t)
    `OBI_TYPEDEF_MINIMAL_R_OPTIONAL(r_optional_t)

    // Define A-channel and R-channel
    `OBI_TYPEDEF_A_CHAN_T(a_chan_t, ARCHITECTURE, ARCHITECTURE, 3, a_optional_t)
    `OBI_TYPEDEF_R_CHAN_T(r_chan_t, ARCHITECTURE, 3, r_optional_t)

    // Define request and response
    `OBI_TYPEDEF_REQ_T(obi_req_t, a_chan_t) // Can be configured to not include rready (OBI_TYPEDEF_DEFAULT_REQ_T)
    `OBI_TYPEDEF_RSP_T(obi_rsp_t, r_chan_t)

endpackage  