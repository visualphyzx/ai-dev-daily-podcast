# Run this once in an elevated PowerShell to create the daily Windows Task Scheduler job.
# It runs run_daily.py every morning at 6:30 AM.

$TaskName = "AIPodcastDaily"
$PodcastDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = (Get-Command python).Source

# Load .env file for environment variables (create .env from .env.example first)
$EnvFile = Join-Path $PodcastDir ".env"
if (-not (Test-Path $EnvFile)) {
    Write-Error ".env file not found at $EnvFile. Copy .env.example to .env and fill in your keys."
    exit 1
}

# Build the action — python run_daily.py, with env vars loaded via a wrapper script
$WrapperScript = Join-Path $PodcastDir "run_with_env.ps1"
@"
# Auto-generated wrapper — loads .env and runs the pipeline
Get-Content "$EnvFile" | ForEach-Object {
    if (`$_ -match '^([^#][^=]*)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable(`$matches[1].Trim(), `$matches[2].Trim(), 'Process')
    }
}
Set-Location "$PodcastDir"
& "$PythonExe" run_daily.py
"@ | Set-Content $WrapperScript

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NonInteractive -WindowStyle Hidden -File `"$WrapperScript`"" `
    -WorkingDirectory $PodcastDir

$Trigger = New-ScheduledTaskTrigger -Daily -At "06:30AM"

$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -WakeToRun

# Remove existing task if present
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -RunLevel Highest `
    -Description "Daily AI Dev Daily podcast generation"

Write-Host "Scheduled task '$TaskName' created. Runs daily at 6:30 AM."
Write-Host "To test: Start-ScheduledTask -TaskName '$TaskName'"
