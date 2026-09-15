# Coding Agents — OpenHands

Camada operacional para tarefas de engenharia. OpenHands recebe trabalho já autorizado pelo PMO e executa em workspace isolado; Claude Code, Codex ou outro worker aprovado é selecionado conforme a tarefa.

Fluxo obrigatório:

```text
Control Plane/PMO
→ work order imutável
→ policy check
→ workspace/sandbox isolado
→ branch ou worktree exclusivo
→ worker de código
→ testes e scans
→ revisão
→ PR
→ CI
→ auditoria
→ merge conforme política
```

O serviço não recebe permissão geral sobre organização GitHub, produção ou segredos. Cada work order contém repositório, base SHA, paths permitidos, critérios de aceitação, budget, ferramentas autorizadas e nível de risco. Merge automático só poderá ocorrer quando política determinística permitir; dinheiro, credenciais, mudanças irreversíveis e produção crítica continuam com gate humano quando aplicável.
