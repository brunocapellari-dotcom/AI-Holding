# Integração — Segundo Cérebro

O Obsidian/Segundo Cérebro é externo à Holding e transversal a todos os projetos.

Contrato lógico:

```text
Segundo Cérebro → contexto validado → Holding
Holding → resultado/evidência/candidato → inbox de validação → Segundo Cérebro
```

A Holding pode manter IDs, checksums, origem, status de transferência, validade operacional e evidência necessária para rastrear a troca. Não mantém a versão canônica do conhecimento.

Durante a migração, `knowledge_claims`/`knowledge_outcomes` permanecem como staging legado auditável. O valor histórico `canonical` é somente leitura; novas promoções foram bloqueadas. Exportações por filesystem usam por padrão `00 - Segundo Cerebro/00 - Inbox/Holding`, nunca uma área canônica.

A integração definitiva deverá oferecer leitura contextual e submissão de candidatos por contrato autenticado, preservando provenance e namespace. A aceitação canônica acontece no pipeline do Segundo Cérebro, não no Control Plane.
