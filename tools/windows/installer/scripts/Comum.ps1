Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Script:PackageRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Script:Registry = Get-Content -Raw -Encoding UTF8 (Join-Path $Script:PackageRoot 'projetos.json') | ConvertFrom-Json
$Script:Workspace = Join-Path $env:USERPROFILE $Script:Registry.workspace
$Script:RepositoryDir = Join-Path $Script:Workspace 'repos'
$Script:LogDir = Join-Path $Script:Workspace 'logs'
function Ensure-Directories { foreach ($p in @($Script:Workspace,$Script:RepositoryDir,$Script:LogDir)) { New-Item -ItemType Directory -Path $p -Force | Out-Null } }
function Command-Exists([string] $Name) { return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue) }
# Windows PowerShell 5.1 transforma stderr redirecionado de comandos nativos em erro terminante quando
# ErrorActionPreference = 'Stop'. Toda chamada nativa com 2> ou *> deve passar por Invoke-Native;
# o resultado e verificado por $LASTEXITCODE (Validar.ps1 impede regressao).
function Invoke-Native([scriptblock] $Command) {
  $previous = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  try { & $Command } finally { $ErrorActionPreference = $previous }
}
function Refresh-UserPath {
  $paths = @($env:PATH,[Environment]::GetEnvironmentVariable('Path','Machine'),[Environment]::GetEnvironmentVariable('Path','User'),(Join-Path $env:APPDATA 'npm'),(Join-Path $env:USERPROFILE '.local\bin'),(Join-Path $env:ProgramFiles 'Git\cmd'),(Join-Path $env:ProgramFiles 'GitHub CLI'))
  $env:PATH = (($paths | Where-Object { $_ } | Select-Object -Unique) -join ';')
}
function Test-ExpectedOrigin([string] $Dir,[string] $Name) {
  $expected = @(('https://github.com/{0}/{1}.git' -f $Script:Registry.owner,$Name),('https://github.com/{0}/{1}' -f $Script:Registry.owner,$Name),('git@github.com:{0}/{1}.git' -f $Script:Registry.owner,$Name))
  $actual = [string](Invoke-Native { & git -C $Dir remote get-url origin 2>$null })
  return ($LASTEXITCODE -eq 0 -and ($actual.Trim().TrimEnd('/') -in $expected))
}
function Sync-Repositories {
  Ensure-Directories
  if (-not (Command-Exists 'git')) { throw 'Git nao instalado. Execute 01-INSTALAR-E-SINCRONIZAR.cmd primeiro.' }
  $failed = @()
  foreach ($r in $Script:Registry.repositories) {
    $dir = Join-Path $Script:RepositoryDir $r.name
    $origin = ('https://github.com/{0}/{1}.git' -f $Script:Registry.owner,$r.name)
    Write-Host ("`n[{0}] {1}" -f $r.project,$r.name) -ForegroundColor Cyan
    if (Test-Path $dir) {
      if (-not (Test-Path (Join-Path $dir '.git'))) { Write-Warning "$dir existe e nao e repositorio: preservado."; $failed += $r.name; continue }
      if (-not (Test-ExpectedOrigin $dir $r.name)) { Write-Warning 'Remote inesperado: nao atualizado.'; $failed += $r.name; continue }
      $changes = & git -C $dir status --porcelain
      if ($LASTEXITCODE -ne 0) { $failed += $r.name; continue }
      if ($changes) { Write-Warning 'Alteracoes locais: nao atualizar nem sobrescrever.'; $failed += $r.name; continue }
      & git -C $dir pull --ff-only | Out-Host
      if ($LASTEXITCODE -ne 0) { Write-Warning 'Falha no fast-forward; preservado.'; $failed += $r.name }
    } else {
      & git clone --origin origin --depth 1 $origin $dir
      if ($LASTEXITCODE -ne 0) { Write-Warning ('Nao foi possivel clonar: ' + $r.name); $failed += $r.name }
    }
  }
  return $failed
}
function Write-Inventory {
  Ensure-Directories
  $lines = @(('RELATORIO DE REPOSITORIOS - ' + (Get-Date -Format 'yyyy-MM-dd HH:mm')),('Pasta: ' + $Script:RepositoryDir),'')
  foreach ($r in $Script:Registry.repositories) {
    $dir = Join-Path $Script:RepositoryDir $r.name
    $status = if (Test-Path (Join-Path $dir '.git')) { 'LOCAL' } else { 'NAO CLONADO' }
    $phase = if ($r.active) { 'ATIVO' } else { 'PAUSADO' }
    $lines += ('[{0}] {1}: {2} ({3})' -f $phase,$r.name,$status,$r.project)
  }
  $path = Join-Path $Script:Workspace 'RELATORIO.txt'
  $lines | Set-Content -Encoding UTF8 $path
  Write-Host ("`nRelatorio: " + $path) -ForegroundColor Green
}
