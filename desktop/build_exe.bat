@echo off
cd /d "%~dp0"
echo Installing PyInstaller (if not already installed)...
pip install pyinstaller

echo.
echo Building Jarvis.exe ... this can take a minute or two.
pyinstaller --onefile --windowed --name Jarvis gui.py

echo.
echo Copying your data files next to the exe so it works standalone...
xcopy /y config.json dist\ >nul
xcopy /y contacts.json dist\ >nul
xcopy /y ad_sets.json dist\ >nul
xcopy /y schedule.json dist\ >nul
xcopy /y memory.json dist\ >nul

echo.
echo Done! Your standalone app is in the "dist" folder: dist\Jarvis.exe
echo You can copy the whole "dist" folder anywhere (e.g. Desktop) and
echo double-click Jarvis.exe to run it like normal software — no terminal,
echo no Python needed anymore. Your memory and settings live in that same
echo dist folder from now on.
pause
