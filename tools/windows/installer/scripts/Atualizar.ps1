. (Join-Path $PSScriptRoot 'Comum.ps1')
Refresh-UserPath
$pending = @(Sync-Repositories)
Write-Inventory
if ($pending.Count -gt 0) { Write-Warning ('Nao atualizados: ' + ($pending -join ', ')) }

if ($pending.Count -gt 0) { exit 1 }
