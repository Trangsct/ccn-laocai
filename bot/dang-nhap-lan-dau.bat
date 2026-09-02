@echo off
chcp 65001 >nul
title Dang nhap Data360X lan dau
rem Tu chon o D neu co, khong thi o C
if exist D:\ (set ROOT=D:\du-an) else (set ROOT=C:\du-an)
set BOT_HOME=%ROOT%\bot-profile
set BOT_DIR=%ROOT%\bot
echo Mo Chrome (ho so rieng cua bot) tai Data360X. Hay dang nhap nhu binh thuong (nhap captcha).
echo Khi da thay trang chu Data360X, quay lai cua so nay va bam Enter.
echo.
python "%BOT_DIR%\bot-data360x.py" --dang-nhap
echo.
pause
