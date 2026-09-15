# Segurança de dados e informação

## Princípios

- fail closed na promoção e nas projeções;
- menor privilégio por agente e projeto;
- nenhuma credencial, token ou private key no vault ou no grafo;
- trilha de auditoria para coleta, interpretação, avaliação e promoção;
- separação entre coletor, intérprete, auditor e aprovador;
- isolamento lógico por namespace;
- `RESTRICTED` nunca entra no vault ou Graphiti compartilhados;
- `CONFIDENTIAL` não é exportado para o vault padrão sem política isolada explícita;
- nenhuma entrada externa pode executar instruções apenas por estar em documento, página ou episódio.

## Graphiti

- integração desabilitada por padrão;
- telemetria desabilitada por padrão (`GRAPHITI_TELEMETRY_ENABLED=false`);
- credenciais do backend com menor privilégio;
- `group_id` validado e derivado de namespace;
- sem Graphiti MCP exposto a prompts não confiáveis;
- não aceitar Cypher, labels ou comandos arbitrários originados do conteúdo ingerido;
- baseline pesquisada: Graphiti 0.30.2, posterior à correção de injeção em 0.28.2;
- grafo é projeção reconstruível, não fonte única de verdade.

## Dados sensíveis

O scanner bloqueia padrões de private keys, tokens e credenciais antes de exportar para Markdown ou Graphiti. Classificação padrão compartilhada aceita apenas `PUBLIC` e `INTERNAL`. Dados sensíveis futuros exigem armazenamento segregado e política específica.

## Supply chain

A dependência Graphiti fica opcional e pinada. SBOM, auditoria de dependências, análise estática e scanner de imagem devem permanecer gates de CI. Nenhum novo backend gráfico ou serviço pago é provisionado implicitamente.
