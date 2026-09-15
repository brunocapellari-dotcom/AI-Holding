# Research AI — E2E Acceptance Matrix

Regra: nenhuma versão é promovida como operacional com apenas testes unitários ou de módulos. Uma única release candidate deve executar o conjunto completo abaixo com os mesmos contratos e infraestrutura de produção, usando mocks somente onde direitos, credenciais ou custos impeçam acesso real. Cenários críticos exigem pelo menos uma integração real autorizada equivalente.

## Gate global

- [ ] CI verde: Ruff, mypy strict, Bandit, pip-audit, tests e coverage >= 90%.
- [ ] Open Source Intake Gate verde para todas as novas dependências.
- [ ] SBOM gerado e assinado.
- [ ] imagem pinada por digest e assinada.
- [ ] nenhum secret no git/log/package.
- [ ] migration up/down validada em ambiente descartável.
- [ ] rollback de aplicação validado.
- [ ] traces, logs e métricas correlacionados por `request_id` e `research_run_id`.

## Cenário 1 — AgroLog: API + dataset oficial

Pedido real sobre uma base oficial agrícola/logística.

- [ ] Query Planner identifica fonte primária.
- [ ] API Discovery registra docs, auth, rate limits, schema, coverage e terms.
- [ ] Probe real autorizado retorna resposta válida.
- [ ] Dataset é baixado ou consultado legalmente.
- [ ] DuckDB profila grain, schema, missingness, duplicates e date coverage.
- [ ] ResearchPackage cita evidências e limitações.
- [ ] Knowledge Factory recebe package sem promoção canônica automática.

## Cenário 2 — Mercado Financeiro: paper + dados

- [ ] Crossref/OpenAlex/DataCite/Semantic Scholar usados para discovery/cross-check.
- [ ] versão publicada é diferenciada de preprint.
- [ ] license/full-text access registrado.
- [ ] série/dataset associado é identificado quando existente.
- [ ] conclusões não excedem o que o paper suporta.
- [ ] Research Auditor rejeita claim financeiro sem evidência suficiente.

## Cenário 3 — Personal Performance & Health OS: guideline científico

- [ ] PubMed/NCBI e pelo menos uma fonte institucional apropriada são consultados.
- [ ] guideline/revisão sistemática recebe prioridade sobre fonte terciária quando aplicável.
- [ ] datas e versões são preservadas.
- [ ] ResearchPackage separa evidência de inferência/prática.
- [ ] nenhum conteúdo de search SaaS vira recomendação médica automática.

## Cenário 4 — Culinária: vídeo + documento + direitos

- [ ] YouTube Data API ou metadata legal identifica conteúdo.
- [ ] rights/access é registrado antes de qualquer download.
- [ ] material não autorizado permanece apenas como referência/URL/metadata.
- [ ] documento autorizado entra em quarantine, MIME, hash, malware e parsing.
- [ ] package diferencia técnica extraída de texto protegido que não pode ser reproduzido extensamente.

## Cenário 5 — Software/Holding: GitHub capability research

- [ ] pesquisa usa capacidade, não só nome do projeto.
- [ ] pelo menos três candidatos plausíveis comparados quando disponíveis.
- [ ] licença, atividade, releases, dependências e supply-chain risk avaliados.
- [ ] classificação `USE/ADAPT/REFERENCE/REJECT` possui justificativa.
- [ ] candidato `USE/ADAPT` atravessa gate Scorecard/ORT/Syft/Gitleaks/Semgrep/Trivy/test/Cosign conforme aplicável.

## Cenário 6 — Web dinâmica

- [ ] Crawl4AI tenta aquisição principal.
- [ ] Playwright é acionado somente quando necessário.
- [ ] HTML/content não consegue alterar system/tool policy por prompt injection.
- [ ] scripts baixados não são executados.
- [ ] redirects são revalidados por SSRF guard.

## Cenário 7 — SSRF/metadata endpoint

- [ ] localhost bloqueado.
- [ ] RFC1918 bloqueado.
- [ ] link-local bloqueado.
- [ ] cloud metadata endpoints bloqueados.
- [ ] DNS rebinding/redirect para destino privado falha fechado.
- [ ] evento de segurança é auditado.

## Cenário 8 — arquivo malicioso

- [ ] asset permanece em quarantine.
- [ ] MIME real divergir da extensão gera alerta/bloqueio.
- [ ] malware detectado não chega ao parser.
- [ ] archive bomb/recursion/size limits funcionam.
- [ ] package registra `SECURITY_REJECTED` sem expor payload.

## Cenário 9 — licença bloqueada

- [ ] código/dataset/documento com uso incompatível é identificado.
- [ ] sistema pode registrar conceito/metadata quando permitido, mas bloqueia incorporação/download/redistribuição incompatível.
- [ ] Research Auditor verifica a decisão.

## Cenário 10 — fontes contraditórias

- [ ] ambas as evidências preservadas.
- [ ] tipo da contradição é classificado.
- [ ] resolução temporal/metodológica/source-priority possui justificativa.
- [ ] contradição não desaparece do package.

## Cenário 11 — freshness enganosa

- [ ] upload recente de documento antigo mantém `published_at` antigo.
- [ ] `retrieved_at` nunca substitui `published_at/effective_at`.
- [ ] versão/source date entra na síntese.

## Cenário 12 — deduplicação

- [ ] canonical URL deduplica trackers/aliases.
- [ ] SHA-256 detecta mesmo asset em URLs distintas.
- [ ] DOI/PMID/arXiv/ISBN/GitHub IDs canonicalizam entidades.
- [ ] preprint e published version são relacionados, não tratados como duplicata cega.

## Cenário 13 — API quebrada/schema drift

- [ ] health check detecta falha.
- [ ] schema drift é versionado.
- [ ] consumidores não recebem silenciosamente payload incompatível.
- [ ] source status vira DEGRADED/BROKEN.
- [ ] watcher abre research request somente quando novidade/relevância justificar.

## Cenário 14 — retry/resume durável

- [ ] worker morre no meio de uma pesquisa.
- [ ] run retoma sem duplicar download/probe/custo já concluído.
- [ ] idempotency keys funcionam.
- [ ] timeout e retry policy são observáveis.

## Cenário 15 — cancelamento

- [ ] Control Plane cancela um run.
- [ ] novas atividades deixam de iniciar.
- [ ] atividades canceláveis são interrompidas com segurança.
- [ ] assets já adquiridos mantêm audit trail segundo retention policy.

## Cenário 16 — budget controller

- [ ] limite de custo interrompe discovery adicional antes de ultrapassagem material.
- [ ] prioridade/freshness pode redirecionar orçamento entre fontes.
- [ ] package parcial explica a cobertura faltante.

## Cenário 17 — search-provider terms

- [ ] provider com proibição de storage não tem payload persistido.
- [ ] source adquirido diretamente possui sua própria avaliação de direitos.
- [ ] mudança de terms dispara reavaliação antes do próximo uso persistente.

## Cenário 18 — autonomous watcher anti-ruído

- [ ] evento repetido não cria pacote duplicado.
- [ ] novelty score e relevance gate são determinísticos/auditáveis.
- [ ] alteração de licença/CVE crítica sempre passa ao gate apropriado.
- [ ] nova ferramenta popular sem benefício material não gera substituição automática.

## Cenário 19 — handoff para Knowledge Factory

- [ ] package é machine-readable e versionado.
- [ ] todos os claims apontam para evidence IDs.
- [ ] assets apontam para provenance e hashes.
- [ ] Knowledge Factory pode aceitar/rejeitar claims individualmente.
- [ ] Segundo Cérebro não recebe verdade canônica diretamente do Research AI.

## Cenário 20 — multi-project concurrency

Executar simultaneamente requests reais/representativos de AgroLog, Mercado Financeiro, Culinária, Personal Performance & Health OS e software/Holding.

- [ ] isolamento por projeto/tenant preservado.
- [ ] limites de custo/rate limit independentes.
- [ ] sem vazamento de secrets ou dados internos entre projetos.
- [ ] prioridade do Control Plane respeitada.
- [ ] packages entregues ao consumidor correto.

## Cenário 21 — source health e failover

- [ ] fonte preferencial indisponível não produz resposta falsa.
- [ ] fallback autorizado é tentado quando existe.
- [ ] ausência de fonte primária material aparece em `uncertainties`.
- [ ] `SOURCE_UNAVAILABLE`/`PARTIAL` é usado quando apropriado.

## Cenário 22 — Research Auditor independente

- [ ] auditor não reutiliza cegamente o texto do Synthesizer como evidência.
- [ ] identifica ao menos um claim propositalmente sem suporte no fixture negativo.
- [ ] falha de citation coverage bloqueia `PASS`.
- [ ] falha de license/security bloqueia entrega operacional.

## Critério final de promoção

`OPERATIONAL` somente se:

1. todos os cenários críticos passam;
2. nenhum P0 do Gap Analysis permanece aberto;
3. cinco domínios diferentes completam E2E na mesma release candidate;
4. pelo menos uma API real, um dataset real, um repositório GitHub real, uma fonte científica real, uma página web real e um documento autorizado real forem processados;
5. security/license negative tests falharem fechado;
6. package → Knowledge Factory handoff estiver comprovado;
7. rollback e recovery forem comprovados;
8. observabilidade mostrar o run completo sem gaps de correlação.
