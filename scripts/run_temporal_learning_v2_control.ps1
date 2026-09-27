param(
    [Parameter(Mandatory = $true)][ValidateSet("run", "verify", "replay")][string]$Mode,
    [Parameter(Mandatory = $true)][string]$OutputDirectory,
    [Parameter(Mandatory = $true)][string]$ControlDirectory,
    [string]$ConfigPath,
    [switch]$WithAudit
)

$ErrorActionPreference = "Stop"
$workspace = Split-Path -Parent $PSScriptRoot
$python = (Get-Command python.exe -ErrorAction Stop).Source
if (Test-Path -LiteralPath $ControlDirectory) { throw "Control directory already exists" }
$controlParent = Split-Path -Parent $ControlDirectory
if ([string]::IsNullOrWhiteSpace($controlParent)) { throw "ControlDirectory must have a parent" }
New-Item -ItemType Directory -Path $controlParent -Force | Out-Null
New-Item -ItemType Directory -Path $ControlDirectory | Out-Null
$started = [DateTime]::UtcNow.ToString("o")
$exitCode = -1
$stdoutPath = Join-Path $ControlDirectory "stdout.log"
$stderrPath = Join-Path $ControlDirectory "stderr.log"
function Write-Utf8File([string]$Path, [string]$Content) {
    [System.IO.File]::WriteAllText($Path, $Content, [System.Text.UTF8Encoding]::new($false))
}
function Quote-ProcessArgument([string]$Argument) {
    if ($Argument.Length -eq 0) { return '""' }
    if ($Argument -notmatch '[\s"]') { return $Argument }
    $quoted = New-Object System.Text.StringBuilder
    [void]$quoted.Append('"')
    $backslashes = 0
    foreach ($character in $Argument.ToCharArray()) {
        if ($character -eq '\') {
            $backslashes += 1
        } elseif ($character -eq '"') {
            [void]$quoted.Append(('\' * (($backslashes * 2) + 1)))
            [void]$quoted.Append('"')
            $backslashes = 0
        } else {
            [void]$quoted.Append(('\' * $backslashes))
            [void]$quoted.Append($character)
            $backslashes = 0
        }
    }
    [void]$quoted.Append(('\' * ($backslashes * 2)))
    [void]$quoted.Append('"')
    return $quoted.ToString()
}
try {
    $arguments = @("-m", "temporal_learning_v2", $Mode, "--output", $OutputDirectory)
    if ($Mode -eq "run") {
        if ([string]::IsNullOrWhiteSpace($ConfigPath)) { throw "ConfigPath is required for run" }
        $arguments = @("-m", "temporal_learning_v2", "run", "--config", $ConfigPath, "--output", $OutputDirectory)
    }
    if ($WithAudit) { $arguments += "--with-audit" }
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $python
    $startInfo.Arguments = [string]::Join(" ", @($arguments | ForEach-Object { Quote-ProcessArgument $_ }))
    $startInfo.WorkingDirectory = $workspace
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $utf8 = [System.Text.UTF8Encoding]::new($false)
    $startInfo.StandardOutputEncoding = $utf8
    $startInfo.StandardErrorEncoding = $utf8
    $previousPythonPath = [Environment]::GetEnvironmentVariable("PYTHONPATH", "Process")
    $previousPythonIoEncoding = [Environment]::GetEnvironmentVariable("PYTHONIOENCODING", "Process")
    try {
        [Environment]::SetEnvironmentVariable("PYTHONPATH", (Join-Path $workspace "src"), "Process")
        [Environment]::SetEnvironmentVariable("PYTHONIOENCODING", "utf-8", "Process")
        $process = New-Object System.Diagnostics.Process
        $process.StartInfo = $startInfo
        if (-not $process.Start()) { throw "Python child did not start" }
        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        $process.WaitForExit()
        Write-Utf8File $stdoutPath $stdoutTask.GetAwaiter().GetResult()
        Write-Utf8File $stderrPath $stderrTask.GetAwaiter().GetResult()
        $exitCode = $process.ExitCode
    } finally {
        [Environment]::SetEnvironmentVariable("PYTHONPATH", $previousPythonPath, "Process")
        [Environment]::SetEnvironmentVariable("PYTHONIOENCODING", $previousPythonIoEncoding, "Process")
    }
} catch {
    $exitCode = 1
    if (-not (Test-Path -LiteralPath $stdoutPath)) { Write-Utf8File $stdoutPath "" }
    $wrapperError = $_ | Out-String
    if (Test-Path -LiteralPath $stderrPath) {
        [System.IO.File]::AppendAllText($stderrPath, $wrapperError, [System.Text.UTF8Encoding]::new($false))
    } else {
        Write-Utf8File $stderrPath $wrapperError
    }
} finally {
    $terminal = @{ mode = $Mode; output_directory = $OutputDirectory; started_utc = $started; ended_utc = [DateTime]::UtcNow.ToString("o"); exit_code = $exitCode } |
        ConvertTo-Json -Compress
    Write-Utf8File (Join-Path $ControlDirectory "terminal.json") $terminal
}
exit $exitCode
