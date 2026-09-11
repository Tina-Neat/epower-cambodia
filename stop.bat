@echo off
chcp 65001 > nul
title E-Power Cambodia - បិទប្រព័ន្ធដំណើរការ

cd /d "%~dp0"

echo ==============================================================================
echo       E-POWER CAMBODIA - បិទប្រព័ន្ធដំណើរការ (Stop Server)
echo ==============================================================================
echo.
echo កំពុងបិទប្រព័ន្ធ E-Power នៅលើ Port 8000...

set FOUND=0
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
    set FOUND=1
)

if "%FOUND%"=="1" (
    echo [OK] ប្រព័ន្ធ E-Power Cambodia ត្រូវបានបិទដោយជោគជ័យ!
) else (
    echo [INFO] ពុំមានប្រព័ន្ធ E-Power ណាមួយកំពុងដំណើរការនៅលើ Port 8000 ឡើយ។
)

if exist "server.pid" del /f /q "server.pid" >nul 2>&1

echo.
echo ផ្ទាំងនេះនឹងបិទក្នុងរយៈពេល ២ វិនាទី...
ping -n 3 127.0.0.1 > nul
exit
