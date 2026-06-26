@echo off
set FILE=%1
set PRESET="all"
python webm.py %FILE% %PRESET%
pause