# Project Control

Fronteira para gestão operacional de projetos: registry, milestones, critérios objetivos, tarefas, dependências, runs, decisões, approvals, incidentes, prioridades e progresso comprovado.

Durante a migração, a implementação validada permanece em `app/` e é a fonte operacional de verdade. Esta fronteira não autoriza uma reescrita: componentes serão extraídos somente quando houver compatibilidade, migration plan, acceptance e rollback.

Nenhum progresso pode ser inferido por narrativa. Estados, critérios e evidências do Control Plane determinam o status real.