@echo off
chcp 65001 > nul
title E-Power Cambodia - បិទហើយបើកប្រព័ន្ធឡើងវិញ (Restart Server)

cd /d "%~dp0"

echo ==============================================================================
echo       E-POWER CAMBODIA - បិទហើយបើកប្រព័ន្ធឡើងវិញ (Restart Server)
echo ==============================================================================
echo.

echo [*] កំពុងបិទដំណើរការចាស់...
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
if exist "server.pid" del /f /q "server.pid" >nul 2>&1

ping -n 2 127.0.0.1 > nul

echo [*] កំពុងចាប់ផ្តើម Server ឡើងវិញ...
call run.bat
