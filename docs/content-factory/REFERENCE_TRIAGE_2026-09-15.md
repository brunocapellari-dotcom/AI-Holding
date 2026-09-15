# Content Factory — Triagem das Referências Originais

Data: 2026-09-15
Status: complemento da revisão GitHub

## Regra

Nenhuma referência original vira dependência por nome, popularidade ou por já existir. Ela precisa resolver um gap melhor que o stack canônico, passar pelo Open Source Intake Gate e não duplicar Research AI, Knowledge Factory, Temporal, ComfyUI, FFmpeg/Remotion, Publishing Engine ou Course Engine.

## MoneyPrinterTurbo

Repositório confirmado: `harry0703/MoneyPrinterTurbo`.
Licença do código: MIT.
Escopo observado: gerador all-in-one de shorts que parte de tópico/keyword e automatiza script, busca/matching de footage, subtitles, background music e composição.
Decisão: `REFERENCE / COMPONENT SOURCE`, não core.

O valor principal é estudar UX e recipe de shorts, seleção de footage, legendas e fluxo de providers. Não incorporar o produto inteiro: ele sobrepõe Content Strategist/Script, Media Engine, captions, provider routing e composição. Componentes/algoritmos úteis podem ser reimplementados ou adaptados após intake e testes.

## AgentTube

Repositório confirmado: `TayyabAsghar/AgentTube`.
Licença declarada: MIT.
Escopo observado: análise de YouTube, transcrição, chat sobre vídeo, geração de títulos/scripts alternativos e thumbnails, além de billing/auth próprios.
Decisão: `REFERENCE`.

Não incorporar Clerk/Stripe/Convex/Schematic nem criar segundo mecanismo de ingestão/pesquisa; isso duplicaria Holding/Research AI. Aproveitar apenas padrões úteis de interação vídeo->transcrição->derivados se superarem o desenho atual.

## OpenShorts

A busca atual retorna múltiplos repositórios/forks com nome `openshorts`, sem origem canônica inequivocamente identificada apenas pelo nome fornecido.
Decisão: `HOLD / REFERENCE_UNRESOLVED`.

Não entra em runtime até resolver provenance do repositório, licença, histórico de commits e diferenciar upstream de forks. Esta regra evita supply-chain confusion/dependency confusion.

## NeoAcademy

Não foi localizado um repositório GitHub inequívoco correspondente ao nome fornecido na busca atual.
Decisão: `REFERENCE_UNRESOLVED`.

O Course Engine não fica bloqueado por isso; sua arquitetura é própria e interoperável. Se a referência exata aparecer, será comparada contra Course Master + pedagogical pipeline + QTI/H5P/SCORM/xAPI adapters.

## PDF-to-Interactive-Lesson

O nome não resolveu para um upstream inequívoco na busca atual; foram encontrados projetos genéricos próximos, não uma correspondência suficientemente segura.
Decisão: `REFERENCE_UNRESOLVED`.

Não adotar projeto de nome aproximado. O caso de uso já está coberto por SOURCE_PACKAGE/CONTENT_MASTER -> Course Master -> lesson/assessment/material pipeline.

## StoryMind / Story-to-Video Studio / StoryboardAI / Calliope / LocalMiniDrama / story2video / NovaClip / Podcast Shorts Factory / TryPost / ContentFlow / Social Agent AI / book-writer / AI Book Generator / Booker / Audiobook Generator

Continuam `REFERENCE_PENDING_INTAKE`. O nome isolado pode corresponder a mais de um repositório/produto e não é suficiente para promoção. A avaliação deve usar URL/upstream exato, commit/tag, licença, manutenção, SBOM, segurança e comparação objetiva de capacidade.

## Remotion — risco de licença explicitado

Remotion é tecnicamente indicado para composição programática, mas não deve ser tratado como open source irrestrito. A política pública atual oferece licença gratuita para indivíduos e organizações de até 3 pessoas; colaboração/empresas com 4+ pessoas requerem Company License. Portanto:

- classificação: `APROVADO_COMPONENTE_CONDICIONAL`;
- FFmpeg permanece primitive canônico;
- Render Spec não pode depender de APIs proprietárias do Remotion;
- manter caminho de substituição documentado;
- antes de uso com clientes/equipe maior, validar licença comercial vigente.

## Resultado

A triagem reforça que não existe vantagem em montar o Content Factory por colagem de geradores completos. O caminho final permanece: núcleo de domínio próprio + registries + Temporal + providers/renderers substituíveis. Repositórios especializados entram somente quando resolvem uma função específica melhor e com fronteira removível.