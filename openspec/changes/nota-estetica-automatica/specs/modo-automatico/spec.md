## ADDED Requirements

### Requirement: Gate do modo automático
O backend MUST recusar (`409`) `PUT /estetica/config` com `modo=automatico` para uma loja e família de modelos se o último relatório, só com sessões cegas do holdout, não mostrar: ≥ 200 aparelhos, ≥ 90% de concordância exata, 0 casos a ≥ 2 notas, kappa ponderado ≥ linha de base técnico × técnico e recall ≥ 80% em cada nota.

#### Scenario: Gate não atendido
- **WHEN** o relatório tem 180 aparelhos
- **THEN** o backend responde `409` com as métricas que faltam

### Requirement: Modo sombra
Antes de ligar o automático, a loja SHALL passar 2 semanas com 100% das sessões cegas.

#### Scenario: Sombra incompleta
- **WHEN** a loja tem menos de 2 semanas em modo sombra
- **THEN** o gate não passa

### Requirement: Automação seletiva
Com o automático ligado, a nota só SHALL sair automática se a margem for > 10%, nenhuma regra `a_definir` for acionada, não houver defeito `anomalia` e nenhuma `trinca` tiver confiança intermediária; senão a sessão vai para o técnico.

#### Scenario: Anomalia presente
- **WHEN** a sugestão contém um defeito `anomalia`
- **THEN** a sessão vai para `aguardando_tecnico`

#### Scenario: Nota automática
- **WHEN** todas as condições são atendidas
- **THEN** a avaliação é gravada com `origem = automatica`, `versao_visao` e `versao_criterio`

### Requirement: Monitoramento e retorno automático
Com o automático ligado, uma amostra cega de 5–10% SHALL continuar; se a janela dos últimos 200 aparelhos cair abaixo do gate, o backend MUST voltar a loja para `assistido` e avisar o responsável.

#### Scenario: Queda de desempenho
- **WHEN** a janela móvel fica abaixo do gate
- **THEN** o modo da loja muda para `assistido` e o responsável é avisado
