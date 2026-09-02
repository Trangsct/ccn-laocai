@echo off
chcp 65001 >nul
title Dat lich Bot Data360X
if exist D:\ (set ROOT=D:\du-an) else (set ROOT=C:\du-an)
set BOT_DIR=%ROOT%\bot
echo Dang ky 4 lich chay trong Windows Task Scheduler (can quyen Administrator):
echo   - Bot Data360X - Chay chinh   : 18:00 hang ngay (ca T7, CN)
echo   - Bot Data360X - Giu phien 1/2/3 : 07:00, 12:00, 15:00
echo   Chay ke ca khi khoa man hinh, danh thuc may neu dang ngu.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$dir='%BOT_DIR%';" ^
  "$set=New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries;" ^
  "$u=[System.Security.Principal.WindowsIdentity]::GetCurrent().Name;" ^
  "$p=New-ScheduledTaskPrincipal -UserId $u -LogonType Interactive -RunLevel Limited;" ^
  "$a1=New-ScheduledTaskAction -Execute 'cmd.exe' -Argument ('/c \"' + $dir + '\chay-bot.bat\" chinh') -WorkingDirectory $dir;" ^
  "Register-ScheduledTask -TaskName 'Bot Data360X - Chay chinh' -Action $a1 -Trigger (New-ScheduledTaskTrigger -Daily -At 18:00) -Settings $set -Principal $p -Force | Out-Null;" ^
  "$a2=New-ScheduledTaskAction -Execute 'cmd.exe' -Argument ('/c \"' + $dir + '\chay-bot.bat\" giu-phien') -WorkingDirectory $dir;" ^
  "foreach($h in @('07:00','12:00','15:00')){ Register-ScheduledTask -TaskName ('Bot Data360X - Giu phien ' + $h) -Action $a2 -Trigger (New-ScheduledTaskTrigger -Daily -At $h) -Settings $set -Principal $p -Force | Out-Null };" ^
  "Get-ScheduledTask -TaskName 'Bot Data360X*' | Select-Object TaskName,State | Format-Table -AutoSize"
if errorlevel 1 (
    echo LOI: hay bam chuot phai vao dat-lich.bat, chon "Run as administrator" roi thu lai.
) else (
    echo Da dat lich. Kiem tra: bam Start, go Task Scheduler, xem muc Task Scheduler Library.
)
echo.
pause
