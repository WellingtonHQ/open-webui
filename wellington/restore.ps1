# Usage: .\wellington\restore.ps1 -BackupPath 'M:\Backups\openwebui\manual\webui-....sqlite3'
# A folder selects its newest webui-*.sqlite3 or webui.db, including subfolders.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$BackupPath,
    [switch]$CheckOnly,
    [string]$ComposeFile = (Join-Path $PSScriptRoot 'docker-compose.custom.yaml')
)

$ErrorActionPreference = 'Stop'
$ComposeFile = (Resolve-Path -LiteralPath $ComposeFile).Path
$item = Get-Item -LiteralPath $BackupPath
if ($item.PSIsContainer) {
    $item = Get-ChildItem -LiteralPath $item.FullName -File -Recurse |
        Where-Object { $_.Name -like 'webui-*.sqlite3' -or $_.Name -eq 'webui.db' } |
        Sort-Object LastWriteTimeUtc, FullName -Descending |
        Select-Object -First 1
    if (-not $item) { throw 'No OpenWebUI database backups found in the specified folder.' }
}

function Invoke-Compose {
    param([string[]]$DockerArguments)
    & docker compose -f $ComposeFile @DockerArguments
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose failed: $($DockerArguments -join ' ')" }
}

Write-Host "Selected backup: $($item.FullName)"
Invoke-Compose -DockerArguments @('build', 'open-webui-backup')
# Mount the parent folder read-only so the helper can also detect journal files.
$inputPath = "/restore-input/$($item.Name)"
$helper = @('run', '--rm', '--no-deps', '--volume', "$($item.DirectoryName):/restore-input:ro",
    '--entrypoint', 'python', 'open-webui-backup', '/restore.py', $inputPath)
Invoke-Compose -DockerArguments ($helper + @('--check-only'))
if ($CheckOnly) { return }

$running = @(Invoke-Compose -DockerArguments @('ps', '--status', 'running', '--services'))
$restart = @($running | Where-Object { $_ -in @('open-webui', 'open-webui-backup') })
try {
    Invoke-Compose -DockerArguments @('stop', 'open-webui-backup', 'open-webui')
    Invoke-Compose -DockerArguments $helper
} finally {
    # Preserve which services were running, including when restoration fails.
    if ($restart.Count -gt 0) {
        Invoke-Compose -DockerArguments (@('start') + $restart)
    }
}
Write-Host 'Restore completed. A safety backup of the previous database was saved in manual/ if it existed.'
