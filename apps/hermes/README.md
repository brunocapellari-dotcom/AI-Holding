# Hermes

Interface executiva persistente do Owner para a Holding.

Hermes recebe ordens, consulta o estado operacional no Control Plane, consulta conhecimento no Segundo Cérebro, solicita análise/execução aos componentes autorizados e acompanha o trabalho até estado terminal.

Hermes não é um modelo e não armazena verdade de projeto em memória própria. Modelos são escolhidos pelo Model Gateway. Toda ação mutável passa pelo Policy Service; ferramentas externas passam pelo MCP Gateway; custos e traces devem carregar project/task/run IDs.

Responsabilidades: status consolidado, bloqueios, “Precisa de você”, prioridades, custos, riscos e acompanhamento de execução. Fora de escopo: executar código diretamente, guardar segredos, substituir CEO/PMO ou canonicalizar conhecimento.
