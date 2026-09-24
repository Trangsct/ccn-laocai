@echo off
chcp 65001 >nul
rem Bao tieng Viet hien dung dau trong cua so nay (khong co dong nay Python in ra dau hoi)
set PYTHONIOENCODING=utf-8
title Dang nhap Data360X lan dau
rem Dung D:\du-an neu thu muc DA CO san, khong thi C:\du-an (may co quan cam ghi vao goc o D - vu 24/9/2026)
if exist D:\du-an\ (set ROOT=D:\du-an) else (set ROOT=C:\du-an)
set BOT_HOME=%ROOT%\bot-profile
set BOT_DIR=%ROOT%\bot
echo Mo Chrome (ho so rieng cua bot) tai Data360X. Hay dang nhap nhu binh thuong (nhap captcha).
echo Khi da thay trang chu Data360X, quay lai cua so nay va bam Enter.
echo.
python "%BOT_DIR%\bot-data360x.py" --dang-nhap
echo.
pause
