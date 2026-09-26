param(
    [Parameter(Mandatory = $true)][ValidateSet("run", "verify", "replay")][string]$Mode,
    [Parameter(Mandatory = $true)][string]$OutputDirectory,
    [Parameter(Mandatory = $true)][string]$ControlDirectory,
    [string]$ConfigPath,
    [switch]$WithAudit,
    [string]$WrapperPath
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($WrapperPath)) {
    $WrapperPath = Join-Path $PSScriptRoot "run_temporal_learning_v2_control.ps1"
}
if (-not (Test-Path -LiteralPath $WrapperPath -PathType Leaf)) { throw "Control wrapper is missing" }
$wrapperArguments = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $WrapperPath, "-Mode", $Mode,
    "-OutputDirectory", $OutputDirectory, "-ControlDirectory", $ControlDirectory)
if ($Mode -eq "run" -and -not [string]::IsNullOrWhiteSpace($ConfigPath)) {
    $wrapperArguments += @("-ConfigPath", $ConfigPath)
}
if ($WithAudit) { $wrapperArguments += "-WithAudit" }
$previousErrorActionPreference = $ErrorActionPreference
try {
    $ErrorActionPreference = "Continue"
    & powershell.exe @wrapperArguments 2> $null
    $wrapperExitCode = $LASTEXITCODE
} finally {
    $ErrorActionPreference = $previousErrorActionPreference
}
$terminalPath = Join-Path $ControlDirectory "terminal.json"
if (-not (Test-Path -LiteralPath $terminalPath -PathType Leaf)) { throw "Control terminal marker is missing" }
try {
    $terminal = Get-Content -Raw -LiteralPath $terminalPath | ConvertFrom-Json -ErrorAction Stop
    $started = [DateTimeOffset]::Parse([string]$terminal.started_utc)
    $ended = [DateTimeOffset]::Parse([string]$terminal.ended_utc)
    $terminalExitCode = [Convert]::ToInt32($terminal.exit_code)
} catch {
    throw "Control terminal marker is invalid"
}
if ($terminal.mode -ne $Mode -or $terminal.output_directory -ne $OutputDirectory) {
    throw "Control terminal marker does not match the request"
}
if ($ended -lt $started -or $terminalExitCode -ne $wrapperExitCode) {
    throw "Control terminal marker does not match the wrapper result"
}
if ($Mode -eq "run" -and $wrapperExitCode -eq 0) {
    if (-not (Test-Path -LiteralPath (Join-Path $OutputDirectory "public\completion.json") -PathType Leaf)) {
        throw "Successful run has no completion evidence"
    }
    if (Test-Path -LiteralPath (Join-Path $OutputDirectory "failure.json") -PathType Leaf) {
        throw "Successful run has failure evidence"
    }
}
exit $wrapperExitCode
