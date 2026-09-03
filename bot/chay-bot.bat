@echo off
chcp 65001 >nul
rem Bao tieng Viet hien dung dau trong cua so nay (khong co dong nay Python in ra dau hoi)
set PYTHONIOENCODING=utf-8
rem File nay do Task Scheduler goi. Tham so: chinh | giu-phien
rem Moi lan chay tu tai ban script moi nhat tu GitHub (bot tu cap nhat).
rem Tu chon o D neu co, khong thi o C
if exist D:\ (set ROOT=D:\du-an) else (set ROOT=C:\du-an)
set BOT_HOME=%ROOT%\bot-profile
set BOT_DIR=%ROOT%\bot
rem Tu cap nhat: tai ban moi cua moi file (tru file dang chay) truoc khi lam viec
curl -sSL --max-time 60 -H "Accept: application/vnd.github.raw" -o "%BOT_DIR%\tai-ban-moi.bat.new" "https://api.github.com/repos/Trangsct/ccn-laocai/contents/bot/tai-ban-moi.bat?ref=main"
if exist "%BOT_DIR%\tai-ban-moi.bat.new" move /y "%BOT_DIR%\tai-ban-moi.bat.new" "%BOT_DIR%\tai-ban-moi.bat" >nul
if exist "%BOT_DIR%\tai-ban-moi.bat" call "%BOT_DIR%\tai-ban-moi.bat" chay-bot.bat
set RAW=https://raw.githubusercontent.com/Trangsct/ccn-laocai/main
if "%~1"=="giu-phien" (
    python "%BOT_DIR%\bot-data360x.py" --giu-phien
) else (
    python "%BOT_DIR%\bot-data360x.py"
)
