# Migração V11.1 -> V12

## Problemas confirmados no V11.x

1. Movimentação e diplomacia alteram variáveis globais diretamente.
2. Regras probabilísticas usam `Math.random()`, impedindo replay determinístico.
3. Direitos de base conjunta são flags globais e regras de capacidade ficam acopladas ao fluxo de interface.
4. Game state, lógica e UI vivem no mesmo HTML monolítico.

## Fase 1 — Instalação sem quebrar a interface

Adicionar ao HTML, depois do script legado:

```html
<script src="src/worldwar-modern-core.js"></script>
<script src="src/legacy-v11-adapter.js"></script>
<script>
  WWMLegacyAdapter.installCompatibilityHooks();
</script>
```

O adapter lê o dataset `DATA.countries` e os `poles` existentes e cria um GameState canônico paralelo.

## Fase 2 — Substituir ações diretas

### Produção

```js
wwmOrder(WWM.ORDER_TYPES.SET_PRODUCTION_PLAN, { plan: { infantry: 20, fighter: 2, destroyer: 1 } });
```

### Diplomacia

```js
wwmOrder(WWM.ORDER_TYPES.DIPLOMATIC_ACTION, {
  to: 'ARG',
  action: 'joint_base',
  terms: { baseId: 'ARG:pole:0' }
});
```

### Patrulha

```js
wwmOrder(WWM.ORDER_TYPES.START_PATROL, {
  kind: 'aewc',
  originBaseId: 'BRA:pole:0',
  area: { mode: 'national_border' },
  assets: { fighter: 2, drone: 1 },
  cycleTurns: 1
});
```

### Operações especiais

```js
wwmOrder(WWM.ORDER_TYPES.SPECIAL_OPERATION, {
  targetCountry: 'ARG',
  targetSystem: 'radar',
  capability: 4,
  intelQuality: 0.7,
  durationTurns: 2
});
```

## Fase 3 — Tornar o novo estado a única fonte de verdade

Depois que cada painel estiver lendo de `wwmGateway.snapshotFor(player)`, remover gradualmente as mutações globais antigas.

## Fase 4 — Separação cliente/servidor

A UI mantém exatamente o mesmo contrato de Orders. Em multiplayer, `AuthoritativeGateway` migra do navegador para servidor e o cliente deixa de possuir World Truth.
