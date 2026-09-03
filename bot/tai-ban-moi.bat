@echo off
rem Tai ban moi nhat cua script va cac file .bat tu GitHub, TRU file dang chay (%1) va tru chinh file nay.
rem Cac file khac se goi file nay o dau moi lan chay -> bo file tren may luon moi, khong phai tai tay.
if exist D:\ (set ROOT=D:\du-an) else (set ROOT=C:\du-an)
set BOT_DIR=%ROOT%\bot
set API=https://api.github.com/repos/Trangsct/ccn-laocai/contents
set TU=%~1
for %%F in (bot-data360x.py cai-dat.bat chay-bot.bat chay-thu.bat dang-nhap-lan-dau.bat dat-lich.bat bo-lich.bat cap-nhat-ngay.bat quet-lai-120-ngay.bat) do (
    if /I not "%%F"=="%TU%" (
        if /I "%%~xF"==".py" (call :tai "%%F" "scripts/%%F") else (call :tai "%%F" "bot/%%F")
    )
)
goto :eof

rem :tai <ten file tren may> <duong dan trong repo>
:tai
curl -sSL --max-time 60 -H "Accept: application/vnd.github.raw" -o "%BOT_DIR%\%~1.new" "%API%/%~2?ref=main"
if exist "%BOT_DIR%\%~1.new" (
    for %%S in ("%BOT_DIR%\%~1.new") do if %%~zS GTR 100 move /y "%BOT_DIR%\%~1.new" "%BOT_DIR%\%~1" >nul
    if exist "%BOT_DIR%\%~1.new" del /q "%BOT_DIR%\%~1.new"
)
goto :eof
