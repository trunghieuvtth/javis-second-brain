@echo off
chcp 65001 >nul
title Javis Second Brain - 1-Click Installer for Windows
cls

echo ==================================================================
echo    CÀI ĐẶT & KÍCH HOẠT JAVIS SECOND BRAIN CHO WINDOWS (1-CLICK)
echo ==================================================================
echo.

cd /d "%~dp0"

:: 1. Kiểm tra Python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [!] Lỗi: Máy tính chưa cài đặt Python hoặc chưa tick chọn "Add python.exe to PATH".
    echo Vui lòng tải và cài đặt Python từ: https://www.python.org/downloads/
    echo Nhớ tick chọn [x] Add Python to PATH khi cài đặt.
    echo.
    pause
    exit /b 1
)

:: 2. Khởi tạo môi trường ảo Python venv
if not exist "venv" (
    echo [*] Đang khởi tạo môi trường ảo Python venv...
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo [!] Lỗi khi tạo môi trường ảo venv.
        pause
        exit /b 1
    )
)

:: 3. Cài đặt các gói thư viện phụ thuộc
echo [*] Đang kiểm tra và cài đặt các thư viện cần thiết...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
if %ERRORLEVEL% NEQ 0 (
    echo [!] Lỗi khi cài đặt thư viện. Vui lòng kiểm tra kết nối mạng.
    pause
    exit /b 1
)

:: 4. Khởi tạo các thư mục dữ liệu
if not exist "data\personal_brain\files" mkdir "data\personal_brain\files"
if not exist "data\drafts" mkdir "data\drafts"

:: 5. Tạo file VBScript khởi động ngầm không hiện cửa sổ đen (Background Runner)
echo Set WshShell = CreateObject("WScript.Shell") > "run_background.vbs"
echo WshShell.Run "cmd /c ""%~dp0venv\Scripts\python.exe"" ""%~dp0app.py""", 0, False >> "run_background.vbs"

:: 6. Thiết lập Tự khởi động cùng Windows (Startup Folder)
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
copy /y "run_background.vbs" "%STARTUP_DIR%\JavisSecondBrain_Startup.vbs" >nul 2>nul

:: 7. Kích hoạt chạy ngầm ngay lập tức
echo [*] Đang kích hoạt dịch vụ chạy ngầm Javis Second Brain...
wscript.exe "%~dp0run_background.vbs"

:: Chờ 2 giây để server khởi động hoàn tất
timeout /t 2 /nobreak >nul

:: 8. Tự động mở trình duyệt web truy cập ngay vào hệ thống
echo [*] Đang mở trình duyệt vào Kho Tri Thức...
start http://localhost:8090

echo.
echo ==================================================================
echo  [OK] CÀI ĐẶT & KÍCH HOẠT THÀNH CÔNG JAVIS SECOND BRAIN TRÊN WINDOWS!
echo.
echo  • Địa chỉ truy cập: http://localhost:8090
echo  • Dịch vụ đã được cấu hình TỰ ĐỘNG CHẠY NGẦM khi bật máy tính.
echo  • Khi cần dừng dịch vụ: Chạy file "stop_service.bat"
echo ==================================================================
echo.
echo Cửa sổ này sẽ tự đóng sau 5 giây...
timeout /t 5 >nul
exit /b 0
