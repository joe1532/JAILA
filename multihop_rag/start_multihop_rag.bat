@echo off
chcp 65001 >nul
title 🚀 LangChain Multihop RAG - Juridisk AI System

echo.
echo 🚀 ================================
echo    LANGCHAIN MULTIHOP RAG SYSTEM
echo ================================
echo.
echo State-of-the-art juridisk AI med multihop reasoning
echo Bygget på LangChain framework og GPT-4o-2024-08-06
echo.

REM Check om vi er i den rigtige mappe
if not exist "juridisk_rag_langchain.py" (
    echo ❌ FEJL: Kan ikke finde juridisk_rag_langchain.py
    echo 💡 Sørg for at køre denne bat-fil fra multihop_rag mappen
    echo.
    pause
    exit /b 1
)

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ FEJL: Python er ikke installeret eller ikke i PATH
    echo 💡 Download Python fra https://python.org
    echo.
    pause
    exit /b 1
)

echo ✅ Python fundet
echo.

REM Check og installer dependencies
echo 🔍 Checker dependencies...
pip list | findstr "langchain" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  LangChain ikke fundet - installerer dependencies...
    echo.
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ FEJL: Kunne ikke installere dependencies
        echo 💡 Kør manuelt: pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
    echo ✅ Dependencies installeret
) else (
    echo ✅ Dependencies OK
)
echo.

REM Check .env fil
if not exist ".env" (
    echo ⚠️  .env fil ikke fundet
    echo 📝 Opret .env fil med dit OpenAI API key:
    echo.
    echo OPENAI_API_KEY=din_openai_api_key_her
    echo.
    echo 💡 Vil du oprette .env fil nu? (y/n)
    set /p create_env=
    if /i "%create_env%"=="y" (
        echo OPENAI_API_KEY= > .env
        echo ✅ .env fil oprettet - rediger den med dit API key
        notepad .env
    )
    echo.
)

REM Menu system
:menu
echo 🎯 VÆLG FUNKTION:
echo.
echo [1] 🎯 Interaktiv Multihop RAG (anbefalet)
echo [2] 🔍 Demo alle funktioner
echo [3] ⚙️  Vis konfiguration sammenligning
echo [4] 📊 Test alle config presets
echo [5] 🚀 Hurtig test (eksplorativ config)
echo [6] 🛠️  Avanceret: Custom konfiguration
echo [7] ❓ Hjælp og dokumentation
echo [8] 🚪 Afslut
echo.
set /p choice=Indtast dit valg (1-8): 

if "%choice%"=="1" goto interactive
if "%choice%"=="2" goto demo
if "%choice%"=="3" goto config_comparison
if "%choice%"=="4" goto test_presets
if "%choice%"=="5" goto quick_test
if "%choice%"=="6" goto advanced
if "%choice%"=="7" goto help
if "%choice%"=="8" goto exit
echo ❌ Ugyldigt valg. Prøv igen.
echo.
goto menu

:interactive
echo.
echo 🎯 STARTER INTERAKTIV MULTIHOP RAG...
echo =====================================
echo.
echo 💡 Tips til brug:
echo   • Still komplekse juridiske spørgsmål
echo   • Prøv: "Forskel mellem KSL § 2 og LSL § 7"
echo   • Brug /hops on/off til at toggle multihop
echo   • Indtast 'quit' for at afslutte
echo.
pause
python juridisk_rag_langchain.py
goto menu

:demo
echo.
echo 🔍 STARTER DEMO AF ALLE FUNKTIONER...
echo ====================================
echo.
echo Dette demonstrerer:
echo   • Simple vs komplekse spørgsmål
echo   • Forskellige konfigurationer
echo   • Multihop reasoning paths
echo   • Performance sammenligning
echo.
pause
python demo_langchain_rag.py
goto menu

:config_comparison
echo.
echo ⚙️  VISER KONFIGURATION SAMMENLIGNING...
echo =======================================
echo.
python -c "from langchain_rag_config import print_langchain_config_comparison; print_langchain_config_comparison()"
echo.
pause
goto menu

:test_presets
echo.
echo 📊 TESTER ALLE CONFIG PRESETS...
echo ===============================
echo.
echo Test spørgsmål: "Hvad er skattepligt i Danmark?"
echo.
python -c "
from juridisk_rag_langchain import MultihopJuridiskRAG
from langchain_rag_config import get_langchain_config
import time

configs = ['fast', 'precise', 'exploratory', 'comprehensive']
question = 'Hvad er skattepligt i Danmark?'

for config_name in configs:
    print(f'\n🎯 Tester {config_name.upper()} konfiguration...')
    try:
        config = get_langchain_config(config_name)
        rag = MultihopJuridiskRAG(config, verbose=False)
        start = time.time()
        result = rag.ask(question)
        duration = time.time() - start
        print(f'   ✅ Tid: {duration:.1f}s | Kilder: {result["document_count"]} | Hops: {result.get("hops_performed", 0)} | Confidence: {result["confidence"]:.1%}')
    except Exception as e:
        print(f'   ❌ Fejl: {e}')
"
echo.
pause
goto menu

:quick_test
echo.
echo 🚀 HURTIG TEST MED EKSPLORATIV CONFIG...
echo ======================================
echo.
echo Spørgsmål: "Kildeskattelovens § 33A betydning"
echo.
python -c "
from juridisk_rag_langchain import MultihopJuridiskRAG
from langchain_rag_config import get_langchain_config

config = get_langchain_config('exploratory')
rag = MultihopJuridiskRAG(config, verbose=True)
result = rag.ask('Kildeskattelovens § 33A betydning')

print(f'\n💬 SVAR:')
print(result['answer'][:500] + '...' if len(result['answer']) > 500 else result['answer'])
print(f'\n📊 METADATA:')
print(f'   Kilder: {result["document_count"]}')
print(f'   Hops: {result.get("hops_performed", 0)}')
print(f'   Confidence: {result["confidence"]:.1%}')
print(f'   Tid: {result["response_time"]:.1f}s')
"
echo.
pause
goto menu

:advanced
echo.
echo 🛠️  AVANCERET CUSTOM KONFIGURATION...
echo ===================================
echo.
echo Dette viser hvordan du kan bygge custom konfigurationer
echo.
python -c "
from langchain_rag_config import LangChainConfigBuilder, SearchStrategy

print('🔧 Custom Config Builder Eksempel:')
print()

config = (LangChainConfigBuilder()
          .with_model('gpt-4o-2024-08-06')
          .with_multihop_settings(max_hops=2, docs_per_hop=4, confidence_threshold=0.6)
          .with_search_strategy(SearchStrategy.PARAGRAPH_FIRST)
          .with_temperature(0.1)
          .with_max_tokens(2000)
          .build())

print(f'Model: {config.model}')
print(f'Max hops: {config.max_hops}')
print(f'Docs per hop: {config.max_documents_per_hop}')
print(f'Temperature: {config.temperature}')
print(f'Search strategy: {config.search_strategy.value}')
print(f'Enable multihop: {config.enable_multihop}')
print()
print('💡 Se langchain_rag_config.py for flere eksempler')
"
echo.
pause
goto menu

:help
echo.
echo ❓ HJÆLP OG DOKUMENTATION
echo =========================
echo.
echo 📖 Filer at læse:
echo   • README.md - Komplet brugervejledning
echo   • langchain_rag_config.py - Konfiguration eksempler
echo   • demo_langchain_rag.py - Demo kode
echo.
echo 🌐 Online ressourcer:
echo   • LangChain docs: https://langchain.readthedocs.io
echo   • OpenAI API: https://platform.openai.com
echo   • Weaviate docs: https://weaviate.io/docs
echo.
echo 🎯 Eksempler på spørgsmål:
echo   • "Hvad siger kildeskattelovens § 2?"
echo   • "Forskel mellem KSL § 2 og LSL § 7?"
echo   • "Sammenhæng mellem skattepligt og fradrag?"
echo   • "Hvordan påvirker ABL andre skattelove?"
echo.
echo 💡 Tips:
echo   • Brug specifikke juridiske termer
echo   • Stil sammenlignende spørgsmål for multihop
echo   • Test forskellige konfigurationer
echo   • Se reasoning paths for transparens
echo.
pause
goto menu

:exit
echo.
echo 👋 Tak for at bruge LangChain Multihop RAG!
echo.
echo 🚀 World-class juridisk AI med:
echo   ✅ Professional LangChain arkitektur
echo   ✅ GPT-4o-2024-08-06 integration
echo   ✅ Intelligent multihop reasoning
echo   ✅ Præcis juridisk dokumentsøgning
echo.
pause
exit /b 0 