# Open Source Intake Gate — Holding Digital

## Objetivo

Nenhum código, modelo, container, dataset, pacote ou projeto externo entra na Holding apenas porque é popular ou open source. Este gate é obrigatório antes de promover qualquer componente a runtime, biblioteca, serviço ou base comercial.

## 1. Identificação

Registrar:

- repositório/origem;
- versão/commit/tag pretendido;
- função que resolverá;
- projeto consumidor;
- alternativa existente;
- owner interno;
- estratégia de remoção/substituição.

## 2. Segurança de supply chain

Executar quando aplicável:

- OpenSSF Scorecard;
- SBOM com Syft;
- vulnerability/misconfiguration scan com Trivy;
- Gitleaks;
- Semgrep;
- verificação de assinatura/proveniência quando disponível;
- dependências diretas/transitivas;
- maintainer activity, releases e histórico de incidentes;
- imagens/container base e registries utilizados.

Componentes críticos devem ser fixados por versão/digest e atualizados de forma controlada.

## 3. Licença e direitos

Verificar separadamente:

- licença do código;
- licença dos modelos/weights;
- licença dos datasets;
- termos de API/serviço;
- direitos de redistribuição;
- obrigações de atribuição/source disclosure;
- restrições de uso comercial.

`Repositório público` não significa `uso comercial irrestrito`.

GPL/AGPL/BSL e licenças não padronizadas exigem análise específica antes de integração que possa afetar distribuição, SaaS ou código proprietário.

## 4. Segurança operacional

Antes de produção:

- executar com menor privilégio;
- negar acesso desnecessário a filesystem/rede/segredos;
- credenciais somente por Secret Manager/OpenBao ou mecanismo aprovado;
- egress restrito quando possível;
- timeouts e limites de recursos;
- audit log;
- rate limits;
- isolamento/sandbox para código não confiável;
- proteção contra prompt injection quando o componente processar conteúdo externo para agentes.

## 5. Dados e privacidade

Classificar dados acessados:

- público;
- interno;
- confidencial;
- pessoal/LGPD;
- segredo/credencial;
- regulado.

Minimizar PII e impedir que dados de um tenant/projeto vazem para outro. Nenhum modelo ou ferramenta externa recebe dados privados automaticamente.

## 6. Score de promoção

Resultado permitido:

- `APROVADO_CORE`: pode virar padrão quando houver caso real.
- `APROVADO_COMPONENTE`: uso isolado/substituível.
- `POC_ISOLADA`: somente ambiente controlado sem dados/credenciais sensíveis.
- `REFERENCIA`: estudar algoritmo/arquitetura; não executar em produção.
- `REJEITADO`: risco, licença, abandono, redundância ou benefício insuficiente.

## 7. Gate de IA/agentes

Ferramentas acessíveis por agentes precisam ainda declarar:

- agente autorizado;
- ações permitidas;
- dados permitidos;
- nível A0-A5 máximo;
- ações que exigem aprovação humana;
- idempotência;
- rollback quando aplicável;
- evidência e AuditEvent;
- política OPA/OpenFGA correspondente.

Nenhum LLM pode ampliar seu próprio nível de autonomia, autorização ou escopo de credencial.

## 8. Pipeline recomendado

`source -> Scorecard -> license/ORT -> SBOM/Syft -> Gitleaks -> Semgrep -> Trivy -> tests -> sign/Cosign -> registry -> deploy controlado -> runtime monitoring`

Usar ferramentas equivalentes quando o ambiente gerenciado já fornecer a função, evitando duplicação sem benefício.

## 9. Reavaliação

Componentes aprovados são reavaliados diante de:

- CVE crítica;
- mudança de licença;
- mudança de mantenedor;
- abandono;
- incidente upstream;
- dependência comprometida;
- mudança material do nosso uso;
- alternativa claramente superior.
