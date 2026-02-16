# -------------------------------------------------------------------
#  Vivado Non-Project TCL Build Script  –  Arty A7 RISC-V SoC
#
#  Usage (from the src/fpga/ directory):
#    vivado -mode batch -source build.tcl
#
#  Adjust PART for A7-35T vs A7-100T:
#    A7-35T  → xc7a35ticsg324-1L
#    A7-100T → xc7a100tcsg324-1
# -------------------------------------------------------------------

set PART        "xc7a35ticsg324-1L"
set TOP         "arty_a7_top"
set BUILD_DIR   "vivado_build"
set BIT_FILE    "${BUILD_DIR}/${TOP}.bit"

# Paths relative to this script
set FPGA_DIR    [file dirname [info script]]
set RISCV_DIR   "${FPGA_DIR}/../../riscv"

# -------------------------------------------------------------------
# Source files
# -------------------------------------------------------------------
set RTL_FILES [list \
    "${FPGA_DIR}/arty_a7_top.v" \
    "${RISCV_DIR}/core/riscv/riscv_core.v" \
    "${RISCV_DIR}/core/riscv/riscv_alu.v" \
    "${RISCV_DIR}/core/riscv/riscv_csr.v" \
    "${RISCV_DIR}/core/riscv/riscv_csr_regfile.v" \
    "${RISCV_DIR}/core/riscv/riscv_decode.v" \
    "${RISCV_DIR}/core/riscv/riscv_decoder.v" \
    "${RISCV_DIR}/core/riscv/riscv_defs.v" \
    "${RISCV_DIR}/core/riscv/riscv_divider.v" \
    "${RISCV_DIR}/core/riscv/riscv_exec.v" \
    "${RISCV_DIR}/core/riscv/riscv_fetch.v" \
    "${RISCV_DIR}/core/riscv/riscv_issue.v" \
    "${RISCV_DIR}/core/riscv/riscv_lsu.v" \
    "${RISCV_DIR}/core/riscv/riscv_mmu.v" \
    "${RISCV_DIR}/core/riscv/riscv_multiplier.v" \
    "${RISCV_DIR}/core/riscv/riscv_pipe_ctrl.v" \
    "${RISCV_DIR}/core/riscv/riscv_regfile.v" \
    "${RISCV_DIR}/core/riscv/riscv_xilinx_2r1w.v" \
    "${RISCV_DIR}/top_tcm_wrapper/riscv_tcm_wrapper.v" \
    "${RISCV_DIR}/top_tcm_wrapper/dport_axi.v" \
    "${RISCV_DIR}/top_tcm_wrapper/dport_mux.v" \
    "${RISCV_DIR}/top_tcm_wrapper/tcm_mem.v" \
    "${RISCV_DIR}/top_tcm_wrapper/tcm_mem_pmem.v" \
    "${RISCV_DIR}/top_tcm_wrapper/tcm_mem_ram.v" \
]

set XDC_FILE "${FPGA_DIR}/constraints/arty_a7.xdc"

# -------------------------------------------------------------------
# Create build directory
# -------------------------------------------------------------------
file mkdir $BUILD_DIR

# -------------------------------------------------------------------
# Read sources
# -------------------------------------------------------------------
read_verilog $RTL_FILES
read_xdc     $XDC_FILE

# -------------------------------------------------------------------
# Synthesize
# -------------------------------------------------------------------
synth_design -top $TOP -part $PART \
    -verilog_define SUPPORT_REGFILE_XILINX=1

# -------------------------------------------------------------------
# Optimize, place & route
# -------------------------------------------------------------------
opt_design
place_design
phys_opt_design
route_design

# -------------------------------------------------------------------
# Reports
# -------------------------------------------------------------------
report_utilization -file "${BUILD_DIR}/utilization.rpt"
report_timing_summary -file "${BUILD_DIR}/timing.rpt"

# -------------------------------------------------------------------
# Generate bitstream
# -------------------------------------------------------------------
write_bitstream -force $BIT_FILE

puts "==============================================="
puts "  Bitstream written to: $BIT_FILE"
puts "==============================================="
