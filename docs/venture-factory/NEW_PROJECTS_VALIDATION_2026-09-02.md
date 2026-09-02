# Novos Projetos — Lista para Validação

Data: 02/09/2026

## Critério

Somente entram aqui oportunidades que merecem existir como projeto/unidade própria ou como candidato forte a spin-off. Módulos que aumentam valor de projetos existentes foram removidos desta lista para evitar fragmentação.

Gates econômicos da Holding:

- automação madura >= 80–90% quando plausível;
- compatível com o emprego atual do Owner;
- baixa dependência presencial recorrente;
- validação barata antes de escala;
- receita recorrente ou efeito de rede/dados;
- caminho plausível para unit economics positivos;
- segurança, licença e compliance controláveis;
- reutilização preferencial do Product/Data/Knowledge/Security Core da Holding.

## Prioridade 1 — AgroLog Fleet OS Brasil

**Status proposto:** VALIDAR AGORA

Plataforma para transportadoras/frotistas, inicialmente MT/corredores AgroLog.

Módulos consolidados no mesmo produto:

- Fleet Profitability e margem econômica real por viagem;
- documentos CT-e/MDF-e/NF-e/POD;
- motorista/viagem/ocorrências;
- manutenção e Asset Health;
- Tire Intelligence;
- Fuel Intelligence/Fuel Fraud;
- detention/waiting/turnaround;
- Route Risk/GeoRisk;
- Driver Copilot voz/offline;
- road quality signals;
- parts/services procurement network futuro;
- counterparty/customer operational score futuro.

Componentes/referências: Fleetbase por módulos/arquitetura, Traccar, OpenDBC/SavvyCAN, NFePHP, OR-Tools/PyVRP/Valhalla/FMM, PyOD, Pipecat, MapLibre/deck.gl.

**Moat:** custo/tempo/rota/manutenção/espera reais acumulados em operação brasileira.

## Prioridade 2 — Corporate Knowledge & Compliance OS

**Status proposto:** VALIDAR INTERNAMENTE PRIMEIRO

Transformar a Knowledge Factory da Holding em produto B2B.

Módulos consolidados:

- knowledge base citada e versionada;
- documentos/contratos;
- obrigações/vencimentos;
- SOP/checklists;
- treinamento/certificação;
- Tax/Regulatory Intelligence por domínio;
- vídeo/aulas/reuniões autorizadas;
- Source Hunter;
- atualização automática de normas e fontes;
- auditoria de resposta e confidence/evidence.

Componentes: Docling, LlamaIndex, Graphiti, pgvector, OpenAlex, Whisper.cpp, PySceneDetect, Frappe LMS, docassemble como referência, assinatura eletrônica via componente selecionado.

**Moat:** conhecimento validado + processo + evidência + atualização + integração operacional, não chatbot genérico.

## Prioridade 3 — Maintenance & Field Intelligence

**Status proposto:** VALIDAR

Vertical reutilizável para energia solar, refrigeração, bombas, irrigação, telecom, máquinas, indústria e facilities.

Módulos:

- assets;
- preventiva/corretiva;
- QR por ativo;
- ordem de serviço;
- agenda/território/técnico;
- rota;
- peças;
- IoT/telemetria;
- predictive maintenance;
- downtime/cost priority;
- voz/foto/evidência de campo.

Componentes/referências: Grash CMMS, OCA Field Service, OR-Tools/Timefold, Traccar, IoT core, PyOD/Nixtla, Pipecat.

## Prioridade 4 — Operational Intelligence Platform

**Status proposto:** VALIDAR APÓS PRIMEIROS CLIENTES OPERACIONAIS

B2B para empresas com ERP/TMS/WMS/CRM que querem reduzir gargalos e melhorar scheduling.

Motores:

- PM4Py process mining;
- OR-Tools/Timefold optimization;
- Nixtla forecasting;
- PyOD anomaly detection;
- document/ERP ingestion;
- scenario/simulation;
- before/after KPI attribution.

Não vender consultoria manual contínua; vender plataforma + diagnóstico automatizado + implantação controlada.

## Prioridade 5 — Risk & Counterparty Intelligence

**Status proposto:** VALIDAR

Monitoramento de fornecedores, clientes e contrapartes sem assumir concessão de crédito.

Módulos:

- identidade/resolução de entidade;
- sanções/compliance;
- corporate changes;
- pagamentos/atrasos autorizados;
- concentração/exposição;
- incidentes/geopolítica;
- maritime counterparties quando aplicável;
- score explicável com evidência.

Componentes/referências: OpenSanctions stack, Aleph, OpenCTI concepts, Graphiti, Official Sources News Engine.

## Prioridade 6 — Procurement Opportunity Radar Brasil

**Status proposto:** VALIDAR RÁPIDO

Radar de oportunidades de compra pública/privada, iniciando por PNCP e fontes oficiais, com matching empresa-oportunidade.

Entrega:

- oportunidades relevantes;
- prazo/valor/objeto;
- fit por CNAE/capacidade/região;
- documentos exigidos;
- checklist;
- alertas;
- histórico de participação/resultado quando autorizado.

Baixa complexidade inicial e forte automação. Não prometer chance de vitória.

## Prioridade 7 — Construction & Infrastructure Intelligence

**Status proposto:** VALIDAR NICHO RURAL/INDUSTRIAL

Não criar ERP de construção. Foco em inteligência de custo/avanço/compras/risco para galpões, silos, armazéns, obras rurais e infraestrutura.

Componentes/referências: OpenConstructionERP como referência, BIM/CAD parsers, SINAPI oficial, GeoRisk, procurement, document intelligence, PM4Py/OR-Tools.

Diferencial: custo regional + logística/frete + execução + geointeligência.

## Prioridade 8 — Agro Quality / Lab Intelligence

**Status proposto:** VALIDAR COMO VERTICAL AGROLOG; SPIN-OFF SÓ SE MERCADO JUSTIFICAR

LIMS/qualidade para solo, água, grãos, sementes, ração, fertilizantes e classificação.

Componentes/referências: SENAITE (licença exige gate), QR/barcode, instruments adapters, document engine, Traceability, analytics/anomaly.

Moat: ligar qualidade do lote a origem, armazenagem, transporte, ambiente e resultado operacional.

## Não abrir como projetos independentes agora

Estes itens ficam como motores/módulos:

- Voice Operations;
- GeoRisk/Live Earth;
- Tax Reform Intelligence;
- Contract Operations;
- Document Automation;
- Corporate Training/SOP;
- Traceability/Export Compliance;
- Carbon Intelligence;
- Road Intelligence Network;
- Tire Intelligence;
- Fuel Fraud;
- Fleet Parts Marketplace;
- Sports Broadcast Hub;
- Sports Realtime Data Gateway;
- Video Intelligence;
- Official Sources News Engine;
- Dataset Scout/Source Hunter;
- Agent Security Platform;
- Software Supply Chain Risk;
- Data Marketplace/API.

Eles devem provar valor dentro de uma plataforma existente antes de qualquer spin-off.

## Ordem de validação recomendada

1. AgroLog Fleet OS Brasil.
2. Procurement Opportunity Radar Brasil em paralelo como teste barato de monetização digital.
3. Corporate Knowledge & Compliance OS usando a própria Holding como cliente zero.
4. Maintenance & Field Intelligence.
5. Risk & Counterparty Intelligence.
6. Operational Intelligence.
7. Construction & Infrastructure Intelligence.
8. Agro Quality/Lab Intelligence.

A Venture Factory deve registrar acceptance criteria, custo máximo de validação, hipótese de preço, cliente-alvo e motivo objetivo de continuidade ou encerramento antes de escalar cada item.
