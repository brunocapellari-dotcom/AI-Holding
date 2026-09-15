# Content Factory — Revisão de Ferramentas GitHub 2026-09-15

Status: recomendação técnica sujeita ao Open Source Intake Gate antes de runtime.

## Critérios

Avaliação por função, atividade/manutenção, licença, risco de lock-in, automação/API, maturidade, qualidade, adequação a uso comercial, facilidade de substituição e sobreposição com ferramentas já previstas.

## Decisões consolidadas

### 1. Orquestração: Temporal — ADOTAR COMO PADRÃO

Repositório: temporalio/temporal
Uso: durable execution, retries, timeout, compensação, timers, long-running jobs, idempotência e reentrada.
Motivo: substitui a ideia genérica de manter múltiplas filas/schedulers/workers como coração do projeto. Redis/BullMQ/Celery não devem virar segunda fonte de verdade de workflow.
Classificação pretendida: APROVADO_CORE após Intake Gate.

### 2. Media primitive: FFmpeg/ffprobe — ADOTAR COMO CORE

Uso: probe, transcode, mux/demux, concat, loudness, waveform, subtitles, thumbnails, codec normalization e mastering.
Não substituir por wrappers completos. Wrappers só podem facilitar chamadas, mantendo recipe explícita e testável.

### 3. Composição de vídeo: Remotion — ADOTAR CONDICIONALMENTE

Repositório: remotion-dev/remotion
Uso: templates, motion design, captions, batch rendering e composição programática.
Vantagem: React/código como fonte de verdade e forte automação.
Risco: licença especial/comercial em determinados usos; Intake Gate jurídico é obrigatório.
Classificação pretendida: APROVADO_COMPONENTE se licença for compatível; caso contrário manter FFmpeg + renderer próprio/adapters.

### 4. Visual generation workflow: ComfyUI — ADOTAR COMO BACKEND MODULAR

Repositório: Comfy-Org/ComfyUI
Uso: workflows de imagem/vídeo/áudio locais e privados via API.
Regra: ComfyUI é executor de workflow, não o domínio da Content Factory. Workflows são versionados no Prompt/Workflow Registry.
Classificação pretendida: APROVADO_COMPONENTE.

### 5. Modelos de vídeo: NÃO FIXAR UM ÚNICO

Candidatos atuais:
- Lightricks/LTX-Video / LTX-2 family
- Wan video family / Wan2.2

A decisão será por benchmark interno por perfil: text-to-video, image-to-video, character continuity, audio-video sync, speed, VRAM, cost e commercial rights. Modelos entram pelo Model/Provider Registry e podem ser substituídos sem alterar o domínio.

### 6. STT/alinhamento: WhisperX — ADOTAR

Repositório: m-bain/whisperX
Uso: transcrição rápida, timestamps por palavra e diarização quando aplicável.
Motivo: já utiliza faster-whisper como backend; não manter WhisperX e faster-whisper como dois produtos paralelos sem necessidade.
Classificação pretendida: APROVADO_COMPONENTE.

### 7. TTS: Chatterbox — BENCHMARK / ADAPTER

Repositório: resemble-ai/chatterbox
Uso candidato: TTS local/multilingual/voice conversion conforme licença e direitos de voz.
Regra: não tornar voz clonada capacidade automática. Consentimento, direito de uso e voice provenance são obrigatórios. Manter providers alternativos via adapter.
Classificação inicial: POC_ISOLADA até benchmark e revisão de licença/model weights.

### 8. Publishing conversion: Pandoc — ADOTAR COMO FERRAMENTA ISOLADA

Repositório: jgm/pandoc
Uso: conversão entre Markdown/HTML/DOCX/EPUB e formatos editoriais.
Observação: GPL exige avaliação do modo de integração/distribuição. Preferir execução como ferramenta externa isolada/CLI quando isso preservar fronteiras adequadas.
Classificação pretendida: APROVADO_COMPONENTE após licença.

### 9. PDF/typesetting: Typst — ADOTAR

Repositório: typst/typst
Uso: PDF/layout reprodutível, templates editoriais e documentos técnicos.
Motivo: pipeline determinístico e mais simples que manter LaTeX completo como requisito obrigatório.
Classificação pretendida: APROVADO_COMPONENTE.

### 10. EPUB validation: EPUBCheck — ADOTAR COMO GATE

Repositório: w3c/epubcheck
Uso: validação oficial de conformidade EPUB.
Regra: nenhum EPUB é marcado como release-ready sem passar pelo EPUBCheck e verificações internas de assets/links/metadata.
Classificação pretendida: APROVADO_CORE para validação EPUB.

### 11. Slides: PptxGenJS — ADOTAR COMO RENDERER PRINCIPAL

Repositório: gitbrent/PptxGenJS
Uso: PPTX programático, masters, charts, imagens, tabelas e branding.
Regra: manter Slide Schema intermediário para permitir troca de renderer e suporte posterior a Google Slides/native connectors.
Classificação pretendida: APROVADO_COMPONENTE.

### 12. Model gateway: LiteLLM — ADOTAR COMO GATEWAY COMPARTILHADO, NÃO COMO DOMÍNIO

Repositório: BerriAI/litellm
Uso: interface comum para múltiplos providers, routing, cost/spend, fallback, rate limits e observabilidade.
Regra: confirmar licença de cada componente/feature e executar preferencialmente como serviço compartilhado da Holding. O Content Factory mantém seu próprio Cost Ledger porque vídeo/imagem/render/GPU não cabem integralmente no custo de LLM.
Classificação pretendida: APROVADO_CORE compartilhado após Intake Gate.

### 13. LLM observability/evals: Langfuse — ADOTAR SE JÁ NÃO HOUVER EQUIVALENTE NA HOLDING

Repositório: langfuse/langfuse
Uso: traces, prompt management, datasets, evals e debugging.
Regra anti-duplicidade: OpenTelemetry continua sendo interface padrão de telemetria. Langfuse é uma implementação especializada, não uma segunda verdade operacional.
Classificação: APROVADO_COMPONENTE compartilhado.

### 14. Prompt/agent testing: Promptfoo — ADOTAR EM CI

Repositório: promptfoo/promptfoo
Uso: evals, comparação de modelos, regressão de prompts e red-team/pentest de aplicações de IA.
Motivo: complementa testes de código e Content QA; não substitui factual/media QA.
Classificação pretendida: APROVADO_COMPONENTE.

### 15. Proveniência: C2PA SDK — ADOTAR

Repositório: contentauth/c2pa-rs
Uso: Content Credentials/provenance em formatos suportados.
Regra: C2PA complementa o lineage ledger interno e os rights records; não substitui nenhum deles.
Classificação pretendida: APROVADO_CORE para proveniência multimídia suportada.

### 16. Social scheduling: Postiz — NÃO INCORPORAR AO CORE

Repositório: gitroomhq/postiz-app
Uso possível: serviço externo/isolado para scheduling/analytics via API.
Risco: AGPL-3.0 e stack completa desnecessária para o domínio central.
Decisão: REFERENCIA/APROVADO_COMPONENTE isolado apenas após análise jurídica. O core mantém adapters oficiais por plataforma.

### 17. Agent framework

OpenAI Agents SDK é uma referência válida para agents, tools, handoffs e guardrails, mas NÃO será o scheduler/durable workflow engine. Temporal controla execução; agent runtime controla raciocínio/tool use dentro de Activities.
Para reduzir lock-in, contratos de domínio, schemas e workflow state permanecem independentes do SDK. Não introduzir simultaneamente LangGraph + CrewAI + AutoGen + Agents SDK sem necessidade comprovada.

## Ferramentas das referências originais

StoryMind, Story-to-Video Studio, StoryboardAI, Calliope, LocalMiniDrama, story2video, AgentTube, MoneyPrinterTurbo, NovaClip, OpenShorts, Podcast Shorts Factory, TryPost, ContentFlow, Social Agent AI, book-writer, AI Book Generator, Booker, Audiobook Generator, NeoAcademy e PDF-to-Interactive-Lesson devem ser tratados como REFERENCE/COMPONENT SOURCE até auditoria individual.

Não fazer fork geral desses projetos. Extrair padrões/algoritmos úteis e comparar contra o stack canônico acima. Se uma referência duplicar Remotion, ComfyUI, Temporal, Publishing Engine ou Course Engine sem vantagem demonstrável, rejeitar por redundância.

## Stack final recomendado sem duplicidades

- Durable workflow: Temporal
- Domain/API: serviço próprio tipado
- Metadata/state: PostgreSQL
- Assets: object storage S3-compatible
- Cache/rate limit: Redis opcional
- Model gateway: LiteLLM compartilhado
- Agent runtime: perfis versionados; SDK substituível
- Visual workflow: ComfyUI
- Video/image models: Model Registry + benchmark
- Composition: FFmpeg + Remotion condicional
- STT/alignment: WhisperX
- TTS: adapter; Chatterbox candidato
- Publishing: Markdown/AST + Pandoc + Typst
- EPUB validation: EPUBCheck
- Slides: PptxGenJS
- Provenance: internal lineage + C2PA
- Telemetry: OpenTelemetry; Langfuse especializado opcional
- Prompt/agent CI: Promptfoo
- Social: adapters oficiais; Postiz apenas isolado se aprovado

## Itens explicitamente evitados

- Celery + BullMQ + Temporal simultaneamente como schedulers principais
- múltiplos bancos para o mesmo estado de negócio
- 28 microserviços para 28 agentes
- LLM framework como fonte de verdade do workflow
- ComfyUI como banco de domínio
- fork integral de geradores de shorts/livros/cursos
- um modelo de vídeo hardcoded
- duplicação de Research AI/Knowledge Factory
- duplicação de observabilidade já fornecida pela Holding
- publicação em plataformas por scraping quando existe integração oficial/autorizada
