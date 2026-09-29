# ============================================================================
#  CAI TAY - tien trinh duy nhat tren may o Lao Cai, canh tay cua Claude (Ban chot 30/9/2026)
#
#  Lam gi: kiem tra Python, cai Playwright (KHONG tai Chromium rieng - dung Chrome san co cua may),
#  tai tay.py + bot-data360x.py, hoi token GitHub (neu chua co), dat 2 lich Task Scheduler de tay.py
#  tu chay an moi khi dang nhap Windows va tu bat lai moi 30 phut. Khong can quyen Administrator.
#
#  Bai hoc 29/9/2026 (ap dung trong ca file nay):
#   - $ErrorActionPreference = 'Continue': lenh Windows in canh bao ra stderr khong duoc lam chet script.
#   - Test-Path -LiteralPath, khong Join-Path tren o dia co the khong ton tai.
#   - -ChayThu: may ao Windows (workflow thu-bo-cai-windows.yml) chay het cac buoc, khong hoi token,
#     khong khoi dong tay.py vo han; TAY_NGUON=<thu muc kho> thi lay ma tu do thay vi tai tu main.
# ============================================================================
param([switch]$ChayThu)

$ErrorActionPreference = 'Continue'
$env:PYTHONIOENCODING = 'utf-8'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Root = 'C:\du-an'
foreach ($o in 'D', 'E', 'F', 'G') { if (Test-Path -LiteralPath "$($o):\du-an") { $Root = "$($o):\du-an" } }
$BotDir  = "$Root\bot"
$BotHome = "$Root\bot-profile"
$CauHinh = "$BotHome\config.json"
$Api     = 'https://api.github.com/repos/Trangsct/ccn-laocai/contents'
$TaskChinh = 'TAY Data360X - chay khi dang nhap'
$TaskCanh  = 'TAY Data360X - canh chung 30 phut'

function Tieu-De($s) { Write-Host ''; Write-Host "== $s" -ForegroundColor Cyan }
function Bao($s)     { Write-Host "   $s" }
function Loi($s)     { Write-Host "   $s" -ForegroundColor Red }
function Tot($s)     { Write-Host "   $s" -ForegroundColor Green }

New-Item -ItemType Directory -Force -Path $BotDir, "$BotHome\logs" | Out-Null

Write-Host ''
Write-Host '============================================================'
Write-Host '   CAI TAY - canh tay cua Claude tren may nay'
Write-Host "   Thu muc: $Root"
Write-Host '   Ban cai: 30/9/2026'
Write-Host '============================================================'

function Tai($duongKho, $dich) {
    # Lay tu kho dang thu (may ao) hay tu main (may that). Qua api.github.com de khong dinh bo dem CDN.
    if ($env:TAY_NGUON) {
        $nguon = Join-Path $env:TAY_NGUON $duongKho
        if (Test-Path -LiteralPath $nguon) { Copy-Item -LiteralPath $nguon -Destination $dich -Force; return $true }
        return $false
    }
    curl.exe -sSL --max-time 120 -H 'Accept: application/vnd.github.raw' -H 'Cache-Control: no-cache' `
        -o "$dich.new" "$Api/$duongKho`?ref=main"
    if ((Test-Path -LiteralPath "$dich.new") -and ((Get-Item -LiteralPath "$dich.new").Length -gt 300)) {
        Move-Item -LiteralPath "$dich.new" -Destination $dich -Force
        return $true
    }
    Remove-Item -LiteralPath "$dich.new" -Force -ErrorAction SilentlyContinue
    return $false
}

# ------------------------------------------------------------------ 1. Python
Tieu-De '1/5  Python'
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Bao 'Chua co Python, dang cai bang winget (2-3 phut)...'
    & winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements | Out-Null
    Loi 'Da cai Python. DONG cua so nay roi bam dup lai cai-tay.bat de tiep tuc.'
    exit 0
}
Bao "Python: $(& python --version 2>&1)"

# ------------------------------------------------------------------ 2. Playwright + Chrome
Tieu-De '2/5  Playwright (dung Chrome san co cua may, khong tai Chromium rieng)'
& python -m pip install --quiet --disable-pip-version-check playwright 2>&1 | Out-Null
$chrome = @("$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
            "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
            "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe") | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if ($chrome) { Tot "Chrome: $chrome" } else { Loi 'Khong thay Google Chrome tren may. Cai Chrome roi chay lai; bot can Chrome that de dang nhap Data360X.' }

# ------------------------------------------------------------------ 3. Ma
Tieu-De '3/5  Tai tay.py, bot-data360x.py va file phu tro'
$ok = $true
foreach ($cap in @(@('tay/tay.py', "$BotDir\tay.py"), @('scripts/bot-data360x.py', "$BotDir\bot-data360x.py"),
                   @('bot/dang-nhap-lan-dau.bat', "$BotDir\dang-nhap-lan-dau.bat"), @('bot/cai-tay.bat', "$BotDir\cai-tay.bat"))) {
    if (Tai $cap[0] $cap[1]) { Bao "da tai $(Split-Path $cap[1] -Leaf)" } else { Loi "KHONG tai duoc $($cap[0])"; $ok = $false }
}
if (-not $ok) { Loi 'Kiem tra mang roi chay lai.'; if (-not $ChayThu) { pause }; exit 1 }

# ------------------------------------------------------------------ 4. Token
Tieu-De '4/5  Token GitHub'
if (Test-Path -LiteralPath $CauHinh) {
    Bao 'Da co config.json (token cu cua bot), dung lai.'
} elseif ($ChayThu) {
    Bao 'Chay thu: bo qua nhap token.'
} else {
    Bao 'Dan token github_pat_... (Contents Read/Write cho 4 kho ccn-laocai, vlncn-laocai, vlncn-laocai-files, skill-sct)'
    $tok = Read-Host '   Token'
    $tok = "$tok".Trim()
    if (-not $tok) { Loi 'Chua co token. Dung lai.'; pause; exit 1 }
    $cfg = @{ github_token = $tok; telegram_token = ''; telegram_chat_id = '' } | ConvertTo-Json
    [System.IO.File]::WriteAllText($CauHinh, $cfg, (New-Object System.Text.UTF8Encoding $false))
    & python "$BotDir\bot-data360x.py" --kiem-tra-token
}

# ------------------------------------------------------------------ 5. Lich
Tieu-De '5/5  Dat lich cho tay.py tu chay (an, khong hien cua so)'
$vbs = "$BotDir\tay-an.vbs"
@"
' Khoi dong TAY o che do an. Dang chay roi thi thoi.
Set sh = CreateObject("WScript.Shell")
Set wmi = GetObject("winmgmts:\\.\root\cimv2")
If wmi.ExecQuery("SELECT * FROM Win32_Process WHERE Name='pythonw.exe' AND CommandLine LIKE '%tay.py%'").Count = 0 Then
  sh.CurrentDirectory = "$BotDir"
  sh.Environment("Process")("PYTHONIOENCODING") = "utf-8"
  sh.Run "pythonw.exe ""$BotDir\tay.py""", 0, False
End If
"@ | Set-Content -LiteralPath $vbs -Encoding ASCII

$nguoi  = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$caiDat = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
          -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
$chuThe = New-ScheduledTaskPrincipal -UserId $nguoi -LogonType Interactive -RunLevel Limited
$viec   = New-ScheduledTaskAction -Execute 'wscript.exe' -Argument "`"$vbs`""
try {
    Register-ScheduledTask -TaskName $TaskChinh -Action $viec -Settings $caiDat -Principal $chuThe `
        -Trigger (New-ScheduledTaskTrigger -AtLogOn -User $nguoi) -Force | Out-Null
    $nhip = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 30)
    Register-ScheduledTask -TaskName $TaskCanh -Action $viec -Settings $caiDat -Principal $chuThe -Trigger $nhip -Force | Out-Null
    Tot 'Da dat 2 lich: dang nhap Windows la chay; cu 30 phut tu kiem tra.'
} catch {
    Loi "Khong dat duoc lich: $($_.Exception.Message)"
    if (-not $ChayThu) { pause; exit 1 }
}

if ($ChayThu) {
    Tieu-De 'Chay thu tay.py --chay-thu'
    & python "$BotDir\tay.py" --chay-thu
    if ($LASTEXITCODE -ne 0) { Loi 'tay.py --chay-thu that bai'; exit 1 }
    Tot 'CHAY THU XONG.'
    exit 0
}

Bao 'Khoi dong TAY ngay bay gio...'
Start-Process -FilePath 'wscript.exe' -ArgumentList "`"$vbs`"" -WindowStyle Hidden
Start-Sleep -Seconds 5
$dang = Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" | Where-Object { $_.CommandLine -like '*tay.py*' }
if ($dang) { Tot 'TAY DANG CHAY.' } else { Loi 'Chua thay tay.py chay. Xem log trong bot-profile\logs\tay-*.log' }

Write-Host ''
Write-Host '============================================================'
Write-Host '   TU GIO TRO DI'
Write-Host '   - Chua dang nhap Data360X tren may nay thi bam dup dang-nhap-lan-dau.bat mot lan.'
Write-Host '   - TAY tu giu phien moi gio 07-17h, tu quet 30 ngay thu Tu (hoac khi qua 7 ngay chua quet),'
Write-Host '     va lam moi yeu cau Claude ghi vao yeu-cau/ cua kho vlncn-laocai.'
Write-Host "   - Log: $BotHome\logs\tay-<ngay>.log ; trang thai: $BotHome\tay-trang-thai.json"
Write-Host '   - Nhip tim tren GitHub: vlncn-laocai/trang-thai/tay.json'
Write-Host '============================================================'
Write-Host ''
pause
