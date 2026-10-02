@echo off
rem Windows cmd wrapper for the gate runner (same targets as the Makefile).
python "%~dp0scripts\make.py" %*
