# Infrastructure

Infraestrutura de produção da Holding. O Terraform validado permanece temporariamente em `infra/terraform`; novas stacks serão consolidadas gradualmente sob esta fronteira sem mover recursos de estado em uma única etapa.

Plataforma atual preservada: GCP, Cloud Run, Cloud SQL PostgreSQL privado, VPC/private service networking, Artifact Registry, WIF e Secret Manager de transição.

Alvos adicionais: AgentOS runtime, LiteLLM, OpenHands, Langfuse, Docker MCP Gateway e Infisical. Cada implantação deve ter identidade própria, menor privilégio, health/readiness, logs, métricas, backups quando persistente, plano de rollback e custo rastreável.
