@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title KHAO SAT CONG EGOV1 - Bot
rem Bot di mot vong egov1.laocai.gov.vn (Van ban den, Van ban di, mot trang chi tiet, Quan ly nhiem vu),
rem ghi HTML, anh chup, danh sach API len kho rieng tu vlncn-laocai/theo-doi/egov/soi/ de Claude hoan thien bo doc.
rem Chay mot lan sau khi dang nhap egov1 (dang-nhap-lan-dau.bat), hoac khi cong doi giao dien.
set ROOT=C:\du-an
for %%d in (D E F G) do if exist %%d:\du-an\ set ROOT=%%d:\du-an
set BOT_HOME=%ROOT%\bot-profile
set BOT_DIR=%ROOT%\bot
curl -sSL --max-time 60 -H "Accept: application/vnd.github.raw" -o "%BOT_DIR%\tai-ban-moi.bat.new" "https://api.github.com/repos/Trangsct/ccn-laocai/contents/bot/tai-ban-moi.bat?ref=main"
if exist "%BOT_DIR%\tai-ban-moi.bat.new" move /y "%BOT_DIR%\tai-ban-moi.bat.new" "%BOT_DIR%\tai-ban-moi.bat" >nul
if exist "%BOT_DIR%\tai-ban-moi.bat" call "%BOT_DIR%\tai-ban-moi.bat" khao-sat-egov.bat
echo.
echo   Chrome se mo egov1 va tu bam qua cac trang. DUNG dong Chrome, dung bam vao cua so.
echo   Neu hien trang dang nhap: dang nhap nhu binh thuong, bot tu chay tiep.
echo.
python "%BOT_DIR%\bot-data360x.py" --he-thong egov --khao-sat
echo.
echo ============================================================
echo   XONG. Bao Claude: "da khao sat egov1" de Claude doc ket qua
echo   trong kho vlncn-laocai, thu muc theo-doi/egov/soi/
echo ============================================================
if not defined KHONG_DUNG pause
