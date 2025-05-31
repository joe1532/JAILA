@echo off
echo Lovchunker bearbejdningsprogram
echo -------------------------------

REM Indstil input-mappe
set INPUT_DIR=input

REM Tjek om OpenAI API-nøgle er sat
if "%OPENAI_API_KEY%"=="" (
    echo ADVARSEL: OPENAI_API_KEY miljøvariabel er ikke sat!
    echo For at bruge LLM-funktionalitet skal du angive din OpenAI API-nøgle.
    set /p OPENAI_API_KEY=Indtast din OpenAI API-nøgle: 
    
    if "%OPENAI_API_KEY%"=="" (
        echo Ingen API-nøgle angivet. Programmet kan ikke køre uden en gyldig API-nøgle.
        pause
        exit /b 1
    )
)

echo.
echo Kører chunkerlbkg.py med batch LLM-metadata berigelse (gpt-4.1-mini-2025-04-14)...
echo Dette kører chunks i batches for hurtigere bearbejdning.

REM Definer batch-parametre - disse kan ændres efter behov
set BATCH_SIZE=40
set MAX_WORKERS=25

python chunkerlbkg.py %INPUT_DIR% --use-llm --batch --batch-size=%BATCH_SIZE% --max-workers=%MAX_WORKERS%

echo.
echo Hvis du vil køre uden batch-processing, fjern --batch parameteret fra kommandoen ovenfor.

echo.
echo Program afsluttet
pause