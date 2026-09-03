@echo off
chcp 65001 >nul
setlocal
title Cai dat Bot Data360X
rem Tu chon o D neu co, khong thi o C
if exist D:\ (set ROOT=D:\du-an) else (set ROOT=C:\du-an)
set BOT_HOME=%ROOT%\bot-profile
set BOT_DIR=%ROOT%\bot
set RAW=https://raw.githubusercontent.com/Trangsct/ccn-laocai/main

echo ================================================================
echo   CAI DAT BOT DATA360X (chay lan dau tren may moi;
echo   chay lai bat cu luc nao de tai ve day du cac file .bat moi)
echo ================================================================
echo.

mkdir "%BOT_HOME%" 2>nul
mkdir "%BOT_HOME%\logs" 2>nul
mkdir "%BOT_DIR%" 2>nul

echo [1/5] Kiem tra Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo   Chua co Python. Dang cai bang winget, co the mat 2-3 phut...
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo   KHONG cai duoc tu dong. Hay tai Python tai https://www.python.org/downloads/windows/
        echo   Khi cai nho tich "Add python.exe to PATH", roi chay lai file nay.
        pause
        exit /b 1
    )
    echo   Da cai Python. Hay DONG cua so nay, mo lai cai-dat.bat de tiep tuc.
    pause
    exit /b 0
)
python --version

echo [2/5] Cai Playwright va Chromium (mat 2-5 phut)...
python -m pip install --upgrade pip playwright >nul
python -m playwright install chromium
if errorlevel 1 (
    echo   Loi cai Chromium. Kiem tra mang roi chay lai.
    pause
    exit /b 1
)

echo [3/5] Tai script bot moi nhat tu GitHub...
curl -sSL -o "%BOT_DIR%\bot-data360x.py" "%RAW%/scripts/bot-data360x.py"
curl -sSL -o "%BOT_DIR%\dang-nhap-lan-dau.bat" "%RAW%/bot/dang-nhap-lan-dau.bat"
curl -sSL -o "%BOT_DIR%\chay-thu.bat" "%RAW%/bot/chay-thu.bat"
curl -sSL -o "%BOT_DIR%\dat-lich.bat" "%RAW%/bot/dat-lich.bat"
curl -sSL -o "%BOT_DIR%\chay-bot.bat" "%RAW%/bot/chay-bot.bat"
curl -sSL -o "%BOT_DIR%\cap-nhat-ngay.bat" "%RAW%/bot/cap-nhat-ngay.bat"
curl -sSL -o "%BOT_DIR%\quet-lai-120-ngay.bat" "%RAW%/bot/quet-lai-120-ngay.bat"
curl -sSL -o "%BOT_DIR%\bo-lich.bat" "%RAW%/bot/bo-lich.bat"
if not exist "%BOT_DIR%\bot-data360x.py" (
    echo   Khong tai duoc script. Kiem tra mang.
    pause
    exit /b 1
)

echo [4/5] Nhap token GitHub (chuoi github_pat_..., chi luu tren may nay, khong len GitHub)
if exist "%BOT_HOME%\config.json" (
    echo   Da co config.json. Bam Enter de giu nguyen, hoac dan token moi:
) else (
    echo   Dan token roi bam Enter:
)
set /p TOKEN=  Token:
python -c "import json,sys,pathlib; p=pathlib.Path(sys.argv[1]); tok=sys.argv[2].strip(); cfg=json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}; cfg.update({'github_token': tok} if tok else {}); cfg.setdefault('telegram_token',''); cfg.setdefault('telegram_chat_id',''); p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8'); print('  Da luu', p)" "%BOT_HOME%\config.json" "%TOKEN%"

echo [5/5] Kiem tra token (doc 4 repo, ghi roi xoa 1 file thu)...
python "%BOT_DIR%\bot-data360x.py" --kiem-tra-token
echo.
echo Cac file dat tai %BOT_DIR%
echo   Neu tren ghi "TOKEN DUNG DUOC": chay tiep dang-nhap-lan-dau.bat.
echo   Neu "TOKEN CHUA DUNG DUOC": chup man hinh gui Claude Code.
echo.
pause
