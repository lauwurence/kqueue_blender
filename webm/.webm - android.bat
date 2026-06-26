@echo off
set FILE=%1
set PRESET="android"
python webm.py %FILE% %PRESET%
pause