@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title BAT DAU - Bot egov1 (bam dup MOT LAN)
rem ============================================================================
rem   MOT CU BAM cho moi viec (Ban yeu cau 29/10/2026: huong dan nhieu buoc kho hieu):
rem     1. tai ban moi nhat cua bot
rem     2. quet egov1 30 ngay (lan dau tu khao sat cong), lay viec cho xu ly + nhiem vu, day len GitHub
rem     3. cai TAY de tu dong hang ngay: 05:50 lay viec + quet, Claude 07:03 gui ban tin
rem ============================================================================
set ROOT=C:\du-an
for %%d in (D E F G) do if exist %%d:\du-an\ set ROOT=%%d:\du-an
set BOT_HOME=%ROOT%\bot-profile
set BOT_DIR=%ROOT%\bot
if not exist "%BOT_DIR%" mkdir "%BOT_DIR%"

echo.
echo ============================================================
echo   BUOC 1/3: tai ban moi nhat
echo ============================================================
curl -sSL --max-time 60 -H "Accept: application/vnd.github.raw" -o "%BOT_DIR%\tai-ban-moi.bat.new" "https://api.github.com/repos/Trangsct/ccn-laocai/contents/bot/tai-ban-moi.bat?ref=main"
if exist "%BOT_DIR%\tai-ban-moi.bat.new" move /y "%BOT_DIR%\tai-ban-moi.bat.new" "%BOT_DIR%\tai-ban-moi.bat" >nul
if exist "%BOT_DIR%\tai-ban-moi.bat" call "%BOT_DIR%\tai-ban-moi.bat" bat-dau.bat

echo.
echo ============================================================
echo   BUOC 2/3: quet egov1 30 ngay (mat khoang 30-60 phut)
echo   Chrome se tu mo. DUNG dong Chrome. Neu hien trang dang nhap
echo   thi dang nhap nhu binh thuong, bot tu chay tiep.
echo ============================================================
if not defined BAT_DAU_CHAY_THU python "%BOT_DIR%\bot-data360x.py" --he-thong egov --ngay 30

echo.
echo ============================================================
echo   BUOC 3/3: cai TAY de may tu chay hang ngay
echo ============================================================
rem cai-tay.bat khong nam trong danh sach tai-ban-moi truoc ngay 29/10/2026 (vu 29/10: "is not recognized") -> tai thang
curl -sSL --max-time 60 -H "Accept: application/vnd.github.raw" -o "%BOT_DIR%\cai-tay.bat.new" "https://api.github.com/repos/Trangsct/ccn-laocai/contents/bot/cai-tay.bat?ref=main"
if exist "%BOT_DIR%\cai-tay.bat.new" move /y "%BOT_DIR%\cai-tay.bat.new" "%BOT_DIR%\cai-tay.bat" >nul
if not exist "%BOT_DIR%\cai-tay.bat" echo   KHONG tai duoc cai-tay.bat - kiem tra mang roi bam dup bat-dau.bat lai.
if not defined BAT_DAU_CHAY_THU if exist "%BOT_DIR%\cai-tay.bat" call "%BOT_DIR%\cai-tay.bat"

echo.
echo ============================================================
echo   XONG. Tu nay khong can bam gi nua. Chi can:
echo     - de may BAT qua dem (khong tat, khong dong nap laptop)
echo     - khi dien thoai bao "phien egov1 het han": bam dup
echo       dang-nhap-lan-dau.bat va dang nhap lai
echo ============================================================
if not defined KHONG_DUNG pause
