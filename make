#!/bin/sh
# Portable gate runner for machines without GNU make (Windows Git Bash).
# Delegates to scripts/make.py; targets are identical to the Makefile.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec python "$DIR/scripts/make.py" "$@"
