@echo off
chcp 65001 >nul
title CAI RUNNER GITHUB - Bot Data360X
rem ============================================================================
rem   CAI RUNNER - de GitHub ra lenh cho may nay chay bot (Ban chot 04/9/2026)
rem   CHI CAN BAM DUP VAO FILE NAY. Khong can quyen Administrator.
rem   Moi viec nang do cai-runner.ps1 lam; file .bat nay chi tai ban moi nhat
rem   cua no ve roi goi, de may luon chay dung ban tren GitHub.
rem ============================================================================
if exist D:\du-an\ (set ROOT=D:\du-an) else (set ROOT=C:\du-an)
set BOT_DIR=%ROOT%\bot
if not exist "%BOT_DIR%" mkdir "%BOT_DIR%"

echo.
echo   Dang tai ban moi nhat cua bo cai...
rem Lay qua api.github.com chu KHONG qua raw.githubusercontent.com: raw di qua bo nho dem CDN,
rem sua xong vai phut sau may van tai ve ban cu (vu 12/9/2026 chay hai lan deu ra ban cu).
curl -sSL --max-time 120 -H "Accept: application/vnd.github.raw" -H "Cache-Control: no-cache" ^
  -o "%BOT_DIR%\cai-runner.ps1.new" ^
  "https://api.github.com/repos/Trangsct/ccn-laocai/contents/bot/cai-runner.ps1?ref=main"
if exist "%BOT_DIR%\cai-runner.ps1.new" (
    for %%S in ("%BOT_DIR%\cai-runner.ps1.new") do if %%~zS GTR 1000 move /y "%BOT_DIR%\cai-runner.ps1.new" "%BOT_DIR%\cai-runner.ps1" >nul
    if exist "%BOT_DIR%\cai-runner.ps1.new" del /q "%BOT_DIR%\cai-runner.ps1.new"
)
if not exist "%BOT_DIR%\cai-runner.ps1" (
    echo.
    echo   KHONG tai duoc bo cai. Kiem tra mang roi bam dup lai file nay.
    echo.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%BOT_DIR%\cai-runner.ps1"
echo.
pause
