@echo off
chcp 65001 >nul
title Chay thu Bot Data360X
rem Tu chon o D neu co, khong thi o C
if exist D:\ (set ROOT=D:\du-an) else (set ROOT=C:\du-an)
set BOT_HOME=%ROOT%\bot-profile
set BOT_DIR=%ROOT%\bot
set RAW=https://raw.githubusercontent.com/Trangsct/ccn-laocai/main
echo Tai ban script moi nhat...
curl -sSL --max-time 60 -H "Accept: application/vnd.github.raw" -o "%BOT_DIR%\bot-data360x.py.new" "https://api.github.com/repos/Trangsct/ccn-laocai/contents/scripts/bot-data360x.py?ref=main" && move /y "%BOT_DIR%\bot-data360x.py.new" "%BOT_DIR%\bot-data360x.py" >nul
echo.
echo Chay bot mot lan (che do SOI: chi doc va luu vao logs\soi, KHONG day len GitHub).
echo Muon chay that (co day len GitHub) thi go:  python "%BOT_DIR%\bot-data360x.py"
echo.
python "%BOT_DIR%\bot-data360x.py" --soi
echo.
echo Ket qua chi tiet: %BOT_HOME%\logs\  (file .log theo ngay, thu muc soi\ chua HTML, anh, PDF)
echo Hay nen thu muc logs\soi gui cho Claude Code de hoan thien selector.
pause
