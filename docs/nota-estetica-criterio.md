# Critério de nota estética — criterio-v1 (rascunho)

**Status:** rascunho para o estudo de concordância da fase 1 (guia, seção 9). Não aprovado.
**Base:** resumo do PRD §10 que está no guia (seção 16.2). O PRD ainda não está no repositório:
conferir este texto contra o PRD antes da reunião.
**Regras em código:** `backend/app/estetica/criterios/criterio-v1.yaml` · motor: `backend/app/estetica/criterio.py`.
Cada exemplo resolvido (seção 8) é um teste em `backend/tests/estetica/test_criterio.py`.

## 1. Antes de avaliar

1. Retire **capa e película**. Película riscada parece tela riscada.
2. Limpe todas as faces com **microfibra**. Poeira parece microrrisco.
3. Avalie com a **tela apagada**. Pixel morto e mancha de tela são testes funcionais, não estéticos.

## 2. Faces e zonas

Seis faces: `frente`, `traseira`, `lat_esq` (lado dos botões de volume), `lat_dir` (lado do
botão lateral), `topo` e `base` (lado do conector). Toda medida é em mm, na face vista de fora.

```
          frente (tela)                         traseira
  ┌──────────────────────────┐          ┌──────────────────────────┐
  │q   ┌──recorte_tela──┐   q│          │q ┌─ilha_camera─┐        q│
  │    └────────────────┘    │          │  │ (lente)     │         │
  │                          │          │  │ (lente)     │         │
  │          tela            │          │  └─────────────┘         │
  │                          │          │      vidro_traseiro      │
  │                          │          │                          │
  │q                        q│          │q                        q│
  └──────────────────────────┘          └──────────────────────────┘
   faixa de 0,5 mm na borda = moldura    q = quina (quadrado do tamanho do raio do canto)

  laterais, topo e base: moldura, quina, botao (volume, silêncio, lateral), porta (conector)
```

As zonas se juntam em **três grupos**, cada um com sua tabela de regras:

| Grupo | Zonas |
|---|---|
| Tela | `tela`, `recorte_tela` |
| Traseira | `vidro_traseiro`, `ilha_camera`, `lente_camera` |
| Moldura | `moldura`, `quina`, `botao`, `porta` |

A **nota da face** é a pior entre os grupos que aparecem nela. A **nota do aparelho** é a pior face.

## 3. Tipos de defeito e como medir

| Tipo | O que é | Como medir |
|---|---|---|
| `risco` | traço fino no vidro ou na moldura ("marca" na moldura) | comprimento do traço |
| `trinca` | vidro rachado | comprimento (qualquer trinca já é D) |
| `lascado` | pedaço faltando no vidro ou na pintura | maior dimensão |
| `amassado` | deformação na moldura | **diâmetro aparente** na luz rasante (profundidade não se mede com uma câmera de cima) |
| `descascado` | pintura saindo | área |
| `desgaste` | quinas gastas | área |
| `mancha` | marca que não sai com microfibra | área |
| `anomalia` | região estranha apontada pela máquina sem classe | sempre revisada pelo técnico |

_(Fotos de exemplo de cada tipo entram aqui depois da fase 0.)_

### Visibilidade

- **Visível:** você vê a olho nu, a ~30 cm, na luz normal da bancada.
- **Só rasante:** só aparece com a luz rente à superfície (lanterna deitada).

O algoritmo é calibrado contra essa definição humana, não o contrário.

## 4. Regras

Dentro de cada grupo, as regras estão da pior nota para a melhor. **Vale a primeira que casar.**
Sem nenhuma regra, o grupo fica A. Contagens ("mais de 5 riscos") são **por face**.

### Tela

| Nota | Quando |
|---|---|
| D | trinca |
| D | lascado maior que 2 mm |
| C | lascado até 2 mm _(a definir, L1)_ |
| C | mancha ou descascado _(a definir, L7)_ |
| C | qualquer risco **visível** |
| C | mais de 5 riscos |
| C | risco maior que 15 mm |
| B | 3 a 5 riscos só rasante |
| B | risco só rasante entre 5 e 15 mm |
| A | até 2 riscos só rasante de até 5 mm |

### Traseira

| Nota | Quando |
|---|---|
| D | vidro traseiro ou lente trincados |
| D | lascado maior que 2 mm _(a definir, L3)_ |
| C | lascado até 2 mm _(a definir, L3)_ |
| C | mancha ou descascado _(a definir, L7)_ |
| C | risco visível |
| B | riscos leves só rasante _(a definir, L2)_ |
| A | sem marcas |

### Moldura (laterais, topo, base, quinas, botões, porta)

| Nota | Quando |
|---|---|
| D | amassado maior que 3 mm |
| C | amassado até 3 mm |
| C | lascado ou descascado de pintura |
| C | desgaste nas quinas |
| C | marca maior que 3 mm _(a definir, L5)_ |
| B | marca entre 1 e 3 mm |
| B | mais de 2 marcas de até 1 mm |
| A | até 2 marcas de até 1 mm |

### Regras gerais

- Trinca em qualquer vidro (tela, vidro traseiro, lente) → a face fica **D**.
- Risco sobre a lente da câmera → a face fica **C** ou pior.
- Nota do aparelho = pior face.
- O técnico pode dar nota diferente da regra, **com justificativa escrita**.

## 5. O que é "a definir"

Regra marcada _(a definir)_ dá a nota da tabela, mas **nunca vira nota automática**: a
sessão sempre vai para o técnico (decisão D5). A reunião da fase 1 fecha cada lacuna.

| # | Lacuna | Proposta |
|---|---|---|
| L1 | Lascado ≤ 2 mm na tela não tem nota no PRD | C |
| L2 | Traseira A = "sem marcas visíveis": aceita marcas só rasante? Quantas são "riscos leves" (B)? | mesmos limites da tela |
| L3 | Lascado no vidro traseiro não aparece no PRD | igual à tela |
| L4 | Moldura A: "até 2 marcas ≤ 1 mm" — podem ser visíveis? | sim |
| L5 | Marca > 3 mm na moldura sem amassado não tem nota | C |
| L6 | "Moldura torta": como medir | o técnico marca; a máquina só sinaliza borda fora de reta (> 0,3 mm) |
| L7 | Mancha e descascado na tela e na traseira | C |
| L8 | Região anômala sem classe | mesma regra de risco do mesmo tamanho + revisão obrigatória |
| L9 | Botões e porta | grupo moldura |
| L10 | "Mais de 5 riscos" conta por face ou no aparelho | por face |

## 6. Película, capa, sujeira

Não são defeito do aparelho. Se não der para tirar a película, **não avalie**: registre e
devolva para a bancada.

## 7. Defeito que não está nas tabelas

Tipo sem regra no grupo (ex.: desgaste na tela) não muda a nota, mas gera uma **pendência**
e a sessão vai para o técnico. Leve o caso para a próxima revisão do critério.

## 8. Exemplos resolvidos

Mesma numeração dos testes. "Só rasante" = não visível a olho nu.

| # | Situação | Nota da frente | Nota do aparelho | Por quê |
|---|---|---|---|---|
| 1 | Sem defeitos | A | A | — |
| 2 | 2 riscos só rasante de 3 mm na tela | A | A | até 2 riscos de até 5 mm |
| 3 | 3 riscos só rasante, maior 9,8 mm | B | B | 3 a 5 riscos só rasante |
| 4 | 1 risco só rasante de 6 mm | B | B | entre 5 e 15 mm |
| 5 | 1 risco visível de 2 mm na tela | C | C | risco visível |
| 6 | 1 risco só rasante de 16 mm | C | C | maior que 15 mm |
| 7 | 6 riscos só rasante de 1 mm | C | C | mais de 5 riscos |
| 8 | Trinca na tela | D | D | trinca |
| 9 | Amassado de 2 mm numa quina (lateral) | A | C | amassado até 3 mm |
| 10 | Amassado de 4 mm no topo | A | D | amassado maior que 3 mm |
| 11 | 2 marcas de 0,8 mm na lateral | A | A | até 2 marcas de até 1 mm |
| 12 | 1 marca de 2 mm na lateral | A | B | marca entre 1 e 3 mm |
| 13 | Risco só rasante sobre a lente da câmera | A | C | regra geral da lente |
| 14 | Risco de 6 mm na tela + trinca na traseira | B | D | pior face (traseira D) |

## 9. Estudo de concordância (fase 1)

- 20 aparelhos, com pelo menos 4 de cada nota (se faltar D, pelo menos 2).
- Dois técnicos avaliam os mesmos aparelhos, **cada um sozinho**, usando este documento.
  Cada um preenche sua cópia de `docs/estudo-concordancia-v1.csv`, sem ver a do outro.
- Análise: `cd visao && uv run python -I ferramentas/concordancia.py docs/estudo/tecnico1.csv docs/estudo/tecnico2.csv`.
- Meta para aprovar `criterio-v1`: concordância exata ≥ 85% na nota final **e** kappa
  ponderado ≥ 0,80. O kappa obtido vira a linha de base do modo automático (fase 5).
