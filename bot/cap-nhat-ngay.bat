@echo off
chcp 65001 >nul
rem Bao tieng Viet hien dung dau trong cua so nay (khong co dong nay Python in ra dau hoi)
set PYTHONIOENCODING=utf-8
title CAP NHAT NGAY - Bot Data360X
rem Bam dup vao file nay khi muon cap nhat ngay, khong cho den 18h.
rem Bot dung lai phien dang nhap san co, quet van ban moi, tai PDF va day len GitHub.
if exist D:\ (set ROOT=D:\du-an) else (set ROOT=C:\du-an)
set BOT_DIR=%ROOT%\bot

echo.
echo ============================================================
echo    CAP NHAT NGAY - Bot doc van ban tren Data360X
echo ============================================================
echo.
echo  Bot se lam 3 viec:
echo    1. Mo Chrome bang phien da dang nhap cua Ban
echo    2. Quet van ban di - den moi cua Phong Cong nghiep
echo    3. Tai PDF va day len GitHub de Gemini doc tiep
echo.
echo  Neu phien dang nhap het han, bot se hien cua so de Ban dang nhap lai.
echo  Ban co the thu nho cua so nay, dung tat.
echo.

echo [1/2] Tai ban script moi nhat...
curl -sSL --max-time 60 -H "Accept: application/vnd.github.raw" -o "%BOT_DIR%\bot-data360x.py.new" "https://api.github.com/repos/Trangsct/ccn-laocai/contents/scripts/bot-data360x.py?ref=main"
if exist "%BOT_DIR%\bot-data360x.py.new" move /y "%BOT_DIR%\bot-data360x.py.new" "%BOT_DIR%\bot-data360x.py" >nul

echo [2/2] Dang quet van ban, vui long cho...
echo.
python "%BOT_DIR%\bot-data360x.py"
set KETQUA=%ERRORLEVEL%

echo.
echo ============================================================
if "%KETQUA%"=="0" echo    XONG. Van ban moi da day len GitHub.
if "%KETQUA%"=="0" echo    Gemini se doc noi dung trong vai phut, sau do du lieu len trang:
if "%KETQUA%"=="0" echo    https://vlncn-laocai.vercel.app
if not "%KETQUA%"=="0" echo    CHUA XONG - ma loi %KETQUA%. Ban chup man hinh nay gui Claude.
echo ============================================================
echo.
pause
