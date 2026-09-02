# Integrações nos Projetos Atuais — 02/09/2026

Este documento registra as inclusões consolidadas decorrentes das rodadas GitHub/arquitetura e das decisões finais do Owner em 02/09/2026. Quando uma unidade ainda não possuir repositório conectado, esta especificação no AI-Holding é a referência para posterior implementação no repositório próprio.

## 1. AgroLog MT

Referência detalhada: repositório `AgroLogMT`, `docs/PRODUCT_EXPANSION_2026-09-02.md`.

Inclusões mantidas:

- Official Sources Intelligence;
- Live Data Fabric;
- GeoRisk/Live Earth;
- Field Weather Station com ESP32/sensores como observação própria;
- Traceability/Export Compliance como módulo interno futuro condicionado a necessidade;
- Carbon Environmental Intelligence apenas como capacidade analítica;
- Maritime Weather/Disruption pós-V1;
- Knowledge/Video ingestion via Holding Knowledge Factory.

**AgroLog Fleet OS Brasil está descontinuado** e não deve consumir desenvolvimento sem nova validação objetiva de público.

Agro Quality/Lab não será novo negócio; manter apenas conhecimento/capacidades que sirvam ao AgroLog quando houver caso real.

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

## 5. WorldWar Modern — REBOOT

A especificação anterior foi substituída por:

`docs/portfolio/WORLDWAR_MODERN_REBOOT_2026-09-02.md`

Nova direção:

- RTS moderno operacional/tático;
- mapa 3D;
- ordens desenhadas no terreno;
- companhias/batalhões/brigadas;
- conquista por setores, cidades e objetivos estratégicos;
- frente dinâmica;
- logística de combustível/munição/manutenção;
- fog of war e sensores;
- defesa aérea e missões aéreas completas;
- artilharia/engenharia;
- guerra naval/litoral quando aplicável;
- IA tática/operacional/estratégica;
- economia e diplomacia como suporte à guerra, não como núcleo baseado em menus;
- batalha visível e comandável.

Stack web candidato:

- Babylon.js/WebGPU para 3D;
- Recast Navigation para navegação local;
- hierarchical pathfinding próprio para escala operacional;
- Web Workers e LOD/instancing para escala;
- engines de orders/combat/territory/logistics/sensors/AI próprios.

OpenRA e Mesa/Mesa-Geo permanecem apenas REFERENCIA conceitual. Não incorporar um RTS inteiro.

## 6. Maintenance & Field Intelligence — novo projeto aprovado

Único novo negócio mantido da rodada de Venture Factory.

Escopo:

- assets;
- manutenção preventiva/corretiva;
- QR por ativo;
- field service;
- agenda/rota/técnico;
- IoT/telemetria;
- predictive maintenance;
- voz/foto/evidência;
- SOP/checklists;
- integração com Security e Knowledge Core.

### Field Weather Station

Módulo formal baseado em ESP32 e sensores, compartilhado com o AgroLog para observações meteorológicas próprias.

Capacidades:

- temperatura/umidade/pressão;
- pluviômetro;
- vento;
- radiação opcional;
- solar/bateria;
- Wi-Fi/LoRa/celular conforme cenário;
- device health;
- armazenamento offline temporário;
- metadata de calibração;
- MQTT/telemetria segura.

Referências: ESPHome, OpenMQTTGateway, rtl_433, WeeWX e componentes LoRa levantados anteriormente, sempre sujeitos ao Open Source Intake Gate.

## 7. Hermes / Holding Assistant

Hermes deve consumir diretamente o AI-Holding Control Plane, não Plane/Jira como fonte de verdade.

Capacidades mantidas:

- Knowledge Factory;
- Official Sources News Engine;
- Source Hunter/Dataset Scout/Video Scout;
- Knowledge Transfer Agent;
- Business OS/ERP read layer;
- Voice engine futuro;
- Open Source Intake Gate;
- decision queue `Precisa de você` já existente no Control Plane.

Corporate Knowledge & Compliance OS foi descartado como nova empresa; a Knowledge Factory permanece infraestrutura interna fundamental da Holding.

## 8. Segundo Cérebro / Obsidian

Papel consolidado:

- conhecimento estrutural e validado;
- relações causais;
- métodos/modelos;
- eventos/casos;
- decisões/post-mortems;
- claims com fonte/data/escopo/confiabilidade/natureza;
- knowledge gaps e maturidade N0-N6.

Não armazenar segredos, credenciais ou dados operacionais brutos que pertencem a ERP/BigQuery/object storage.

## 9. Serviços compartilhados obrigatórios

Todos os projetos novos e atuais devem consumir quando aplicável:

- Security Control Plane;
- Product Core;
- Knowledge Factory;
- Data/Model Core;
- observabilidade;
- Open Source Intake Gate;
- AI-Holding Project/Task/Decision/Audit ledgers.

A regra é evitar cada projeto construir novamente auth, billing, audit, feature flag, ingestion de documentos, news engine, video engine, model registry ou policy engine.

## 10. Projetos comerciais descartados nesta decisão

Não entram na fila atual de novos negócios:

- AgroLog Fleet OS Brasil;
- Corporate Knowledge & Compliance OS como spin-off;
- Operational Intelligence Platform;
- Risk & Counterparty Intelligence como unidade nova;
- Procurement Opportunity Radar Brasil;
- Construction & Infrastructure Intelligence;
- Agro Quality/Lab Intelligence como spin-off.

Tecnologia útil descoberta nesses estudos pode ser reaproveitada por projetos existentes, mas não justifica reabrir uma unidade sem nova decisão do Owner.
