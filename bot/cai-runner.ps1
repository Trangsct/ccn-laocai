# ============================================================================
#  CAI RUNNER GITHUB CHO MAY CO QUAN  (Ban chot 04/9/2026 - huong 4)
#
#  Muc dich: de GitHub ra lenh, may nay thi hanh. Nho vay Ban ngoi bat cu dau
#  cung bam duoc nut "Run workflow" tren dien thoai, may o co quan tu chay bot
#  vao Data360X. Lich co dinh: 11h30 THU TU hang tuan.
#
#  Tu dong toi da: doc token GitHub co san trong config.json, tu xin ma dang ky
#  runner qua API, tu tai ban runner moi nhat, tu dat lich chay lai moi khi
#  dang nhap Windows, tu kiem tra runner da len mang chua.
#  KHONG can quyen Administrator. Chi bam dup la xong.
#
#  Vi sao KHONG cai dang dich vu Windows (--runasservice): bot mo Chrome THAT
#  (co giao dien) bang ho so da dang nhap Data360X. Dich vu Windows chay o
#  phien 0 va bang tai khoan khac nen khong mo duoc cua so, cung khong giai ma
#  duoc cookie phien (Windows ma hoa cookie theo tung tai khoan). Vi vay runner
#  chay ngay trong phien dang nhap cua Ban, o che do an (khong hien cua so den).
# ============================================================================

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Repo        = 'Trangsct/vlncn-laocai'
$Root        = if (Test-Path 'D:\') { 'D:\du-an' } else { 'C:\du-an' }
$RunnerDir   = Join-Path $Root 'actions-runner'
$CauHinh     = Join-Path $Root 'bot-profile\config.json'
$TenRunner   = 'may-so-cong-thuong'
$Nhan        = 'windows,laocai'
$TaskChinh   = 'Bot Data360X - Runner GitHub'
$TaskCanh    = 'Bot Data360X - Runner GitHub (canh chung)'
$BanDuPhong  = '2.328.0'   # dung khi khong hoi duoc ban moi nhat

function Tieu-De($s) { Write-Host ''; Write-Host "== $s" -ForegroundColor Cyan }
function Bao($s)     { Write-Host "   $s" }
function Loi($s)     { Write-Host "   $s" -ForegroundColor Red }
function Tot($s)     { Write-Host "   $s" -ForegroundColor Green }

function Lay-Pat {
    # Token GitHub Ban da nhap luc cai-dat.bat, nam trong config.json cua bot.
    if (-not (Test-Path $CauHinh)) { return '' }
    try { $c = Get-Content -Raw -LiteralPath $CauHinh } catch { return '' }
    if ($c -match '"github_token"\s*:\s*"([^"]+)"') { return $Matches[1] }
    return ''
}

function Goi-Api($PhuongThuc, $Duong, $Pat, $Than) {
    $h = @{ Authorization = "Bearer $Pat"; Accept = 'application/vnd.github+json';
            'X-GitHub-Api-Version' = '2022-11-28'; 'User-Agent' = 'bot-data360x' }
    $tham = @{ Method = $PhuongThuc; Uri = "https://api.github.com/$Duong"; Headers = $h; TimeoutSec = 90 }
    if ($Than) { $tham['Body'] = ($Than | ConvertTo-Json -Compress); $tham['ContentType'] = 'application/json' }
    return Invoke-RestMethod @tham
}

Write-Host ''
Write-Host '============================================================'
Write-Host '   CAI RUNNER GITHUB CHO MAY NAY'
Write-Host "   Kho: $Repo"
Write-Host "   Thu muc: $RunnerDir"
Write-Host '============================================================'

# --------------------------------------------------------------- 0. Cong cu
Tieu-De '1/7  Kiem tra cong cu tren may (git, python)'
# Workflow "Tim van ban vien dan" dung actions/checkout nen may PHAI co git.
# Bot Data360X dung python. Thieu cai nao thi cai bang winget cho khoi phai lam tay.
foreach ($ct in @(@{ ten = 'git'; id = 'Git.Git' }, @{ ten = 'python'; id = 'Python.Python.3.12' })) {
    $co = $null
    try { $co = Get-Command $ct.ten -ErrorAction SilentlyContinue } catch { }
    if ($co) {
        Bao "$($ct.ten): da co."
    } else {
        Bao "$($ct.ten): chua co, dang cai bang winget (co the mat vai phut)..."
        try {
            & winget install -e --id $ct.id --accept-package-agreements --accept-source-agreements | Out-Null
            Bao "$($ct.ten): da cai. Neu buoc sau bao thieu $($ct.ten) thi dong cua so va bam dup lai file nay."
        } catch {
            Bao "$($ct.ten): khong cai tu dong duoc. Runner van cai tiep duoc, nhung hay cai $($ct.ten) sau."
        }
    }
}

function Nhat-Ma($chu) {
    # Ban dan kieu gi cung duoc: rieng ma, hay ca dong lenh ./config.cmd --url ... --token AXXXX
    # (vu 12/9/2026: dan ca dong nen config.cmd nhan --token la "./config.cmd", GitHub tra 404).
    $chu = "$chu".Trim().Trim([char]34).Trim([char]39)
    if ($chu -match '--token\s+([A-Za-z0-9]+)') { return $Matches[1] }
    if ($chu -match '([A-Z0-9]{25,})') { return $Matches[1] }
    return $chu
}

function Lay-Ma-Dang-Ky($pat, $imLang) {
    # Uu tien xin qua API bang token san co; khong duoc thi huong dan dan tay.
    if ($pat) {
        if (-not $imLang) { Bao 'Da thay token GitHub trong config.json, dang hoi GitHub...' }
        try {
            $ma = (Goi-Api POST "repos/$Repo/actions/runners/registration-token" $pat).token
            Tot 'GitHub da cap ma dang ky. Khong phai lam gi them.'
            return $ma
        } catch {
            if (-not $imLang) {
                Bao "Token nay khong xin duoc ma dang ky ($($_.Exception.Message))."
                Bao 'Thuong la do token chi co quyen Contents, chua co quyen Administration.'
            }
        }
    } elseif (-not $imLang) {
        Bao 'Chua thay token GitHub trong config.json.'
    }
    $trang = "https://github.com/$Repo/settings/actions/runners/new?arch=x64&os=win"
    Write-Host ''
    Bao 'Lam tay 1 lan, khoang 30 giay:'
    Bao '  1. Trang GitHub vua mo ra trong trinh duyet (neu khong, mo dia chi duoi).'
    Bao "     $trang"
    Bao '  2. Keo xuong muc Configure, tim dong co chu  --token'
    Bao '  3. Boi den VA COPY (Ctrl+C). Boi ca dong cung duoc, hay chi rieng chuoi AXXXX... cung duoc.'
    Bao '  4. Quay lai cua so nay, bam CHUOT PHAI de dan, roi bam Enter.'
    Write-Host ''
    try { Start-Process $trang } catch { }
    return (Nhat-Ma (Read-Host '   Ma dang ky'))
}

# --------------------------------------------------------------- 1. Ma dang ky
Tieu-De '2/7  Xin ma dang ky runner'
$pat = Lay-Pat
$maDangKy = Lay-Ma-Dang-Ky $pat $false
if (-not $maDangKy) { Loi 'Chua co ma dang ky. Dung lai.'; exit 1 }

# --------------------------------------------------------------- 2. Tai runner
Tieu-De '3/7  Tai bo runner ve may'
New-Item -ItemType Directory -Force -Path $RunnerDir | Out-Null
Set-Location $RunnerDir
if (Test-Path (Join-Path $RunnerDir 'run.cmd')) {
    Bao 'Da co san bo runner, khong tai lai.'
} else {
    $ban = $BanDuPhong
    try {
        $ban = ((Invoke-RestMethod -Uri 'https://api.github.com/repos/actions/runner/releases/latest' `
                 -Headers @{ 'User-Agent' = 'bot-data360x' } -TimeoutSec 60).tag_name) -replace '^v', ''
    } catch { Bao "Khong hoi duoc ban moi nhat, dung ban $BanDuPhong." }
    $zip = Join-Path $RunnerDir 'runner.zip'
    Bao "Dang tai runner $ban (khoang 60 MB), vui long cho..."
    curl.exe -sSL --max-time 900 -o "$zip" "https://github.com/actions/runner/releases/download/v$ban/actions-runner-win-x64-$ban.zip"
    if (-not (Test-Path $zip) -or (Get-Item $zip).Length -lt 1MB) { Loi 'Khong tai duoc runner. Kiem tra mang roi chay lai.'; exit 1 }
    Expand-Archive -Path $zip -DestinationPath $RunnerDir -Force
    Remove-Item $zip -Force
    Tot "Da tai va giai nen runner $ban."
}

# --------------------------------------------------------------- 3. Go ban cu
Tieu-De '4/7  Go dang ky cu (neu co)'
$dv = Get-Service -Name 'actions.runner.*' -ErrorAction SilentlyContinue
if ($dv) {
    Bao 'Phat hien runner cai dang dich vu Windows - dang go (can quyen quan tri).'
    foreach ($d in $dv) { & sc.exe stop $d.Name | Out-Null; & sc.exe delete $d.Name | Out-Null }
}
if (Test-Path (Join-Path $RunnerDir '.runner')) {
    $goBo = ''
    if ($pat) { try { $goBo = (Goi-Api POST "repos/$Repo/actions/runners/remove-token" $pat).token } catch { } }
    # Loi o buoc go khong quan trong: xoa file .runner ben duoi la du de dang ky lai.
    if ($goBo) { try { & "$RunnerDir\config.cmd" remove --token $goBo | Out-Null } catch { } }
    Remove-Item (Join-Path $RunnerDir '.runner')      -Force -ErrorAction SilentlyContinue
    Remove-Item (Join-Path $RunnerDir '.credentials') -Force -ErrorAction SilentlyContinue
    Remove-Item (Join-Path $RunnerDir '.credentials_rsaparams') -Force -ErrorAction SilentlyContinue
    Bao 'Da xoa dang ky cu.'
} else {
    Bao 'May chua tung dang ky - bo qua.'
}

# --------------------------------------------------------------- 4. Dang ky
Tieu-De '5/7  Dang ky may nay voi GitHub'
for ($lan = 1; $lan -le 3; $lan++) {
    & "$RunnerDir\config.cmd" --unattended --url "https://github.com/$Repo" --token $maDangKy `
        --name $TenRunner --labels $Nhan --work _work --replace
    if ($LASTEXITCODE -eq 0) { break }
    if ($lan -eq 3) {
        Loi 'Dang ky khong thanh cong sau 3 lan. Dong cua so va chay lai file nay.'
        exit 1
    }
    Write-Host ''
    Loi 'Dang ky khong thanh cong - thuong do ma sai hoac da het han (ma chi song 1 gio).'
    Bao "Thu lai lan $($lan + 1)/3 voi ma moi."
    $maDangKy = Lay-Ma-Dang-Ky $pat $true
    if (-not $maDangKy) { Loi 'Chua co ma. Dung lai.'; exit 1 }
}
Tot "Da dang ky, ten may tren GitHub: $TenRunner"

# --------------------------------------------------------------- 5. Dat lich
Tieu-De '6/7  Dat cho runner tu chay moi khi bat may'
# File .vbs chi de chay run.cmd o che do AN (khong hien cua so den) va khong chay trung.
$vbs = Join-Path $RunnerDir 'chay-runner-an.vbs'
@"
' Khoi dong runner GitHub o che do an. Dang chay roi thi thoi (khong mo hai lan).
Set sh = CreateObject("WScript.Shell")
Set wmi = GetObject("winmgmts:\\.\root\cimv2")
If wmi.ExecQuery("SELECT * FROM Win32_Process WHERE Name='Runner.Listener.exe'").Count = 0 Then
  sh.CurrentDirectory = "$RunnerDir"
  sh.Run "run.cmd", 0, False
End If
"@ | Set-Content -LiteralPath $vbs -Encoding ASCII

$nguoi = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$caiDat = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
          -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero)
$chuThe = New-ScheduledTaskPrincipal -UserId $nguoi -LogonType Interactive -RunLevel Limited
$viec   = New-ScheduledTaskAction -Execute 'wscript.exe' -Argument "`"$vbs`""
Register-ScheduledTask -TaskName $TaskChinh -Action $viec -Settings $caiDat -Principal $chuThe `
    -Trigger (New-ScheduledTaskTrigger -AtLogOn -User $nguoi) -Force | Out-Null
# Canh chung: cu 30 phut xem runner con song khong, chet thi dung day (mat dien, thoat nham...).
$nhip = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName $TaskCanh -Action $viec -Settings $caiDat -Principal $chuThe `
    -Trigger $nhip -Force | Out-Null
Tot 'Da dat 2 lich: bat may la chay, va cu 30 phut tu kiem tra mot lan.'

Bao 'Dang khoi dong runner ngay bay gio...'
Start-Process -FilePath 'wscript.exe' -ArgumentList "`"$vbs`"" -WindowStyle Hidden

# --------------------------------------------------------------- 6. Kiem tra
Tieu-De '7/7  Kiem tra runner da len mang chua'
$xong = $false
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 5
    if ($pat) {
        try {
            $ds = (Goi-Api GET "repos/$Repo/actions/runners" $pat).runners | Where-Object { $_.name -eq $TenRunner }
            if ($ds -and $ds.status -eq 'online') { $xong = $true; break }
        } catch { }
    }
    if (Get-Process -Name 'Runner.Listener' -ErrorAction SilentlyContinue) { $xong = $true; break }
}
Write-Host ''
if ($xong) {
    Tot 'RUNNER DA CHAY. May nay san sang nhan lenh tu GitHub.'
} else {
    Loi 'Chua thay runner chay. Mo Task Scheduler, chay tay muc "Bot Data360X - Runner GitHub".'
}

Write-Host ''
Write-Host '============================================================'
Write-Host '   TU GIO TRO DI'
Write-Host "   - Tu dong: 11h30 THU TU hang tuan, may tu quet Data360X."
Write-Host "   - Chay ngay (o bat ky dau, ke ca dien thoai):"
Write-Host "       https://github.com/$Repo/actions"
Write-Host '       chon "Quet Data360X (may co quan)" -> Run workflow.'
Write-Host '   - May tat thi lenh nam cho, bat may len la chay tiep.'
Write-Host "   - Xem may con noi voi GitHub khong:"
Write-Host "       https://github.com/$Repo/settings/actions/runners"
Write-Host '============================================================'

if ($pat) {
    Write-Host ''
    $tra = Read-Host '   Quet Data360X mot luot ngay bay gio cho chac? (Enter = co, n = thoi)'
    if ($tra -notmatch '^[nN]') {
        try {
            Goi-Api POST "repos/$Repo/actions/workflows/quet-tren-may.yml/dispatches" $pat `
                @{ ref = 'main'; inputs = @{ ngay = '30' } } | Out-Null
            Tot 'Da ra lenh quet 30 ngay gan nhat. Chrome se tu mo, khong dong no lai.'
            Bao "Xem tien trinh: https://github.com/$Repo/actions"
        } catch {
            Bao "Khong ra lenh duoc ($($_.Exception.Message)). Vao trang Actions bam Run workflow cung duoc."
        }
    }
}
Write-Host ''
