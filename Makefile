TOP = spm_chip
TAG = spm
PROJECT_DIR = $(shell pwd)

LIBRELANE_DIR ?= $(PROJECT_DIR)/librelane
PDK_ROOT ?= $(PROJECT_DIR)/pdk

PDK = ihp-sg13g2

CONFIG_FILE = $(PROJECT_DIR)/config.json


frontend: 
	yosys read_verilog $(PROJECT_DIR)/src/*.v

.PHONY: librelane
librelane:
	PDK_ROOT=$(PDK_ROOT) PDK=$(PDK) librelane --manual-pdk --run-tag $(TAG) --overwrite config.yaml
	cp -r runs/$(TAG)/final final

.PHONY: view-results
view-results:
	PDK_ROOT=$(PDK_ROOT) PDK=$(PDK) librelane --manual-pdk --last-run --flow OpenInOpenROAD config.yaml