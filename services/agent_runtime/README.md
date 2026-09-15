# Agent Runtime — Agno AgentOS

Runtime principal de agentes da Holding.

A migração usa `base_app` para incorporar o FastAPI do Control Plane sem descartar as rotas e garantias atuais. Em conflitos de rota, o Control Plane existente é preservado. AgentOS usa PostgreSQL em schema próprio, fila durável e scheduler próprio; Cloud Scheduler deixa de ser o orquestrador primário.

Requisitos de produção antes de ativar o runtime:

1. autenticação das rotas AgentOS independente do prompt;
2. banco compartilhado e migrations verificadas;
3. model access somente via LiteLLM;
4. tool access somente via Policy/MCP Gateway;
5. tracing para Langfuse com redaction;
6. acceptance test que execute uma tarefa real de forma idempotente;
7. nenhum componente de Knowledge do AgentOS configurado como repositório canônico.

O worker PMO atual permanece como fallback durante a transição e será retirado somente depois de equivalência operacional comprovada.
