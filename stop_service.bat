@echo off
chcp 65001 >nul
title Stop Javis Second Brain
cls

echo [*] Đang dừng dịch vụ Javis Second Brain...
taskkill /f /im python.exe /fi "WINDOWTITLE eq Javis*" >nul 2>nul
powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*app.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>nul

echo [OK] Đã dừng dịch vụ thành công!
timeout /t 2 >nul
exit /b 0
