"""Relatório da fase 0 (guia 8.3 passo 11) → docs/nota-estetica-fase0-relatorio.md.

Lê as tabelas de saida/ geradas pelos outros protótipos, copia as imagens principais
(reduzidas) para docs/img/fase0/ e propõe D1 a D4. As propostas são automáticas:
o Claude Code e o responsável revisam o texto antes da decisão.

    uv run python -I prototipos/relatorio.py [--altura-mm 250]
"""

import argparse
import shutil
import statistics
from collections import defaultdict
from datetime import date
from pathlib import Path

import cv2

from visao import config, fase0

DOCS = fase0.DIR_DOCS
DIR_IMG = DOCS / "img" / "fase0"
APARELHOS_MES = 4000
S = fase0.DIR_SAIDA


def f(x, casas=1):
    """Número em pt-BR."""
    if x in ("", None):
        return "—"
    return f"{float(x):.{casas}f}".replace(".", ",")


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def mediana(valores):
    v = [x for x in (num(y) for y in valores) if x is not None]
    return statistics.median(v) if v else None


def tabela(cabecalho, linhas):
    out = ["| " + " | ".join(cabecalho) + " |", "|" + "---|" * len(cabecalho)]
    out += ["| " + " | ".join(str(c) for c in l) + " |" for l in linhas]
    return "\n".join(out)


def copiar_imagem(origem: Path, lado=1600) -> str | None:
    if not origem.exists():
        return None
    destino = DIR_IMG / origem.name
    img = cv2.imread(str(origem))
    if img is None:
        return None
    h, w = img.shape[:2]
    if max(h, w) > lado:
        k = lado / max(h, w)
        img = cv2.resize(img, (round(w * k), round(h * k)), interpolation=cv2.INTER_AREA)
    DIR_IMG.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(destino), img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return f"img/fase0/{origem.name}"


def imagens(padrao: str, limite=4, legenda="") -> str:
    out = []
    for p in sorted(S.glob(padrao))[:limite]:
        rel = copiar_imagem(p)
        if rel:
            out.append(f"![{legenda or p.stem}]({rel})")
    return "\n\n".join(out) if out else "_(sem imagens)_"


# ---------------------------------------------------------------- seções


def secao_fotos(cat):
    por_formato = defaultdict(list)
    for p in fase0.DIR_FOTOS.glob("*"):
        if p.suffix.lower() in fase0.FORMATOS:
            por_formato[fase0.FORMATOS[p.suffix.lower()]].append(p.stat().st_size / 1e6)
    linhas = [[fmt, len(v), f(statistics.mean(v)), f(max(v))] for fmt, v in sorted(por_formato.items())]
    return por_formato, tabela(["Formato", "Fotos", "MB médio", "MB máximo"], linhas)


def p1():
    linhas = [l for l in fase0.ler_csv(S / "iluminacao.csv") if l["inclui_borda"] == "False"]
    if not linhas:
        return "_Sem dados (faltam fotos `ra` e `rb`)._", None
    tot = {k: sum(num(l[k]) or 0 for l in linhas) for k in ("mm_so_ra", "mm_so_rb", "mm_ambos")}
    total = sum(tot.values())
    perde_so_a = 100 * tot["mm_so_rb"] / total if total else 0
    perde_so_b = 100 * tot["mm_so_ra"] / total if total else 0
    tab = tabela(
        ["Aparelho", "Face", "Só ra (n / mm)", "Só rb (n / mm)", "Nos dois (n / mm)", "Ângulo médio só ra", "Ângulo médio só rb"],
        [[f"ap{l['aparelho']}", l["face"], f"{l['n_so_ra']} / {f(l['mm_so_ra'])}", f"{l['n_so_rb']} / {f(l['mm_so_rb'])}",
          f"{l['n_ambos']} / {f(l['mm_ambos'])}", f(l["angulo_medio_so_ra"]), f(l["angulo_medio_so_rb"])] for l in linhas],
    )
    texto = (
        f"{tab}\n\nÂngulo = entre o risco e o eixo longo do aparelho (0° paralelo, 90° perpendicular). "
        f"`ra` ilumina ao longo do comprimento; pela hipótese de R1, os riscos que só aparecem em `rb` "
        f"tendem a ser paralelos ao eixo longo (ângulo baixo).\n\n"
        f"**Total:** {f(total)} mm de risco (longe da borda). Com só `ra` se perderiam **{f(perde_so_a)}%** do "
        f"comprimento; com só `rb`, **{f(perde_so_b)}%**."
    )
    return texto, max(perde_so_a, perde_so_b)


def p2(altura_mm):
    esc = [l for l in fase0.ler_csv(S / "escala.csv")
           if l["variante"] == "sem_contraluz" and l["foto"] in ("frente_amb", "traseira_amb") and l.get("px_mm_aparelho")]
    px = mediana(l["px_mm_aparelho"] for l in esc)
    h_est = mediana(l.get("altura_estimada_mm") for l in esc)
    h20 = mediana(l.get("altura_para_20pxmm") for l in esc)
    campo = mediana(l.get("campo_util_mm") for l in esc)
    res = fase0.ler_csv(S / "resolucao.csv")
    agg = defaultdict(lambda: [0, 0])
    for l in res:
        agg[(int(l["px_mm_alvo"]), l["faixa"])][0] += int(l["n_nativo"])
        agg[(int(l["px_mm_alvo"]), l["faixa"])][1] += int(l["n_achados"])
    faixas = [nome for _, _, nome in [(0, 3, "< 3 mm"), (3, 5, "3–5 mm"), (5, 15, "5–15 mm"), (15, 0, "> 15 mm")]]
    alvos = sorted({a for a, _ in agg})
    tab_res = tabela(
        ["px/mm"] + faixas,
        [[a] + [f"{agg[(a, fx)][1]}/{agg[(a, fx)][0]} ({f(100 * agg[(a, fx)][1] / agg[(a, fx)][0], 0)}%)" if agg[(a, fx)][0] else "—"
                for fx in faixas] for a in alvos],
    ) if alvos else "_Sem dados de resolução._"

    alvo_ok = None
    for a in alvos:
        ok = all(agg[(a, fx)][0] == 0 or agg[(a, fx)][1] / agg[(a, fx)][0] >= 0.95 for fx in faixas[1:])
        if ok:
            alvo_ok = a
            break
    texto = (
        f"- px/mm medido no aparelho (mediana, frente e traseira): **{f(px)}** com a câmera a {f(altura_mm, 0)} mm "
        f"(informada); altura estimada pelas duas escalas: **{f(h_est, 0)} mm**.\n"
        f"- Campo de visão útil na largura da imagem: **{f(campo, 0)} mm**.\n"
        f"- Altura que daria 20 px/mm: **{f(h20, 0)} mm** (proporcional ao inverso da distância).\n\n"
        f"Riscos achados na imagem reduzida ÷ riscos na resolução nativa ({f(px)} px/mm), por comprimento:\n\n{tab_res}"
    )
    return texto, px, h20, alvo_ok


def p3():
    linhas = fase0.ler_csv(S / "foco.csv")
    if not linhas:
        return "_Sem dados de foco._", {}
    por_foto = defaultdict(list)
    for l in linhas:
        if num(l.get("largura_vs_deitado")):
            por_foto[l["foto"]].append(num(l["largura_vs_deitado"]))
    tab = tabela(
        ["Aparelho", "Foto", "Região", "Borda 10–90% (px)", "Borda (mm)", "× deitado", "Var. Laplaciano"],
        [[f"ap{l['aparelho']}", l["foto"], l["regiao"], f(l["largura_borda_px"], 2), f(l["largura_borda_mm"], 3),
          f(l["largura_vs_deitado"], 2), f(l["laplaciano_var"], 0)] for l in linhas],
    )
    medianas = {k: statistics.median(v) for k, v in por_foto.items()}
    return tab + "\n\nBorda mais larga que a do aparelho deitado = mais borrada (1,0 = igual).", medianas


def p4():
    linhas = [l for l in fase0.ler_csv(S / "escala.csv") if l["foto"] in ("frente_amb", "traseira_amb", "lat_amb")]
    res = {}
    for var in ("sem_contraluz", "com_contraluz"):
        g = [l for l in linhas if l["variante"] == var]
        if g:
            ok = [l for l in g if l["contorno_ok"] == "True"]
            res[var] = {
                "n": len(g), "falhas": len(g) - len(ok),
                "residuo": mediana(l.get("residuo_bordas_mm") for l in ok),
                "dif": mediana(abs(num(l["dif_corrigida_pct"])) for l in ok if num(l.get("dif_corrigida_pct")) is not None),
            }
    tab = tabela(
        ["Variante", "Fotos", "Falhas de contorno", "Resíduo das bordas (mm, mediana)", "|Dif. × ArUco corrigida| (%)"],
        [[k, v["n"], v["falhas"], f(v["residuo"], 3), f(v["dif"], 2)] for k, v in res.items()],
    )
    return tab, res


def p5():
    cz = fase0.ler_csv(S / "cruzamento.csv")
    po = fase0.ler_csv(S / "poeira.csv")
    tab_cz = tabela(
        ["Aparelho", "Face", "Nota técnico", "Técnico: riscos (visíveis)", "Técnico: maior mm", "Algoritmo: riscos (≥ 3 mm)",
         "Algoritmo: maior mm", "Concorda (tem/não tem)", "Outros defeitos anotados"],
        [[f"ap{l['aparelho']}", l["face"], l["nota_tecnico"], f"{l['tec_n_riscos']} ({l['tec_n_visiveis']})", f(l["tec_maior_mm"]),
          f"{l.get('alg_n_riscos', '—')} ({l.get('alg_n_ge_3mm', '—')})", f(l.get("alg_maior_mm")),
          {"True": "sim", "False": "**não**"}.get(l.get("concorda_tem_risco", ""), "—"), l["tec_outros_defeitos"]] for l in cz],
    ) if cz else "_Sem cruzamento (falta anotacao.csv ou fotos)._"
    tab_po = tabela(
        ["Aparelho", "Estado", "Riscos", "< 3 mm", "mm total"],
        [[f"ap{l['aparelho']}", l["estado"], l["n_riscos"], l["n_curtos_lt_3mm"], f(l["mm_total"])] for l in po],
    ) if po else "_Sem foto `sujo_ra`._"
    return tab_cz, tab_po


def p6(por_formato):
    principal = "heic" if "heic" in por_formato else next(iter(por_formato), None)
    if not principal:
        return "_Sem fotos._"
    mb = statistics.mean(por_formato[principal])
    linhas = []
    for nome, fotos in (("espelhos, 2 passos × 3 luzes", 6), ("em pé, 13 fotos", 13), ("em pé, 18 fotos", 18)):
        tb = APARELHOS_MES * fotos * mb / 1e6
        linhas.append([nome, fotos, f(mb), f(tb, 2)])
    extra = ""
    if "dng" in por_formato:
        extra = f"\n\nDNG/ProRAW: média de {f(statistics.mean(por_formato['dng']))} MB por foto — só para teste."
    return tabela(["Roteiro", "Fotos/aparelho", f"MB/foto ({principal})", "TB/mês (4.000 aparelhos)"], linhas) + extra


def surpresas(cat):
    itens = []
    for l in fase0.ler_csv(S / "escala.csv"):
        if l["contorno_ok"] != "True":
            itens.append(f"Contorno não encontrado em `{l['arquivo']}` ({l['variante']}).")
    for l in fase0.ler_csv(S / "faces.csv"):
        if (num(l.get("deslocamento_max_px")) or 0) > config.DESLOCAMENTO_MAX_PX:
            itens.append(f"ap{l['aparelho']} {l['face']}: fotos desalinhadas em {l['deslocamento_max_px']} px "
                         "(o celular ou o aparelho mexeu entre as luzes; corrigido por translação).")
        if (num(l.get("residuo_bordas_mm")) or 0) > config.RESIDUO_BORDAS_MAX_MM:
            itens.append(f"ap{l['aparelho']} {l['face']}: resíduo das bordas de {l['residuo_bordas_mm']} mm "
                         f"(> {config.RESIDUO_BORDAS_MAX_MM}): contorno ruim, moldura torta ou distorção da lente.")
        for luz in ("ra", "rb"):
            n, b = num(l.get(f"n_{luz}")), num(l.get(f"n_{luz}_perto_borda"))
            if n and b and b / n > 0.3:
                itens.append(f"ap{l['aparelho']} {l['face']} {luz}: {int(b)} de {int(n)} riscos perto da borda "
                             "(brilho da moldura? avaliar faixa excluída maior).")
    return itens


# ---------------------------------------------------------------- recomendações


FOCO_MINIMO_MM = 200  # lente 1x: ~150–200 mm conforme o modelo (guia 14.1); medir


def recomendar(perda_uma_luz, px, h20, alvo_ok, foco_med, contorno, altura_mm):
    r = {}
    if perda_uma_luz is None:
        r["D1"] = "Sem dados. Manter o padrão: duas barras, fotos separadas."
    elif perda_uma_luz > 10:
        r["D1"] = (f"**Duas barras, fotos separadas** (padrão). Com uma direção só, até {f(perda_uma_luz)}% do "
                   "comprimento de risco some. A fase 0 não testou as duas juntas (`rasante_ab`): testar na cabine.")
    else:
        r["D1"] = (f"Uma direção perdeu no máximo {f(perda_uma_luz)}% do comprimento. Uma barra pode bastar, mas a "
                   "amostra é pequena: manter duas na cabine e reavaliar com mais aparelhos.")

    if alvo_ok:
        alvo = 20  # guia R4: alvo ≥ 20 px/mm; abaixo disso os microrriscos (< 3 mm) somem primeiro
        r["D2"] = (f"Sem perdas relevantes (≥ 95% achados em riscos ≥ 3 mm) a partir de {alvo_ok} px/mm. "
                   f"Proposta: alvo **≥ {alvo} px/mm**, câmera a **~{f(altura_mm * px / alvo, 0) if px else '—'} mm** "
                   "(conferir que fica acima do foco mínimo da lente + espessura do aparelho em pé, se D3 = suportes).")
        if px and altura_mm * px / alvo < FOCO_MINIMO_MM:
            r["D2"] += (f" **Atenção:** essa altura fica abaixo de ~{FOCO_MINIMO_MM} mm, perto do foco mínimo da lente 1x. "
                        "Com esta câmera, 20 px/mm pode não ser alcançável; confirmar com um iPhone de 48 MP.")
    else:
        r["D2"] = (f"Alguma faixa perde riscos mesmo a 20 px/mm ou não houve dados. Proposta: o maior px/mm que o foco "
                   f"mínimo permite; 20 px/mm pede a câmera a ~{f(h20, 0)} mm.")

    esp = foco_med.get("espelho_amb")
    lat, pon = foco_med.get("foco_lateral"), foco_med.get("foco_ponta")
    if esp is not None and esp <= 1.5:
        r["D3"] = (f"**Espelhos a 45°**: borda refletida {f(esp, 2)}× a do aparelho deitado "
                   f"(em pé: lateral {f(lat, 2)}×, ponta {f(pon, 2)}×). Conferir a iluminação das bordas na imagem.")
    elif esp is not None:
        r["D3"] = (f"Borda refletida {f(esp, 2)}× mais larga que a do aparelho deitado. Testar foco intermediário; "
                   f"se não melhorar, **suportes em pé** com foco por pose (lateral {f(lat, 2)}×, ponta {f(pon, 2)}×).")
    else:
        r["D3"] = "Sem foto de espelho. Manter o padrão (espelhos, se nítidos) e testar na montagem da cabine."

    sem, com = contorno.get("sem_contraluz"), contorno.get("com_contraluz")
    if sem:
        taxa = 100 * sem["falhas"] / sem["n"]
        if taxa > 2:
            r["D4"] = f"**Usar contraluz**: sem ela, o contorno falhou em {f(taxa)}% das fotos (limite: 2%)."
        elif com and com["residuo"] and sem["residuo"] and sem["residuo"] > 2 * com["residuo"]:
            r["D4"] = (f"Contorno sempre encontrado, mas o resíduo sem contraluz ({f(sem['residuo'], 3)} mm) é mais que o "
                       f"dobro do com contraluz ({f(com['residuo'], 3)} mm). Proposta: **usar contraluz**.")
        else:
            r["D4"] = f"Contorno sem contraluz falhou em {f(taxa)}% (≤ 2%). Proposta: **não usar contraluz** por enquanto."
    else:
        r["D4"] = "Sem dados de contorno."
    return r


# ---------------------------------------------------------------- montagem


def gerar(altura_mm):
    cat = fase0.catalogo()
    anot = fase0.ler_anotacao()
    if DIR_IMG.exists():
        shutil.rmtree(DIR_IMG)
    por_formato, tab_fotos = secao_fotos(cat)
    txt_p1, perda = p1()
    txt_p2, px, h20, alvo_ok = p2(altura_mm)
    txt_p3, foco_med = p3()
    txt_p4, contorno = p4()
    tab_cz, tab_po = p5()
    txt_p6 = p6(por_formato)
    rec = recomendar(perda, px, h20, alvo_ok, foco_med, contorno, altura_mm)
    p = config.PARAM_RISCOS
    modelos = sorted({anot.modelo(n) or "?" for n in fase0.aparelhos(cat)})
    lista_surpresas = surpresas(cat)

    md = f"""# Fase 0 — relatório do teste na mão

**Data:** {date.today().isoformat()} · **Guia:** seção 8 · **Mudança:** `openspec/changes/nota-estetica-automatica/`
**Status:** gerado por `visao/prototipos/relatorio.py`; números automáticos, texto a revisar antes das decisões D1 a D4.

## Resumo

- Aparelhos: {len(fase0.aparelhos(cat))} ({", ".join(modelos)}).
- Fotos: {sum(len(v) for v in por_formato.values())}. Altura da câmera informada: {f(altura_mm, 0)} mm.

| Decisão | Proposta |
|---|---|
| D1 — luz rasante | {rec["D1"]} |
| D2 — altura e px/mm | {rec["D2"]} |
| D3 — laterais, topo e base | {rec["D3"]} |
| D4 — contraluz | {rec["D4"]} |

## P1 — A luz rasante mostra os riscos? Uma direção basta?

{txt_p1}

Vermelho = só `ra`; azul = só `rb`; amarelo = nas duas. Número = comprimento em mm.

{imagens("riscos/ap*_frente.jpg", 3)}

Recortes 1:1 dos maiores riscos (esquerda: rasante; direita: detecção):

{imagens("riscos/ap*_frente_zoom.jpg", 2)}

## P2 — Quantos px/mm temos e quantos precisamos?

{txt_p2}

Riscos perdidos a 10 px/mm (magenta):

{imagens("resolucao/*_perdidos_10pxmm.jpg", 2)}

## P3 — Nitidez fora do plano de foco e nos espelhos

{txt_p3}

{imagens("foco/*.jpg", 6)}

## P4 — Contorno em fundo preto; a contraluz ajuda?

{txt_p4}

{imagens("escala/*_frente_amb_*.jpg", 2)}

## P5 — Risco × poeira, digital e reflexo

O técnico viu × o algoritmo achou (camada (a), união de `ra` e `rb`, longe da borda):

{tab_cz}

Poeira — mesma face antes e depois da microfibra:

{tab_po}

{imagens("poeira/*.jpg", 2)}

## P6 — Tamanho das fotos e armazenamento

{tab_fotos}

{txt_p6}

## Limiares iniciais da camada (a)

Valores em `visao/src/visao/config.py` usados nesta rodada:

| Parâmetro | Valor |
|---|---|
| Largura máxima de risco (top-hat = 4×) | {f(p.largura_max_mm, 2)} mm |
| Limiar | mediana + {f(p.k_mad)} × MAD |
| Emenda de fragmentos | {f(p.emenda_mm)} mm |
| Comprimento mínimo | {f(p.comp_min_mm)} mm |
| Alongamento mínimo | {f(p.alongamento_min)} |
| Faixa da borda excluída | {f(p.borda_excluida_mm)} mm |

Ajustar depois de revisar as imagens: falsos positivos pedem `k_mad` maior; riscos visíveis perdidos pedem menor.

## Surpresas

{chr(10).join(f"- {s}" for s in lista_surpresas) if lista_surpresas else "- Nenhuma detectada automaticamente."}
- _(Acrescentar o que a revisão humana das imagens mostrar.)_

## Próximos passos

1. O responsável decide D1 a D4; registrar em `openspec/changes/nota-estetica-automatica/design.md`.
2. Se algo do PRD mudar, propor o texto da versão 1.1.
3. Fase 1 (critério de nota), com as fotos desta fase como exemplos.
"""
    destino = DOCS / "nota-estetica-fase0-relatorio.md"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(md, encoding="utf-8")
    print(destino)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--altura-mm", type=float, default=config.ALTURA_CAMERA_MM_PADRAO)
    gerar(ap.parse_args().altura_mm)
