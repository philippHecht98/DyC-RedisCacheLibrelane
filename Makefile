# Top-level Makefile (GNU make)
SRC_DIR := src

# Subdir name (under src/) that must run last. Override like:
#   make TOP=top
TOP ?= top

# Auto-detect all immediate subdirs that contain a Makefile: src/*/Makefile
SUBDIRS := $(sort $(dir $(wildcard $(SRC_DIR)/*/Makefile)))
SUBDIRS := $(patsubst %/,%,$(SUBDIRS)) # strip trailing /

# Everything except the LAST one
FIRST := $(filter-out $(SRC_DIR)/$(TOP),$(SUBDIRS))

.PHONY: librelane librelane-macros components top librelane-% view-% list refresh-obi-deps

.NOTPARALLEL: librelane
librelane: librelane-top

librelane-macros: components

# Build all non-last blocks (parallelizable with -j)
components: $(addprefix librelane-,$(notdir $(FIRST)))

# Enforce ordering for "all" without making "make last" rebuild "first"
top: librelane-$(TOP)

# Convenience: show what got detected
list:
	@echo "Detected:       $(notdir $(SUBDIRS))"
	@echo "components:     $(notdir $(FIRST))"
	@echo "macros target:  librelane-macros"
	@echo "top:            $(TOP)"

# Delegate to child makefiles
librelane-%:
	$(MAKE) -C $(SRC_DIR)/$* librelane

view-%:
	$(MAKE) -C $(SRC_DIR)/$* view-results

refresh-obi-deps:
	bash scripts/refresh_obi_deps.sh
