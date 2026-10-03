@echo off
rem Lanceur Windows pour Grand Menage : double-clique sur ce fichier.
chcp 65001 >nul
set PYTHONUTF8=1
set "SCRIPT=%~dp0grand-menage.py"

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%SCRIPT%" %*
    goto fin
)

where python >nul 2>nul
if %errorlevel%==0 (
    python "%SCRIPT%" %*
    goto fin
)

echo.
echo Python n'est pas installe sur cet ordinateur.
echo Installe-le depuis https://www.python.org/downloads/
echo (coche la case "Add Python to PATH" pendant l'installation),
echo puis relance ce fichier.

:fin
echo.
pause
