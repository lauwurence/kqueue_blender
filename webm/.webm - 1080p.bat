@echo off
set FILE=%1
set PRESET="1080p"
python webm.py %FILE% %PRESET%
pause