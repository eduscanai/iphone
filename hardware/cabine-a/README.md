# Cabine A — montagem física

Guia, seção 10.1. Valores de altura e distância vêm das decisões D1 a D4
(`openspec/changes/nota-estetica-automatica/design.md`). Enquanto a fase 0 não fecha,
valem os padrões: duas barras rasantes, câmera a ≥ 20 px/mm, espelhos a 45°, sem contraluz.

> **Antes de comprar os espelhos:** veja "Risco: sombra dos espelhos" no fim deste arquivo.

## 1. Lista de compras

| Item | Qtde | Observação |
|---|---|---|
| EVA preto fosco 40 × 40 cm | 1 | anteparo em volta da câmera; furo de ~3 cm para a lente |
| Barra de LED 12 V, 5000 K, ~30 cm, **com perfil e difusor** | 2 | canais `a` e `b`; CRI alto se possível |
| ESP32 DevKit (ESP32-WROOM-32) | 1 | |
| MOSFET canal N de nível lógico (3,3 V no gate) | 4 | IRLB8721 ou AO3400; ou módulo MOSFET de 4 canais **próprio para 3,3 V** |
| Resistor 220 Ω | 4 | gate |
| Resistor 10 kΩ | 4 | gate → GND (mantém apagado no boot) |
| Fonte 12 V 2 A | 1 | barras de LED |
| Fonte USB 5 V (ou carregador) + cabo | 1 | ESP32 |
| Braço articulado com garra para celular | 1 | firme; trava sem folga |
| Feltro adesivo fino | 1 | áreas de apoio do berço |
| Espelho de **primeira superfície**, 12 × 170 mm e 12 × 80 mm | 2 + 2 | só se D3 = espelhos; espelho comum dá imagem dupla |
| Painel de LED A4 branco | 1 | só se D4 = contraluz (canal `contraluz`) |
| Painel difuso para luz de cima | 1 | opcional (canal `difusa`) |
| Impressão 3D do berço e suportes | — | `berco.stl`, `suporte_espelho.stl` (4×), `suporte_led.stl` (4×) |

## 2. Impressão

```bash
openscad -D 'peca="berco"' -o berco.stl berco.scad
openscad -D 'peca="suporte_espelho"' -o suporte_espelho.stl berco.scad
openscad -D 'peca="suporte_led"' -o suporte_led.stl berco.scad
openscad -D 'peca="montagem"' berco.scad     # prévia (abre a interface)
```

Os STL desta pasta já estão exportados com os valores padrão. PLA ou PETG **preto fosco**,
0,2 mm, 3 perímetros. A placa tem 260 × 250 mm: se a mesa da impressora for menor, divida
em duas metades (`placa_largura`) e cole.

Variáveis principais (topo do `berco.scad`): `origem_x/origem_y` (quina onde o aparelho
encosta), `batente_altura` (≤ 3 mm), `espelho_largura`, `trilho_curso` e `led_altura_eixo`.

## 3. Montagem

1. **Berço:** cole o feltro nos rebaixos. Recorte os 4 marcadores de `marcadores-aruco.pdf`
   (impresso em 100%) na linha tracejada e cole nos bolsões dos cantos, ids 0 a 3.
   _Confira:_ cada quadrado preto mede 30,0 mm.
2. **Câmera:** prenda o iPhone da cabine no braço, olhando para baixo, lente 1x sobre o
   centro do berço. Altura da lente até o feltro: **definida em D2** (padrão: a que dá
   ≥ 20 px/mm; com 48 MP, ~250 mm). Nunca abaixo do foco mínimo da lente (~150–200 mm).
   _Confira o paralelismo:_ app Medida (ou de nível) com o iPhone deitado no berço e depois
   no braço: diferença ≤ 0,5°. Use o assistente de calibração do app para o ajuste fino
   (os 4 ArUco devem ter o mesmo tamanho na imagem, ±0,5%).
3. **Anteparo:** EVA preto em volta do braço, acima da câmera, furo na lente. Ele corta
   reflexos do teto e de pessoas no vidro do aparelho.
4. **Barras rasantes:** nos suportes `suporte_led`, com o **centro a 1–2 cm da mesa**
   (`led_altura_eixo`). Barra `a` paralela ao lado comprido do berço; barra `b` paralela ao
   lado curto. Distância até o aparelho: a medida na fase 0 (padrão ~20 cm).
   _Confira:_ com a barra acesa e a sala escura, um risco conhecido brilha na tela inteira.
5. **Espelhos (D3 = espelhos):** espelho nos suportes, suportes nos trilhos, a ~6 mm do
   aparelho. Ajuste no trilho até a lateral refletida aparecer inteira na imagem.
6. **Eletrônica:** ligação abaixo; firmware em `../cabine-luz/`.

## 4. Ligação elétrica

Um canal (repetir para `a`, `b`, `difusa`, `contraluz`):

```
 +12 V ────────────────────────────┐
                                   │ (+) barra de LED (−)
                                   └──────────────┐
                                                  │ dreno (D)
 GPIO ── 220 Ω ──┬──────────────── gate (G)   MOSFET canal N (IRLB8721 / AO3400)
                 │                                │ fonte (S)
               10 kΩ                              │
                 │                                │
 GND ESP32 ──────┴────────────────────────────────┴──── GND fonte 12 V   (GND COMUM)
```

| Canal | GPIO padrão (`main.cpp`) |
|---|---|
| `a` | 25 |
| `b` | 26 |
| `difusa` | 27 |
| `contraluz` | 14 |

- O GND do ESP32 e o GND da fonte de 12 V **precisam** estar ligados.
- O ESP32 é alimentado pelo USB, não pelos 12 V.
- Com módulo MOSFET pronto, confira que ele aciona com 3,3 V (muitos módulos de 5 V não acionam).

## 5. Conferências finais

| # | Teste | Resultado esperado |
|---|---|---|
| 1 | Ligar tudo | LED da placa pisca até conectar ao Wi-Fi; depois fica aceso |
| 2 | `curl http://morecheck-cabine-1.local/estado -H 'X-Chave-Cabine: …'` | JSON com os 4 canais em 0 |
| 3 | `POST /luz {"a":100}` | barra `a` acende; resposta mostra `"a": 100` |
| 4 | Foto com a barra acesa, câmera do iPhone em 1/60 s | sem faixas horizontais (PWM a 20 kHz) |
| 5 | Esperar 2 minutos sem comando | todas as luzes apagam sozinhas |
| 6 | Calibração no app (modo Cabine) | 4 ArUco detectados; px/mm ≥ alvo de D2 |
| 7 | Aparelho de teste com risco conhecido | risco visível nas fotos `rasante_a` e/ou `rasante_b` |
| 8 | Laterais nos espelhos | as 4 laterais aparecem inteiras e nítidas |

## Risco: sombra dos espelhos

Com espelhos nos 4 lados, cada barra rasante fica **atrás de um espelho**. O raio rasante
passa a ~8 mm de altura sobre a cunha; uma cunha mais alta faz sombra na tela. Por isso o
espelho padrão tem 12 mm de largura (cunha de ~9,5 mm). A foto `espelho_frente_ra` da fase 0
mede isso. Se houver sombra, as saídas são:

1. espelhos rebatíveis, no lugar só durante a foto `ambiente`;
2. barras mais altas (luz menos rasante: conferir a detecção de riscos);
3. D3 = suportes em pé (laterais, topo e base em passos próprios, com foco por pose).
