@echo off
set FILE=%1
set PRESET="2160p"
python webm.py %FILE% %PRESET%
pause