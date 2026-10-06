# Control Plane

Aplicação de domínio da Holding. O pacote histórico `app/` continua sendo a implementação ativa durante a migração e será absorvido gradualmente por esta fronteira sem reescrita total.

Mantém projetos, milestones, acceptance criteria, tarefas, dependências, agentes, runs, decisões, aprovações, incidentes, políticas e auditoria. PostgreSQL é a fonte de verdade operacional.

O Control Plane não escolhe diretamente provedores de modelo, não executa coding agents no próprio processo, não distribui segredos e não é repositório canônico de conhecimento. Essas responsabilidades pertencem, respectivamente, a Model Gateway, Coding Agents, Secrets e Segundo Cérebro.
