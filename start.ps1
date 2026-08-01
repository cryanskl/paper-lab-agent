<#
  paper-lab-agent 一键启动（Windows / PowerShell）

  与 start.sh 等价：建 venv → 装依赖 → 腾出端口 → 启动 FastAPI
  → 等 API 与原生工作台就绪 → 打印 URL 并打开工作台。

  用法：
    powershell -ExecutionPolicy Bypass -File .\start.ps1

  环境变量与 start.sh 同名，可在 .env 或当前会话中覆盖：
    API_HOST / API_PORT / API_BASE_URL
    DEV_READY_TIMEOUT / DEV_EXIT_AFTER_READY / START_OPEN_BROWSER
    PAPER_LAB_SCHEDULER_ENABLED / PYTHON / LOG_DIR
#>

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RootDir

# UTF-8 全程固定：中文 Windows 的默认 ANSI 代码页会把中文日志和 .env 解成乱码。
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

function Get-EnvOrDefault([string]$Name, [string]$Default) {
    $value = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrWhiteSpace($value)) { return $Default }
    return $value
}

# .env 里已存在于环境中的键不覆盖，与 scripts/env.sh 的 load_env_file_if_unset 行为一致。
function Import-EnvFile([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return }
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        $trimmed = $line.Trim()
        if ($trimmed -eq '' -or $trimmed.StartsWith('#')) { continue }
        $split = $trimmed.IndexOf('=')
        if ($split -lt 1) { continue }
        $key = $trimmed.Substring(0, $split).Trim()
        $value = $trimmed.Substring($split + 1).Trim().Trim('"').Trim("'")
        if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($key))) {
            [Environment]::SetEnvironmentVariable($key, $value)
        }
    }
}

# 合并了 start.sh 的 resolve_connect_host + format_url_host：绑定地址转成可连接地址，
# IPv6 加方括号。'::' 这一档刻意与 start.sh 不同——bash 版给 [::]，那是未指定地址、
# 浏览器连不上；这里给可连接的 [::1]。请勿"修正"回 [::]。
function Format-UrlHost([string]$HostName) {
    switch ($HostName) {
        '0.0.0.0' { return '127.0.0.1' }
        '::'      { return '[::1]' }
        '::1'     { return '[::1]' }
        default {
            if ($HostName -match ':') { return "[$HostName]" }
            return $HostName
        }
    }
}

function Resolve-Python {
    $configured = [Environment]::GetEnvironmentVariable('PYTHON')
    if (-not [string]::IsNullOrWhiteSpace($configured)) { return $configured }
    $venv = Join-Path $RootDir '.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $venv) { return $venv }
    foreach ($candidate in @('py', 'python', 'python3')) {
        if (Get-Command $candidate -ErrorAction SilentlyContinue) { return $candidate }
    }
    throw 'No Python executable found. Install Python 3.11+ or set PYTHON=C:\path\to\python.exe.'
}

function Reset-Port([string]$Label, [int]$Port) {
    $owners = @()
    try {
        $owners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop |
            Select-Object -ExpandProperty OwningProcess -Unique)
    } catch {
        # 老系统上没有 Get-NetTCPConnection，退回 netstat 解析。
        $owners = @(netstat -ano -p TCP |
            Select-String -Pattern "LISTENING" |
            Where-Object { $_ -match ":$Port\s" } |
            ForEach-Object { ($_ -split '\s+')[-1] } |
            Sort-Object -Unique)
    }
    $owners = @($owners | Where-Object { $_ -and $_ -ne 0 })
    if ($owners.Count -eq 0) {
        Write-Host "$Label port $Port is free."
        return
    }
    Write-Host "$Label port $Port is occupied by PID(s): $($owners -join ' '). Resetting..."
    foreach ($pidValue in $owners) {
        Stop-Process -Id $pidValue -Force -ErrorAction SilentlyContinue
    }
    for ($i = 0; $i -lt 5; $i++) {
        Start-Sleep -Seconds 1
        $still = $null
        try {
            $still = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        } catch { $still = $null }
        if (-not $still) {
            Write-Host "$Label port $Port has been released."
            return
        }
    }
    Write-Warning "$Label port $Port still occupied; continuing anyway."
}

function Wait-ForService([string]$Name, [string]$Url, [double]$TimeoutSeconds, [System.Diagnostics.Process]$Process, [string]$LogPath) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if ($Process.HasExited) {
            Write-Error "$Name process exited before becoming ready (exit code $($Process.ExitCode))."
            Show-LogTail $Name $LogPath
            exit 1
        }
        try {
            $response = Invoke-WebRequest -Uri $Url -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
            if ($response.StatusCode -eq 200) { return }
        } catch {
            # 还没起来，继续等。
        }
        Start-Sleep -Milliseconds 500
    }
    Write-Error "$Name failed to become ready: $Url"
    Show-LogTail $Name $LogPath
    exit 1
}

function Show-LogTail([string]$Name, [string]$LogPath) {
    if (Test-Path -LiteralPath $LogPath) {
        Write-Host "$Name log: $LogPath"
        Get-Content -LiteralPath $LogPath -Tail 40 -Encoding UTF8 | ForEach-Object { Write-Host $_ }
    }
}

if (-not (Test-Path -LiteralPath (Join-Path $RootDir 'requirements.txt'))) {
    throw 'requirements.txt not found; run this script from the paper-lab-agent checkout.'
}
if (-not (Test-Path -LiteralPath (Join-Path $RootDir '.env')) -and
    (Test-Path -LiteralPath (Join-Path $RootDir '.env.example'))) {
    Copy-Item -LiteralPath (Join-Path $RootDir '.env.example') -Destination (Join-Path $RootDir '.env')
}
Import-EnvFile (Join-Path $RootDir '.env')

$ApiHost = Get-EnvOrDefault 'API_HOST' '127.0.0.1'
$ApiPort = [int](Get-EnvOrDefault 'API_PORT' '8000')
$ReadyTimeout = [double](Get-EnvOrDefault 'DEV_READY_TIMEOUT' '45')
$ExitAfterReady = (Get-EnvOrDefault 'DEV_EXIT_AFTER_READY' 'false')
$OpenBrowser = (Get-EnvOrDefault 'START_OPEN_BROWSER' 'true')
$SchedulerEnabled = Get-EnvOrDefault 'PAPER_LAB_SCHEDULER_ENABLED' 'false'

$ApiUrlHost = Format-UrlHost $ApiHost
$ApiBaseUrl = Get-EnvOrDefault 'API_BASE_URL' "http://${ApiUrlHost}:${ApiPort}/api/v1"
$BackendHealthUrl = "http://${ApiUrlHost}:${ApiPort}/api/v1/health"
$WorkbenchUrl = "http://${ApiUrlHost}:${ApiPort}/ui/"

$RunId = Get-Date -Format 'yyyyMMdd-HHmmss'
$LogDir = Get-EnvOrDefault 'LOG_DIR' (Join-Path 'logs' "run-$RunId")
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$BackendLog = Join-Path $LogDir 'backend.log'
$BackendErrLog = Join-Path $LogDir 'backend.err.log'
$PidFile = Join-Path $LogDir 'pids.env'

$Python = Resolve-Python
$UserPython = [Environment]::GetEnvironmentVariable('PYTHON')
if (-not (Test-Path -LiteralPath (Join-Path $RootDir '.venv')) -and
    [string]::IsNullOrWhiteSpace($UserPython)) {
    Write-Host 'Creating Python virtual environment: .venv'
    & $Python -m venv .venv
    $Python = Join-Path $RootDir '.venv\Scripts\python.exe'
}

Write-Host 'paper-lab-agent startup'
Write-Host "Project: $RootDir"
Write-Host "Logs: $LogDir"
Write-Host "Python: $Python"

Write-Host 'Installing Python dependencies from requirements.txt...'
& $Python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "pip install failed with exit code $LASTEXITCODE" }

Reset-Port 'FastAPI' $ApiPort

$env:PAPER_LAB_SCHEDULER_ENABLED = $SchedulerEnabled
$env:API_BASE_URL = $ApiBaseUrl

Write-Host 'Starting FastAPI backend...'
$apiProcess = Start-Process -FilePath $Python -PassThru -NoNewWindow `
    -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--host', $ApiHost, '--port', "$ApiPort") `
    -RedirectStandardOutput $BackendLog -RedirectStandardError $BackendErrLog

try {
    Wait-ForService 'FastAPI' $BackendHealthUrl $ReadyTimeout $apiProcess $BackendLog
    Wait-ForService 'Workbench' $WorkbenchUrl $ReadyTimeout $apiProcess $BackendLog

    @(
        "API_PID=$($apiProcess.Id)"
        "API_URL=http://${ApiUrlHost}:${ApiPort}"
        "WORKBENCH_URL=$WorkbenchUrl"
        "API_BASE_URL=$ApiBaseUrl"
    ) | Set-Content -LiteralPath $PidFile -Encoding UTF8

    Write-Host "FastAPI:  http://${ApiUrlHost}:${ApiPort}"
    Write-Host "工作台:    $WorkbenchUrl"
    Write-Host "API_BASE_URL=$ApiBaseUrl"
    Write-Host "Backend log: $BackendLog"

    if ($OpenBrowser -eq 'true') {
        Start-Process $WorkbenchUrl | Out-Null
    } else {
        Write-Host "Browser auto-open disabled: START_OPEN_BROWSER=$OpenBrowser"
    }

    if ($ExitAfterReady -eq 'true') {
        Write-Host 'DEV_EXIT_AFTER_READY=true; services verified, exiting and cleaning child processes.'
        exit 0
    }

    Write-Host 'Press Ctrl+C to stop the workbench.'
    while (-not $apiProcess.HasExited) {
        Start-Sleep -Seconds 1
    }
} finally {
    foreach ($process in @($apiProcess)) {
        if ($process -and -not $process.HasExited) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
    }
}
