@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
rem Dua phien dang nhap Data360X len GitHub de GitHub tu quet hang ngay, khong phu thuoc may nay nua.
if exist D:\ (set ROOT=D:\du-an) else (set ROOT=C:\du-an)
set BOT_DIR=%ROOT%\bot
rem Tu cap nhat: tai ban moi cua moi file (tru file dang chay) truoc khi lam viec
curl -sSL --max-time 60 -H "Accept: application/vnd.github.raw" -o "%BOT_DIR%\tai-ban-moi.bat.new" "https://api.github.com/repos/Trangsct/ccn-laocai/contents/bot/tai-ban-moi.bat?ref=main"
if exist "%BOT_DIR%\tai-ban-moi.bat.new" move /y "%BOT_DIR%\tai-ban-moi.bat.new" "%BOT_DIR%\tai-ban-moi.bat" >nul
if exist "%BOT_DIR%\tai-ban-moi.bat" call "%BOT_DIR%\tai-ban-moi.bat" xuat-phien.bat
python -m pip install --quiet pynacl
echo.
echo   Cua so Chrome se mo ra.
echo   - Neu hien trang dang nhap: dang nhap nhu thuong le (tu nhap captcha), thay trang chu Data360X
echo     thi quay lai cua so nay va bam Enter.
echo   - Neu da dang nhap san: khong phai lam gi, cho vai giay.
echo.
python "%BOT_DIR%\bot-data360x.py" --xuat-phien
echo.
pause
