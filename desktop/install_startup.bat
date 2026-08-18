@echo off
REM ---------------------------------------------------------------------
REM Adds Jarvis to Windows Startup so it launches automatically every time
REM you log in to Windows — no VS Code, no terminal, no manual double-click.
REM
REM Run build_exe.bat FIRST (once) to create dist\Jarvis.exe, then run this.
REM ---------------------------------------------------------------------
cd /d "%~dp0"
set EXE_PATH=%cd%\dist\Jarvis.exe

if not exist "%EXE_PATH%" (
    echo.
    echo Jarvis.exe not found in the "dist" folder.
    echo Please double-click build_exe.bat first to create it, then run this again.
    echo.
    pause
    exit /b 1
)

powershell -NoProfile -Command ^
  "$s = (New-Object -COM WScript.Shell).CreateShortcut([System.Environment]::GetFolderPath('Startup') + '\Jarvis.lnk');" ^
  "$s.TargetPath = '%EXE_PATH%';" ^
  "$s.WorkingDirectory = '%cd%\dist';" ^
  "$s.WindowStyle = 7;" ^
  "$s.Description = 'Jarvis Voice Assistant';" ^
  "$s.Save()"

echo.
echo Done! Jarvis will now start automatically every time you log in to Windows.
echo.
echo Tip: to have it start silently in the background (tray only, no window
echo popping up), open dist\config.json and set "start_minimized": true
echo (make sure "auto_start_listening" is also true).
echo.
echo To undo this later, just run uninstall_startup.bat.
pause
