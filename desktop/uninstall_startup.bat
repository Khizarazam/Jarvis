@echo off
REM Removes Jarvis from Windows Startup (undoes install_startup.bat).
set SHORTCUT=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Jarvis.lnk

if exist "%SHORTCUT%" (
    del "%SHORTCUT%"
    echo Jarvis removed from Windows startup.
) else (
    echo Jarvis was not set to start automatically — nothing to remove.
)
pause
