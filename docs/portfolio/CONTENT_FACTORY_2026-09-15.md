# Portfolio — Content Factory

Data: 2026-09-15
Status: ATIVO / especificação arquitetural final registrada
Repositório de produção pretendido: `Content-Factory` (private, ainda não criado no GitHub conectado)

## Papel na organização

Content Factory é a fábrica multimodal compartilhada para transformar conhecimento validado em produtos de conteúdo. Não duplica Research AI nem Segundo Cérebro.

Entradas canônicas:
- RESEARCH_REQUEST/SOURCE_PACKAGE do Research AI
- knowledge snapshots do Segundo Cérebro
- briefing
- brand profile
- assets autorizados

Saídas:
- vídeo longo
- Short/Reel/Story
- post/carrossel
- artigo
- PDF/EPUB/KDP-ready
- livro/e-book
- audiobook
- curso/aula/slides/quiz/material de apoio

## Arquitetura canônica

Referências:
- `docs/content-factory/CONTENT_FACTORY_FINAL_ARCHITECTURE_2026-09-15.md`
- `docs/content-factory/GITHUB_TOOL_REVIEW_2026-09-15.md`
- `docs/content-factory/E2E_ACCEPTANCE_MATRIX_2026-09-15.md`
- `docs/content-factory/REPOSITORY_BOOTSTRAP_2026-09-15.md`

## Regras permanentes

- versões são aprovadas somente pelo E2E_FULL completo;
- não declarar versão operacional com engines ausentes ou não testados;
- 28 especialistas são roles/capabilities, não 28 microserviços;
- Content Master é a unidade central versionada;
- lineage, direitos, custo, QA e provenance são obrigatórios;
- multi-tenancy desde o primeiro schema;
- providers/modelos são substituíveis via registry/router;
- novas ferramentas entram pelo Open Source Intake Gate;
- evitar forks gerais, duplicidade de schedulers, duplicidade de bancos e duplicidade de pesquisa/knowledge;
- AI-Holding fornece governança compartilhada; código de produção deve ficar no repo próprio.

## Stack alvo consolidado

Temporal + PostgreSQL + object storage S3-compatible + OpenTelemetry + LiteLLM compartilhado + ComfyUI + FFmpeg + Remotion condicional + WhisperX + TTS adapter + Pandoc + Typst + EPUBCheck + PptxGenJS + C2PA + Promptfoo; Langfuse compartilhado/opcional se não duplicar observabilidade existente; Postiz apenas isolado/referência sujeito à AGPL.

## Bloqueio atual

O conector GitHub disponível permite branches, arquivos, issues e PRs em repositórios existentes, mas não oferece ação para criar um novo repositório. Portanto, a arquitetura e o bootstrap estão registrados na Holding, enquanto a criação de `Content-Factory` permanece o único bloqueio externo para materializar o código no repositório correto.
