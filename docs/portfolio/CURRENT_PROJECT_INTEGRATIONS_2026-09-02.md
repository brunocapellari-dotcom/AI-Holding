# Integrações nos Projetos Atuais — 02/09/2026

Este documento registra as inclusões consolidadas decorrentes das rodadas GitHub/arquitetura. Quando uma unidade ainda não possuir repositório conectado, esta especificação no AI-Holding é a referência para posterior implementação no repositório próprio.

## 1. AgroLog MT

Referência detalhada: repositório `AgroLogMT`, `docs/PRODUCT_EXPANSION_2026-09-02.md`.

Inclusões:

- Official Sources Intelligence;
- Live Data Fabric;
- GeoRisk/Live Earth;
- Fleet OS candidato/subprojeto lógico;
- Traceability/Export Compliance;
- Carbon Environmental Intelligence;
- Agro Quality/Lab;
- Maritime Weather/Disruption pós-V1;
- Knowledge/Video ingestion via Holding Knowledge Factory.

Pecuária e Maritime permanecem domínios do AgroLog, com fronteiras lógicas próprias.

## 2. Inteligência Esportiva Quantitativa

### Sports Realtime Data Gateway

Criar adapters por modalidade/provedor, preferindo ligas, federações, organizadores e APIs oficiais. Provedores especializados entram como fallback/complemento e precisam de contrato de dados comum.

Cobertura progressiva:

- futebol;
- NBA/basquete;
- tênis;
- NFL;
- MLB;
- NHL;
- NCAA;
- F1/F2/F3/Formula E/IndyCar/NASCAR/MotoGP/WRC quando fonte adequada existir;
- vôlei, handebol, futsal, MMA, boxe, rugby, cricket, golfe, ciclismo, esports e outras modalidades conforme qualidade da fonte.

Níveis de capacidade por esporte: calendário/placar -> stats -> play-by-play -> tracking/event data -> video intelligence.

### Sports Broadcast Hub

Uma tela única deve mostrar onde assistir legalmente. Para conteúdo pago, abrir/deep-linkar o app/site oficial (Disney+, Globoplay/Premiere, Prime etc.) usando a autenticação já mantida pelo próprio serviço/dispositivo. Nunca armazenar senha do usuário em prompt/código/banco e nunca retransmitir sinal sem autorização.

Para transmissões abertas, exibir link oficial (YouTube/canal/federação/detentor). IPTV não autorizado fica fora do projeto.

### Sports Vision / Video Learning

Stack composto por partes, não produto único:

- SoccerNet datasets/devkits quando licença permitir;
- Kloppy;
- floodlight;
- socceraction;
- SportsLabKit;
- Supervision/trackers;
- CVAT/FiftyOne para dataset QA;
- Whisper/PySceneDetect/vision para contexto narrativo/visual quando autorizado.

Objetivo: produzir features próprias de tracking, espaço, pressão, transição, formação, matchup e comportamento tático. Não substituir validação quantitativa/OOS por análise visual subjetiva.

## 3. Mercado Financeiro

Stack funcional consolidado:

- OpenBB: dados/pesquisa e adapters;
- Qlib: pesquisa ML/fatores;
- VectorBT: experimentação/backtests rápidos;
- skfolio: portfolio construction/optimization;
- NautilusTrader: runtime de execução/risk quando necessário;
- MLflow/Feast/Evidently: compartilhados pela Holding somente após modelos operacionais reais.

Official Sources News Engine deve priorizar B3, CVM, BCB, Tesouro, IBGE, SEC/Fed e RI das empresas. Notícias secundárias podem contextualizar, mas fatos materiais devem apontar para fonte primária.

Preservar permanentemente survivorship bias, identidade histórica, vintages, leakage, OOS, CLV quando aplicável, drawdown e risco de ruína.

## 4. Monitor de Conflitos / Geopolitical Watch

Inclusões:

- Official Sources News Engine;
- GDELT como sinal/event discovery, nunca confirmação única;
- CelesTrak para camada orbital pública/propagada;
- readsb/ADS-B autorizado;
- AIS/maritime signals por contratos com o Maritime Core;
- OpenCTI/MISP como REFERENCIA de modelo de evento, confiança, first/last seen e relações;
- Cesium para 3D globe quando agregar valor; MapLibre/deck.gl continuam adequados a 2D;
- camada de infraestrutura crítica global;
- cross-project disruption events para Maritime/AgroLog/Energy.

Toda alegação de ataque, sanção, fechamento, dano ou controle territorial exige evidência e confidence; social media não é fonte canônica.

## 5. WorldWar Modern

Manter a especificação funcional canônica existente. GitHub entra como fonte de componentes/metodologias:

- OpenRA: REFERENCIA de ordens, state, produção, fog-of-war, units e AI;
- Mesa/Mesa-Geo: simulação multiagente e territorial;
- OR-Tools: logística/planejamento quando útil;
- MapLibre/Cesium conforme decisão de frontend;
- engines próprios obrigatórios: orders/idempotency, missions, sovereignty, routing, defense, battle, territory, diplomacy, economy, covert ops, production e events.

Não incorporar um RTS inteiro; absorver padrões e manter regras/estado do WorldWar sob código próprio.

## 6. Hermes / Holding Assistant

Hermes deve consumir diretamente o AI-Holding Control Plane, não Plane/Jira como fonte de verdade.

Novas capacidades:

- Knowledge Factory;
- Official Sources News Engine;
- Source Hunter/Dataset Scout/Video Scout;
- Knowledge Transfer Agent;
- Business OS/ERP read layer;
- Voice engine futuro;
- Open Source Intake Gate;
- decision queue `Precisa de você` já existente no Control Plane.

## 7. Segundo Cérebro / Obsidian

Papel consolidado:

- conhecimento estrutural e validado;
- relações causais;
- métodos/modelos;
- eventos/casos;
- decisões/post-mortems;
- claims com fonte/data/escopo/confiabilidade/natureza;
- knowledge gaps e maturidade N0-N6.

Não armazenar segredos, credenciais ou dados operacionais brutos que pertencem a ERP/BigQuery/object storage.

## 8. Serviços compartilhados obrigatórios

Todos os projetos novos e atuais devem consumir quando aplicável:

- Security Control Plane;
- Product Core;
- Knowledge Factory;
- Data/Model Core;
- observabilidade;
- Open Source Intake Gate;
- AI-Holding Project/Task/Decision/Audit ledgers.

A regra é evitar cada projeto construir novamente auth, billing, audit, feature flag, ingestion de documentos, news engine, video engine, model registry ou policy engine.
