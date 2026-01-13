@echo off
REM Script batch para ejecutar reconcile_cabinet_leads_pipeline
REM Uso: run_reconcile_cabinet_leads.bat [--days-back N] [--limit N] [--only-limbo] [--dry-run]

cd /d "%~dp0\.."

REM Configurar encoding UTF-8
chcp 65001 >nul

REM Ejecutar job
python -m jobs.reconcile_cabinet_leads_pipeline %*

REM Verificar código de salida
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: El job fallo con codigo %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)

echo Job completado exitosamente
exit /b 0
