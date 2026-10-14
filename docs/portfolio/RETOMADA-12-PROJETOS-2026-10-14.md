# Retomada dos 12 projetos — auditoria de estado real (2026-10-14)

Executado por Claude Code em sessão de nuvem, sobre os branches padrão (`main`) clonados em 2026-10-14.
Escopo: inventário e verificação. Nenhum deploy, merge, custo, trade, pagamento ou publicação foi feito.
**Nada aqui comprova go-live.** Testes unitários verdes não substituem E2E, persistência real, backup/restore executado e operação remota.

## 1. Comprovado nesta sessão

| Projeto | Repositório | Testes no `main` (executados aqui) | PRs abertos |
|---|---|---|---:|
| Holding / Control Plane | AI-Holding | 129 passed, cobertura 90,79% | 13 |
| Hermes / orquestrador | Hermes-AI-Platform | 275 passed, cobertura 90,04% | 8 |
| Pesquisa | Research-AI | 25 passed, cobertura 93,05% | 1 |
| Segundo Cérebro | Second-Brain | 7 passed, cobertura 95,49% | 2 |
| AgroLog | AgroLogMT | gate `ci`: 7 etapas PASS, 11 BLOCKED por falta de evidência, 0 FAIL | 26 |
| WhatsApp Freight | WHATSAPP_AI | 112 passed, 4 skipped | 1 |
| Monitor de Conflitos | Geopolitical-Watch | 236 testes OK (unittest) | 10 |
| Mercado Financeiro | Mercado-Financeiro | 45 passed | 4 |
| Inteligência Esportiva | Sports-Intelligence | 69 passed (somente `services/api`) | 9 |
| Content Factory | Content-Factory | 22 passed | 8 |
| Game Studio | Game-Studio | 20 pass, 0 fail (`npm test`) | 4 |
| Health OS (PAUSADO) | Personal-Performance-Health-OS | **7 failed**, 79 passed, 2 skipped — não corrigido (projeto pausado) | 3 |

PRs prioritários testados localmente (head do PR):

- AI-Holding #68 (backup/restore PostgreSQL): 136 passed, cobertura 90,79%.
- Hermes #32 (fairness da fila de prioridade): 276 passed, cobertura 90,03% (venv isolado do branch).
- AI-Holding #64 (control plane operacional): **1 failed**, 230 passed. `tests/test_cloudbuild_contract.py::test_quality_cloud_build_is_low_privilege_and_provenance_gated` falha porque o commit `cc1ae55` removeu `images:`, `source-commit.txt` e `build-id.txt` do `cloudbuild.yaml` (zero custo) sem atualizar o contrato de proveniência. **Decisão humana:** manter zero custo (ajustar contrato e release) ou manter release com proveniência de imagem.

## 2. Bloqueios transversais

1. **GitHub Actions não executa.** Desde ~2026-10-13 os jobs falham em 2–3 s sem log (AgroLogMT, AI-Holding, Hermes), inclusive em `main`. Inferido: falha de provisionamento/cota de runner da conta (repositórios privados). Não verificado: tela de billing. Ação humana: GitHub → Settings → Billing → Actions. Até lá, nenhum check de PR é evidência.
2. `autonomous-workers` do AI-Holding continua agendado e falhando várias vezes por dia.
3. Muito trabalho está fora do `main`: dezenas de branches e PRs abertos por repositório. Estado real = `main` + PRs; os PRs precisam de triagem antes de qualquer nova implementação.

## 3. Status declarado nos repositórios (não reexecutado aqui)

- Hermes `GO_LIVE_STATUS.md`: HGL-007, 010, 012–016 e 020 em TODO; HGL-018/019 dependem de drill/smoke local real.
- WHATSAPP_AI `GO_LIVE_STATUS.md`: falta pareamento humano do número dedicado (WA-012) e E2E real com duas mensagens (WA-013).
- AgroLogMT: o gate final exige contêineres, gitleaks, trivy, SBOM, restore, qualidade/freshness de dados, GCP preflight e N6, todos sem evidência.

## 4. Divergências entre missões e código

- Geopolitical-Watch: a missão fala em "Render 512 MiB", mas o `main` não tem configuração de Render; o deploy documentado é Cloud Run + Cloud Run Job. É preciso confirmar se existe serviço Render fora do repositório.
- Health OS: as falhas parecem depender de dados/tempo (422 na API, limiares de TDEE). Inferido, não verificado. Permanece pausado.

## 5. Instalador Windows

A fonte canônica passa a ser `tools/windows/installer` (este branch). Correções e testes estão no README do instalador. Não foi executado em Windows real.

## 6. Próximos passos sugeridos (dependem de autorização)

1. Resolver a execução do GitHub Actions (billing/cota).
2. Decidir o conflito de proveniência do PR #64.
3. Triagem dos PRs abertos por projeto (merge, fechar ou atualizar) antes de novas features.
4. Executar localmente os drills pendentes declarados (backup/restore Hermes/WhatsApp/Holding, compose zero-cost) e registrar a evidência.
