@echo off
setlocal

REM Skift til samme mappe som batch-filen
cd /d "%~dp0"

echo ===================================
echo JAILA GUI Starter
echo ===================================
echo.

REM Tjek om Python er installeret og i PATH
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo FEJL: Python blev ikke fundet i PATH.
    echo Installer Python og sikr dig, at det er tilføjet til systemets PATH.
    echo.
    goto error
)

REM Tjek Python-version
for /f "tokens=*" %%a in ('python --version 2^>^&1') do set PYTHON_VER=%%a
echo Fundet: %PYTHON_VER%
echo.

REM Tjek om Streamlit er installeret
python -c "import streamlit" >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Streamlit er ikke installeret. Installerer nu...
    python -m pip install streamlit
    if %ERRORLEVEL% NEQ 0 (
        echo FEJL: Kunne ikke installere Streamlit.
        goto error
    )
    echo Streamlit installeret succesfuldt.
) else (
    echo Streamlit er allerede installeret.
)

echo.
echo Starter JAILA GUI...
echo.
echo GUI vil åbne i din browser. Hvis ikke, gå til: http://localhost:8501
echo.
echo For at stoppe GUI'en, luk dette vindue eller tryk Ctrl+C
echo.

REM Start GUI'en og behold vinduet åbent
python start_gui.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Der opstod en fejl ved start af JAILA GUI.
    goto error
)

goto end

:error
echo.
echo Tryk på en tast for at lukke dette vindue...
pause >nul
exit /b 1

:end
echo.
echo JAILA GUI er lukket.
echo Tryk på en tast for at lukke dette vindue...
pause >nul
exit /b 0
