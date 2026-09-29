@echo off
chcp 65001 >nul
rem Bao tieng Viet hien dung dau trong cua so nay (khong co dong nay Python in ra dau hoi)
set PYTHONIOENCODING=utf-8
title CAI BOT DATA360X TREN MAY NAY - mot cu bam
rem ============================================================================
rem   CAI TRON BO BOT DATA360X TREN MAY MOI (laptop ca nhan) - Ban yeu cau 29/9/2026
rem
rem   Vi sao co file nay: bot chi tung chay tren may ban co quan (DESKTOP-0C3HIUP), may do
rem   im tu 18/9/2026 nen 11 ngay khong co ban tin. Tren laptop truoc day phai lam 4 buoc
rem   rieng le (cai-dat, dang-nhap-lan-dau, cai-runner, quet). File nay goi lan luot ca 4,
rem   BAM DUP MOT LAN la xong. Khong can quyen Administrator. Chay lai luc nao cung an toan.
rem
rem   Thu tu:
rem     1. tai ban moi nhat cua bot va moi file .bat (qua api.github.com, khong dinh bo dem CDN)
rem     2. cai-dat.bat            : Python, Playwright, Chromium; hoi token GitHub; kiem tra token
rem     3. dang-nhap-lan-dau.bat  : mo Chrome ho so rieng cua bot, Ban dang nhap Data360X (captcha)
rem     4. cai-runner.bat         : dang ky may nay voi GitHub (nhan windows,laocai,laptop),
rem                                 dat lich runner tu bat moi khi dang nhap Windows,
rem                                 cuoi cung hoi quet 30 ngay ngay - bam Enter la quet.
rem ============================================================================
set ROOT=C:\du-an
for %%d in (D E F G) do if exist %%d:\du-an\ set ROOT=%%d:\du-an
set BOT_DIR=%ROOT%\bot
set BOT_HOME=%ROOT%\bot-profile
rem Cac file con goi khong dung lai cho "Press any key" giua chung
set KHONG_DUNG=1
if not exist "%BOT_DIR%" mkdir "%BOT_DIR%"
if not exist "%BOT_HOME%" mkdir "%BOT_HOME%"

echo.
echo ================================================================
echo   CAI BOT DATA360X TREN MAY NAY (mot cu bam)
echo   Thu muc: %ROOT%
echo ================================================================
echo.
echo [1/4] Tai ban moi nhat cua bot va cac file .bat...
curl -sSL --max-time 120 -H "Accept: application/vnd.github.raw" -H "Cache-Control: no-cache" ^
  -o "%BOT_DIR%\tai-ban-moi.bat.new" ^
  "https://api.github.com/repos/Trangsct/ccn-laocai/contents/bot/tai-ban-moi.bat?ref=main"
if exist "%BOT_DIR%\tai-ban-moi.bat.new" (
    for %%S in ("%BOT_DIR%\tai-ban-moi.bat.new") do if %%~zS GTR 100 move /y "%BOT_DIR%\tai-ban-moi.bat.new" "%BOT_DIR%\tai-ban-moi.bat" >nul
    if exist "%BOT_DIR%\tai-ban-moi.bat.new" del /q "%BOT_DIR%\tai-ban-moi.bat.new"
)
if not exist "%BOT_DIR%\tai-ban-moi.bat" (
    echo   KHONG tai duoc tu GitHub. Kiem tra mang ^(wifi^) roi bam dup lai file nay.
    pause
    exit /b 1
)
call "%BOT_DIR%\tai-ban-moi.bat" cai-laptop.bat
if not exist "%BOT_DIR%\cai-dat.bat" (
    echo   Tai thieu file cai-dat.bat. Kiem tra mang roi bam dup lai file nay.
    pause
    exit /b 1
)
echo   Da tai xong.

echo.
echo [2/4] Cai Python, Playwright, Chromium va nhap token GitHub...
echo   ^(Token: chuoi github_pat_..., can quyen Contents Read/Write tren 4 kho;
echo    them Administration Read/Write tren vlncn-laocai thi buoc 4 khong phai dan ma tay.^)
echo.
call "%BOT_DIR%\cai-dat.bat"
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo   Python vua duoc cai, cua so nay chua nhan. DONG cua so nay roi bam dup lai cai-laptop.bat.
    pause
    exit /b 0
)
if not exist "%BOT_HOME%\config.json" (
    echo.
    echo   Chua co token trong %BOT_HOME%\config.json. Bam dup lai cai-laptop.bat va dan token.
    pause
    exit /b 1
)

echo.
echo [3/4] Dang nhap Data360X lan dau tren may nay...
echo   Chrome ^(ho so rieng cua bot^) se mo. Dang nhap nhu thuong le, nhap captcha.
echo   Thay trang chu Data360X thi quay lai cua so nay va bam Enter.
echo.
call "%BOT_DIR%\dang-nhap-lan-dau.bat"

echo.
echo [4/4] Dang ky may nay voi GitHub de nhan lenh quet...
echo.
call "%BOT_DIR%\cai-runner.bat"

echo.
echo ================================================================
echo   XONG. Tu gio:
echo   - Moi gio 07-17h ^(T2-T7^) may tu mo Data360X thu nho de giu phien.
echo   - 11h30 thu Tu may tu quet 30 ngay; muon quet ngay thi vao
echo     https://github.com/Trangsct/vlncn-laocai/actions ^> "Quet Data360X (may co quan)" ^> Run workflow.
echo   - Xem may con noi GitHub khong: https://github.com/Trangsct/vlncn-laocai/settings/actions/runners
echo   - Bot bao "phien het han" thi bam dup dang-nhap-lan-dau.bat trong %BOT_DIR%
echo ================================================================
echo.
pause
