# Arquitetura oficial do Segundo Cérebro

## Propriedade

O Segundo Cérebro é infraestrutura cognitiva de todos os projetos. A Holding, AgroLog, Mercado Financeiro, Esportes, Geopolitical Watch e qualquer projeto futuro são clientes com namespaces e permissões próprios.

Nenhum componente do Segundo Cérebro pode exigir que a Holding exista. Dependências de integração são unidirecionais: `projeto -> Segundo Cérebro`.

## Autoridade

Markdown é a representação humana durável e canônica legível. Graphiti recebe uma projeção relacional/temporal idempotente e reconstruível e nunca possui capacidade de promover conteúdo ou alterar o vault.

Uma promoção canônica só é válida depois de passar pelos gates de evidência e validação e poder ser materializada de forma determinística em Markdown. Falha do grafo gera retry; nunca altera ou corrompe o conhecimento canônico.

## Pipeline governado

1. Source: cadastro e política da origem.
2. Observation: dado/afirmação capturada, ainda não institucional.
3. Evidence: evidência localizável, com proveniência e temporalidade.
4. Claim: interpretação proposta por agente/humano.
5. Comparison: deduplicação, revisão, conflito, conhecimento existente e histórico.
6. Audit: revisão independente proporcional ao risco.
7. Validation: aplicação determinística das regras de promoção.
8. Fact/Knowledge: registro institucional com claim, evidência e validação rastreáveis.
9. Graphiti: projeção temporal e relacional para máquinas.
10. Obsidian: representação humana, portátil e inspecionável.

Agentes de coleta, extração ou interpretação não podem autopromover o próprio Claim.

## Bitemporalidade

Separar sempre que aplicável:

- `valid_from` / `valid_to`: validade no mundo;
- `known_from` / `known_to`: quando aquela versão era conhecida pelo sistema;
- `observed_at`: momento da observação;
- `reference_date`: referência do dado;
- `publication_date`: publicação;
- `collected_at`: coleta.

Fatos superados permanecem consultáveis historicamente.

## IDs e namespaces

IDs seguem `sb:<tipo>:<identificador>` e não dependem de nome de arquivo. Namespaces começam por `shared/...` ou `project/<slug>/...`.

Conhecimento transversal existe uma vez no núcleo compartilhado. Projetos criam relações para esse conhecimento em vez de duplicar notas.

## Estrutura lógica do vault

`00_CORE`, `01_DOMAINS`, `02_PROJECTS`, `03_SOURCES`, `04_METHODS`, `05_MODELS`, `06_EVENTS`, `07_CASES`, `08_SKILLS`, `09_ENTITIES`, `10_DATA_DICTIONARIES`, `11_GLOSSARY`, `12_REFERENCES`, `13_LEARNINGS`, `14_DECISIONS`, `15_EVALUATIONS`.

Estruturas existentes melhores podem ser preservadas se mantiverem separação lógica equivalente.

## N1-N6

Promoção de maturidade considera fontes canônicas, literatura, metodologias, dados estruturados, modelos, validação empírica, casos históricos, incerteza, aplicação operacional e auditoria. Quantidade de notas não determina maturidade.

## Skills

Skill é capacidade operacional reutilizável e versionável. Conhecimento explica; Skill executa procedimento. Uma Skill referencia o conhecimento que a sustenta, mas não o duplica.

## Memória

A memória institucional inicial é formada por Segundo Cérebro + Graphiti + contexto fornecido pelo runtime. Letta e Cognee não fazem parte do núcleo inicial. Outros memory engines só entram se testes demonstrarem ganho material sem duplicação funcional.
