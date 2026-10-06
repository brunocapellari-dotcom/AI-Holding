# Migração sem ruptura do Knowledge Core da Holding

## Situação encontrada

O Knowledge Core atual está embutido em `AI-Holding`. Ele já preserva namespace, evidência, confiança, validade e supersessão, mas ainda usa o banco da Holding como núcleo e não implementa Graphiti nem bitemporalidade completa.

## Compatibilidade

Mapeamento legado:

- `raw` -> `PROPOSTO`
- `candidate` -> `EM_REVISÃO`
- `validated` -> `VALIDADO`
- `canonical` -> `CANÔNICO`
- `superseded` -> `SUPERADO`

Nenhuma linha antiga será apagada na migração. `compat/holding.py` recebe estruturas genéricas; o Segundo Cérebro não importa `app` e não pressupõe que a Holding exista.

## Fases

1. Contratos portáveis, políticas, temporalidade, renderer/linter e projeção Graphiti.
2. Recuperar o deploy atual da Holding e estabilizar migrations pendentes.
3. Criar migration persistente do Segundo Cérebro em PR separado, sem colidir com migrations de segurança em andamento.
4. Implementar dual-read/dual-write governado por outbox idempotente durante a transição.
5. Reconciliar contagens, hashes, proveniência, supersessões e consultas históricas.
6. Trocar consumidores para uma Knowledge API universal.
7. Extrair `second_brain/` para repositório independente; a Holding mantém apenas adapter/cliente.
8. Remover legado somente após backup, reconciliação e janela de rollback.

## Drive e vault legado

O `AGROLOG MT/Obsidian` permanece intacto e passa a ser fonte/namespace `project/agrolog`. Ele não é renomeado nem movido automaticamente. O novo `SEGUNDO_CEREBRO` criado no nível raiz do Drive é o espaço institucional independente.

## Infraestrutura deliberadamente não criada

Não se provisiona banco Graphiti pago, IAM amplo ou memória paralela nesta etapa. O backend gráfico persistente será ativado em mudança separada, depois de escolha de backend, custo e controles de acesso.
