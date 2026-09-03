@echo off
chcp 65001 >nul
rem Bao tieng Viet hien dung dau trong cua so nay (khong co dong nay Python in ra dau hoi)
set PYTHONIOENCODING=utf-8
title QUET BU 120 NGAY - Bot Data360X
rem Chay bu cac van ban cu (mac dinh bot chi quet 3 ngay gan nhat).
rem Dung khi can bo sung giay phep da ky truoc do, vi du GP van chuyen HHNH thang 6-7/2026.
if exist D:\ (set ROOT=D:\du-an) else (set ROOT=C:\du-an)
set BOT_DIR=%ROOT%\bot

echo.
echo ============================================================
echo    QUET BU 120 NGAY - lay lai van ban cu tren Data360X
echo ============================================================
echo.
echo  Bot se quet van ban di - den cua Phong Cong nghiep trong
echo  120 ngay gan nhat, tai PDF cac giay phep chua co va day len GitHub.
echo  Van ban da xu ly truoc do se tu bo qua, khong tai lai.
echo.
echo  Viec nay lau hon binh thuong: khoang 10 den 25 phut.
echo  Ban co the thu nho cua so, dung tat.
echo.
pause

echo [1/2] Tai ban script moi nhat...
curl -sSL --max-time 60 -H "Accept: application/vnd.github.raw" -o "%BOT_DIR%\bot-data360x.py.new" "https://api.github.com/repos/Trangsct/ccn-laocai/contents/scripts/bot-data360x.py?ref=main"
if exist "%BOT_DIR%\bot-data360x.py.new" move /y "%BOT_DIR%\bot-data360x.py.new" "%BOT_DIR%\bot-data360x.py" >nul

echo [2/2] Dang quet 120 ngay, vui long cho...
echo.
python "%BOT_DIR%\bot-data360x.py" --ngay 120
set KETQUA=%ERRORLEVEL%

echo.
echo ============================================================
if "%KETQUA%"=="0" echo    XONG. Cac van ban cu da day len GitHub.
if "%KETQUA%"=="0" echo    Gemini se doc noi dung, sau do du lieu len trang:
if "%KETQUA%"=="0" echo    https://vlncn-laocai.vercel.app
if not "%KETQUA%"=="0" echo    CHUA XONG - ma loi %KETQUA%. Ban chup man hinh nay gui Claude.
echo ============================================================
echo.
pause
