# Research AI — Improvements & Hardening Review

Data de corte: 2026-09-15

Esta revisão foi feita após comparar a arquitetura inicial com projetos e serviços atuais. Só entram melhorias com função distinta; alternativas sobrepostas permanecem como referência.

## Melhorias incorporadas

### 1. WARC para snapshots web reproduzíveis

Adicionar `webrecorder/warcio` (Apache-2.0) como formato/ferramenta de preservação opcional de páginas adquiridas legalmente. O WARC preserva request/response e melhora reproducibility/provenance. Não substitui GCS: WARC é o formato do snapshot, GCS é o armazenamento.

Classificação: `USE` para captures em que os direitos permitam retenção.

### 2. Schemathesis para APIs próprias/sandbox

Adicionar `schemathesis/schemathesis` (MIT) para validação de APIs OpenAPI/GraphQL controladas pela organização ou explicitamente autorizadas para teste. Ele gera casos e verifica divergência de schema/edge cases.

Regra: não executar fuzz/property testing agressivo contra APIs públicas de terceiros. Para terceiros, o `API Probe Engine` usa requests mínimos, read-only e aderentes aos termos/rate limits.

Classificação: `ADAPT`.

### 3. Egress web realmente controlado

Research AI é uma workload de alto risco porque acessa URLs fornecidas por fontes externas. A configuração `PRIVATE_RANGES_ONLY` usada pelo Control Plane não é suficiente como política final para esse serviço, pois destinos públicos podem sair diretamente para a internet.

Para Research AI:

- Cloud Run Direct VPC egress com `all-traffic`;
- network tags dedicadas;
- egress policy central;
- Google Cloud Secure Web Proxy para HTTP/HTTPS quando economicamente/tecnicamente apropriado;
- deny-by-default para categorias/endpoints internos;
- logs de egress para investigação;
- SSRF guard na aplicação continua obrigatório, mesmo com proxy.

O proxy não substitui validação de URL/DNS/redirect na aplicação.

### 4. Video acquisition com separação discovery/download

YouTube Data API permanece owner de discovery/metadata. `yt-dlp` pode ser usado apenas no `Download Manager`, em worker isolado, para conteúdo cujo download é autorizado por direitos/termos.

Preferir instalação Python/PyPI auditada em vez de bundle executável que agrega licenças adicionais. Registrar versão, extractor, URL, rights decision e SHA-256 do asset.

Classificação: `ADAPT`, jamais crawler indiscriminado.

### 5. ClamAV isolado

`Cisco-Talos/clamav` permanece scanner antimalware em boundary separado. Como é GPL-2.0, não incorporar seu código ao produto proprietário. Consumir como processo/serviço operacional e manter a avaliação de licença registrada.

### 6. Search provider sem lock-in

A busca geral terá `SearchProvider` interface. Nenhum vendor ocupa o Source Registry como fonte de verdade.

- Brave: condicional; termos padrão 2026 restringem retenção de Search Results sem storage rights.
- Tavily: candidato de discovery; não usar output de AI Functionality para decisões críticas ou como fonte primária.
- Exa: candidato semântico/deep discovery; contratos/custos/direitos devem passar por auditoria.
- Crawl4AI: acquisition após discovery; não é substituto conceitual do search index.

### 7. Evidence-first synthesis

O Synthesizer só recebe `Evidence` e metadados aprovados pelo quality/security/rights gates. Texto cru não validado não entra diretamente no prompt de síntese quando puder ser separado/normalizado antes. Isso reduz prompt injection e claims sem rastreabilidade.

### 8. Reproducibility manifest

Cada `ResearchPackage` deve conter/ligar um manifest com:

- versão do pipeline;
- versões dos adapters/parsers;
- query plan hash;
- source/snapshot IDs;
- timestamps;
- modelo + model policy usados na análise/auditoria;
- tool calls/probes redigidos de secrets;
- package hash;
- environment/build digest.

O objetivo é reproduzir o caminho da evidência sem depender do histórico de chat.

### 9. Provider capability benchmark

Watchers não substituem ferramenta automaticamente. Para promover um candidato `superior_component`, executar benchmark comparável contra owner atual em corpus fixo, medindo:

- success rate;
- extraction quality;
- latency;
- resource/cost;
- security findings;
- license/commercial impact;
- maintenance/activity;
- failure recovery.

Só depois pode ocorrer `USE/ADAPT`.

## Melhorias rejeitadas por redundância

- segundo crawler geral junto com Crawl4AI;
- segundo parser documental padrão junto com Docling;
- Elasticsearch/OpenSearch antecipado;
- MinIO ao lado de GCS;
- Redis apenas para manter estado de workflow;
- Celery apenas para duplicar Temporal;
- LangGraph/LangChain ao lado de PydanticAI + Temporal;
- segunda plataforma de observabilidade em paralelo ao OpenTelemetry + stack GCP;
- YARA como requisito padrão quando ClamAV + MIME/archive controls atendem o risco inicial; pode ser acrescentado somente por ameaça concreta.

## Consequência arquitetural

A versão final fica menor em número de owners, mas mais robusta em provenance, segurança, rights, durability e auditabilidade. Novas ferramentas são adicionadas somente onde não existe owner equivalente ou onde um boundary de segurança específico exige tecnologia própria.
