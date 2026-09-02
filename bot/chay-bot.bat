@echo off
chcp 65001 >nul
rem File nay do Task Scheduler goi. Tham so: chinh | giu-phien
rem Moi lan chay tu tai ban script moi nhat tu GitHub (bot tu cap nhat).
rem Tu chon o D neu co, khong thi o C
if exist D:\ (set ROOT=D:\du-an) else (set ROOT=C:\du-an)
set BOT_HOME=%ROOT%\bot-profile
set BOT_DIR=%ROOT%\bot
set RAW=https://raw.githubusercontent.com/Trangsct/ccn-laocai/main
curl -sSL --max-time 60 -o "%BOT_DIR%\bot-data360x.py.new" "%RAW%/scripts/bot-data360x.py" && move /y "%BOT_DIR%\bot-data360x.py.new" "%BOT_DIR%\bot-data360x.py" >nul
if "%~1"=="giu-phien" (
    python "%BOT_DIR%\bot-data360x.py" --giu-phien
) else (
    python "%BOT_DIR%\bot-data360x.py"
)
