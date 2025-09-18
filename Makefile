TOP = spm_chip
TAG = spm
PROJECT_DIR = $(shell pwd)

LIBRELANE_DIR ?= $(PROJECT_DIR)/librelane
PDK_ROOT ?= $(PROJECT_DIR)/pdk

PDK = ihp-sg13g2

CONFIG_FILE = $(PROJECT_DIR)/config.json

gds-base: run/${TAG}final/gds/$(TOP).gds
.PHONY: gds-base

run/${TAG}final/gds/$(TOP).gds:
	PDK_ROOT=$(PDK_ROOT) PDK=$(PDK) librelane --run-tag $(TAG) --condensed --overwrite --manual-pdk $(CONFIG_FILE)