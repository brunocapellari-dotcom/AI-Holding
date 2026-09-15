# Content Factory — E2E_FULL Acceptance Matrix

Data: 2026-09-15
Regra do Owner: versões são validadas pelo projeto completo, nunca por módulos isolados.

## 1. Princípio

Testes unitários, contract tests e integração parcial continuam existindo para localizar defeitos, mas NÃO promovem uma versão sozinhos. Toda release candidata deve executar o cenário `E2E_FULL` ponta a ponta com todos os engines ativos.

## 2. Fixture canônica

Cada execução de release usa uma base de conhecimento real/autorizada contendo:

- briefing
- SOURCE_PACKAGE do Research AI ou snapshot equivalente aprovado
- mínimo de claims verificáveis
- referências e direitos
- brand profile
- assets autorizados
- público e objetivo
- orçamento/cost ceiling
- formatos-alvo completos

A fixture deve possuir conteúdo suficiente para artigo, vídeo, livro, audiobook e curso sem inventar fatos.

## 3. Fluxo obrigatório

1. receber briefing
2. emitir/consumir RESEARCH_REQUEST/SOURCE_PACKAGE quando necessário
3. materializar CONTENT_MASTER vN
4. validar claims/evidences
5. gerar Editorial Plan
6. gerar Story/Video Plan
7. criar/selecionar assets com rights records
8. gerar vídeo longo
9. derivar Short/Reel 9:16
10. gerar artigo
11. gerar manuscript/e-book
12. exportar EPUB
13. validar EPUBCheck
14. exportar PDF
15. gerar audiobook com chapter map e pronunciation rules
16. gerar Course Master
17. gerar módulos/aulas
18. gerar slides PPTX
19. gerar quiz/assessment
20. gerar material de apoio
21. executar Content QA consolidado
22. executar Rights/Provenance QA
23. executar Cost QA
24. montar publication/export package
25. gravar lineage completo
26. registrar métricas técnicas e custos

Falha em qualquer etapa crítica reprova a release.

## 4. Contratos mínimos de saída

### CONTENT_MASTER
- ID/version/status válidos
- source_package_ids
- claims ligados a evidence
- rights policy
- brand/tone
- target formats
- lineage roots

### Vídeo longo
- arquivo reproduzível
- codec/container suportado
- resolução/aspect ratio do profile
- áudio sincronizado
- loudness dentro da política
- captions quando requeridas
- assets rastreáveis
- C2PA/provenance quando suportado

### Short/Reel
- 9:16
- safe areas
- hook/CTA conforme plano
- captions legíveis
- duração/plataforma dentro da política configurada
- lineage para o vídeo/conteúdo-mãe

### Artigo
- claim coverage
- referências quando política exigir
- estrutura/editorial/style QA
- sem conteúdo-fonte reproduzido indevidamente

### EPUB
- metadata
- TOC
- links/assets válidos
- EPUBCheck PASS sem erro bloqueante

### PDF
- fontes autorizadas/incorporadas conforme política
- imagens com resolução mínima
- margens/bleed quando perfil de impressão exigir
- páginas/TOC sem quebra estrutural

### Audiobook
- chapter mapping
- pronunciation dictionary aplicado
- sem clipping
- loudness target
- silêncio/pausas dentro do profile
- voz autorizada/provenance

### Curso
- learning objectives
- prerequisites
- progressão pedagógica
- módulos e lessons
- exemplos/prática
- quiz bank
- assessment blueprint
- remediation/feedback quando aplicável
- slides e material de apoio derivados do mesmo Course Master

## 5. QA gates

### Factual
- nenhuma claim factual material sem evidence link
- claims com conflito ficam bloqueadas ou sinalizadas conforme policy
- atualização de claim deve permitir localizar derivados potencialmente desatualizados

### Rights
- todo asset possui origem e uso permitido
- nenhum asset expirado/sem direito entra em release
- attribution aplicada quando exigida
- voz/face/identidade sintética obedece consent/policy

### Continuity
- entidades principais respeitam Continuity Registry
- mudanças intencionais são declaradas no shot/scene state
- detecção de drift gera finding

### Brand
- typography/palette/logo/tone/CTA policy verificadas

### Media
- ffprobe PASS
- sem stream inválido
- A/V sync dentro da tolerância configurada
- captions sem overflow crítico
- imagem/vídeo dentro do aspect ratio correto

### Security
- uploads externos passam por quarantine/sanitization
- nenhum path traversal/SSRF/command injection em fixtures adversariais
- prompt injection de documento externo não altera policy/tool permissions
- secrets não aparecem em log/artifact/output

### Cost
- cost_estimated pré-job
- cost_actual pós-job
- job é bloqueado/escalado quando ultrapassa policy
- custo atribuído a tenant/project/content_master

### Provenance
- lineage graph completo
- workflow/prompt/model versions registradas
- hashes de assets finais
- C2PA aplicado quando configurado/suportado

## 6. Testes adversariais obrigatórios

A suíte E2E_FULL deve incluir, sem remover o cenário normal:

- HTML/SVG malicioso
- arquivo com extensão enganosa
- archive path traversal
- URL SSRF para faixa privada/metadata service
- prompt injection em documento/fonte
- asset sem licença
- asset expirado
- claim contraditória
- provider indisponível
- timeout GPU/render
- retry após worker crash
- publicação duplicada/idempotency key repetida
- orçamento excedido
- tenant A tentando acessar asset de tenant B

O workflow deve falhar de modo seguro ou compensar sem corrupção de estado.

## 7. Provider/model failure tests

Model/Provider Router deve provar:

- fallback autorizado
- ausência de fallback quando direitos/policy não permitem
- retry controlado
- circuit breaker/rate limit
- preservação de idempotência
- custo final correto
- output lineage registra o provider realmente usado

## 8. Testes de atualização de conhecimento

Após release do cenário normal:

1. alterar uma claim no knowledge snapshot;
2. executar impact analysis;
3. localizar artigo, vídeo, e-book, audiobook, slides/aulas afetados;
4. regenerar somente os derivados impactados sem duplicar os não afetados;
5. produzir CONTENT_MASTER nova versão e manter histórico anterior.

Este teste é obrigatório porque reutilização e atualização são requisitos centrais do produto.

## 9. Performance/reliability

Registrar:

- duração total
- duração por stage
- filas/worker wait
- GPU time
- render time
- tokens
- cost por stage
- retries
- cache hits
- artefatos produzidos

A release deve possuir baseline comparável; regressões acima do threshold configurado geram finding.

## 10. Critério de aprovação

`RELEASE_READY = TRUE` somente se:

- E2E_FULL normal PASS
- security adversarial PASS
- cross-tenant isolation PASS
- rights/provenance PASS
- publication artifact validation PASS
- knowledge-update impact test PASS
- cost ledger reconciliado
- findings críticos = 0
- findings altos = 0 ou waiver explícito autorizado

Nenhum engine pode ser marcado como 'não testado nesta release' para ainda assim chamar a versão de 100% operacional.