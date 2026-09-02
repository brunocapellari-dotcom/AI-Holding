# Novos Projetos — Decisão Consolidada

Data: 02/09/2026
Status: decisão do Owner

## Decisão

Após as rodadas de pesquisa, somente **Maintenance & Field Intelligence** permanece como novo projeto em validação.

O **AgroLog Fleet OS Brasil está descontinuado** neste estágio por ausência de público validado. Não deve consumir desenvolvimento, infraestrutura ou esforço comercial até existir nova evidência objetiva de demanda.

Os demais candidatos da lista anterior foram descartados como novos negócios independentes. Capacidades úteis encontradas durante a pesquisa podem continuar existindo como componentes internos de projetos já ativos, desde que não abram uma nova unidade de negócio sem nova decisão do Owner.

## Projeto aprovado — Maintenance & Field Intelligence

**Status:** APROVADO PARA VALIDAÇÃO

Vertical reutilizável para manutenção e operação de campo em energia solar, refrigeração, bombas, irrigação, telecom, máquinas, agro, indústria e facilities.

### Núcleo

- cadastro e histórico de ativos;
- preventiva e corretiva;
- QR por ativo;
- ordem de serviço;
- agenda, território e técnico;
- rota e deslocamento;
- peças e consumíveis;
- IoT e telemetria;
- predictive maintenance;
- prioridade por risco/custo de parada;
- voz, foto e evidência de campo;
- checklists e SOPs;
- integração com Knowledge Factory e Security Control Plane.

### Módulo aprovado — Field Weather Station

Criar uma estação meteorológica modular de baixo custo baseada em **ESP32** como parte do Maintenance & Field Intelligence, com capacidade de alimentar também o AgroLog MT.

Capacidades por etapas:

1. temperatura, umidade e pressão;
2. pluviômetro de báscula;
3. velocidade e direção do vento;
4. radiação/iluminação quando houver sensor adequado;
5. energia solar + bateria para operação remota;
6. Wi-Fi no modelo simples e LoRa/4G/gateway quando a operação exigir;
7. armazenamento local temporário e sincronização após retorno da conectividade;
8. telemetria com timestamp, qualidade, calibração e health do dispositivo.

Componentes/referências a avaliar pelo Open Source Intake Gate:

- ESPHome;
- OpenMQTTGateway;
- rtl_433 quando fizer sentido integrar sensores RF existentes;
- MQTT;
- WeeWX como referência de software de estação;
- sensores ESP32/LoRa já levantados nas rodadas anteriores.

A estação não será tratada como estação oficial INMET. O sistema deverá confrontar leituras com INMET/CPTEC/CEMADEN/ANA e outras fontes canônicas quando aplicável, preservando diferença entre dado próprio observado e dado oficial.

### Segurança obrigatória do dispositivo

- credencial única por dispositivo;
- nunca usar senha/API key global embutida no firmware;
- TLS quando tecnicamente suportado;
- ACL por dispositivo/tópico no broker;
- sem portas de administração expostas diretamente à internet;
- OTA controlado e assinado quando adotado;
- secrets fora do GitHub;
- segmentação de rede/gateway;
- logs de atualização e identidade do firmware;
- revogação de dispositivo comprometido.

### Componentes de software de referência

- Grash CMMS — arquitetura de manutenção;
- OCA Field Service — arquitetura de operação de campo;
- OR-Tools/Timefold — agenda/roteamento quando útil;
- Traccar — localização autorizada quando houver caso real;
- PyOD/Nixtla — anomalia/predição após histórico suficiente;
- Pipecat — voz quando houver caso real;
- IoT Core próprio — ingestão, device registry, health, security e contratos.

Nenhum projeto externo será copiado integralmente. O domínio, APIs e regras comerciais serão próprios da Holding.

## Projetos descontinuados ou descartados como novos negócios

1. AgroLog Fleet OS Brasil — **DESCONTINUADO** por falta de público validado.
2. Corporate Knowledge & Compliance OS — **DESCARTADO COMO NEGÓCIO**; Knowledge Factory permanece infraestrutura interna da Holding.
3. Operational Intelligence Platform — **DESCARTADO**.
4. Risk & Counterparty Intelligence — **DESCARTADO COMO UNIDADE NOVA**; técnicas de risco podem ser reutilizadas internamente quando necessárias.
5. Procurement Opportunity Radar Brasil — **DESCARTADO**.
6. Construction & Infrastructure Intelligence — **DESCARTADO**.
7. Agro Quality / Lab Intelligence — **DESCARTADO COMO NOVO NEGÓCIO**; conhecimento útil pode permanecer no AgroLog sem spin-off.

## Regra de reaproveitamento

Descartar um projeto não significa apagar tecnologia útil. Componentes, algoritmos ou ideias descobertas podem ser absorvidos por um projeto existente quando:

- resolvam uma necessidade real já existente;
- passem por segurança, licença e testes;
- não criem nova fonte de verdade;
- não abram nova frente comercial sem validação;
- reduzam código/custo ou aumentem capacidade de forma mensurável.

A Venture Factory não deve reabrir os projetos descartados sem nova evidência objetiva de mercado ou decisão explícita do Owner.
