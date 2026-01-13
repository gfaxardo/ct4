@echo off
REM Script batch para ejecutar check_limbo_alerts.py
REM Uso: check_limbo_alerts.bat

cd /d "%~dp0\.."

REM Configurar encoding UTF-8
chcp 65001 >nul

REM Ejecutar script
python scripts/check_limbo_alerts.py

REM Verificar código de salida
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: El script de alertas fallo con codigo %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)

exit /b 0
