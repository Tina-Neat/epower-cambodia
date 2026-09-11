@echo off
chcp 65001 > nul
title E-Power Cambodia - កំពុងចាប់ផ្តើមប្រព័ន្ធ...

:: 1. កំណត់ Working Directory ឱ្យចំ Folder នៃ Project E-Power នេះតែមួយគត់ (ហាមលោតទៅ Project ផ្សេង)
cd /d "%~dp0"

echo ==============================================================================
echo       E-POWER CAMBODIA - ប្រព័ន្ធគ្រប់គ្រងអគ្គិសនី (Online / Offline)
echo ==============================================================================
echo.

:: 2. ពិនិត្យវត្តមាន Python
python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] មិនទាន់មាន Python នៅក្នុងកុំព្យូទ័រនេះទេ!
    echo សូមដំឡើង Python 3.10+ ជាមុនសិន។
    pause
    exit /b 1
)

:: 3. សម្អាត Port 8000 ដើម្បីធានាដំណើរការតែ Project E-Power នេះតែមួយគត់ (ហាមជាន់ Project ផ្សេង)
echo [*] កំពុងពិនិត្យ និងសម្អាត Port 8000...
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

:: 4. ចាប់ផ្តើម Server ដំណើរការក្នុង Background ដោយគ្មានផ្ទាំង CMD (Headless Mode)
echo [*] កំពុងចាប់ផ្តើម Server E-Power ក្នុង Background (Online / Offline)...
start "" pythonw run_server.py

:: 5. រង់ចាំ Server ត្រៀមរួចរាល់ (Wait 2 seconds)
echo [*] កំពុងភ្ជាប់ទៅកាន់ប្រព័ន្ធ E-Power...
ping -n 3 127.0.0.1 > nul

:: 6. អាន Local IP ពី server_info.txt
set LOCAL_IP=127.0.0.1
if exist "server_info.txt" (
    for /f "tokens=2 delims==" %%a in ('findstr "LOCAL_IP" server_info.txt 2^>nul') do set LOCAL_IP=%%a
)
set LOCAL_IP=%LOCAL_IP: =%

:: 7. បើក Browser ចូលទៅកាន់ប្រព័ន្ធ E-Power ដោយស្វ័យប្រវត្តិ
echo [*] កំពុងបើកកម្មវិធីរុករក (Opening E-Power in Browser)...
start http://localhost:8000

echo.
echo ==============================================================================
echo   [OK] ប្រព័ន្ធ E-Power Cambodia បានដំណើរការដោយជោគជ័យ!
echo   - ដំណើរការ Offline (កុំព្យូទ័រនេះ)  : http://localhost:8000
echo   - ដំណើរការ Online (ទូរសព្ទ / LAN)  : http://%LOCAL_IP%:8000
echo   - កត់ត្រាទិន្នន័យ Server ក្នុង       : server.log
echo   - បិទប្រព័ន្ធដំណើរការ               : សូមចុចបើក stop.bat
echo ==============================================================================
echo.
echo ផ្ទាំង CMD នេះនឹងបិទដោយស្វ័យប្រវត្តិក្នងរយៈពេល ២ វិនាទី...
ping -n 3 127.0.0.1 > nul
exit
