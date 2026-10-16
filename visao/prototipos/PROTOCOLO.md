# Protocolo de fotos — fase 0

Guia, seção 8.2. Tempo: ~meio dia. Objetivo: responder P1 a P6 com números antes de
comprar ou imprimir qualquer coisa.

## Material

- [ ] iPhone para fotografar, de preferência Pro (48 MP e ProRAW); se possível, o mesmo modelo que será a câmera da cabine.
- [ ] Apoio fixo: tripé com garra de celular (~R$ 30) ou pilha de livros com o celular na beirada.
- [ ] Lanterna de outro celular.
- [ ] Régua.
- [ ] Folha de marcadores: `visao/prototipos/saida/marcadores.pdf`.
- [ ] Pano ou cartolina **preta fosca**.
- [ ] Tablet ou celular com a tela toda **branca** (teste de contraluz).
- [ ] Espelho pequeno + massa de modelar para incliná-lo a 45°.
- [ ] Pano de microfibra.
- [ ] 3 a 5 aparelhos: 1 quase perfeito, 1 com riscos finos, 1 com riscos visíveis, 1 com marca ou amassado na moldura, 1 trincado se houver. **Pelo menos um preto.**

## Passo a passo

1. **Imprima** `marcadores.pdf` em 100% (sem "ajustar à página").
   _Confira:_ cada quadrado preto mede 30,0 mm e a régua impressa mede 100 mm.
2. **Prenda o iPhone** olhando para baixo, paralelo à mesa, com **25 cm da lente até a mesa**.
   Anote a distância real; ela entra no comando da análise.
   **Não fotografe com o celular na mão:** as fotos de uma face precisam ficar alinhadas pixel a pixel.
3. **App Câmera**, lente 1x, sem flash. ProRAW 48 MP se houver; senão HEIF 48 MP.
   Toque e segure no aparelho para **travar foco e exposição (AE/AF)**.
4. **Limpe** o aparelho com a microfibra. Coloque-o sobre o pano preto, com a folha de marcadores ao lado.
   _Confira:_ aparelho e os 4 marcadores inteiros na imagem, sem encostar na borda.
5. Para cada aparelho, **sem mexer em nada entre as fotos da mesma face**:

   | Face | Foto | Como |
   |---|---|---|
   | Frente (tela para cima, tela apagada) | `amb` | luz da sala |
   | | `ra` | lanterna rente à mesa (1–2 cm de altura), a ~20 cm do aparelho, apontada **ao longo do comprimento** |
   | | `rb` | o mesmo, apontada **ao longo da largura** |
   | | `sil` | aparelho sobre o tablet de tela branca, luz da sala apagada se possível |
   | Traseira | `amb`, `ra`, `rb` | igual à frente |
   | Uma lateral (aparelho em pé, apoiado) | `amb`, `ra` | igual |

   _Confira:_ na `ra` e na `rb`, os riscos brilham sobre fundo escuro.
6. **Teste de foco:** com o foco travado no aparelho deitado, sem tocar na tela de novo:
   `foco_lateral` (aparelho em pé de lado) e `foco_ponta` (em pé na ponta).
7. **Teste de espelho:** aparelho deitado, espelho inclinado a 45° encostado numa lateral,
   foco travado no aparelho: `espelho_amb` e `espelho_ra`.
   Se der, anote a região do espelho na foto em `fotos/rois.csv` (`arquivo,x,y,w,h`, em px).
   **Sombra do espelho:** com o espelho no lugar, **entre a lanterna e o aparelho**, repita a
   `ra` da frente: `espelho_frente_ra`. Na cabine, os espelhos ficam entre as barras de luz e
   o aparelho; esta foto mostra se a luz rasante ainda alcança a tela inteira.
   _Confira:_ compare com `frente_ra` — os mesmos riscos aparecem, sem faixa escura perto do espelho?
8. **Poeira (opcional):** uma foto `ra` da frente **antes** de limpar: `sujo_ra`.
9. **Nomes dos arquivos:** `ap{n}_{face}_{luz}.{ext}`.

   ```
   ap1_frente_amb.dng   ap1_frente_ra.dng   ap1_frente_rb.dng   ap1_frente_sil.dng
   ap1_traseira_amb.dng ap1_traseira_ra.dng ap1_traseira_rb.dng
   ap1_lat_amb.dng      ap1_lat_ra.dng
   ap1_foco_lateral.dng ap1_foco_ponta.dng
   ap1_espelho_amb.dng  ap1_espelho_ra.dng  ap1_espelho_frente_ra.dng  ap1_sujo_ra.dng
   ```

10. **Anotação do técnico:** `anotacao.csv` com uma linha por defeito (ou uma linha por face sem
    defeito). Colunas: `aparelho,modelo,cor,face,tipo,local,tamanho_mm_aprox,visivel_olho_nu,nota_tecnico`.
    Modelo pelo nome comercial (ex.: `iPhone 13`). Exemplo em `anotacao-modelo.csv`.
11. **Copie tudo** (fotos + `anotacao.csv`) para `visao/prototipos/fotos/`.

## Depois

```bash
cd visao
uv run python -I prototipos/conferir_fotos.py   # deve terminar com "OK"
prototipos/rodar_tudo.sh 250                    # troque 250 pela distância real em mm
```

Resultado: `docs/nota-estetica-fase0-relatorio.md`.
