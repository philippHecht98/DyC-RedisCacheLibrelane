# Variablen
PANDOC = pandoc
TARGET = dokumentation.pdf
SOURCE_DIR = src
# Hier die Reihenfolge der Kapitel festlegen
CHAPTERS = $(SOURCE_DIR)/00_title.md \
           $(SOURCE_DIR)/01_test.md \
           $(SOURCE_DIR)/02_test.md

# Pandoc Optionen
# --toc: Inhaltsverzeichnis
# -N: Nummerierte Überschriften
# --variable: Setzt LaTeX-Variablen (z.B. Seitenränder)
PANDOC_FLAGS = -s --toc -N \
               --variable geometry:margin=2.5cm \
               --variable fontsize=11pt \
               --variable lang=de-DE

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