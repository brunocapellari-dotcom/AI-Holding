# Secrets — Infisical

Infisical é o destino oficial para segredos, credenciais e machine identities da Holding. A migração deve ser gradual: GCP Secret Manager permanece como bootstrap/ponte até cada consumidor ser validado com Infisical.

Princípios:
- identidade distinta por serviço e, quando necessário, por projeto;
- menor privilégio e acesso temporário quando possível;
- agentes não recebem segredo bruto se proxy/injeção resolver a chamada;
- rotação não depende de prompts;
- nenhum segredo entra em Git, trace, issue, PR ou Segundo Cérebro;
- Secret Manager só é removido depois de cutover testado e rollback disponível.

A ativação em produção depende de uma instância/conta Infisical e das identidades necessárias; até lá nenhuma credencial fictícia será criada.
