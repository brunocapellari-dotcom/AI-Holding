# AI Holding — instalador Windows corrigido

1. Clique com o botão direito no ZIP e escolha **Extrair Tudo**. Não execute na visualização do ZIP.
2. Abra a pasta extraída AI-HOLDING-INSTALADOR. Execute **00-VALIDAR-PACOTE.cmd**.
3. Execute **01-INSTALAR-E-SINCRONIZAR.cmd**. Tenha internet e energia; aprove as instalações do Windows e faça login no GitHub quando solicitado.
4. Abra um novo terminal e execute `codex login` e `claude` para autenticar suas contas.

O erro original ocorre quando o Explorer disponibiliza somente o CMD em uma pasta temporária: scripts/Instalar.ps1 não acompanha o arquivo. Agora todos os inicializadores de scripts verificam arquivos essenciais e encerram com orientação e código 2. Não tentamos adivinhar qual ZIP recuperar. Extraia sempre o pacote completo, inclusive scripts.

## Conteúdo e limites
Git, GitHub CLI, Node LTS/npm, Python 3.12, Claude Code (winget) e Codex CLI (npm). Windows com Windows PowerShell 5.1 e winget/App Installer. Sem Docker, WSL obrigatório, banco local ou modelos locais. Claude requer Git Bash, fornecido pelo Git para Windows; se não localizado, configure CLAUDE_CODE_GIT_BASH_PATH com o caminho do bash.exe conforme a documentação oficial.

Os 12 nomes e missões originais são preservados em projetos.json: AI-Holding, Hermes-AI-Platform, Research-AI, Second-Brain, AgroLogMT, WHATSAPP_AI, Geopolitical-Watch, Mercado-Financeiro, Sports-Intelligence, Content-Factory, Game-Studio, Personal-Performance-Health-OS. Apenas os 10 projetos ativos são sincronizados e elegíveis para o lote de trabalho. Game Studio e Personal Performance & Health OS permanecem pausados: sem clone/atualização, agentes, testes ou deploy; repositórios remotos e arquivos locais existentes são preservados. Repositórios privados exigem acesso da conta GitHub.

Repos: %USERPROFILE%\AI-Holding-Workspace\repos. Relatório: RELATORIO.txt nesse workspace. Logs: logs. O relatório indica presença local, não saúde do projeto. Alterações locais e remotes inesperados são preservados e reportados como pendências; não há reset. Reexecute 01 após corrigir pendências. 02 sincroniza; 03 abre páginas dos agentes; 04 executa trabalho local com confirmação e pode consumir quota; 05 simula o lote. Abrir uma página não configura execução remota.

Para validação sem instalar/clonar: 00-VALIDAR-PACOTE.cmd ou 01-INSTALAR-E-SINCRONIZAR.cmd -Validar. Códigos: 0 etapa concluída, 1 erro/pendência, 2 pacote incompleto. Para testes automatizados, defina AI_HOLDING_NO_PAUSE=1. O teste valida arquivos, sintaxe e cadastro, sem autenticação ou rede.

Este pacote prepara ferramentas e clones; não instala dependências específicas de cada aplicação, não faz deploy e não comprova go-live. Builds, testes E2E, segredos, persistência e operação remota precisam de validação própria. Não foi executada instalação real durante a verificação do ZIP.

Fontes oficiais consultadas: https://developers.openai.com/codex/cli e https://code.claude.com/docs/en/setup

## Correções v3 (fonte canônica: AI-Holding/tools/windows/installer)
- Windows PowerShell 5.1 com `ErrorActionPreference = 'Stop'` transforma stderr redirecionado de comando nativo em erro terminante. `gh auth status *> $null` abortava a instalação justamente quando o GitHub ainda não estava autenticado (primeira execução); o mesmo valia para `git remote get-url 2>$null` e `claude ... 2>&1`. Agora essas chamadas passam por `Invoke-Native`, e `Validar.ps1` falha se surgir um novo redirecionamento nativo fora dele.
- O lote local (04) não executa Codex/Claude em repositório com remote inesperado (mesma verificação da sincronização).
- Cabeçalho do RELATORIO.txt saía em uma única linha (precedência da vírgula sobre `+`).
- `-Validar` retorna código 1 com mensagem quando a validação falha.
- A verificação final de ferramentas usa `py` e `npm.cmd`, evitando o falso positivo do alias `python` da Microsoft Store.
- `tools/windows/setup-all-projects.ps1` (versão anterior, mesmo defeito) foi removido para manter uma única implementação.

Testado em PowerShell 7.4 (Linux) com `git` simulado: validação, sincronização (repositório limpo, alterações locais, remote inesperado, sem origin, pasta não-git, falha de fast-forward, clone ausente e falha de clone), simulação do lote e teste negativo do bloqueio de regressão. O comportamento específico do Windows PowerShell 5.1 e os arquivos CMD não foram executados em Windows nesta revisão.
