# Graphiti no Segundo Cérebro

Graphiti representa entidades, relações, eventos, episódios, validade temporal, proveniência e contexto histórico para agentes. Ele não substitui Markdown e não recebe direito de escrita no vault.

A projeção usa `namespace -> group_id`, nome de episódio determinístico e hash do conteúdo para idempotência. O payload só é gerado a partir de registros permitidos pela política de classificação. `RESTRICTED` e `CONFIDENTIAL` são bloqueados no grafo compartilhado.

Consultas futuras devem aceitar `valid_at` e `known_at`. Recuperação atual sem data explícita equivale a `now/now`.

O grafo deve ser reconstruível a partir dos registros aprovados; qualquer divergência é tratada como defeito da projeção, não como motivo para alterar o Markdown canônico.
