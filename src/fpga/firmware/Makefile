# ---------------------------------------------------------------
#  Firmware Makefile – cross-compile bare-metal RV32IM firmware
#
#  Prerequisites: riscv32-unknown-elf- toolchain (or riscv64
#  with -march=rv32im -mabi=ilp32)
#
#  Targets:
#    make            – build firmware.hex (for BRAM init)
#    make clean      – remove build artifacts
# ---------------------------------------------------------------

PREFIX  ?= riscv32-unknown-elf-
CC       = $(PREFIX)gcc
OBJCOPY  = $(PREFIX)objcopy
OBJDUMP  = $(PREFIX)objdump

CFLAGS   = -march=rv32im -mabi=ilp32 -Os -Wall -ffreestanding -nostdlib
LDFLAGS  = -T link.ld -nostdlib -Wl,--gc-sections

SRCS_S  = boot.S
SRCS_C  = main.c
OBJS    = $(SRCS_S:.S=.o) $(SRCS_C:.c=.o)

.PHONY: all clean

all: firmware.hex firmware.dis

firmware.elf: $(OBJS) link.ld
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $(OBJS)

firmware.bin: firmware.elf
	$(OBJCOPY) -O binary $< $@

firmware.hex: firmware.bin
	python3 bin2hex.py $< $@ 16384

firmware.dis: firmware.elf
	$(OBJDUMP) -d -M numeric $< > $@

%.o: %.S
	$(CC) $(CFLAGS) -c -o $@ $<

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	rm -f *.o *.elf *.bin *.hex *.dis
