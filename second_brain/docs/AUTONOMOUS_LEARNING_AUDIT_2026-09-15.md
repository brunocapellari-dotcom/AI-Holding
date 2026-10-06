# Auditoria do Aprendizado Autônomo — baseline 2026-09-15

Status: FASE 0 / auditoria antes de expansão.

Esta auditoria preserva o sistema de aprendizado já existente. Nenhum collector existente deve ser substituído apenas para adequação estética ou tecnológica. A regra é provar primeiro, federar depois e ampliar somente após os gates funcionais.

## Régua de evidência

- `PROVEN_LIVE`: execução real observada em ambiente operacional com fonte externa ou estado persistido.
- `PROVEN_CODE_AND_TEST`: implementação e testes existem, mas a execução operacional completa ainda não foi demonstrada.
- `PARTIAL`: parte do fluxo funciona ou existe, mas falta um elo necessário.
- `CODE_ONLY`: código/contrato existe sem backend/runtime operacional demonstrado.
- `ABSENT_OR_NOT_FOUND`: não encontrado nos repositórios/vault auditados.
- `BLOCKED_EXTERNAL`: teste preparado, mas impedido por infraestrutura externa ao código.

## Veredito executivo

O ecossistema possui automação real de coleta, atualização, persistência e geração de claims/evidências, especialmente no Geopolitical Watch. Porém ainda NÃO está provado que o Segundo Cérebro central execute autonomamente, de ponta a ponta:

`coletar -> interpretar -> verificar -> validar -> promover a canônico -> atualizar Obsidian/Graphiti -> recuperar depois`.

O principal motivo não é ausência de toda a base: no Geopolitical Watch, a política existente deliberadamente define `auto_mutate_knowledge=False`, exige decisões revisadas, proveniência e mudança versionada. Isso é uma proteção correta contra memorização automática de erro, mas significa que a etapa de conhecimento canônico autônomo não pode ser considerada funcional hoje.

## Matriz da Fase 0

| Componente | Estado | Evidência / observação |
|---|---|---|
| Estrutura do vault central | PARTIAL | `SEGUNDO_CEREBRO/vault` e `00_CORE`–`15_EVALUATIONS` existem, mas áreas centrais verificadas ainda estão vazias. |
| Vault antigo AgroLog | PROVEN_LIVE/PRESERVAR | Acervo existente permanece como conhecimento de projeto; não deve ser apagado nem transformado no cérebro global. |
| Ingestão | PROVEN_LIVE | Geopolitical Watch possui pipeline operacional com coleta, raw store, parsing, canonicalização de eventos e persistência. |
| Collectors | PROVEN_LIVE | GDELT/GDACS executados em scheduler real; outros adaptadores e refreshes existem. |
| Collector Registry central | PARTIAL | Há source configs/checkpoints/coverage no Geopolitical Watch e source registry/health no Sports Intelligence, mas não há registry institucional único. |
| Graphiti | CODE_ONLY | Contrato/projeção está no PR arquitetural; backend Graphiti persistente não está ativo. Pasta central `graph` verificada vazia. |
| Embeddings | ABSENT_OR_NOT_FOUND | Nenhum stack central de embeddings/pgvector/vector index encontrado nos cinco repositórios auditados. |
| Indexação semântica | ABSENT_OR_NOT_FOUND | Há índices relacionais e recuperação estruturada, mas não foi encontrado índice semântico institucional. |
| Claims | PROVEN_CODE_AND_TEST / operacional no projeto | Geopolitical Watch gera IDs determinísticos, merge de evidência, supersession/retraction/support. Pasta central `claims` verificada vazia. |
| Evidências | PROVEN_CODE_AND_TEST / operacional no projeto | Evidência possui provider/source/url/raw_ref e associação claim-evidence; raw artifacts têm SHA256. |
| Validação | PARTIAL | Há flags de qualidade, coverage e governança. Promoção canônica autônoma não está habilitada. Pasta central `validation` vazia. |
| Deduplicação | PARTIAL | Raw artifacts têm unicidade por source/hash e claims possuem merge determinístico. Deduplicação semântica cross-project não foi provada. |
| Proveniência | PROVEN_CODE_AND_TEST / operacional no projeto | Source/provider/URL/raw ref/hash/checkpoints são persistidos. Pasta central `provenance` ainda vazia. |
| Versionamento | PARTIAL | Supersession/change tracking existe; bitemporalidade institucional está em arquitetura, não demonstrada live. |
| Links | PARTIAL | Obsidian bundle valida frontmatter/wikilinks básicos; linter completo ainda não foi provado no vault central. |
| Pesquisa/recuperação | PARTIAL | SQLite/Postgres do Geopolitical Watch recuperam events/episodes/claims/evidence. Recuperação central cross-project não foi demonstrada. |
| Atualização automática | PROVEN_LIVE/PARTIAL | Public beta e sanctions têm execução real; refreshes UCDP/WPI/World Bank processam dados, mas workflows ficaram vermelhos por quota de artifacts. |
| Workers | PARTIAL | GitHub Actions e embedded collector existem e já executaram; workers centrais da Holding ainda dependem de acceptance de produção. |
| Filas | PARTIAL | Alert outbox existe no Geopolitical Watch; fila institucional de validação/promoção não foi demonstrada live. |
| Scheduler | PROVEN_LIVE/PARTIAL | `public-beta-monitor` horário executou com sucesso; outras rotinas existem. Infra central ainda não teve acceptance final comprovado. |
| Fontes | PROVEN_LIVE/PARTIAL | GDELT, GDACS e refreshes estruturados têm evidência; saúde/freshness variam e devem ser registradas por collector. |
| Segurança de ingestão | PARTIAL | Bloqueios de esquemas perigosos/credenciais em URL, defused XML, hashes e workflows read-only existem. Prompt-injection-as-data boundary institucional não foi encontrado. |
| Aprendizado canônico autônomo | NÃO PROVADO | Política atual explicitamente impede mutação automática de conhecimento canônico. |

## Prova operacional encontrada

### Public beta monitor

Workflow: `.github/workflows/public-beta-monitor.yml`

Execução auditada: GitHub Actions run `34917303272`, 2026-09-15 UTC, conclusão `success`.

A execução:

- restaurou estado persistente;
- executou collectors GDELT e GDACS;
- GDACS retornou 37 registros nessa passagem;
- persistiu banco e checkpoints;
- gerou análise, clusters, episodes, changes e alertas;
- executou health assertion;
- persistiu novamente o estado.

O histórico presente na execução reportava 103 runs por fonte, com sucessos e falhas registrados separadamente. Isso prova scheduler + collection + persistence + update state em operação. Não prova promoção automática a conhecimento institucional.

## Diagnóstico dos refreshes marcados como falha

As execuções mais recentes auditadas de UCDP, WPI e World Bank ficaram vermelhas, mas a coleta/processamento NÃO falhou.

### UCDP

Run `34820899552`:

- build UCDP: sucesso;
- build empirical history: sucesso;
- geração de summaries: sucesso;
- falha somente em `actions/upload-artifact` por `Artifact storage quota has been hit`.

O processamento produziu, entre outros, 2.816 linhas conflito-ano, 1.987 atores, 2.752 linhas de termination e 628 episódios contínuos.

### World Bank

Run `34834671380`:

- build: sucesso;
- 217 países;
- 4.860 observações;
- 5 indicadores;
- falha somente no upload de artifact pela mesma quota.

### WPI

Run `34829933682`:

- build: sucesso;
- 3.807 linhas de origem;
- 300 candidatos;
- falha somente no upload de artifact pela mesma quota.

Conclusão: esses três workflows estavam emitindo falso negativo operacional por dependência de artifact storage. Health de collector e health de artifact/CI devem ser métricas distintas.

## Teste funcional dedicado

Foi criado, em branch isolada do Geopolitical Watch, um probe que usa os collectors existentes sem alterar produção:

- executa `sources.public-beta.json` duas vezes contra fontes live;
- usa SQLite/raw/report temporários;
- verifica coleta e raw payloads;
- verifica events, episodes, claims e evidence;
- verifica referências claim->evidence;
- verifica segundo ciclo/update;
- fecha e reabre o storage para provar recuperação durável;
- consulta a policy de learning;
- somente declara `END_TO_END_CANONICAL_PROVEN` se a mutação canônica autônoma estiver realmente habilitada e todos os gates anteriores passarem.

PR de auditoria: Geopolitical-Watch #24 (draft).

A primeira tentativa do probe foi `BLOCKED_EXTERNAL`: GitHub Actions não alocou runner (`runner_id=0`, nenhuma etapa executada). O workflow foi ajustado para não depender de upload de artifact, pois a cota de artifacts já foi diagnosticada como saturada. Não considerar esse run nem sucesso nem falha funcional.

## Arquitetura distribuída encontrada

### Geopolitical Watch

É hoje a implementação mais próxima do ciclo autônomo requerido:

`source -> raw artifact -> parse -> event -> entity/episode -> claim/evidence -> quality/review -> persistence`.

Além disso possui source checkpoints, source coverage, failover/resilience, knowledge drift, Obsidian bundle e scheduled refreshes.

### Sports Intelligence

Possui padrões reutilizáveis de source registry, source health, adapters/normalizers e workers. Deve ser preservado como referência para o futuro Collector Registry institucional.

### AgroLog MT

O `main` auditado está centrado em ingestão de domínio, scheduler, quality gates e canonical BigQuery loads. Não foi encontrado nele um motor genérico de claims/evidence/aprendizado institucional equivalente ao Geopolitical Watch. Não atribuir ao AgroLog módulos que não existem no branch auditado.

### Mercado Financeiro

O `main` auditado prioriza point-in-time data, evidência, proveniência e controles de integridade. É uma fonte importante de padrões de auditabilidade, mas não foi demonstrado como motor geral de aprendizado autônomo.

### AI-Holding

Possui o Universal Knowledge Core e o redesenho independente do Second Brain em PR. A produção central ainda não deve ser marcada como aceita enquanto migrations/bootstrap/worker acceptances não tiverem execução comprovada.

## Segurança — baseline real

Controles encontrados e que devem ser preservados:

- SHA256 de raw artifacts;
- referência à fonte/URL/raw artifact;
- checkpoints somente após coleta bem-sucedida;
- rejeição de `file:`, `ftp:`, `gopher:` e credenciais embutidas em URLs em componentes auditados;
- XML parser endurecido contra entity expansion;
- workflows de leitura com `contents: read` quando possível;
- refreshes estruturados projetados para branch temporária/PR revisado em vez de mutação irrestrita de `main`;
- regra existente de não automutar conhecimento sem review.

Gaps de segurança ainda não provados institucionalmente:

- regra executável universal `conteúdo ingerido = dado, nunca instrução`;
- detecção/neutralização de prompt injection em documentos, HTML, captions e transcrições;
- quarantine de arquivos;
- allowlist central de tipos/MIME;
- antivirus quando aplicável;
- bloqueio central de executáveis/macros perigosas;
- classificação PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED aplicada end-to-end;
- ACL por namespace aplicada no runtime central;
- backup/recovery testado do cérebro central.

## Gates antes de ampliar fontes

A expansão para vídeo, documentos, papers, RSS/notícias e novos adapters só deve iniciar quando os seguintes gates da Fase 0 estiverem fechados:

1. executar o probe live collect-to-retrieve sem bloqueio externo;
2. separar health do collector de health de CI/artifact;
3. demonstrar a etapa de validação e promoção conforme risco, sem permitir auto-canonicidade insegura;
4. demonstrar que uma informação aprovada chega ao armazenamento institucional e pode ser recuperada depois;
5. demonstrar provenance completa até a fonte original;
6. demonstrar supersession/histórico sem apagar fatos antigos;
7. executar o linter no vault real;
8. provar isolamento/ACL por namespace;
9. provar que conteúdo malicioso não consegue converter texto ingerido em instrução para os agentes;
10. documentar recovery/backup e executar pelo menos um teste de reconstrução.

Somente após esses gates o Collector Registry central e os novos pipelines de vídeo/documentos/papers/notícias devem ser ativados em escala.
