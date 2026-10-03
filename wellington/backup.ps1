# Usage: .\wellington\backup.ps1
# Manual snapshots are saved in OPENWEBUI_BACKUP_DIR/manual and never pruned.
[CmdletBinding()]
param(
    [string]$ComposeFile = (Join-Path $PSScriptRoot 'docker-compose.custom.yaml')
)

$ErrorActionPreference = 'Stop'
$ComposeFile = (Resolve-Path -LiteralPath $ComposeFile).Path

& docker compose -f $ComposeFile build open-webui-backup
if ($LASTEXITCODE -ne 0) { throw 'Could not build the backup helper image.' }

& docker compose -f $ComposeFile run --rm --no-deps open-webui-backup --manual
if ($LASTEXITCODE -ne 0) { throw 'Manual backup failed. See the Docker output above.' }

Write-Host 'Manual backup completed. No previous backups were deleted.'
