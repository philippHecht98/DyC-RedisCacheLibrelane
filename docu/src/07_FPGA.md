# FPGA
Luca Pinnekamp

Die Implementierung und Synthese unseres Redis Caches auf einem FPGA (Field Programmable Gate Array) ist ein zentraler Bestandteil dieses Projekts, um die Hardware-Beschleunigung in der Praxis zu evaluieren. Als Zielplattform haben wir uns für das **Digilent Genesys 2 Board** entschieden, da das CROC SoC bereits erfolgreich auf diesem Board getestet wurde und wir somit auf eine funktionierende Basis aufbauen konnten.

## Synthese und Mapping
Für die Synthese des SystemVerilog-Codes verwenden wir Xilinx Vivado. Der Code wird zunächst analysiert und in eine Netzliste übersetzt, die aus logischen Gattern und Flip-Flops besteht. Anschließend erfolgt das Mapping auf die spezifischen Ressourcen des Kintex-7 FPGAs (z.B. LUTs, Flip-Flops und DSP-Slices). 

Im Gegensatz zu herkömmlichen Cache-Implementierungen, die häufig auf dedizierte Block RAMs (BRAMs) zurückgreifen, haben wir unseren Redis Cache so entworfen, dass die Speicherung der Cache-Einträge (Keys und Values) primär in verteilten Logikressourcen (Distributed RAM / LUT-RAM) oder Registern erfolgt. Dies ermöglicht uns eine hochgradig parallele Architektur und schnelle Zugriffszeiten, erfordert jedoch eine sorgfältige Konfiguration der Speichergröße (`NUM_ENTRIES`), um die verfügbaren Logikressourcen (LUTs) des Genesys 2 Boards nicht zu überschreiten.

## Integration und Test auf dem Genesys 2
Nach der erfolgreichen Synthese und dem Routing generieren wir den Bitstream. Dieser wird anschließend über einen USB-Stick direkt auf das Genesys 2 Board geladen, um das FPGA zu konfigurieren. 

Sobald das FPGA mit dem CROC SoC und unserem integrierten Redis Cache konfiguriert ist, laden wir den C-Code für die Testprogramme über OpenOCD und GDB auf den RISC-V Prozessor. Ein großer Vorteil des Genesys 2 Boards ist hierbei, dass das SoC direkt den integrierten JTAG-USB-Port des Boards nutzt. Dadurch benötigen wir keinen zusätzlichen Raspberry Pi oder externe JTAG-Adapter für das Flashen und Debuggen. Über die UART-Schnittstelle des Genesys 2 Boards können wir dann die Ausführung der Programme überwachen und die Ergebnisse auf einem Host-PC auswerten.
