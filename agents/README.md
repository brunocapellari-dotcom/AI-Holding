# Agents

Papéis persistentes da Holding. Definições aqui descrevem autoridade e contratos; execução ocorre no AgentOS e acesso a modelos/ferramentas passa pelos gateways.

- **Hermes** — Chief of Staff do Owner; interface executiva persistente. Apresenta apenas estado comprovado e não substitui o Control Plane nem o Segundo Cérebro.
- **CEO IA** — priorização do portfólio, trade-offs, delegação e decisões dentro dos limites do Owner.
- **PMO IA** — milestones, tarefas, dependências, continuidade, replanejamento e evidência de conclusão.
- **Governance AI** — políticas, compliance, autonomia e gates de autorização.
- **Risk AI** — riscos operacionais, financeiros, legais e técnicos.
- **Auditor AI** — revisão independente de evidências, controles, testes e incidentes; quando usar modelo, não deve reutilizar o mesmo modelo produtor sem justificativa explícita.
- **Security AI** — acessos, comportamento anormal, postura de segurança, incidentes e segurança de ferramentas.
- **Architect AI** — arquitetura transversal, integrações, dependências e coerência técnica entre projetos.
- **Finance AI** — custos, runway, ROI, monetização e orçamento por unidade/projeto.
- **Consultores** — especialistas independentes para decisões sensíveis ou domínio específico.
- **Shared** — capacidades reutilizáveis sem serem fonte canônica de estado.
- **Projects** — agentes especializados vinculados às unidades/projetos.

Todos os agentes canônicos são registrados inicialmente de forma fail-closed. Registro não significa runtime ativo, permissão técnica ou acesso a segredo.

A0–A6 mede autonomia decisória. Cada agente também possui permissões técnicas independentes e explicitamente limitadas.