@echo off
chcp 65001 >nul
title Bo lich tu chay - Bot Data360X
rem Dung khi may nay chi chay tay (may khac da giu lich 18h).
echo Se GO 4 lich tu chay cua bot tren may nay:
echo   Bot Data360X - Chay chinh (18:00) va Giu phien 07:00, 12:00, 15:00
echo Bot van chay duoc khi Ban bam dup cap-nhat-ngay.bat.
echo.
pause
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-ScheduledTask -TaskName 'Bot Data360X*' -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false;" ^
  "$con = Get-ScheduledTask -TaskName 'Bot Data360X*' -ErrorAction SilentlyContinue;" ^
  "if ($con) { $con | Select-Object TaskName,State | Format-Table -AutoSize } else { Write-Host '  Da go het lich tren may nay.' }"
echo.
pause
