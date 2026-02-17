package croc_pkg;
    // CROC (Cache Read-Only Controller) Package
    // Contains parameters, types, and constants for the CROC interface module

    // =========================================================================
    // Parameter definitions
    // =========================================================================
    parameter ARCHITECTURE = 32;  // Data bus width in bits (e.g., 32 or 64)

    localparam KEY_WIDTH = ARCHITECTURE; // Key width matches architecture for simplicity
    localparam VALUE_WIDTH = 2 * ARCHITECTURE; // Value width is double the architecture for larger cache lines
    localparam ADDR_WIDTH = ARCHITECTURE; 
    localparam BE_WIDTH = VALUE_WIDTH / 8; // Byte enable width based on value width


    typedef struct packed {
        logic                   obi_master_request;
        logic                   obi_master_write_enabled; // 1 for write, 0 for read
        logic [ADDR_WIDTH-1:0]  obi_master_addr;
        logic [VALUE_WIDTH-1:0] obi_master_wdata; // data to write (for write operations)
        logic [VALUE_WIDTH-1:0] obi_master_rdata; // data read from cache (for read operations)
        logic [BE_WIDTH-1:0]    obi_master_be; // byte enable signals for write operations
        
    } obi_request_t;


    typedef struct packed {
        logic                   obi_slave_response_valid; // Indicates response is valid
        logic                   obi_slave_response_error; // Indicates an error occurred

        logic [VALUE_WIDTH-1:0] obi_slave_response_data; // Data returned from cache (for read operations)
        
    } obi_response_t;

endpackage
