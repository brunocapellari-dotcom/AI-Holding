$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
foreach ($file in @('scripts/Instalar.ps1','scripts/Comum.ps1','scripts/Atualizar.ps1','scripts/Trabalhar-Local.ps1','projetos.json','README.md')) {
  if (-not (Test-Path -LiteralPath (Join-Path $root $file) -PathType Leaf)) { throw "Arquivo ausente: $file. Extraia TODO o ZIP." }
}
Get-ChildItem -LiteralPath $PSScriptRoot -Filter '*.ps1' | ForEach-Object {
  $tokens = $null; $errors = $null
  $null = [System.Management.Automation.Language.Parser]::ParseFile($_.FullName,[ref]$tokens,[ref]$errors)
  if ($errors.Count) { throw ($errors | Out-String) }
}
# Regressao Windows PowerShell 5.1: redirecionamento de stderr de comando nativo precisa de Invoke-Native.
Get-ChildItem -LiteralPath $PSScriptRoot -Filter '*.ps1' | ForEach-Object {
  $n = 0
  foreach ($line in (Get-Content -LiteralPath $_.FullName -Encoding UTF8)) {
    $n++
    if ($line -match '&\s*(git|gh|claude|codex|npm|npm\.cmd|winget)\b.*(2>|\*>)' -and $line -notmatch 'Invoke-Native') { throw ('Redirecionamento nativo sem Invoke-Native: ' + $_.Name + ':' + $n) }
  }
}
$registry = Get-Content -LiteralPath (Join-Path $root 'projetos.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if (@($registry.repositories).Count -ne 12) { throw 'Esperados 12 repositorios.' }
if (@($registry.repositories.name | Select-Object -Unique).Count -ne 12) { throw 'Nomes duplicados.' }
foreach ($r in $registry.repositories) { if ($r.name -notmatch '^[A-Za-z0-9_-]+$') { throw 'Nome de repositorio invalido.' }; Write-Host $r.name }
foreach ($pausedName in @('Game-Studio','Personal-Performance-Health-OS')) {
  $paused = @($registry.repositories | Where-Object { $_.name -eq $pausedName })
  if ($paused.Count -ne 1 -or $paused[0].active) { throw ('Projeto pausado indevidamente ativo: ' + $pausedName) }
}
if (@($registry.repositories | Where-Object { $_.active }).Count -ne 10) { throw 'Esperados 10 projetos ativos e 2 pausados.' }
Write-Host 'OK: pacote completo, sintaxe PowerShell valida, 12 repositorios. Nada instalado ou clonado.'
