## ADDED Requirements

### Requirement: Sugestão a partir da fusão
Com o resultado da fusão, o backend SHALL aplicar o critério, gravar `sugestao_estetica` e as propostas em `defeito_estetico` (estado `proposto`, imutáveis) e emitir `sugestao_pronta`.

#### Scenario: Sugestão gerada
- **WHEN** o worker envia o resultado da `fusao`
- **THEN** a sessão passa para `aguardando_tecnico` e o evento `sugestao_pronta` é emitido

### Requirement: Amostra cega
Ao criar a sessão, o backend SHALL sortear `cega` pelo `percentual_cego` da loja. Em sessão cega sem avaliação final, a API MUST esconder sugestão e defeitos da máquina, inclusive para a cabine.

#### Scenario: Sessão cega na cabine
- **WHEN** a cabine consulta `GET /cabine/{token}/sugestao` de uma sessão cega
- **THEN** recebe `{"status": "pronta", "mostrar": false}`

#### Scenario: Depois de salvar
- **WHEN** o técnico salva a avaliação de uma sessão cega
- **THEN** o painel passa a mostrar a comparação com a sugestão

### Requirement: Confirmação ou correção pelo técnico
O técnico SHALL confirmar, rejeitar, editar ou desenhar defeitos e dar a nota. O backend MUST recalcular `nota_regra`, exigir justificativa se `nota_final` ≠ `nota_regra` e definir `origem` (`sugerida` se nada mudou, senão `tecnico`).

#### Scenario: Nota diferente da regra sem justificativa
- **WHEN** o técnico envia `nota_final` diferente de `nota_regra` sem `justificativa`
- **THEN** o backend responde `422`

#### Scenario: Correção posterior
- **WHEN** uma avaliação é corrigida
- **THEN** uma nova linha é inserida com `substitui_id` e a anterior não é alterada

### Requirement: Tela de avaliação rápida
O painel SHALL oferecer visualizador com zoom 1:1, camadas alternáveis e atalhos de teclado, permitindo avaliar uma sessão em < 30 s quando a sugestão estiver certa.

#### Scenario: Recalcular ao editar
- **WHEN** o técnico marca ou desmarca um defeito
- **THEN** o painel mostra a nova "nota pela regra" via `POST /estetica/criterio/avaliar`

### Requirement: Relatório de concordância
O painel SHALL mostrar concordância exata, ±1, casos a ≥ 2 notas, kappa ponderado com IC 95%, recall por nota e matriz 4×4, considerando por padrão só sessões cegas.

#### Scenario: Incluir sessões não cegas
- **WHEN** o usuário liga "incluir sessões não cegas"
- **THEN** o relatório mostra um aviso de possível viés de automação
