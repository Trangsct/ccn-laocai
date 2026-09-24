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
$Root        = if (Test-Path 'D:\du-an') { 'D:\du-an' } else { 'C:\du-an' }   # chi dung o D khi thu muc da co (may co quan cam ghi goc o D)
$RunnerDir   = Join-Path $Root 'actions-runner'
$CauHinh     = Join-Path $Root 'bot-profile\config.json'
# Ban chot 20/9/2026: Ban dung HAI may (laptop rieng dung wifi, may ban co quan dung day mang LAN).
# Moi may dang ky mot runner rieng, ten theo ten may, nhan them 'laptop' hoac 'may-ban' de co the
# chi dinh dung may khi can; nhan chung 'laocai' de may nao dang bat thi may do nhan viec.
$CoPin       = $null -ne (Get-CimInstance -ClassName Win32_Battery -ErrorAction SilentlyContinue)
$LoaiMay     = if ($CoPin) { 'laptop' } else { 'may-ban' }
$TenRunner   = "$env:COMPUTERNAME-$LoaiMay"
$Nhan        = "windows,laocai,$LoaiMay"
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
Write-Host "   Ban cai: 12/9/2026-b (dan ca dong lenh cung nhan duoc ma)"
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
    # (vu 20/9/2026: dan "token AVMZ..." - co chu 'token' lot vao ma).
    $chu = "$chu".Trim().Trim([char]34).Trim([char]39)
    if ($chu -match '--token\s+([A-Za-z0-9]+)') { return $Matches[1] }
    # Ma dang ky cua GitHub: chuoi CHU HOA + so, thuong 29 ky tu. Lay chuoi dai nhat trong cau.
    # @(...) BAT BUOC: mot ket qua thi PowerShell tra ve chuoi, $ung[0] se lay KY TU dau tien
    # (vu 20/9/2026: "Ma se dung: A").
    $ung = @([regex]::Matches($chu, '[A-Z0-9]{20,}') | ForEach-Object { $_.Value } |
             Sort-Object Length -Descending)
    if ($ung.Count -gt 0) { return [string]$ung[0] }
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
function Tai-Va-Giai-Nen-Runner {
    # Tach thanh ham de dung lai duoc o buoc dang ky (khi phai cai lai tu dau).
    New-Item -ItemType Directory -Force -Path $RunnerDir | Out-Null
    Set-Location $RunnerDir
    if (Test-Path (Join-Path $RunnerDir 'run.cmd')) {
        Bao 'Da co san bo runner, khong tai lai.'
        return
    }
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

Tieu-De '3/7  Tai bo runner ve may'
Tai-Va-Giai-Nen-Runner

# --------------------------------------------------------------- 3. Go ban cu
Tieu-De '4/7  Go dang ky cu (neu co)'
$dv = Get-Service -Name 'actions.runner.*' -ErrorAction SilentlyContinue
if ($dv) {
    Bao 'Phat hien runner cai dang dich vu Windows - dang go (can quyen quan tri).'
    foreach ($d in $dv) { & sc.exe stop $d.Name | Out-Null; & sc.exe delete $d.Name | Out-Null }
}
# Runner dang chay thi file .runner bi KHOA, xoa khong duoc, config.cmd se bao
# "already configured" (vu 20/9/2026 khi doi ten runner theo may). Phai dung han truoc khi go.
# Tat han lich truoc khi dung: chi /End thi Task Scheduler bat lai runner ngay, file trong _diag
# van bi khoa (vu 20/9/2026: "cannot access ... Runner_...-utc.log"). Buoc 6/7 se tao lai lich.
foreach ($t in @($TaskChinh, $TaskCanh)) {
    & schtasks.exe /Change /TN $t /DISABLE 2>$null | Out-Null
    & schtasks.exe /End    /TN $t          2>$null | Out-Null
}
& taskkill.exe /IM Runner.Listener.exe /F /T 2>$null | Out-Null
& taskkill.exe /IM Runner.Worker.exe   /F /T 2>$null | Out-Null
Start-Sleep -Seconds 3
if (Get-Process -Name 'Runner.Listener' -ErrorAction SilentlyContinue) {
    Bao 'Runner cu van chua chiu dung - cho them 5 giay.'
    Start-Sleep -Seconds 5
    & taskkill.exe /IM Runner.Listener.exe /F /T 2>$null | Out-Null
}
# Tim dang ky cu o MOI cho co the, khong chi $RunnerDir: vu 20/9/2026 buoc nay bao "chua tung dang
# ky" nhung config.cmd van bao "already configured" vi cau hinh nam o thu muc khac (C: hay D:).
Bao "Thu muc runner lan nay: $RunnerDir"
$noCu = @()
foreach ($d in @($RunnerDir, 'C:\du-an\actions-runner', 'D:\du-an\actions-runner',
                 (Join-Path $PWD 'actions-runner'), "$PWD")) {
    if ($d -and (Test-Path (Join-Path $d '.runner')) -and ($noCu -notcontains $d)) { $noCu += $d }
}
if ($noCu.Count -eq 0) {
    Bao 'Khong thay dang ky cu o bat ky thu muc nao - bo qua.'
} else {
    $goBo = ''
    if ($pat) { try { $goBo = (Goi-Api POST "repos/$Repo/actions/runners/remove-token" $pat).token } catch { } }
    foreach ($d in $noCu) {
        Bao "Go dang ky cu tai: $d"
        Push-Location $d
        try {
            if (Test-Path (Join-Path $d 'config.cmd')) {
                if ($goBo) { try { & "$d\config.cmd" remove --token $goBo | Out-Null } catch { } }
                # Khong co token go (Ban dan ma bang tay): --local go cau hinh ngay tren may.
                try { & "$d\config.cmd" remove --local | Out-Null } catch { }
            }
        } finally { Pop-Location }
        foreach ($f in @('.runner', '.credentials', '.credentials_rsaparams', '.env', '.path')) {
            Remove-Item (Join-Path $d $f) -Force -ErrorAction SilentlyContinue
        }
        if (Test-Path (Join-Path $d '.runner')) {
            Loi "Van khong xoa duoc dang ky cu tai $d (file dang bi khoa)."
            Bao 'Hay KHOI DONG LAI MAY roi bam dup lai file nay - khi do runner cu chua kip chay.'
            pause
            exit 1
        }
        Tot "Da xoa dang ky cu tai $d"
    }
}

# --------------------------------------------------------------- 4. Dang ky
Tieu-De '5/7  Dang ky may nay voi GitHub'
Bao "Ma se dung: $maDangKy"
Push-Location $RunnerDir      # config.cmd doc/ghi cau hinh theo thu muc dang dung
for ($lan = 1; $lan -le 3; $lan++) {
    & "$RunnerDir\config.cmd" --unattended --url "https://github.com/$Repo" --token $maDangKy `
        --name $TenRunner --labels $Nhan --work _work --replace
    if ($LASTEXITCODE -eq 0) { break }
    if ($lan -eq 2) {
        # Cach cuoi (vu 20/9/2026): cau hinh cu con sot dau do trong thu muc runner -> doi ten ca
        # thu muc roi giai nen ban moi. Khong mat gi vi runner chi la cong cu chay lenh.
        Pop-Location
        Bao 'Van bao "already configured" - doi ten thu muc runner cu va cai lai tu dau.'
        foreach ($t in @($TaskChinh, $TaskCanh)) { & schtasks.exe /End /TN $t 2>$null | Out-Null }
        Get-Process -Name 'Runner.Listener', 'Runner.Worker' -ErrorAction SilentlyContinue |
            Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 3
        $cu = "$RunnerDir-cu-$(Get-Date -Format 'yyyyMMdd-HHmm')"
        try { Rename-Item $RunnerDir $cu -Force } catch { Loi "Khong doi ten duoc: $_"; exit 1 }
        Tot "Da chuyen thu muc cu sang: $cu (co the xoa sau)"
        New-Item -ItemType Directory -Path $RunnerDir -Force | Out-Null
        Tai-Va-Giai-Nen-Runner
        Push-Location $RunnerDir
    }
    if ($lan -eq 3) {
        Pop-Location
        Loi 'Dang ky khong thanh cong sau 3 lan. Dong cua so va chay lai file nay.'
        exit 1
    }
    Write-Host ''
    Loi 'Dang ky khong thanh cong - thuong do ma sai hoac da het han (ma chi song 1 gio).'
    Bao "Thu lai lan $($lan + 1)/3 voi ma moi."
    $maDangKy = Lay-Ma-Dang-Ky $pat $true
    if (-not $maDangKy) { Loi 'Chua co ma. Dung lai.'; exit 1 }
}
Pop-Location
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
