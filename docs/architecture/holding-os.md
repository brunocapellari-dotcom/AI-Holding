# Holding Digital / AI OS — Arquitetura oficial

Status: **oficial**. Esta definição substitui decisões anteriores quando houver conflito, preservando regras de negócio, projetos, agentes, integrações e níveis A0–A6 ainda válidos.

## 1. Responsabilidade do sistema

A Holding é o sistema de gestão, decisão, coordenação, execução, segurança e controle do portfólio. Ela mantém estado operacional, não conhecimento canônico.

Fontes de verdade:

| Domínio | Fonte canônica |
| --- | --- |
| Estado operacional da Holding | PostgreSQL / Control Plane |
| Código e histórico de software | GitHub |
| Conhecimento consolidado | Obsidian / Segundo Cérebro |
| Dados analíticos das unidades | armazenamentos próprios de cada unidade, como BigQuery quando aplicável |
| Segredos | Infisical após migração; GCP Secret Manager apenas como ponte controlada |

## 2. Cadeia de comando

```text
Owner / Conselho Humano
        ↓
      Hermes
        ↓
Holding Control Plane
        ↓
CEO IA ─ PMO IA ─ Governança/Risco/Auditoria ─ Consultores
        ↓
Unidades / Projetos
        ↓
Agentes / Workers
```

Hermes não é um modelo. É a interface executiva persistente que lê o estado canônico, consulta o Segundo Cérebro, transforma ordens em trabalho estruturado, acompanha execução e apresenta somente fatos, riscos, bloqueios e decisões relevantes.

## 3. Runtime e execução

### Agno AgentOS

É o runtime principal para agentes, teams, workflows, filas duráveis, scheduler e human-in-the-loop. O Control Plane de domínio existente será montado como aplicação FastAPI base durante a migração. A persistência do AgentOS deve usar PostgreSQL em schema próprio para evitar mistura com as tabelas de domínio.

Não é permitido introduzir outro runtime geral em paralelo apenas por preferência de implementação. ADK, Microsoft Agent Framework, LangGraph, CrewAI e AutoGen ficam fora do caminho principal.

### Workers de engenharia

OpenHands é a camada operacional de coding agents. Claude Code e Codex são workers especializados. O fluxo padrão é:

```text
PMO → tarefa aprovada → OpenHands/workspace isolado → Claude Code/Codex
→ branch/worktree → testes → revisão → PR → CI → auditoria → merge por política
```

Nenhum coding worker recebe permissão implícita para merge, produção, segredo ou recurso externo.

## 4. Modelos

LiteLLM é o gateway central. O Control Plane e AgentOS não devem carregar chaves diretas de provedores quando o gateway estiver operacional.

O gateway deverá aplicar:
- alias lógico de modelos, sem acoplamento a nomes de fornecedor no domínio;
- budgets por projeto, agente e classe de trabalho;
- rate limits;
- retry e fallback explicitamente autorizados;
- tags de custo e rastreio;
- negação quando o orçamento exigir fail-closed;
- fallback para modelos locais/zero-cost apenas quando compatível com a política da tarefa.

## 5. Ferramentas, segredos e sandbox

Fluxo obrigatório:

```text
IA solicita
→ Policy/Gateway autoriza
→ identidade/escopo é validado
→ credencial mínima é injetada
→ sandbox executa quando necessário
→ resultado/evidência é registrado
→ auditoria verifica
```

Docker MCP Gateway é a fronteira padrão para MCPs e ferramentas externas. Infisical é o destino para credenciais e machine identities. Docker é o isolamento comum; E2B/microVM é reservado para código não confiável ou de risco elevado.

Prompt nunca concede permissão.

## 6. Observabilidade

Langfuse é a camada central de observabilidade de IA. Traces devem carregar, quando permitido:
- project_id;
- agent_id;
- task_id/run_id;
- modelo/alias;
- custo e tokens;
- latência;
- retries/fallbacks;
- resultado de policy checks;
- avaliação e erro.

Dados sensíveis devem ser redigidos antes de observabilidade. Prompts completos não são obrigatórios quando contiverem material restrito.

## 7. Autonomia A0–A6

Autonomia mede capacidade decisória dentro de políticas. Permissão mede autoridade técnica. São independentes.

Um agente A5 pode analisar e escolher a próxima ação de forma ampla e ainda assim não possuir credencial de produção, autorização financeira ou permissão para excluir dados. A promoção de autonomia depende de evidência operacional, testes e histórico auditável.

## 8. Segundo Cérebro

Fluxo oficial:

```text
Segundo Cérebro → contexto → Holding → decisão → execução
→ resultado/evidência → fila de validação do Segundo Cérebro
```

A Holding pode manter referências, caches operacionais, hashes, provenance e estado de transferência. Não pode declarar seus próprios registros como conhecimento canônico.

As tabelas `knowledge_claims`/`knowledge_outcomes` existentes são legado de transição. Não serão apagadas automaticamente. Novas promoções para `canonical` ficam proibidas; registros antigos permanecem legíveis para migração e auditoria.

## 9. Dependências condicionais

Temporal entra somente se os mecanismos duráveis do AgentOS falharem em requisitos comprovados. OpenFGA entra somente quando a autorização atual não conseguir expressar a granularidade necessária. Phoenix não duplica Langfuse na fase inicial.

## 10. Critério de migração

Nenhuma etapa pode degradar as garantias já conquistadas: idempotência, auditabilidade, restrição A0–A6, segurança por identidade, banco privado, CI, migration round-trip, vulnerability gate, aceitação de produção e rollback operacional.
