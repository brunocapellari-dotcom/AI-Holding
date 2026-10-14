param([switch] $Validar, [switch] $SemLogin)
if ($Validar) {
  try { & (Join-Path $PSScriptRoot 'Validar.ps1'); exit 0 } catch { Write-Host ('FALHA NA VALIDACAO: ' + $_.Exception.Message) -ForegroundColor Red; exit 1 }
}
. (Join-Path $PSScriptRoot 'Comum.ps1')
Ensure-Directories
$failures = New-Object System.Collections.Generic.List[string]
$log = Join-Path $Script:LogDir ('instalacao-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
Start-Transcript -Path $log | Out-Null
try {
  Write-Host 'AI HOLDING - INSTALACAO UNICA, TODOS OS REPOSITORIOS' -ForegroundColor Green
  $mem = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
  if ($mem -and ($mem.TotalPhysicalMemory / 1GB) -lt 6) { Write-Warning '4 GB RAM: instalando apenas ferramentas leves, sem Docker ou servicos pesados.' }
  if (-not (Command-Exists 'winget')) { throw 'Windows Package Manager (winget) indisponivel. Atualize o App Installer da Microsoft Store.' }
  function Add-Package([string] $id,[string] $command) {
    if (Command-Exists $command) { Write-Host "Ja instalado: $command"; return }
    Write-Host "Instalando $id..." -ForegroundColor Cyan
    & winget install --exact --id $id --silent --accept-package-agreements --accept-source-agreements --disable-interactivity
    if ($LASTEXITCODE -ne 0) { Write-Warning "Falha ao instalar: $id"; $failures.Add($id) }
    Refresh-UserPath
  }
  Add-Package 'Git.Git' 'git'
  Add-Package 'GitHub.cli' 'gh'
  Add-Package 'OpenJS.NodeJS.LTS' 'npm.cmd'
  Add-Package 'Python.Python.3.12' 'py'
  Add-Package 'Anthropic.ClaudeCode' 'claude'
  Refresh-UserPath
  if (-not (Command-Exists 'codex')) {
    if (Command-Exists 'npm.cmd') {
      Write-Host 'Instalando Codex CLI via npm oficial...' -ForegroundColor Cyan
      & npm.cmd install --global '@openai/codex'
      if ($LASTEXITCODE -ne 0) { Write-Warning 'Falha no npm Codex.'; $failures.Add('Codex CLI') }
    } else { Write-Warning 'Node/npm ausente: Codex nao instalado.'; $failures.Add('Codex CLI') }
  }
  Refresh-UserPath
  Write-Host "`nVERSOES:" -ForegroundColor Green
  # 'py' (launcher instalado pelo pacote Python) evita falso positivo do alias python da Microsoft Store.
  foreach ($cmd in @('git','gh','node','npm.cmd','py','claude','codex')) {
    if (Command-Exists $cmd) { Write-Host ('  '+$cmd+': OK') } else { Write-Warning ($cmd+': NAO ENCONTRADO NESTA SESSAO'); $failures.Add($cmd) }
  }
  if ((Command-Exists 'gh') -and (Command-Exists 'git')) {
    Invoke-Native { & gh auth status *> $null }
    if ($LASTEXITCODE -ne 0 -and -not $SemLogin) {
      Write-Host "`nLogin do GitHub necessario uma unica vez. Siga o navegador (nao cole tokens aqui)." -ForegroundColor Yellow
      & gh auth login --hostname github.com --web --git-protocol https
      if ($LASTEXITCODE -ne 0) { Write-Warning 'Sem GitHub autenticado; repositorios privados podem falhar.' }
    }
    & gh auth setup-git --hostname github.com
    if ($LASTEXITCODE -ne 0) { $failures.Add('GitHub credenciais') }
  }
  if (Command-Exists 'git') { $failedRepos = @(Sync-Repositories); foreach ($f in $failedRepos) { $failures.Add("repo: $f") } }
  Write-Inventory
  Write-Host "`nAUTENTICACOES DOS AGENTES: precisam ser feitas pelo titular da conta:" -ForegroundColor Yellow
  Write-Host '  codex login'
  Write-Host '  claude (abra o programa e use /login se solicitado)'
  Write-Host '  Sem tokens em scripts ou repositorios.'
  Write-Host "`nCodex e Claude em nuvem: execute 03-ABRIR-AGENTES-NA-NUVEM.cmd para conectar os repositorios." -ForegroundColor Green
  if ($failures.Count -gt 0) { Write-Warning ('Etapas pendentes: ' + ($failures -join ', ')) }
  else { Write-Host 'Instalacao/sincronizacao concluida (go-live remoto ainda requer configuracao).' -ForegroundColor Green }
} finally { Stop-Transcript | Out-Null }

if ($failures.Count -gt 0) { exit 1 }
