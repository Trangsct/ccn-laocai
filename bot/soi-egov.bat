@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title SOI EGOV - ghi lai cau truc trang egov1.laocai.gov.vn
rem Tu 10/10/2026 van ban di, den chuyen sang EGOV (egov1.laocai.gov.vn), thay Data360X va vOffice.
rem File nay chay MOT LAN: mo Chrome cua bot, Ban dang nhap EGOV, bot tu di qua menu Van ban den/di,
rem roi Ban tu bam them 10 phut; bot chi DOC, ghi lai cau truc trang va day len kho rieng tu vlncn-laocai
rem (theo-doi/egov/soi/) de Claude viet bot EGOV that. Ma phien, mat khau, cookie da che truoc khi day.
set ROOT=C:\du-an
for %%d in (D E F G) do if exist %%d:\du-an\ set ROOT=%%d:\du-an
set BOT_DIR=%ROOT%\bot
if not exist "%BOT_DIR%" mkdir "%BOT_DIR%"
set API=https://api.github.com/repos/Trangsct/ccn-laocai/contents

rem Tai ban moi nhat cua 2 script (SOI_NGUON = thu muc kho ma: chi dung khi chay thu tren may ao)
for %%F in (egov_soi.py bot-data360x.py) do call :tai "%%F"

if not exist "%BOT_DIR%\egov_soi.py" (
    echo KHONG TAI DUOC egov_soi.py - kiem tra mang roi chay lai.
    goto :het
)
python --version >nul 2>&1
if errorlevel 1 (
    echo May chua co Python. Chay cai-tay.bat hoac cai-dat.bat truoc.
    goto :het
)

echo.
echo ============================================================
echo   SOI EGOV: Chrome se mo trang egov1.laocai.gov.vn
echo   - Chua dang nhap thi Ban dang nhap nhu thuong (bot cho 20 phut)
echo   - Bot tu di qua menu khoang 2-3 phut, roi den luot Ban bam 10 phut
echo   - KHONG dong cua so Chrome va cua so den nay cho toi khi thay XONG
echo ============================================================
echo.
python "%BOT_DIR%\egov_soi.py" %SOI_THAM_SO%
set MA=%errorlevel%
echo.
echo ============================================================
if "%MA%"=="0" (
    echo   XONG. Ket qua da day len kho vlncn-laocai, thu muc theo-doi/egov/soi/
    echo   Bao Claude: "da soi EGOV xong" de Claude viet bot EGOV.
) else (
    echo   CO LOI ^(ma %MA%^). Chup man hinh cua so nay gui Claude.
)
echo ============================================================
:het
echo.
if not defined SOI_KHONG_DUNG pause
goto :eof

rem :tai <ten file> - tai tu GitHub (hoac chep tu SOI_NGUON khi chay thu)
:tai
if defined SOI_NGUON (
    copy /y "%SOI_NGUON%\scripts\%~1" "%BOT_DIR%\%~1" >nul
    goto :eof
)
curl -sSL --max-time 60 -H "Accept: application/vnd.github.raw" -o "%BOT_DIR%\%~1.new" "%API%/scripts/%~1?ref=main"
if exist "%BOT_DIR%\%~1.new" (
    for %%S in ("%BOT_DIR%\%~1.new") do if %%~zS GTR 1000 move /y "%BOT_DIR%\%~1.new" "%BOT_DIR%\%~1" >nul
    if exist "%BOT_DIR%\%~1.new" del /q "%BOT_DIR%\%~1.new"
)
goto :eof
