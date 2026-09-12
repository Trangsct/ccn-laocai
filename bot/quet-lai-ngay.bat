@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title QUET LAI N NGAY - Bot Data360X
rem Quet lai mot khoang ngay tu chon. Dung khi du an nghi vai hom, cap-nhat-ngay.bat (chi 3 ngay) bo sot.
rem An toan: van ban da xu ly roi thi bot tu bo qua, khong tai trung, khong ghi trung.
if exist D:\ (set ROOT=D:\du-an) else (set ROOT=C:\du-an)
set BOT_DIR=%ROOT%\bot
rem Tu cap nhat: tai ban moi cua moi file (tru file dang chay) truoc khi lam viec
curl -sSL --max-time 60 -H "Accept: application/vnd.github.raw" -o "%BOT_DIR%\tai-ban-moi.bat.new" "https://api.github.com/repos/Trangsct/ccn-laocai/contents/bot/tai-ban-moi.bat?ref=main"
if exist "%BOT_DIR%\tai-ban-moi.bat.new" move /y "%BOT_DIR%\tai-ban-moi.bat.new" "%BOT_DIR%\tai-ban-moi.bat" >nul
if exist "%BOT_DIR%\tai-ban-moi.bat" call "%BOT_DIR%\tai-ban-moi.bat" quet-lai-ngay.bat

echo.
echo ============================================================
echo   QUET LAI BAO NHIEU NGAY GAN NHAT?
echo ============================================================
echo   - Nghi vai hom       : 10
echo   - Nghi vai tuan      : 30   (nen dung cho chac)
echo   - Bo sung giay phep cu: 120
echo.
set NGAY=
set /p NGAY=  So ngay (Enter de lay 30):
if "%NGAY%"=="" set NGAY=30

echo.
echo   Dang quet %NGAY% ngay gan nhat, vui long cho...
echo   (van ban da xu ly se tu bo qua, chi tai ve cai moi)
echo.
python "%BOT_DIR%\bot-data360x.py" --ngay %NGAY%

echo.
echo ============================================================
echo   XONG. Van ban moi da day len GitHub.
echo   Gemini va Mistral se doc noi dung trong vai phut, sau do
echo   du lieu len trang: https://vlncn-laocai.vercel.app
echo ============================================================
echo.
pause
