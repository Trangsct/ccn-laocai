@echo off
chcp 65001 >nul
rem Bao tieng Viet hien dung dau trong cua so nay (khong co dong nay Python in ra dau hoi)
set PYTHONIOENCODING=utf-8
title Chay thu Bot Data360X
rem Tu chon o D neu co, khong thi o C
if exist D:\ (set ROOT=D:\du-an) else (set ROOT=C:\du-an)
set BOT_HOME=%ROOT%\bot-profile
set BOT_DIR=%ROOT%\bot
rem Tu cap nhat: tai ban moi cua moi file (tru file dang chay) truoc khi lam viec
curl -sSL --max-time 60 -H "Accept: application/vnd.github.raw" -o "%BOT_DIR%\tai-ban-moi.bat.new" "https://api.github.com/repos/Trangsct/ccn-laocai/contents/bot/tai-ban-moi.bat?ref=main"
if exist "%BOT_DIR%\tai-ban-moi.bat.new" move /y "%BOT_DIR%\tai-ban-moi.bat.new" "%BOT_DIR%\tai-ban-moi.bat" >nul
if exist "%BOT_DIR%\tai-ban-moi.bat" call "%BOT_DIR%\tai-ban-moi.bat" chay-thu.bat
set RAW=https://raw.githubusercontent.com/Trangsct/ccn-laocai/main
echo Tai ban script moi nhat...
echo.
echo Chay bot mot lan (che do SOI: chi doc va luu vao logs\soi, KHONG day len GitHub).
echo Muon chay that (co day len GitHub) thi go:  python "%BOT_DIR%\bot-data360x.py"
echo.
python "%BOT_DIR%\bot-data360x.py" --soi
echo.
echo Ket qua chi tiet: %BOT_HOME%\logs\  (file .log theo ngay, thu muc soi\ chua HTML, anh, PDF)
echo Hay nen thu muc logs\soi gui cho Claude Code de hoan thien selector.
pause
