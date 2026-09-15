# WorldWar Modern — Core 1.0 / V12

## Regra central

A interface nunca altera diretamente unidades, dinheiro, território, relações, bases, pesquisa ou combate. O fluxo canônico é:

`UI/AI -> Order -> SecurityGate -> OrderService -> Mission/System -> EventStore -> GameState -> UI`

## World Truth e Country Knowledge

`GameState` contém a verdade da simulação. Cada país recebe apenas sua `CountryKnowledge`, alimentada por sensores, patrulhas, inteligência e eventos observáveis. IAs nacionais não leem diretamente a verdade de outros países.

## Determinismo

Existe um único PRNG serializável (`DeterministicRNG`). Combate, diplomacia probabilística, operações especiais e estimativas usam esse PRNG. `Math.random()` não deve ser utilizado por regras de simulação.

## Event sourcing

Eventos importantes recebem ID, sequência, turno, data e payload. O save contém GameState, EventStore, versão do motor e estado do RNG. Isso permite auditoria e replay lógico.

## IAs

Global: `WorldDirectorAI`.

Por país: `NationalLeaderAI`, `MilitaryAI`, `EconomyAI`, `DiplomacyAI`, `IntelligenceAI`, `IndustryAI`, `ResearchAI`.

Os agentes operam somente sobre o estado nacional e o conhecimento disponível ao país.

## Bases conjuntas

Permissões explícitas:

- can_station_ground_units
- can_station_aircraft
- can_station_naval_units
- can_launch_air_missions
- can_launch_ground_operations
- can_resupply
- can_repair

## Patrulhas persistentes

Ciclo: `departing -> on_station -> returning -> refuel -> departing`.

Tipos suportados pelo núcleo: fronteira aérea, costa aérea, patrulha marítima, AEW&C e reconhecimento.

## Ocupação

Quando um país é ocupado, missões e patrulhas próprias ativas são encerradas. A soberania operacional é desativada, evitando que forças continuem patrulhando normalmente após a conquista.

## Indústria

A produção mensal abrange força completa: infantaria, forças especiais, artilharia, IFV, MBT, MLRS, drones, helicópteros, caças, bombardeiros, navios de superfície, destroyers, submarinos e porta-aviões. Produção é limitada por tesouro e capacidade industrial.

## Segurança / futuro multiplayer

`AuthoritativeGateway` representa a fronteira do servidor. Orders validam tipo, ownership, timestamps, rate limit, coordenadas e disponibilidade de recursos antes de alterar estado. O cliente recebe snapshots filtrados.

## Operações especiais

`SpecialOperationsSystem` permite efeitos temporários sobre sistemas como radar, defesa aérea, comunicações, energia e logística. Detecção gera alertas ao país afetado.
