@echo off
chcp 65001 >nul
title CAI TAY - canh tay cua Claude tren may nay
rem ============================================================================
rem   CAI TAY (Ban chot 30/9/2026): bam dup MOT LAN. Khong can quyen Administrator.
rem   File nay chi tai ban moi nhat cua cai-tay.ps1 tu GitHub roi goi; moi viec do ps1 lam.
rem   Bo cai nay da duoc chay thu tren may ao Windows (workflow thu-bo-cai-windows.yml) truoc khi merge.
rem ============================================================================
set ROOT=C:\du-an
for %%d in (D E F G) do if exist %%d:\du-an\ set ROOT=%%d:\du-an
set BOT_DIR=%ROOT%\bot
if not exist "%BOT_DIR%" mkdir "%BOT_DIR%"

echo.
echo   Dang tai ban moi nhat cua bo cai...
curl -sSL --max-time 120 -H "Accept: application/vnd.github.raw" -H "Cache-Control: no-cache" ^
  -o "%BOT_DIR%\cai-tay.ps1.new" ^
  "https://api.github.com/repos/Trangsct/ccn-laocai/contents/bot/cai-tay.ps1?ref=main"
if exist "%BOT_DIR%\cai-tay.ps1.new" (
    for %%S in ("%BOT_DIR%\cai-tay.ps1.new") do if %%~zS GTR 1000 move /y "%BOT_DIR%\cai-tay.ps1.new" "%BOT_DIR%\cai-tay.ps1" >nul
    if exist "%BOT_DIR%\cai-tay.ps1.new" del /q "%BOT_DIR%\cai-tay.ps1.new"
)
if not exist "%BOT_DIR%\cai-tay.ps1" (
    echo   KHONG tai duoc bo cai. Kiem tra mang roi bam dup lai file nay.
    pause
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%BOT_DIR%\cai-tay.ps1"
