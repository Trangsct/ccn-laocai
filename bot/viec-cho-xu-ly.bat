@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title VIEC CHO XU LY TREN EGOV1 - Bot
rem Lay cac van ban den co trang thai Chua / Cho / Dang xu ly tren egov1 (viec Lanh dao giao, thay vOffice),
rem tai toan van + dinh kem, day len kho rieng tu vlncn-laocai/theo-doi/viec-cho-xu-ly/<ngay>/ de Claude soan du thao.
set ROOT=C:\du-an
for %%d in (D E F G) do if exist %%d:\du-an\ set ROOT=%%d:\du-an
set BOT_HOME=%ROOT%\bot-profile
set BOT_DIR=%ROOT%\bot
curl -sSL --max-time 60 -H "Accept: application/vnd.github.raw" -o "%BOT_DIR%\tai-ban-moi.bat.new" "https://api.github.com/repos/Trangsct/ccn-laocai/contents/bot/tai-ban-moi.bat?ref=main"
if exist "%BOT_DIR%\tai-ban-moi.bat.new" move /y "%BOT_DIR%\tai-ban-moi.bat.new" "%BOT_DIR%\tai-ban-moi.bat" >nul
if exist "%BOT_DIR%\tai-ban-moi.bat" call "%BOT_DIR%\tai-ban-moi.bat" viec-cho-xu-ly.bat
echo.
echo   Dang lay viec cho xu ly tren egov1 (30 ngay gan nhat), vui long cho...
echo.
python "%BOT_DIR%\bot-data360x.py" --he-thong egov --viec --ngay 30
echo.
echo ============================================================
echo   XONG. Ket qua: kho vlncn-laocai, theo-doi/viec-cho-xu-ly/
echo ============================================================
if not defined KHONG_DUNG pause
