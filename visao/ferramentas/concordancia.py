"""Concordância entre avaliadores (guia 9.2 passo 4): técnico × técnico (fase 1) ou
máquina × técnico (relatórios da fase 4/5, a partir de CSV exportado).

Entrada: dois CSV no formato de docs/estudo-concordancia-v1.csv
(`aparelho_id,modelo,cor,tecnico,face,nota,observacao`). A face `final` é a nota do
aparelho; sem ela, a nota final é calculada como a pior face.

Saída: concordância exata, ±1, casos a ≥ 2 notas, kappa ponderado quadrático, matriz de
confusão 4×4 (final e por face) e a lista de divergências para a reunião.

    uv run python -I ferramentas/concordancia.py a.csv b.csv [--saida divergencias.csv]
"""

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import cohen_kappa_score, confusion_matrix

NOTAS = ["A", "B", "C", "D"]
ORDEM = {n: i for i, n in enumerate(NOTAS)}
FACES = ["frente", "traseira", "lat_esq", "lat_dir", "topo", "base"]


def ler(caminho: Path) -> tuple[str, dict[tuple[str, str], str], dict[str, str]]:
    notas, observacoes, tecnicos = {}, {}, set()
    with open(caminho, newline="", encoding="utf-8-sig") as f:
        for l in csv.DictReader(f):
            nota = (l.get("nota") or "").strip().upper()
            if not nota:
                continue
            if nota not in ORDEM:
                sys.exit(f"{caminho}: nota inválida '{nota}' em {l}")
            ap, face = l["aparelho_id"].strip(), l["face"].strip().lower()
            notas[(ap, face)] = nota
            if l.get("observacao"):
                observacoes[(ap, face)] = l["observacao"].strip()
            if l.get("tecnico"):
                tecnicos.add(l["tecnico"].strip())
    for ap in {a for a, _ in notas}:
        if (ap, "final") not in notas:
            faces = [notas[(ap, f)] for f in FACES if (ap, f) in notas]
            if faces:
                notas[(ap, "final")] = max(faces, key=ORDEM.__getitem__)
    nome = "/".join(sorted(tecnicos)) or caminho.stem
    return nome, notas, observacoes


def metricas(a: list[str], b: list[str]) -> dict:
    x, y = np.array([ORDEM[n] for n in a]), np.array([ORDEM[n] for n in b])
    dif = np.abs(x - y)
    kappa = cohen_kappa_score(x, y, weights="quadratic", labels=range(4)) if len(set(x) | set(y)) > 1 else float("nan")
    return {
        "n": len(x),
        "exata": float(np.mean(dif == 0)),
        "mais_menos_1": float(np.mean(dif <= 1)),
        "a_2_ou_mais": int(np.sum(dif >= 2)),
        "kappa_quadratico": float(kappa),
        "matriz": confusion_matrix(x, y, labels=range(4)),
    }


def recall_por_nota(ref: list[str], outro: list[str]) -> dict[str, float | None]:
    """Recall de `outro` tomando `ref` como verdade (usado no gate da fase 5)."""
    out = {}
    for n in NOTAS:
        idx = [i for i, r in enumerate(ref) if r == n]
        out[n] = sum(outro[i] == n for i in idx) / len(idx) if idx else None
    return out


def imprimir_matriz(m, nome_a, nome_b):
    print(f"      {nome_b} →")
    print("        " + "  ".join(f"{n:>3}" for n in NOTAS))
    for i, n in enumerate(NOTAS):
        print(f"  {n} ↓  " + "  ".join(f"{v:>3}" for v in m[i]))


def pct(x):
    return f"{100 * x:.1f}%".replace(".", ",")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("a", type=Path)
    ap.add_argument("b", type=Path)
    ap.add_argument("--saida", type=Path, help="CSV com as divergências")
    args = ap.parse_args()
    nome_a, na, obs_a = ler(args.a)
    nome_b, nb, obs_b = ler(args.b)
    comuns = sorted(set(na) & set(nb))
    if not comuns:
        sys.exit("Nenhuma nota preenchida em comum nas duas planilhas ainda.")
    so_um = sorted({k[0] for k in set(na) ^ set(nb)})
    if so_um:
        print(f"Aviso: aparelhos/faces avaliados por só um lado: {', '.join(so_um)}\n")

    for escopo in ["final"] + FACES:
        chaves = [k for k in comuns if k[1] == escopo]
        if not chaves:
            continue
        m = metricas([na[k] for k in chaves], [nb[k] for k in chaves])
        kappa = "—" if np.isnan(m["kappa_quadratico"]) else f"{m['kappa_quadratico']:.3f}".replace(".", ",")
        titulo = "NOTA FINAL" if escopo == "final" else f"face {escopo}"
        print(f"== {titulo}: {m['n']} aparelhos")
        print(f"   exata {pct(m['exata'])} · ±1 {pct(m['mais_menos_1'])} · a ≥ 2 notas: {m['a_2_ou_mais']} · kappa ponderado {kappa}")
        if escopo == "final":
            imprimir_matriz(m["matriz"], nome_a, nome_b)
            ok = m["exata"] >= 0.85 and not np.isnan(m["kappa_quadratico"]) and m["kappa_quadratico"] >= 0.80
            print(f"   Meta da fase 1 (exata ≥ 85% e kappa ≥ 0,80): {'ATINGIDA' if ok else 'não atingida'}")
        print()

    divergencias = []
    for k in comuns:
        if na[k] != nb[k]:
            divergencias.append({
                "aparelho_id": k[0], "face": k[1], nome_a: na[k], nome_b: nb[k],
                "distancia": abs(ORDEM[na[k]] - ORDEM[nb[k]]),
                f"obs_{nome_a}": obs_a.get(k, ""), f"obs_{nome_b}": obs_b.get(k, ""),
            })
    divergencias.sort(key=lambda d: (-d["distancia"], d["aparelho_id"], d["face"]))
    print(f"== Divergências para a reunião: {len(divergencias)}")
    for d in divergencias:
        print(f"   {d['aparelho_id']} {d['face']}: {d[nome_a]} × {d[nome_b]}"
              + (f"  ({d[f'obs_{nome_a}']} | {d[f'obs_{nome_b}']})" if d[f"obs_{nome_a}"] or d[f"obs_{nome_b}"] else ""))
    if args.saida and divergencias:
        with open(args.saida, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(divergencias[0]))
            w.writeheader()
            w.writerows(divergencias)
        print(f"\n{args.saida}")


if __name__ == "__main__":
    main()
