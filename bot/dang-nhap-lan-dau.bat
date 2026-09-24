@echo off
chcp 65001 >nul
rem Bao tieng Viet hien dung dau trong cua so nay (khong co dong nay Python in ra dau hoi)
set PYTHONIOENCODING=utf-8
title Dang nhap Data360X lan dau
rem Dung thu muc du-an DA CO san tren o D/E/F/G (tao truoc khi cai), khong thi C:\du-an (may co quan: o D cam ghi, o D be - vu 24/9/2026)
set ROOT=C:\du-an
for %%d in (D E F G) do if exist %%d:\du-an\ set ROOT=%%d:\du-an
set BOT_HOME=%ROOT%\bot-profile
set BOT_DIR=%ROOT%\bot
echo Mo Chrome (ho so rieng cua bot) tai Data360X. Hay dang nhap nhu binh thuong (nhap captcha).
echo Khi da thay trang chu Data360X, quay lai cua so nay va bam Enter.
echo.
python "%BOT_DIR%\bot-data360x.py" --dang-nhap
echo.
pause
