# Segurança

Modelo obrigatório:

```text
intenção da IA
→ autorização determinística
→ identidade/credencial mínima
→ gateway de ferramenta
→ sandbox quando necessário
→ execução
→ evidência/auditoria
```

## Ferramentas

Docker MCP Gateway é a fronteira padrão para MCPs: allowlist de servidores/ferramentas, restrição de rede, profiles por agente/projeto e registro de tool calls. Um prompt nunca habilita ferramenta.

## Execução

- Docker: isolamento normal para workloads conhecidos.
- E2B/microVM: código desconhecido, gerado por agentes ou com risco superior.
- Sem mount do host, Docker socket ou rede ampla por padrão.
- Workspace temporário, branch/worktree exclusivo e cleanup verificável.

## Credenciais

Infisical fornece machine identities e injeção/proxy de segredos. Secret Manager é ponte de migração, não arquitetura final.

## Autorização

A0–A6 não equivale a permissão. O Policy Service pode reduzir autoridade; aumento de permissão exige política explícita. OpenFGA só entra se houver necessidade comprovada de relações mais granulares.
