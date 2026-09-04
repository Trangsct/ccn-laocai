@echo off
chcp 65001 >nul
rem ============================================================================
rem   CAI RUNNER - de GitHub ra lenh cho may nay chay bot (Ban chot 04/9/2026)
rem   BAM CHUOT PHAI VAO FILE NAY -> "Run as administrator"
rem ============================================================================
net session >nul 2>&1
if errorlevel 1 (
    echo.
    echo   CHUA CHAY BANG QUYEN QUAN TRI.
    echo   Dong cua so nay, bam CHUOT PHAI vao cai-runner.bat roi chon "Run as administrator".
    echo.
    pause
    exit /b 1
)
if exist D:\ (set ROOT=D:\du-an) else (set ROOT=C:\du-an)
set RUNNER_DIR=%ROOT%\actions-runner
set REPO=https://github.com/Trangsct/vlncn-laocai

echo.
echo ============================================================
echo   CAI RUNNER CHO MAY NAY
echo ============================================================
echo.
echo   Buoc 1: mo trang sau trong trinh duyet (bam Ctrl roi bam vao duong dan):
echo     %REPO%/settings/actions/runners/new?arch=x64^&os=win
echo.
echo   Buoc 2: tren trang do, keo xuong muc "Configure", tim dong bat dau bang
echo     --token  roi COPY chuoi phia sau (dang AXXXX...). Chuoi nay het han sau 1 gio.
echo.
set /p TOKEN=  Dan chuoi token vao day roi bam Enter:
if "%TOKEN%"=="" (
    echo   Chua nhap token. Dung lai.
    pause
    exit /b 1
)

echo.
echo [1/4] Tai runner ve %RUNNER_DIR% ...
if not exist "%RUNNER_DIR%" mkdir "%RUNNER_DIR%"
cd /d "%RUNNER_DIR%"
if not exist run.cmd (
    curl -sSL -o runner.zip https://github.com/actions/runner/releases/latest/download/actions-runner-win-x64-2.328.0.zip
    if not exist runner.zip (
        echo   Khong tai duoc runner. Kiem tra mang roi chay lai.
        pause
        exit /b 1
    )
    powershell -NoProfile -Command "Expand-Archive -Path runner.zip -DestinationPath . -Force"
    del /q runner.zip
)

echo [2/4] Go ban cu neu co ...
if exist .runner (
    call config.cmd remove --token %TOKEN% >nul 2>&1
)

echo [3/4] Dang ky may nay voi GitHub ...
call config.cmd --unattended --url %REPO% --token %TOKEN% ^
     --name "may-so-cong-thuong" --labels windows,laocai --work _work --runasservice
if errorlevel 1 (
    echo.
    echo   DANG KY KHONG THANH CONG. Thuong do token het han (chi song 1 gio).
    echo   Lay token moi o trang buoc 1 roi chay lai file nay.
    pause
    exit /b 1
)

echo [4/4] Bat dich vu chay nen ...
sc start "actions.runner.Trangsct-vlncn-laocai.may-so-cong-thuong" >nul 2>&1

echo.
echo ============================================================
echo   XONG. May nay da san sang nhan lenh tu GitHub.
echo   - Lich tu dong: 11h30 THU TU hang tuan.
echo   - Chay ngay: vao %REPO%/actions -^> "Quet Data360X (may co quan)" -^> Run workflow.
echo   - May tat thi lenh nam cho, bat may len la chay tiep.
echo   Kiem tra: %REPO%/settings/actions/runners  (phai thay dong mau xanh "Idle")
echo ============================================================
echo.
pause
