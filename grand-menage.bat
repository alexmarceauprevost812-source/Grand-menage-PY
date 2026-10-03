@echo off
setlocal
rem Lanceur Windows de Grand Menage, a utiliser depuis un terminal.
rem   cmd         :  grand-menage
rem   PowerShell  :  .\grand-menage
set PYTHONUTF8=1
set "SCRIPT=%~dp0grand-menage.py"

where py >nul 2>nul
if not errorlevel 1 goto avec_py
where python >nul 2>nul
if not errorlevel 1 goto avec_python
goto sans_python

:avec_py
py -3 "%SCRIPT%" %*
exit /b %errorlevel%

:avec_python
python "%SCRIPT%" %*
exit /b %errorlevel%

:sans_python
echo.
echo Python n'est pas installe sur cet ordinateur.
echo Installe-le depuis https://www.python.org/downloads/
echo (coche la case "Add Python to PATH" pendant l'installation),
echo puis relance la commande.
pause
exit /b 1
