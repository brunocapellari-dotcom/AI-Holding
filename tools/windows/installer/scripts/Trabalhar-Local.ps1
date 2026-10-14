param([int] $MaxProjects = 10,[switch] $Simular)
. (Join-Path $PSScriptRoot 'Comum.ps1')
Refresh-UserPath
Ensure-Directories
Write-Host 'ATENCAO: ESTE MODO E LOCAL. O NOTEBOOK PRECISA FICAR LIGADO.' -ForegroundColor Yellow
Write-Host 'Para trabalhar com o notebook desligado, use Codex Cloud e Claude Code Remote (opcao 03).'
if (-not $Simular) {
  if (-not (Command-Exists 'codex') -or -not (Command-Exists 'claude')) { throw 'Instale e autentique ambos os agentes antes de executar.' }
  $confirmation = Read-Host 'Confirme o processamento SEQUENCIAL, com limites de sua assinatura. Digite EXECUTAR'
  if ($confirmation -ne 'EXECUTAR') { Write-Host 'Cancelado.'; exit 0 }
}
$paused = @('Game-Studio','Personal-Performance-Health-OS')
$selected = @($Script:Registry.repositories | Where-Object { $_.active -and $_.name -notin $paused } | Sort-Object priority,name | Select-Object -First $MaxProjects)
foreach ($r in $selected) {
  $repo = Join-Path $Script:RepositoryDir $r.name
  if (-not (Test-Path (Join-Path $repo '.git'))) { Write-Warning ('Repo nao clonado: ' + $r.name); continue }
  if (-not (Test-ExpectedOrigin $repo $r.name)) { Write-Warning ('Remote inesperado; agentes nao executados: ' + $r.name); continue }
  $dirty = & git -C $repo status --porcelain
  if ($LASTEXITCODE -ne 0 -or $dirty) { Write-Warning ('Repo com alteracoes locais ou erro: ' + $r.name + ' (preservado)'); continue }
  $branch = 'ai/go-live-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
  $prompt = @"
Trabalhe SOMENTE neste repositorio ($($r.name)). MISSÃO: $($r.mission)
Audite a implementacao existente; entregue pelo menos uma correcao material de P0/P1 com teste reproduzivel, preservando dados, integracoes, schemas, seguranca e historico. Nao escreva apenas planos ou documentos.
Nao executar deploy, transferencias, pagamento, API paga, trades reais, exclusao de dados ou comandos destrutivos. Nao ler/imprimir segredos. Nao alterar outros repositorios. Implementar mudancas reversiveis e relatar testes executados e riscos.
Se bloqueado, documente o motivo tecnico e o comando exato de verificacao, sem inventar sucesso. Nunca declarar go-live sem E2E e readiness comprovados.
"@
  $out = Join-Path $Script:LogDir ($r.name+'-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
  if ($Simular) { Write-Host ("SIMULACAO: {0}: Codex implementa -> Claude revisa, saida {1}" -f $r.name,$out); continue }
  & git -C $repo switch -c $branch
  if ($LASTEXITCODE -ne 0) { Write-Warning 'Falha ao criar branch.'; continue }
  Write-Host ('Codex executando em ' + $r.name) -ForegroundColor Cyan
  $prompt | & codex exec -C $repo --sandbox workspace-write --output-last-message ($out+'-codex.txt') -
  if ($LASTEXITCODE -ne 0) { Write-Warning 'Codex interrompido; nao executarei Claude automaticamente.'; continue }
  Write-Host 'Claude: revisao de seguranca e testes (modo somente planejamento)' -ForegroundColor Cyan
  $reviewPrompt = $prompt + "`nRevise criticamente as mudancas nao commitadas do Codex; nao modifique arquivos, relate falhas de testes, seguranca e integridade dos dados."
  Push-Location -LiteralPath $repo
  try { Invoke-Native { & claude -p --permission-mode plan $reviewPrompt 2>&1 | Out-File -Encoding utf8 ($out+'-claude-review.txt') } } finally { Pop-Location }
  if ($LASTEXITCODE -ne 0) { Write-Warning 'Claude nao completou revisao.' }
  Write-Host ('Branch local preservada para revisao: ' + $branch) -ForegroundColor Green
}
Write-Host 'FIM. Nenhum deploy/push/merge automatico realizado. Veja logs e branches antes de publicar.'
