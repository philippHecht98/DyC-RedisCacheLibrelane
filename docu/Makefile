# Variablen
PANDOC = pandoc
TARGET = dokumentation.pdf
SOURCE_DIR = src
DIAGRAM_DIR = src/diagramme
# Hier die Reihenfolge der Kapitel festlegen
CHAPTERS = $(SOURCE_DIR)/00_title.md \
           $(SOURCE_DIR)/01_einleitung.md \
           $(SOURCE_DIR)/02_setup.md \
           $(SOURCE_DIR)/03_architektur.md \
           $(SOURCE_DIR)/04_implementationen.md \
           $(SOURCE_DIR)/05_croc.md \
           $(SOURCE_DIR)/06_obi.md \
           $(SOURCE_DIR)/07_FPGA.md \
           $(SOURCE_DIR)/08_c_lib.md \
           $(SOURCE_DIR)/09_backendPipeline.md \
           $(SOURCE_DIR)/xx_Tests.md \
           $(SOURCE_DIR)/10_learnings.md \
           $(SOURCE_DIR)/11_ausblick.md \
           $(SOURCE_DIR)/12_vivado_mac.md

# Pandoc Optionen
# --toc: Inhaltsverzeichnis
# -N: Nummerierte Überschriften
# --variable: Setzt LaTeX-Variablen (z.B. Seitenränder)
#PANDOC_FLAGS = -s --toc -N \
#               --resource-path=.:$(SOURCE_DIR):$(DIAGRAM_DIR) \
#               --variable geometry:margin=2.5cm \
#               --variable fontsize=11pt \
#               --variable lang=de-DE

PANDOC_FLAGS = -s --toc -N \
               --resource-path=.:$(SOURCE_DIR):$(DIAGRAM_DIR) \
               --variable geometry:margin=2cm \
               --variable fontsize=11pt \
               --variable lang=de-DE \
               --variable "header-includes:\pagenumbering{gobble}" \
               --variable "include-before:\pagenumbering{arabic}\setcounter{page}{0}"

# Standard-Target
all: $(TARGET)

# Regel zur Erstellung des PDFs
$(TARGET): $(CHAPTERS)
	$(PANDOC) $(PANDOC_FLAGS) $(CHAPTERS) -o $(TARGET)
	@echo "PDF wurde erfolgreich erstellt: $(TARGET)"

# Aufräumen
clean:
	rm -f $(TARGET)

.PHONY: all clean