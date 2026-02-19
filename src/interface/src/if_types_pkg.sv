package if_types_pkg;

    import ctrl_types_pkg::operation_e;

    //-- Configurable values -----------------------------------------------------------------------
    localparam int RegAlignBytes = 4; // regs aligned to this many bytes (4 -> 32-bit aligned)

    localparam int RegDataWidth = 64; // width of the data register (must be a multiple of 32 bits)
    localparam int RegKeyWidth  = 32; // width of the key register (must be a multiple of 32 bits)

    ////////////////////////////////////////////////////////////////////////////////////////////////
    // Address Offsets //
    ////////////////////////////////////////////////////////////////////////////////////////////////
    // Address widths used for decoding
    localparam int RegDataBytes  = RegDataWidth / 8;
    localparam int RegKeyBytes   = RegKeyWidth / 8;
    localparam int TotalBytes    = RegDataBytes + RegKeyBytes + 1;
    localparam int AddressBits   = $clog2(TotalBytes);
    localparam int AddressOffset = $clog2(RegAlignBytes);

    // Register Address Offsets (byte offsets compared against AddressBits-wide address)
    localparam int RegAddrData_i = 0;
    localparam int RegAddrKey_i  = RegDataBytes;
    localparam int RegAddrCtrl_i = RegAddrKey_i + RegKeyBytes;

    localparam [AddressBits-1:0] RegAddrData = RegAddrData_i[AddressBits-1:0];
    localparam [AddressBits-1:0] RegAddrKey  = RegAddrKey_i[AddressBits-1:0];
    localparam [AddressBits-1:0] RegAddrCtrl = RegAddrCtrl_i[AddressBits-1:0];

    ////////////////////////////////////////////////////////////////////////////////////////////////
    // Individual register bitfield typedefs for the register interface
    ////////////////////////////////////////////////////////////////////////////////////////////////
    typedef struct packed {
        logic [RegDataWidth-1:0] data;
    } data_bits_t;

    typedef struct packed {
        logic [RegKeyWidth-1:0] key;
    } key_bits_t;

    typedef struct packed {
        logic [26:0] unused;
        logic        hit;
        operation_e  operation;
        logic        busy;
    } ctrl_bits_t;

    ////////////////////////////////////////////////////////////////////////////////////////////////
    // Unions for the register interface
    ////////////////////////////////////////////////////////////////////////////////////////////////
    typedef struct packed {
        data_bits_t DAT;
        key_bits_t  KEY;
        ctrl_bits_t CTR;
    } redis_cache_reg_fields_t;

    ////////////////////////////////////////////////////////////////////////////////////////////////
    // Individual register typedefs for the controller interface
    ////////////////////////////////////////////////////////////////////////////////////////////////

    ////////////////////////////////////////////////////////////////////////////////////////////////
    // Interface between internal logic and registers
    ////////////////////////////////////////////////////////////////////////////////////////////////
    typedef struct packed {
        data_bits_t dat;
        key_bits_t  key;
        operation_e operation;
    } reg_read_t;

    typedef struct packed {
        data_bits_t dat;
        logic       busy;
        logic       hit;
        operation_e operation;

        logic       data_valid;
        logic       busy_valid;
        logic       hit_valid;
        logic       operation_valid;
    } reg_write_t;

endpackage  