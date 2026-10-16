## ADDED Requirements

### Requirement: Pareamento da cabine
A cabine SHALL se autenticar com um token obtido por pareamento no painel (`POST /cabines/pareamento` → código; `POST /cabines/ativar` → token). O backend MUST guardar só o hash do token e permitir revogação.

#### Scenario: Ativação com código válido
- **WHEN** o app envia um código de pareamento válido e não expirado para `POST /cabines/ativar`
- **THEN** o backend devolve `cabine_id` e `token`, e o app guarda o token no Keychain

#### Scenario: Token revogado
- **WHEN** a cabine usa um token revogado no painel
- **THEN** o backend responde `401` e o app volta ao estado `naoPareado`

### Requirement: Abertura da sessão pelo QR
Ao ler o QR do aparelho avaliado, a cabine SHALL chamar `GET /cabine/{token}` e receber modelo, dimensões e roteiro. O roteiro MUST vir do backend.

#### Scenario: Modelo sem dimensões cadastradas
- **WHEN** o modelo da sessão não tem dimensões em `dimensoes.py`
- **THEN** o backend responde `422` com a mensagem "Modelo <identificador> sem dimensões cadastradas"

#### Scenario: Sessão já avaliada
- **WHEN** a sessão já tem avaliação final e a chamada não usa `?refazer=1`
- **THEN** o backend responde `409`

### Requirement: Tela do aparelho avaliado
O aparelho avaliado SHALL receber eventos por long-poll (`GET /pagina/{token}/eventos`) e, no evento `preto`, mostrar tela preta em tela cheia com brilho 0, restaurando o brilho ao sair.

#### Scenario: Pedido de tela preta
- **WHEN** a cabine chama `POST /cabine/{token}/tela {"acao": "preto"}`
- **THEN** o aparelho avaliado fica preto com brilho 0 em ≤ 2 s

### Requirement: Câmera travada por perfil
Durante a captura, exposição, ISO, foco e balanço de branco MUST ficar travados pelo perfil de calibração, com tempo de exposição múltiplo de 1/120 s, foco por pose, lente 1x física e rotação fixa (`videoRotationAngle = 0`).

#### Scenario: Metadados idênticos
- **WHEN** 10 sessões seguidas são capturadas
- **THEN** ISO, exposição, foco e balanço de branco são idênticos dentro de cada combinação de luz e pose

### Requirement: Controle das luzes pelo ESP32
Para cada luz do passo, a cabine SHALL chamar `POST /luz` no ESP32 e só capturar depois da resposta com o estado pedido. O ESP32 MUST desligar todos os canais após 120 s sem comando.

#### Scenario: ESP32 não responde
- **WHEN** o ESP32 não responde em 1 s por 3 tentativas
- **THEN** a cabine pausa o roteiro e avisa o técnico

### Requirement: Disparo por estabilidade e qualidade local
A cabine SHALL disparar só quando a imagem estiver parada por 500 ms, o aparelho presente e sem mão na cena, e SHALL verificar nitidez, estouro, contorno e tela apagada em cada foto.

#### Scenario: Foto reprovada localmente
- **WHEN** a qualidade local reprova uma foto
- **THEN** a cabine repete o passo (até 3 vezes) e depois pede ajuda ao técnico

### Requirement: Envio idempotente durante a captura
Cada foto SHALL ser enviada em segundo plano, durante a captura, por `POST /cabine/{token}/fotos` com `Idempotency-Key` própria, a partir de uma fila persistida em disco.

#### Scenario: Reenvio da mesma foto
- **WHEN** a mesma `Idempotency-Key` é enviada duas vezes
- **THEN** o backend devolve a mesma `foto_id` com `"duplicada": true` e não cria outra foto

#### Scenario: Wi-Fi cai no meio da captura
- **WHEN** a rede cai durante o roteiro
- **THEN** a captura continua e as fotos sobem quando a rede voltar

### Requirement: Tempo da cabine
O roteiro completo SHALL levar ≤ 60 s por aparelho (mediana de 10 aparelhos, técnico real), com ≥ 95% das fotos aceitas na primeira tentativa.

#### Scenario: Medição de tempo
- **WHEN** o técnico avalia 10 aparelhos seguidos
- **THEN** a mediana do tempo entre leitura do QR e `POST /concluir` é ≤ 60 s
