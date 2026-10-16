## ADDED Requirements

### Requirement: Fila de tarefas puxada pelo worker
O backend SHALL manter tarefas em `tarefa_visao` e o worker SHALL reservá-las por HTTPS (`POST /visao/tarefas/reservar`) com `SKIP LOCKED`, prazo de 120 s e até 3 tentativas.

#### Scenario: Ordem de liberação
- **WHEN** chega a foto `rasante_a` de um passo cuja foto `ambiente` ainda não chegou
- **THEN** a tarefa da rasante fica bloqueada até a `ambiente` chegar

#### Scenario: Fusão só no fim
- **WHEN** a cabine chama `POST /concluir`
- **THEN** a tarefa `fusao` só é liberada depois que todas as tarefas `foto` da sessão terminarem

#### Scenario: Prazo de reserva vencido
- **WHEN** um worker não renova nem conclui a tarefa em 120 s
- **THEN** a tarefa volta para `pendente`

### Requirement: Qualidade no servidor
O worker SHALL reprovar fotos com motivo fixo (`tremida`, `estourada`, `contorno não encontrado`, `orientação errada`, `aparelho fora do quadro`, `tela acesa`) devolvendo `qualidade.ok = false`, sem tratar isso como falha da tarefa.

#### Scenario: Contorno não encontrado
- **WHEN** o contorno do aparelho não é encontrado
- **THEN** o resultado vem com `qualidade.ok = false` e o backend emite `foto_reprovada` para a cabine

### Requirement: Retificação pelo próprio aparelho
O worker SHALL achar os 4 cantos por ajuste de retas às bordas e retificar cada face para o referencial em mm da seção 7.2 do guia, a ≥ 20 px/mm, ignorando a orientação EXIF.

#### Scenario: Geometria sintética
- **WHEN** um retângulo de cantos arredondados é deformado por homografia aleatória
- **THEN** o erro de canto é < 0,2 mm e o erro de escala < 0,5%

### Requirement: Detecção e medição de riscos
A camada (a) SHALL detectar riscos na luz rasante (subtração da ambiente, top-hat, limiar por MAD, esqueleto) na resolução nativa e medir o comprimento em mm.

#### Scenario: Riscos sintéticos
- **WHEN** riscos de comprimento conhecido são desenhados numa imagem sintética
- **THEN** o erro de comprimento é ≤ 5% ou ≤ 0,5 mm

#### Scenario: Poeira
- **WHEN** a imagem tem poeira sintética em pontos
- **THEN** ≥ 95% da poeira é rejeitada pelo filtro de alongamento

### Requirement: Fusão por face
A tarefa `fusao` SHALL juntar as detecções da mesma face em todas as fotos e devolver a lista final de defeitos com tipo, zona, visibilidade, medidas e fotos.

#### Scenario: Mesmo risco em duas luzes
- **WHEN** um risco aparece em `rasante_a` e `rasante_b` com distância de Hausdorff ≤ 1,0 mm
- **THEN** a fusão devolve um único defeito com as duas fotos

### Requirement: Reprodutibilidade e tempo
Mesma foto e mesmo modelo MUST gerar a mesma saída, e a sugestão SHALL ficar pronta em ≤ 10 s (p95) após a última foto.

#### Scenario: Regressão com as fotos da fase 0
- **WHEN** o pipeline roda duas vezes sobre as fotos da fase 0
- **THEN** os resultados são idênticos aos guardados

### Requirement: Licenças de modelos e bases
O pipeline MUST usar só modelos e bases com licença comercial permitida (RF-DETR N/S/M/L e Seg; bases CC BY), registrados em `visao/DATASETS.md` e `visao/MODELOS.md`.

#### Scenario: Novo modelo treinado
- **WHEN** um modelo é treinado
- **THEN** `MODELOS.md` registra versão, hash SHA-256, dados, métricas no holdout e data
