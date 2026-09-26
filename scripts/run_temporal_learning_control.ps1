param(
    [Parameter(Mandatory = $true)][ValidateSet("run", "verify", "replay")][string]$Mode,
    [Parameter(Mandatory = $true)][string]$RunId,
    [Parameter(Mandatory = $true)][string]$ControlDirectory,
    [string]$ConfigPath
)

$ErrorActionPreference = "Stop"
$workspace = "C:\AI\ai-emotion-lab"
$python = "C:\Users\kjunw\AppData\Local\Programs\Python\Python312\python.exe"
if (Test-Path -LiteralPath $ControlDirectory) { throw "Control directory already exists" }
New-Item -ItemType Directory -Path $ControlDirectory | Out-Null
$started = [DateTime]::UtcNow.ToString("o")
$exitCode = -1
try {
    $env:PYTHONPATH = Join-Path $workspace "src"
    Push-Location $workspace
    if ($Mode -eq "run") {
        if ([string]::IsNullOrWhiteSpace($ConfigPath)) { throw "ConfigPath is required for run" }
        & $python -m temporal_learning run --config $ConfigPath --run-id $RunId
    } else {
        & $python -m temporal_learning $Mode --run-id $RunId
    }
    $exitCode = $LASTEXITCODE
} finally {
    Pop-Location -ErrorAction SilentlyContinue
    @{ mode = $Mode; run_id = $RunId; started_utc = $started; ended_utc = [DateTime]::UtcNow.ToString("o"); exit_code = $exitCode } |
        ConvertTo-Json -Compress | Set-Content -LiteralPath (Join-Path $ControlDirectory "terminal.json") -Encoding utf8 -NoNewline
}
exit $exitCode
