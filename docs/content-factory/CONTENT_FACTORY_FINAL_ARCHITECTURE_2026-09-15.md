# Content Factory — Arquitetura Final 1.0

Data: 2026-09-15
Status: CANÔNICO / arquitetura-alvo final

## 1. Missão

Construir uma fábrica autônoma multimodal capaz de transformar uma única base de conhecimento validada em produtos de conteúdo consistentes, rastreáveis e reutilizáveis: vídeo longo, Shorts/Reels/Stories, posts/carrosséis, artigos, e-books/livros, PDF/EPUB/KDP-ready, audiobook, cursos, aulas, slides, quizzes e materiais de apoio.

A fábrica atende projetos internos e, no futuro, clientes externos. O objetivo não é volume vazio, mas qualidade, utilidade, originalidade, consistência de marca, direitos claros, factualidade e reprodutibilidade.

## 2. Fronteiras obrigatórias

- Research AI é a camada de descoberta/pesquisa; Content Factory NÃO duplica pesquisa.
- Segundo Cérebro é a camada de conhecimento validado; Content Factory NÃO cria outra verdade canônica.
- Content Factory transforma SOURCE_PACKAGE e conhecimento aprovado em produtos.
- AI-Holding fornece, quando existente, serviços compartilhados de identidade, autorização, secrets, auditoria, observabilidade, Open Source Intake Gate e governança.
- Publicação é realizada por adapters/conectores. O núcleo não depende de rede social, LMS, marketplace ou vendor específico.
- KDP-ready significa geração e validação de artefatos prontos para submissão; automação de upload só é permitida se existir integração oficial/autorizada.

## 3. Princípio arquitetural

A unidade central é o CONTENT_MASTER versionado. Nenhum formato derivado deve virar uma ilha de conhecimento.

Fluxo:

IDEIA/BRIEF -> RESEARCH_REQUEST quando necessário -> SOURCE_PACKAGE/Segundo Cérebro -> CONTENT_MASTER -> EDITORIAL_PLAN -> PRODUCTION_GRAPH -> derivados -> QA -> APPROVAL_POLICY -> publicação/export -> métricas -> aprendizado.

## 4. CONTENT_MASTER canônico

Campos mínimos:

- content_master_id
- tenant_id
- project_id
- version
- status
- theme
- objective
- audience
- brand_id
- tone_profile
- source_package_ids[]
- knowledge_snapshot_id
- claim_ids[]
- outline
- canonical_narrative
- restrictions[]
- asset_requirements[]
- rights_policy_id
- editorial_policy_id
- generation_policy_id
- locale/languages
- target_formats[]
- created_at / updated_at

Claims devem apontar para evidência e natureza da afirmação. Conteúdos factuais devem possuir claim/evidence mapping suficiente para revisão e atualização futura.

## 5. Registries transversais

### 5.1 Asset Registry

Todo asset recebe asset_id, hash, MIME, origem, owner, licença, usage_right, attribution, derivative_permission, tenant/project scope, expiry quando houver, geração/modelo/provider, prompt/workflow version, C2PA/provenance quando aplicável e relações com derivados.

### 5.2 Continuity Registry

Registra entidades narrativas e visuais: personagem, idade, face identity, roupa, objetos, cenário, estilo, proporções, paleta, iluminação, tempo narrativo, câmera, voz e regras de persistência. Não depende de um único modelo de imagem/vídeo.

### 5.3 Brand Registry

Brand profile, linguagem, palavras permitidas/bloqueadas, identidade visual, tipografia autorizada, paleta, templates, logotipos, audio identity, CTA policy e platform rules.

### 5.4 Rights & License Registry

source, license, usage_right, attribution, derivative_permission, territory, media, commercial_use, expiration, evidence/documento de autorização.

### 5.5 Model/Provider Registry

Provider/modelo/checkpoint/version, modalidade, capacidades, limites, custo, latência, quality benchmark, direitos comerciais, local/API, requisitos de hardware, região e status. Modelos são substituíveis por benchmark; não ficam hardcoded no domínio.

### 5.6 Prompt/Workflow Registry

Prompts, templates, workflows ComfyUI, parâmetros, render recipes, QA rules e agent profiles são versionados e reprodutíveis.

### 5.7 Cost Ledger

Custo estimado e real por job, stage, provider, LLM, imagem, vídeo, TTS/STT, GPU, render, storage, egress, projeto, tenant e conteúdo.

### 5.8 Content Lineage Graph

Relaciona SOURCE_PACKAGE -> CONTENT_MASTER -> claim -> asset -> derivado -> publicação. Permite descobrir o que ficou desatualizado quando uma claim ou fonte muda.

## 6. Agentes e runtime

Os nomes funcionais permanecem: Content Director, Research Liaison, Content Strategist, Fact Checker, Brand, Copywriter, Story Director, Screenwriter, Character, World Building, Storyboard, Cinematography, Continuity, Video Generation, Video Editor, Voice, Sound, Social, Publishing, Book Editor, Layout, Audiobook, Learning Director, Curriculum, Lesson, Quiz e Content QA.

Eles NÃO serão 28 microserviços. São perfis/capabilities versionados executados sobre um runtime comum, com tool permissions e schemas de entrada/saída. Serviços separados só surgem quando houver necessidade de escala/isolamento real, especialmente GPU/render.

## 7. Orquestração

Temporal é o padrão para durable workflows: retries, timeout, compensação, jobs longos e reentrada idempotente. Workers são separados por capability: orchestration/LLM, media CPU, GPU generation, render, publishing/export e QA.

Estado de negócio fica em PostgreSQL; blobs e masters ficam em object storage compatível com S3. Redis é opcional para cache/rate limiting, não a fonte de verdade de jobs.

## 8. Media Engine

### 8.1 Geração visual

ComfyUI é backend visual modular para workflows locais/privados. Modelos de imagem/vídeo entram pelo Model Registry. LTX e Wan são candidatos de benchmark, não dependências canônicas imutáveis. Providers fechados podem coexistir via adapters.

### 8.2 Composição e edição

- FFmpeg/ffprobe: media primitive canônico, transcode, mux, loudness, probes, subtitles e utilitários.
- Remotion: composição programática/template-driven, shorts, motion graphics, captions, batch render e design systems, condicionado à revisão de licença comercial.
- PySceneDetect/auto-editor podem ser componentes substituíveis para segmentação/trimming se aprovados pelo Intake Gate.

### 8.3 STT/TTS

WhisperX é candidato principal de STT/alinhamento/diarização quando aplicável; usa faster-whisper backend. TTS usa adapter/provider model; Chatterbox é candidato local a benchmark. Pronunciation Dictionary é obrigatório para nomes, marcas, siglas e termos técnicos.

### 8.4 Áudio

Sound AI produz music/SFX plan e respeita direitos. Mastering e normalização são determinísticos com FFmpeg/EBU R128. Assets musicais precisam de rights record; conteúdo gerado precisa de provenance/model record.

## 9. Publishing Engine

Fonte editorial canônica em Markdown/AST estruturado. Pandoc é o conversor universal candidato; Typst é candidato para PDF/layout determinístico. EPUB é validado com W3C EPUBCheck. DOCX/HTML/Markdown/EPUB/PDF são derivados do mesmo conteúdo editorial.

KDP-ready passa por preflight de dimensões, bleed, fontes, imagens, links, índice, metadata e EPUB/PDF validation. Cover e miolo ficam versionados separadamente mas ligados ao mesmo Content Master.

## 10. Slides

PptxGenJS é candidato principal para PPTX programático com Slide Masters, branding e charts. Slides também podem ser renderizados em PDF. A fábrica mantém um Slide Schema intermediário para não depender de uma biblioteca única.

## 11. Course Engine

Course Master deriva do CONTENT_MASTER, mas possui objetivos de aprendizagem, pré-requisitos, competências, módulos, lessons, examples, exercises, quiz banks, assessment blueprint e remediation paths.

Não converter resumo em curso. Aplicar progressão pedagógica, active recall, exemplos, prática e avaliação. Exportar artefatos web/slides/PDF e, quando necessário, adapters para padrões de interoperabilidade (QTI/H5P/SCORM/xAPI), evitando embutir um LMS completo no core.

## 12. Social & Publishing Connectors

Cada plataforma usa adapter com OAuth/credencial oficial, rate limits, idempotency, platform policy e audit. Postiz pode ser usado como serviço externo/isolado para scheduling após avaliação AGPL; nunca é dependência interna do domínio.

## 13. Segurança

Todo arquivo externo é não confiável. Sanitizar HTML/SVG/metadata/archives/documents; bloquear executáveis, macros e scripts; validar MIME/magic bytes; media processing em sandbox; proteger contra path traversal, SSRF, command injection, dependency poisoning e prompt injection.

Ferramentas externas passam pelo Open Source Intake Gate. Secrets ficam em mecanismo aprovado pela Holding. Workers têm least privilege, egress control e limites de recurso. Uploads e derivados possuem malware scan e quarantine state.

## 14. Proveniência e autenticidade

Implementar provenance ledger interno e C2PA quando o formato/fluxo permitir. C2PA complementa, não substitui, os registros internos de source/license/usage_right/derivative_permission.

## 15. Observabilidade e avaliação

OpenTelemetry é a interface de telemetria. Langfuse pode ser usado para LLM traces/evals se aprovado como serviço compartilhado. Promptfoo entra em CI para evals/red-team de prompts/agentes. Media QA e factual QA têm métricas próprias.

## 16. QA final

Verificar obrigatoriamente:

- factualidade e claim coverage
- gramática/estilo
- originalidade e duplicação
- continuidade narrativa/visual
- branding
- direitos/licenças/atribuição
- resolução, fps, aspect ratio, bitrate e codec
- áudio/loudness/clipping
- sincronização A/V
- captions, timing e safe areas
- links e metadata
- PDF/EPUB/PPTX integrity
- accessibility mínima aplicável
- custos versus budget
- provenance completeness

## 17. Approval Policy Engine

Cada tenant/project define quais classes podem auto-publicar e quais exigem aprovação humana. Mudança de direitos, conteúdo sensível, claims de alto impacto, novo provider/modelo ou custo acima do limite pode elevar o gate automaticamente.

## 18. Multi-tenancy

Tenant isolation desde o primeiro schema: tenant_id em todo objeto de negócio relevante, namespaces de storage, quotas, credentials, brand libraries, policies e cost ledgers separados. Nunca reutilizar asset privado de um cliente em outro sem autorização explícita.

## 19. Critério de versão final

A versão só é considerada operacional quando um único E2E_FULL, usando uma mesma base de conhecimento real, produz e valida:

1. CONTENT_MASTER
2. vídeo longo
3. Short/Reel 9:16
4. artigo
5. e-book EPUB + PDF
6. audiobook
7. curso com slides + quiz + material de apoio
8. lineage/provenance/rights/cost records
9. QA consolidado
10. publication/export package

Não existe aprovação por 'módulo 70% pronto'. Componentes podem ser implementados internamente em ordem técnica, mas toda promoção de versão exige o fluxo completo.