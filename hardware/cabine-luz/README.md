# cabine-luz — firmware do ESP32

Controla as luzes da cabine pela rede local (guia 7.10). Ligação elétrica:
`../cabine-a/README.md`, seção 4.

## API

Cabeçalho obrigatório em todas as rotas: `X-Chave-Cabine: <chave>`. Sem ele: `401`.

| Rota | Corpo | Resposta |
|---|---|---|
| `GET /estado` | — | `{"canais": {"a": 0, "b": 0, "difusa": 0, "contraluz": 0}, "versao": "1.0.0", "uptime_s": 1234}` |
| `POST /luz` | `{"a": 100, "b": 0}` (0–100; canal omitido = sem mudança) | `200` com o estado **depois** de aplicar |
| `POST /desligar` | — | `200`, todos em 0 |

- Canal desconhecido ou valor fora de 0–100 → `400` e **nada** muda.
- PWM a 20 kHz, 10 bits (sem faixas na foto).
- Sem nenhum comando por 120 s → apaga tudo sozinho.
- LED da placa pisca até conectar ao Wi-Fi; aceso = conectado. Se o Wi-Fi cair, apaga as luzes e reconecta.
- mDNS: `<NOME_MDNS>.local`, serviço `_http._tcp`, TXT `tipo=cabine-luz`.

## Gravar

1. Instale o PlatformIO (ou use `uvx --from platformio pio …`, sem instalar).
2. Copie os segredos e preencha:
   ```bash
   cp include/segredos.exemplo.h include/segredos.h
   ```
   `CHAVE_CABINE`: gere com `openssl rand -hex 16` e use a mesma no app (modo Cabine → Luzes).
   O `segredos.h` fica fora do Git.
3. Ligue o ESP32 no USB e grave:
   ```bash
   pio run -t upload
   pio device monitor        # mostra o IP e o nome mDNS
   ```
   _Confira:_ o monitor mostra `Wi-Fi conectado: 192.168.x.y` e `mDNS: morecheck-cabine-1.local`.

## Testar

```bash
CHAVE=<chave>
curl -s http://morecheck-cabine-1.local/estado -H "X-Chave-Cabine: $CHAVE"
curl -s -X POST http://morecheck-cabine-1.local/luz \
  -H "X-Chave-Cabine: $CHAVE" -H 'Content-Type: application/json' -d '{"a":100}'
curl -s -X POST http://morecheck-cabine-1.local/desligar -H "X-Chave-Cabine: $CHAVE"
```

Esperado: a barra `a` acende no segundo comando e apaga no terceiro; cada resposta traz o estado.

## Problemas comuns

| Sintoma | Causa provável |
|---|---|
| `*.local` não resolve | rede com isolamento de clientes; use o IP (o app aceita IP fixo) |
| Barra não acende, LED da placa ok | MOSFET que não conduz com 3,3 V, ou GND não comum |
| Barra acesa fraca | MOSFET de nível não lógico (aquecendo); trocar por IRLB8721/AO3400 |
| Faixas horizontais na foto | exposição da câmera não múltipla de 1/120 s (rede de 60 Hz); ver guia R17 |
