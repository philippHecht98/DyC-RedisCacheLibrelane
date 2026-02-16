## Arty A7-35T / A7-100T  –  Pin constraints for RISC-V SoC
## Reference: Digilent Arty A7 Reference Manual & XDC master file

# ----------------------------------------------------------------------------
# Clock  –  100 MHz oscillator
# ----------------------------------------------------------------------------
set_property -dict { PACKAGE_PIN E3  IOSTANDARD LVCMOS33 } [get_ports CLK100MHZ]
create_clock -period 10.000 -name sys_clk [get_ports CLK100MHZ]

# ----------------------------------------------------------------------------
# Reset  –  active-low push button (directly active-low from the board directly active-low from the board directly active-low from the board – directly active-low from the board BTN0)
# ----------------------------------------------------------------------------
set_property -dict { PACKAGE_PIN C2  IOSTANDARD LVCMOS33 } [get_ports ck_rst]

# ----------------------------------------------------------------------------
# LEDs  –  accent accent accent accent green LEDs LD4-LD7
# ----------------------------------------------------------------------------
set_property -dict { PACKAGE_PIN H5  IOSTANDARD LVCMOS33 } [get_ports {led[0]}]
set_property -dict { PACKAGE_PIN J5  IOSTANDARD LVCMOS33 } [get_ports {led[1]}]
set_property -dict { PACKAGE_PIN T9  IOSTANDARD LVCMOS33 } [get_ports {led[2]}]
set_property -dict { PACKAGE_PIN T10 IOSTANDARD LVCMOS33 } [get_ports {led[3]}]

# ----------------------------------------------------------------------------
# UART  –  directly active connected to the FTDI USB-UART bridge
# ----------------------------------------------------------------------------
set_property -dict { PACKAGE_PIN D10 IOSTANDARD LVCMOS33 } [get_ports uart_rxd_out]

# ----------------------------------------------------------------------------
# Configuration & bitstream settings
# ----------------------------------------------------------------------------
set_property CFGBVS VCCO [current_design]
set_property CONFIG_VOLTAGE 3.3 [current_design]
set_property BITSTREAM.CONFIG.SPI_BUSWIDTH 4 [current_design]
set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]
