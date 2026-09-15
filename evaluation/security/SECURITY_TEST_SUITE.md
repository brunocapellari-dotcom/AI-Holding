# Security Test Suite — Holding Digital / AI OS

Esta matriz é um gate de ativação, não uma declaração de proteção já concluída. Um cenário só muda para `COVERED` quando existe enforcement no caminho operacional e teste automatizado reproduzível.

| Cenário | Estado atual | Controle/gate | Próxima evidência necessária |
| --- | --- | --- | --- |
| Vazamento de secret em Git | PARTIAL | secrets fora do código, WIF, Secret Manager | Gitleaks CI fail-closed + fixture sintética |
| Prompt injection | PARTIAL | tool authorization não deriva grants do prompt; private routing fail-closed | integrar ao MCP Gateway e executar corpus adversarial |
| Tool injection / ferramenta proibida | PARTIAL | `services.policy.tool_authorization` deny-by-default | integrar ao MCP Gateway e auditar toda chamada |
| Privilege escalation | PARTIAL | escopo solicitado deve ser subconjunto de grant; IAM least privilege | integration test contra credencial efêmera real |
| SQL injection | PARTIAL | SQLAlchemy/Pydantic e queries estruturadas | DAST contra staging autenticado |
| Path traversal | PARTIAL | exportação do Segundo Cérebro resolve e valida caminhos contra raiz | teste adversarial dedicado + sandbox integration |
| SSRF | NOT IMPLEMENTED | nenhum executor de fetch genérico deve ser ativado antes do egress policy | gateway de egress + allowlist + testes metadata/internal IP |
| Command injection | NOT IMPLEMENTED | coding/shell execution ainda não operacional | sandbox + structured argv + corpus adversarial |
| Acesso entre projetos | PARTIAL | ToolGrant exige `project_key` exato | RBAC de dados/API por projeto + integration tests |
| Acesso sem autenticação | COVERED CORE | Cloud Run IAM + token verificado + auth tests | manter em production acceptance |
| Manipulação de webhook | NOT IMPLEMENTED | webhooks não devem entrar sem assinatura/replay protection | adapter assinado + nonce/timestamp/idempotency tests |
| Dependência comprometida | PARTIAL | pip-audit, Trivy, SBOM, pinned security actions | provenance/lock policy + secret/license scans |
| Ação externa por conteúdo não confiável | PARTIAL | mutating scope + untrusted source exige humano | integrar policy ao MCP/tool gateway |
| Ação irreversível | COVERED POLICY | policy A0–A6 e tool contract exigem humano | manter regression tests |
| Segredo exposto a agente | PARTIAL | arquitetura Infisical/proxy definida, Secret Manager de transição | cutover com machine identities e teste de no-plaintext logs |
| Egress não autorizado | NOT IMPLEMENTED | alvo é allowlist/network policy | gateway/sandbox network tests |
| Restore inválido | NOT IMPLEMENTED | Cloud SQL backup/PITR existe | restore periódico isolado + integrity/readiness test |

## Gate de ativação por superfície

- **MCP Gateway:** não ativar ferramentas mutáveis até tool authorization, project scope, audit e egress allowlist estarem conectados.
- **OpenHands / coding agents:** não ativar autonomia de código desconhecido até sandbox, workspace isolado, no-host-mount, no-Docker-socket e egress policy passarem.
- **AgentOS:** não substituir PMO recorrente atual até parity acceptance provar idempotência, fila durável, auth, policy e recuperação.
- **LiteLLM/vLLM:** não enviar carga privada para endpoint remoto sem autorização explícita e classificação de dados.
- **Infisical:** não remover Secret Manager antes de leitura paralela, rotação/revogação e acceptance.

## Evidência automatizada já adicionada nesta migração

- `tests/test_tool_authorization.py`: ferramenta proibida, escalation de scope, isolamento por projeto, conteúdo não confiável, side effect externo e irreversibilidade.
- `tests/test_model_router.py`: privacidade fail-closed e independência lógica do auditor.
- `tests/test_scheduler_security.py`: WIF branch-bound, ausência de chave estática e proibição de roles administrativas no scheduler.
- testes existentes de autenticação/policy/identidade continuam obrigatórios.

Nenhum item `PARTIAL` ou `NOT IMPLEMENTED` deve ser descrito por Hermes como proteção concluída.