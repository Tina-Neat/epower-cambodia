@echo off
chcp 65001 > nul
title E-Power Cambodia - បើកឱ្យចូលប្រើលើ Internet ភ្លាមៗ (Instant Internet Tunnel)

cd /d "%~dp0"

echo ==============================================================================
echo       E-POWER CAMBODIA - បើកឱ្យចូលប្រើលើ INTERNET ភ្លាមៗ (PUBLIC URL)
echo ==============================================================================
echo.

:: 1. ពិនិត្យមើលថាតើ Server កំពុងដំណើរការដែរឬទេ
netstat -aon 2^>nul | findstr ":8000" | findstr "LISTENING" > nul
if errorlevel 1 (
    echo [*] Server មិនទាន់ដំណើរការទេ។ កំពុងចាប់ផ្តើម Server ក្នុង Background...
    start "" pythonw run_server.py
    ping -n 3 127.0.0.1 > nul
) else (
    echo [OK] Server E-Power កំពុងដំណើរការរួចរាល់លើ Port 8000!
)

echo.
echo ------------------------------------------------------------------------------
echo សូមជ្រើសរើសមធ្យោបាយបង្កើត Public Link លើ Internet៖
echo ------------------------------------------------------------------------------
echo   [1] ប្រើ Cloudflare Tunnel (ឥតគិតថ្លៃ ១០០%% គ្មានកំណត់ម៉ោង - ណែនាំបំផុត)
echo   [2] ប្រើ Pinggy (តាម OpenSSH មិនបាច់ដំឡើងអ្វីទាំងអស់)
echo   [3] ប្រើ Localhost.run (តាម OpenSSH មិនបាច់ដំឡើងអ្វីទាំងអស់)
echo   [4] បើកមើលសៀវភៅណែនាំ Hosting លើ Cloud 24/7 (DEPLOYMENT_GUIDE_KH.md)
echo   [5] ចាកចេញ (Exit)
echo ------------------------------------------------------------------------------
set /p opt="សូមវាយលេខជម្រើស (1-5) រួចចុច Enter: "

if "%opt%"=="1" goto cloudflare
if "%opt%"=="2" goto pinggy
if "%opt%"=="3" goto localhost_run
if "%opt%"=="4" goto open_guide
goto end

:cloudflare
echo.
echo [*] កំពុងពិនិត្យកម្មវិធី Cloudflare Tunnel...
if not exist "cloudflared.exe" (
    echo [*] កំពុងទាញយក cloudflared.exe ពី Cloudflare (ទំហំប្រមាណ 20MB ត្រឹមតែប៉ុន្មានវិនាទី)...
    curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe -o cloudflared.exe
)
if exist "cloudflared.exe" (
    echo.
    echo ==============================================================================
    echo  កំពុងបង្កើត Public HTTPS Link... សូមមើល Link ដែលមានកន្ទុយ .trycloudflare.com
    echo  ឧទាហរណ៍៖ https://xxxx.trycloudflare.com
    echo  (សូមកុំបិទផ្ទាំងនេះ ពេលកំពុងចែករំលែក Link ទៅកាន់អ្នកដទៃ)
    echo ==============================================================================
    echo.
    cloudflared.exe tunnel --url http://localhost:8000
) else (
    echo [ERROR] មិនអាចទាញយក cloudflared.exe បានឡើយ។ សូមពិនិត្យមើលការតភ្ជាប់ Internet។
    pause
)
goto end

:pinggy
echo.
echo ==============================================================================
echo  កំពុងបង្កើត Public HTTPS Link តាមរយៈ Pinggy...
echo  (សូមកុំបិទផ្ទាំងនេះ ពេលកំពុងចែករំលែក Link ទៅកាន់អ្នកដទៃ)
echo ==============================================================================
echo.
ssh -p 443 -R0:localhost:8000 qr@a.pinggy.io
goto end

:localhost_run
echo.
echo ==============================================================================
echo  កំពុងបង្កើត Public HTTPS Link តាមរយៈ Localhost.run...
echo  (សូមកុំបិទផ្ទាំងនេះ ពេលកំពុងចែករំលែក Link ទៅកាន់អ្នកដទៃ)
echo ==============================================================================
echo.
ssh -R 80:localhost:8000 localhost.run
goto end

:open_guide
start DEPLOYMENT_GUIDE_KH.md
goto end

:end
exit /b 0
