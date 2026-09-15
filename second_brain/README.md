# Segundo Cérebro — núcleo universal

Este diretório é o núcleo **independente da Holding** do Segundo Cérebro. Ele existe temporariamente dentro deste repositório para permitir migração sem ruptura; deve poder ser extraído para um repositório próprio sem depender de `app/`, do PMO ou de qualquer projeto consumidor.

## Fonte canônica e projeções

- **Obsidian/Markdown:** representação humana, portátil e canônica legível.
- **Graphiti:** projeção relacional/temporal para recuperação por agentes.
- **Banco operacional:** pode indexar estados e filas, mas não torna o conteúdo humano inacessível.
- **Graphiti não promove Claims e não escreve no vault.**

## Pipeline

`Fonte -> Observação -> Evidência -> Claim -> Comparação -> Auditoria -> Validação -> Conhecimento -> Graphiti -> Obsidian`

A promoção é fail-closed. Coletores podem observar e propor; não podem transformar a própria descoberta em fato canônico.

## Estados

`PROPOSTO`, `EM_REVISÃO`, `VALIDADO`, `CANÔNICO`, `SUPERADO`, `REJEITADO`, `CONFLITANTE`, `BAIXA_CONFIANÇA`.

## Organização lógica

O vault preserva a separação equivalente a `00_CORE` até `15_EVALUATIONS`. Conhecimento transversal usa `shared/...`; conhecimento específico usa `project/<slug>/...`. Uma mesma nota não é duplicada para cada consumidor.

## Memória

A memória institucional é o Segundo Cérebro + Graphiti. Letta e Cognee não fazem parte do núcleo inicial. Skills são capacidades operacionais versionadas separadamente do conhecimento que as fundamenta.
