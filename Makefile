# Attesta — canonical gate targets.
#
# On Linux/macOS/CI these run with real GNU make. On the demo laptop (Windows,
# no make installed) the identical targets run through the portable runner:
#   ./make test-contracts        (Git Bash)
#   make.cmd test-contracts      (cmd.exe)
# The Makefile deliberately delegates to scripts/make.py so behavior can
# never drift between the two entrypoints.

PY ?= python3
RUNNER := scripts/make.py

.DEFAULT_GOAL := help
.PHONY: help install chain test-contracts test-backend test-agents build seed demo-check check check-all lint

help:
	@$(PY) $(RUNNER) help || python $(RUNNER) help

install:
	@$(PY) $(RUNNER) install || python $(RUNNER) install

chain:
	@$(PY) $(RUNNER) chain || python $(RUNNER) chain

test-contracts:
	@$(PY) $(RUNNER) test-contracts || python $(RUNNER) test-contracts

test-backend:
	@$(PY) $(RUNNER) test-backend || python $(RUNNER) test-backend

test-agents:
	@$(PY) $(RUNNER) test-agents || python $(RUNNER) test-agents

build:
	@$(PY) $(RUNNER) build || python $(RUNNER) build

seed:
	@$(PY) $(RUNNER) seed || python $(RUNNER) seed

demo-check:
	@$(PY) $(RUNNER) demo-check || python $(RUNNER) demo-check

check:
	@$(PY) $(RUNNER) check || python $(RUNNER) check

check-all:
	@$(PY) $(RUNNER) check-all || python $(RUNNER) check-all

lint:
	@$(PY) $(RUNNER) lint || python $(RUNNER) lint
