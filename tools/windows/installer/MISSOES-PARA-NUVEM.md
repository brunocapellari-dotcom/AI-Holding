# MISSÕES PARA CODEX CLOUD E CLAUDE CODE REMOTE

**Modo recomendado para continuar com notebook desligado.**

1. Abra `03-ABRIR-AGENTES-NA-NUVEM.cmd`.
2. Em cada serviço, conecte sua conta GitHub aos repositórios. Isso pode exigir autorização e login.
3. Escolha o repositório e cole a missão correspondente.
4. Peça que o agente trabalhe em sua própria branch e abra PR, sem auto-merge nem deploy para produção.
5. Divida o trabalho entre Codex (implementação e testes) e Claude (revisão, validação independente e correções em branch separada ou PR), sem ambos editarem o mesmo branch ao mesmo tempo.
6. Os jobs remotos podem continuar após o notebook desligar quando lançados na modalidade hospedada. Limites e cobranças dependem de seu plano.

## Política transversal

Usar código já existente; implementar antes de documentar; P0/P1 primeiro; testes reais; histórico e backup; nenhuma despesa cloud nova nem API paga sem autorização; não usar GitHub Actions nem runners próprios como dependência; preservar segredos; não operar dinheiro real; não publicar em produção sem segurança, health/readiness, backup e testes E2E.

---

## Holding / Control Plane — AI-Holding
Status: ATIVO

Repositório: brunocapellari-dotcom/AI-Holding.

Objetivo: Entregar Control Plane realmente operacional: registro de projetos, estados, health, integrações, métricas reais, bloqueios e trilha de auditoria. Corrigir deploy remoto, autenticação, persistência, backup/restore e E2E com Hermes. Não criar painel de dados simulados.

Audite código, testes, estrutura, deploy e dependências reais primeiro. Implemente melhorias operacionais verificáveis P0/P1 no repositório atual, inclua teste reproduzível e resultados, preserve componentes úteis e histórico. Trabalhe em branch isolada, prepare pull request, não faça merge nem deploy automaticamente. Se houver credencial, faturamento, licença, permissão ou risco irreversível, pare essa ação e registre bloqueio; continue as partes independentes. Entrega obrigatória: mudanças de código, testes executados, diferenças reais, blockers e como verificar, sem porcentagens inventadas nem relatos de go-live sem evidência.

## Hermes / orquestrador — Hermes-AI-Platform
Status: ATIVO

Repositório: brunocapellari-dotcom/Hermes-AI-Platform.

Objetivo: Fechar o ciclo de execução real: worker persistente, filas, retry, DLQ, outbox, checkpoint, políticas, integração Holding, autenticação e E2E em nuvem. Não depender de localhost ou notebook. Preservar controles de autorização humana.

Audite código, testes, estrutura, deploy e dependências reais primeiro. Implemente melhorias operacionais verificáveis P0/P1 no repositório atual, inclua teste reproduzível e resultados, preserve componentes úteis e histórico. Trabalhe em branch isolada, prepare pull request, não faça merge nem deploy automaticamente. Se houver credencial, faturamento, licença, permissão ou risco irreversível, pare essa ação e registre bloqueio; continue as partes independentes. Entrega obrigatória: mudanças de código, testes executados, diferenças reais, blockers e como verificar, sem porcentagens inventadas nem relatos de go-live sem evidência.

## Pesquisa — Research-AI
Status: ATIVO

Repositório: brunocapellari-dotcom/Research-AI.

Objetivo: Tornar pesquisa E2E funcional: descobrir fontes, testar APIs/datasets, baixar apenas conteúdo autorizado, proveniência, licença, pacote de pesquisa estruturado e entrega a Knowledge Factory e projetos clientes. Testar com casos reais.

Audite código, testes, estrutura, deploy e dependências reais primeiro. Implemente melhorias operacionais verificáveis P0/P1 no repositório atual, inclua teste reproduzível e resultados, preserve componentes úteis e histórico. Trabalhe em branch isolada, prepare pull request, não faça merge nem deploy automaticamente. Se houver credencial, faturamento, licença, permissão ou risco irreversível, pare essa ação e registre bloqueio; continue as partes independentes. Entrega obrigatória: mudanças de código, testes executados, diferenças reais, blockers e como verificar, sem porcentagens inventadas nem relatos de go-live sem evidência.

## Obsidian / Segundo Cérebro — Second-Brain
Status: ATIVO

Repositório: brunocapellari-dotcom/Second-Brain.

Objetivo: Consolidar ingestão de claims, fontes, evidências, entidades e notas Markdown/Obsidian, deduplicação, auditoria e conexões com Research, AgroLog, Holding e Hermes; preservar base canônica, migrar sem perda e testar restore.

Audite código, testes, estrutura, deploy e dependências reais primeiro. Implemente melhorias operacionais verificáveis P0/P1 no repositório atual, inclua teste reproduzível e resultados, preserve componentes úteis e histórico. Trabalhe em branch isolada, prepare pull request, não faça merge nem deploy automaticamente. Se houver credencial, faturamento, licença, permissão ou risco irreversível, pare essa ação e registre bloqueio; continue as partes independentes. Entrega obrigatória: mudanças de código, testes executados, diferenças reais, blockers e como verificar, sem porcentagens inventadas nem relatos de go-live sem evidência.

## AgroLog / agro e logística — AgroLogMT
Status: ATIVO

Repositório: brunocapellari-dotcom/AgroLogMT.

Objetivo: Entregar cadeia E2E de dados reais agrícolas, clima, safra, preços, line-up, logística e fretes anunciados via WhatsApp, com dados históricos, proveniência, validação e interface integrada. PROIBIDO média municipal de frete; consolidar por ponto de embarque+transportadora+destino+condições, sem inventar cotação negociada.

Audite código, testes, estrutura, deploy e dependências reais primeiro. Implemente melhorias operacionais verificáveis P0/P1 no repositório atual, inclua teste reproduzível e resultados, preserve componentes úteis e histórico. Trabalhe em branch isolada, prepare pull request, não faça merge nem deploy automaticamente. Se houver credencial, faturamento, licença, permissão ou risco irreversível, pare essa ação e registre bloqueio; continue as partes independentes. Entrega obrigatória: mudanças de código, testes executados, diferenças reais, blockers e como verificar, sem porcentagens inventadas nem relatos de go-live sem evidência.

## WhatsApp Freight Intelligence — WHATSAPP_AI
Status: ATIVO

Repositório: brunocapellari-dotcom/WHATSAPP_AI.

Objetivo: Garantir ingestão autorizada de mensagens, extração de ofertas, entity resolution, deduplicação histórica e atualização de anúncio de frete por ponto de embarque+transportadora+destino+produto+condições; preservar versões e proveniência; integrar AgroLog. Sem burlar regras do WhatsApp.

Audite código, testes, estrutura, deploy e dependências reais primeiro. Implemente melhorias operacionais verificáveis P0/P1 no repositório atual, inclua teste reproduzível e resultados, preserve componentes úteis e histórico. Trabalhe em branch isolada, prepare pull request, não faça merge nem deploy automaticamente. Se houver credencial, faturamento, licença, permissão ou risco irreversível, pare essa ação e registre bloqueio; continue as partes independentes. Entrega obrigatória: mudanças de código, testes executados, diferenças reais, blockers e como verificar, sem porcentagens inventadas nem relatos de go-live sem evidência.

## Monitor de Conflitos — Geopolitical-Watch
Status: ATIVO

Repositório: brunocapellari-dotcom/Geopolitical-Watch.

Objetivo: Corrigir falhas de memória no Render de 512MiB, separar jobs pesados do servidor web, validar endpoints, segurança, coletores, histórico e mapas com dados reais, health/readiness e alerta. Validar disponibilidade fora do notebook.

Audite código, testes, estrutura, deploy e dependências reais primeiro. Implemente melhorias operacionais verificáveis P0/P1 no repositório atual, inclua teste reproduzível e resultados, preserve componentes úteis e histórico. Trabalhe em branch isolada, prepare pull request, não faça merge nem deploy automaticamente. Se houver credencial, faturamento, licença, permissão ou risco irreversível, pare essa ação e registre bloqueio; continue as partes independentes. Entrega obrigatória: mudanças de código, testes executados, diferenças reais, blockers e como verificar, sem porcentagens inventadas nem relatos de go-live sem evidência.

## Mercado Financeiro — Mercado-Financeiro
Status: ATIVO

Repositório: brunocapellari-dotcom/Mercado-Financeiro.

Objetivo: Entregar ingestão histórica B3/CVM/BCB/NEFIN, normalização e auditoria de datasets, backtests sem data leakage, risk engine, paper trading, observabilidade e relatórios. Proibir dinheiro real sem aprovação humana.

Audite código, testes, estrutura, deploy e dependências reais primeiro. Implemente melhorias operacionais verificáveis P0/P1 no repositório atual, inclua teste reproduzível e resultados, preserve componentes úteis e histórico. Trabalhe em branch isolada, prepare pull request, não faça merge nem deploy automaticamente. Se houver credencial, faturamento, licença, permissão ou risco irreversível, pare essa ação e registre bloqueio; continue as partes independentes. Entrega obrigatória: mudanças de código, testes executados, diferenças reais, blockers e como verificar, sem porcentagens inventadas nem relatos de go-live sem evidência.

## Inteligência Esportiva — Sports-Intelligence
Status: ATIVO

Repositório: brunocapellari-dotcom/Sports-Intelligence.

Objetivo: Completar pipeline de vídeo para tracking, eventos, métricas, scouting e análise com testes E2E; preservar integração dados históricos, validação e limites de uso. Modelos preditivos com avaliação fora da amostra; sem apostas reais automáticas.

Audite código, testes, estrutura, deploy e dependências reais primeiro. Implemente melhorias operacionais verificáveis P0/P1 no repositório atual, inclua teste reproduzível e resultados, preserve componentes úteis e histórico. Trabalhe em branch isolada, prepare pull request, não faça merge nem deploy automaticamente. Se houver credencial, faturamento, licença, permissão ou risco irreversível, pare essa ação e registre bloqueio; continue as partes independentes. Entrega obrigatória: mudanças de código, testes executados, diferenças reais, blockers e como verificar, sem porcentagens inventadas nem relatos de go-live sem evidência.

## Content Factory — Content-Factory
Status: ATIVO

Repositório: brunocapellari-dotcom/Content-Factory.

Objetivo: Finalizar brief->pesquisa->roteiro->storyboard->assets->voz->edição->legendas->QC->render->vídeo, com artefato final verificável, armazenamento, retries, custos controlados e direitos autorais. Integrar com projetos consumidores sem duplicar lógica.

Audite código, testes, estrutura, deploy e dependências reais primeiro. Implemente melhorias operacionais verificáveis P0/P1 no repositório atual, inclua teste reproduzível e resultados, preserve componentes úteis e histórico. Trabalhe em branch isolada, prepare pull request, não faça merge nem deploy automaticamente. Se houver credencial, faturamento, licença, permissão ou risco irreversível, pare essa ação e registre bloqueio; continue as partes independentes. Entrega obrigatória: mudanças de código, testes executados, diferenças reais, blockers e como verificar, sem porcentagens inventadas nem relatos de go-live sem evidência.

## Game Studio (3 jogos) — Game-Studio
Status: ATIVO

Repositório: brunocapellari-dotcom/Game-Studio.

Objetivo: Auditar três jogos: WorldWar Modern, gestão de corrida e futebol/ Brasfoot; corrigir bugs P0 com testes e builds jogáveis separados, mapas e IA quando aplicável; manter especificações canônicas existentes e evitar protótipos descartáveis.

Audite código, testes, estrutura, deploy e dependências reais primeiro. Implemente melhorias operacionais verificáveis P0/P1 no repositório atual, inclua teste reproduzível e resultados, preserve componentes úteis e histórico. Trabalhe em branch isolada, prepare pull request, não faça merge nem deploy automaticamente. Se houver credencial, faturamento, licença, permissão ou risco irreversível, pare essa ação e registre bloqueio; continue as partes independentes. Entrega obrigatória: mudanças de código, testes executados, diferenças reais, blockers e como verificar, sem porcentagens inventadas nem relatos de go-live sem evidência.

## Personal Performance & Health OS — Personal-Performance-Health-OS
Status: PAUSADO

Repositório: brunocapellari-dotcom/Personal-Performance-Health-OS.

Objetivo: PROJETO PAUSADO: apenas inventário, segurança e preservação do repositório. Não implementar, fazer deploy nem gerar custo até liberação explícita.

Audite código, testes, estrutura, deploy e dependências reais primeiro. Implemente melhorias operacionais verificáveis P0/P1 no repositório atual, inclua teste reproduzível e resultados, preserve componentes úteis e histórico. Trabalhe em branch isolada, prepare pull request, não faça merge nem deploy automaticamente. Se houver credencial, faturamento, licença, permissão ou risco irreversível, pare essa ação e registre bloqueio; continue as partes independentes. Entrega obrigatória: mudanças de código, testes executados, diferenças reais, blockers e como verificar, sem porcentagens inventadas nem relatos de go-live sem evidência.
