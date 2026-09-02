# WorldWar Modern — Reboot Operacional/Tático

Data: 02/09/2026
Status: ESPECIFICAÇÃO CANÔNICA NOVA

Esta especificação **substitui a direção funcional anterior do WorldWar Modern**. O código, assets ou regras existentes só devem ser reaproveitados se servirem ao novo desenho e passarem por revisão técnica. Não manter sistemas antigos apenas por já existirem.

## 1. Visão

Transformar WorldWar Modern em um **RTS moderno operacional/tático de guerra em larga escala**, no qual o jogador atua como comandante militar e conduz campanhas, batalhas e conquista territorial diretamente no terreno.

A principal referência conceitual enviada pelo Owner foi *The Last General*: ordens estratégicas desenhadas no mapa, companhias executando ações, captura de território/cidades, economia de guerra e combate moderno em grande escala. A referência é de direção de produto, não autorização para copiar código, assets, mapas, interface ou propriedade intelectual.

O WorldWar deve ter identidade própria, com foco em:

- guerra moderna;
- comando de batalhas;
- manobra;
- território;
- logística;
- inteligência/sensores;
- defesa aérea;
- apoio aéreo/naval;
- fog of war;
- cadeia de comando;
- decisões táticas e operacionais.

## 2. Loop principal do jogo

`reconhecer -> planejar -> desenhar ordens -> posicionar forças -> executar -> reagir -> conquistar/perder terreno -> reabastecer/reorganizar -> continuar campanha`

O jogador deve sentir que está comandando uma guerra, não preenchendo menus.

## 3. Escalas de comando

### 3.1 Escala operacional

Mapa 3D amplo com:

- cidades;
- vilas;
- estradas;
- pontes;
- rios;
- áreas industriais;
- aeroportos;
- portos;
- depósitos;
- colinas/relevo;
- florestas/áreas abertas;
- setores territoriais;
- linhas de frente;
- eixos de suprimento.

O jogador desloca forças, forma reservas, escolhe eixos de ataque, protege logística e decide onde concentrar poder de combate.

### 3.2 Escala tática

Zoom contínuo ou transição fluida para acompanhar a batalha em detalhe:

- infantaria;
- blindados;
- IFV/APC;
- artilharia;
- defesa aérea;
- engenharia;
- reconhecimento;
- logística;
- helicópteros;
- aeronaves quando em missão;
- forças especiais quando aplicável.

A unidade básica de comando deve ser inicialmente **companhia**, com elementos subordinados internos. Batalhões/brigadas agregam várias companhias para ordens de alto nível.

Controle de cada soldado individual não é requisito do primeiro ciclo. O objetivo é escala + clareza + performance.

## 4. Ordens desenhadas no terreno

Este é um requisito central.

O jogador deve poder desenhar ou apontar ações no mapa e atribuí-las a uma ou várias unidades.

Tipos iniciais:

- MOVE;
- ADVANCE;
- ATTACK;
- ASSAULT;
- DEFEND;
- HOLD;
- RECON;
- SCREEN;
- FLANK;
- BREACH;
- SUPPRESS;
- WITHDRAW;
- RETREAT;
- RESUPPLY;
- SUPPORT;
- ARTILLERY FIRE MISSION;
- AIR ASSAULT;
- CAS REQUEST;
- CAP/INTERCEPT;
- SEAD;
- NAVAL SUPPORT quando aplicável.

Uma ordem pode conter:

- origem;
- rota/eixo desenhado;
- objetivo;
- horário/condição de início;
- postura;
- velocidade;
- regras de engajamento;
- prioridade;
- unidade de apoio;
- condição de abortar/retirar.

O engine interpreta a ordem e a unidade executa autonomamente ações de baixo nível.

## 5. Território

Eliminar a lógica simplista de 'capturou uma base = dominou um país'.

O território deve ser dividido em **setores geográficos e objetivos estratégicos**.

Controle territorial depende de:

- presença militar;
- captura de cidades/vilas;
- infraestrutura crítica;
- linhas de comunicação;
- capacidade de sustentar forças;
- contestação inimiga.

Estados do setor:

- FRIENDLY_CONTROLLED;
- FRIENDLY_CONTESTED;
- NEUTRAL;
- ENEMY_CONTESTED;
- ENEMY_CONTROLLED.

A linha de frente é derivada desses setores e muda durante a batalha.

Conquistar uma cidade deve alterar visualmente e operacionalmente o mapa.

## 6. Objetivos estratégicos

Objetivos possíveis:

- cidade;
- capital regional;
- porto;
- aeroporto/base aérea;
- ponte;
- entroncamento rodoviário;
- depósito;
- refinaria;
- fábrica militar;
- usina/energia;
- centro de comunicações;
- radar;
- área industrial;
- posição defensiva relevante.

Cada objetivo pode fornecer valor militar/logístico/econômico.

## 7. Logística de combate

Nenhuma força deve lutar indefinidamente sem suprimento.

Cada unidade possui, conforme tipo:

- combustível;
- munição;
- munição especializada;
- peças/manutenção;
- disponibilidade;
- efetivo;
- moral/cohesion;
- fadiga;
- readiness.

Rede logística:

`indústria/estoque -> depósito estratégico -> depósito avançado -> caminhões/rotas -> unidade`

Interdição de estradas, pontes, depósitos ou comboios reduz capacidade de combate.

Unidade isolada pode:

- reduzir ritmo;
- ficar sem munição;
- ficar sem combustível;
- perder coesão;
- render-se/abandonar posição em situações extremas definidas pelo modelo.

## 8. Sensores, inteligência e fog of war

O jogador não vê tudo.

Fontes de detecção:

- observador terrestre;
- radar;
- AEW&C;
- UAV;
- aeronave de reconhecimento;
- satélite abstrato quando cenário permitir;
- SIGINT/EW abstrato;
- navios;
- sensores de defesa aérea.

Cada contato possui:

- posição estimada;
- timestamp;
- classificação provável;
- confiança;
- erro/incerteza;
- última detecção.

Contatos envelhecem e podem estar errados.

AEW&C volta a ter função real e deve detectar alvos aéreos dentro de cobertura; sistemas terrestres/ISR específicos tratam alvos de solo.

## 9. Defesa aérea e guerra aérea

Missões aéreas devem ser ordens operacionais completas:

- CAP;
- interceptação;
- escort;
- strike;
- CAS;
- SEAD/DEAD;
- reconnaissance;
- AEW&C;
- transport;
- air assault;
- tanker quando aplicável.

O sistema considera:

- alcance;
- combustível;
- armamento;
- base de origem;
- sortie generation;
- radar;
- SAM;
- interceptadores;
- perdas;
- turnaround/manutenção.

Aeronaves não ficam eternamente em missão e voltam à disponibilidade apenas após o ciclo real de retorno/rearm/refuel.

## 10. Guerra terrestre

A resolução de combate não será uma simples comparação de números.

Fatores:

- terreno;
- cobertura;
- elevação;
- linha de visão;
- alcance;
- tipo de arma;
- blindagem;
- postura;
- surpresa;
- moral/cohesion;
- supressão;
- apoio de artilharia;
- apoio aéreo;
- reconhecimento;
- engenharia;
- supply;
- flanco;
- fortificação;
- concentração de forças.

Batalhas devem ser visíveis, com projéteis/efeitos/linhas de fogo de forma compatível com performance e sem transformar o jogo em arcade.

## 11. Artilharia

Criar um Fire Support Engine próprio.

Capacidades:

- seleção de bateria;
- alcance;
- tipo de munição;
- salvas;
- tempo de preparação;
- tempo de voo;
- dispersão;
- observador/correção;
- counter-battery;
- consumo de munição;
- deslocamento após tiro;
- risco de detecção.

## 12. Engenharia

Unidades de engenharia devem alterar batalha:

- abrir passagem;
- remover/lançar obstáculos;
- preparar defesa;
- reparar ponte;
- construir ponte temporária quando cenário permitir;
- apoiar travessia;
- recuperar veículos;
- melhorar posições.

## 13. Naval e litoral

Quando o teatro possuir costa:

- surface combat;
- submarino de forma compatível com o modelo;
- defesa aérea naval;
- patrulha;
- bloqueio;
- escolta;
- desembarque/amphibious assault;
- shore fire support;
- proteção de rotas marítimas.

Navios nunca atravessam terra. Rotas devem respeitar geometria navegável.

## 14. IA militar

A IA adversária deve agir como comandante, não como script passivo.

Ela deve:

- reconhecer;
- identificar ameaças;
- escolher objetivos;
- concentrar forças;
- manter reservas;
- defender gargalos;
- explorar flancos;
- recuar quando necessário;
- contra-atacar;
- usar artilharia;
- empregar defesa aérea;
- proteger logística;
- atacar logística inimiga;
- reagir a perdas;
- adaptar plano.

Arquitetura recomendada:

- Strategic Planner;
- Operational Planner;
- Tactical Controller;
- Unit Controller;
- Threat/Opportunity Map;
- Utility/goal scoring;
- state machine/behavior tree apenas onde fizer sentido;
- simulação/evaluation para escolha entre COAs (courses of action).

Mesa/Mesa-Geo e OpenRA permanecem referências conceituais; regras do jogo serão próprias.

## 15. Economia e produção

Economia deixa de ser um painel abstrato e passa a sustentar o esforço de guerra.

Territórios podem fornecer:

- população/manpower abstrato;
- indústria;
- combustível;
- logística;
- capacidade de reparo;
- capacidade de produção.

A produção militar pode continuar automática por política/prioridade, mas agora alimenta pools reais de equipamento, munição e reposição.

O jogador define prioridade, não precisa clicar para fabricar cada unidade.

## 16. Diplomacia e política

Diplomacia permanece, mas deixa de ocupar o núcleo do gameplay.

Ela deve surgir de ações e interesses reais:

- alianças;
- acesso militar;
- bases conjuntas;
- comércio;
- sanções;
- cessar-fogo;
- apoio;
- reputação;
- escalada.

Nenhum botão simplesmente 'aumenta diplomacia'. Relações mudam por eventos, acordos e comportamento.

## 17. Operações especiais e guerra eletrônica

Mantidas como capacidades de suporte, não como botão mágico.

Possíveis efeitos abstratos/operacionais:

- reconnaissance;
- sabotagem de infraestrutura militar;
- interferência de sensores/comunicações;
- apoio a reconhecimento de alvos;
- ações clandestinas conforme regras do cenário.

Sucesso, duração e evidência devem ser modelados; ações inimigas relevantes geram aviso/inteligência ao jogador quando detectadas.

## 18. Controle direto

Capacidade FUTURA e opcional de assumir diretamente um veículo/aeronave/soldado em primeira ou terceira pessoa.

Não entra no primeiro gate se atrasar o RTS. O jogo deve ser excelente como comandante antes de adicionar controle direto.

## 19. Mapas

Direção preferencial: mapas grandes, visualmente ricos e coerentes, sem obrigar uso de mapa mundial inteiro em uma única cena.

Arquitetura possível:

- campanha/teatro;
- battlefield tiles/regions;
- streaming de terreno e objetos;
- terreno real simplificado quando houver dados adequados;
- geração procedural onde necessário.

Fontes abertas podem futuramente fornecer relevo/estradas/uso do solo, respeitando licenças e atribuições. O jogo não depende de serviços pagos de mapas.

## 20. Stack web recomendado

O produto continua **site privado**, não app.

### Cliente 3D

- `BabylonJS/Babylon.js` — candidato principal para engine 3D/WebGPU;
- WebGPU com fallback compatível quando necessário;
- instancing/thin instances/LOD para milhares de objetos;
- Web Workers para simulação pesada fora da UI;
- assets próprios/licenciados.

### Navegação

- `recastnavigation/recastnavigation` — referência/componente para navmesh local;
- hierarchical pathfinding próprio para ordens operacionais em grande escala;
- path classes distintas para infantaria, veículo, helicóptero e naval.

### Simulação

Código próprio para:

- orders;
- command hierarchy;
- combat;
- territory;
- logistics;
- sensors;
- air missions;
- naval missions;
- economy;
- strategic AI.

Não usar física completa em milhares de unidades se um modelo determinístico/kinemático resolver melhor e com mais performance.

### Persistência/backend

Servidor privado e estado persistente. Nenhuma regra sensível ou segredo deve depender exclusivamente do cliente do navegador.

Multiplayer não é requisito inicial; se entrar depois, deve usar servidor autoritativo e solução de rede avaliada pelo Intake Gate.

## 21. Segurança

Inegociável:

- site privado autenticado;
- HTTPS;
- secrets somente no servidor/cofre;
- nunca enviar credenciais do backend ao cliente;
- CSP e headers de segurança;
- dependências pelo Open Source Intake Gate;
- SBOM;
- Gitleaks;
- Semgrep;
- Trivy/Grype conforme pipeline;
- build assinado quando adotado;
- audit log de comandos administrativos;
- rate limiting;
- backups;
- isolamento entre ambiente de desenvolvimento e produção;
- sem execução arbitrária de mods/scripts enviados pelo usuário;
- assets externos somente após validação de licença/origem.

## 22. O que é descartado da versão anterior

Por padrão, ficam descartados até prova de utilidade:

- UI baseada principalmente em menus e botões desconectados do terreno;
- turno como mecanismo principal de andamento;
- diplomacia por clique;
- captura de país baseada em uma única base;
- batalhas invisíveis ou apenas numéricas;
- unidades que executam missões sem ciclo completo;
- produção manual repetitiva;
- IA que não reage militarmente;
- movimentação simplificada que ignora terreno/soberania/geometria;
- sistemas antigos que obriguem preservar arquitetura inadequada.

## 23. O que pode ser reaproveitado

Somente após auditoria:

- catálogo de equipamentos;
- dados de países;
- assets licenciados/legítimos;
- conceitos de bases/aeroportos/portos;
- modelos de disponibilidade;
- partes de economia que tenham domínio limpo;
- regras já corretas de idempotência/missão;
- qualquer componente que reduza trabalho sem impor o desenho antigo.

## 24. Gates de desenvolvimento

### Gate A — campo de batalha funcional

- mapa 3D;
- seleção de unidades;
- ordens desenhadas;
- deslocamento respeitando terreno;
- setores territoriais;
- captura de objetivo;
- linha de frente visível.

### Gate B — combate tático

- detecção/fog of war;
- combate terrestre;
- artilharia;
- moral/readiness;
- perdas;
- recuo;
- IA tática.

### Gate C — guerra operacional

- logística;
- depósitos;
- supply routes;
- reservas;
- defesa aérea;
- missões aéreas;
- engenharia;
- campanha territorial.

### Gate D — guerra conjunta

- naval/litoral;
- operações especiais/EW;
- economia de guerra;
- diplomacia baseada em ações;
- IA estratégica completa.

### Gate E — expansão

- multiplayer se desejado;
- controle direto se agregar mais valor que custo;
- geração procedural/real geospatial mais avançada;
- novos teatros e campanhas.

## 25. Critério de sucesso

O WorldWar Modern novo deve permitir que o jogador olhe para o mapa e pense em termos militares:

- onde atacar;
- onde defender;
- onde está o inimigo;
- onde pode estar;
- qual terreno favorece cada força;
- como cortar suprimento;
- quando empregar reserva;
- onde colocar artilharia/defesa aérea;
- qual cidade/ponte/rodovia vale conquistar;
- quando recuar;
- como transformar uma vitória tática em ganho territorial.

Se o jogo voltar a ser principalmente uma sequência de menus, cliques administrativos e eventos sem batalha visível, o reboot falhou.
