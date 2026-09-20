@echo off
chcp 65001 >nul
title MO CHROME CHO BOT - Bot Data360X / vOffice
rem ============================================================================
rem   MO CHROME DE BOT DUNG CHUNG PHIEN DANG NHAP (Ban chot 20/9/2026)
rem
rem   Vi sao: vOffice (qlvb.yenbai.gov.vn) dang nhap qua SSO login.yenbai.gov.vn co
rem   MA XAC THUC (captcha). Bot KHONG duoc phep tu dang nhap, phien lai het nhanh.
rem   Cach giai: Ban lam viec tren Chrome mo bang file nay; bot mo them mot tab an
rem   trong chinh cua so do de doc danh sach viec, dung xong dong tab lai.
rem
rem   MOI NGAY chi can bam dup file nay MOT LAN (thay cho viec mo Chrome nhu thuong).
rem ============================================================================
setlocal
set PORT=9222
set DATA_DIR=%LOCALAPPDATA%\Google\Chrome\User Data

rem 1) Chrome dang chay thi co gỡ loi se bi bo qua -> phai dong Chrome truoc.
tasklist /FI "IMAGENAME eq chrome.exe" 2>nul | find /I "chrome.exe" >nul
if not errorlevel 1 (
    echo.
    echo   Chrome dang chay. De bot dung chung duoc phien, can DONG HET cua so Chrome
    echo   roi mo lai bang chinh file nay.
    echo.
    choice /C YN /M "   Dong Chrome ngay bay gio va mo lai"
    if errorlevel 2 goto :cuoi
    taskkill /IM chrome.exe /F >nul 2>&1
    timeout /t 3 >nul
)

rem 2) Mo Chrome voi cong gỡ loi CHI NGHE TRONG MAY (127.0.0.1), khong mo ra mang.
set CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe
if not exist "%CHROME%" set CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe
if not exist "%CHROME%" set CHROME=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe
if not exist "%CHROME%" (
    echo   Khong tim thay chrome.exe — bao lai cho Claude.
    goto :cuoi
)

start "" "%CHROME%" --remote-debugging-port=%PORT% --remote-allow-origins=http://127.0.0.1:%PORT% ^
  --user-data-dir="%DATA_DIR%" https://qlvb.yenbai.gov.vn/index.zul

echo.
echo   Da mo Chrome. Ban dang nhap vOffice nhu binh thuong roi cu lam viec tiep.
echo   Bot se doc danh sach viec trong chinh cua so nay (mo tab an, dung xong dong lai).
echo.
:cuoi
timeout /t 6 >nul
endlocal
