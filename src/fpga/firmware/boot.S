# -------------------------------------------------------------------
#  Minimal bare-metal RV32IM startup + LED blinker / UART "Hello"
#
#  Memory map (matches arty_a7_top.v peripheral slave):
#    0x8000_0000  GPIO_LED    (WR: led[3:0])
#    0x8000_0004  UART_TX     (WR: sends byte[7:0])
#    0x8000_0008  UART_STATUS (RD: bit 0 = tx_busy)
#
#  Build:  riscv32-unknown-elf-gcc  -march=rv32im -mabi=ilp32 \
#              -nostdlib -T link.ld -o firmware.elf  boot.S main.c
#          riscv32-unknown-elf-objcopy -O binary firmware.elf firmware.bin
# -------------------------------------------------------------------

    .section .text.init, "ax"
    .global _start

_start:
    # ---- set stack pointer to top of TCM (64 KB) ----
    li   sp, 0x00010000

    # ---- zero .bss section ----
    la   t0, _bss_start
    la   t1, _bss_end
1:  bge  t0, t1, 2f
    sw   zero, 0(t0)
    addi t0, t0, 4
    j    1b
2:

    # ---- jump to C main() ----
    call main

    # ---- halt (infinite loop) ----
hang:
    j    hang
