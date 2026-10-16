"""Faz o papel da cabine contra um backend (guia 17.3).

Envia as fotos de um aparelho da fase 0 seguindo o roteiro (passo 1 = frente, passo 2 =
traseira; amb → ambiente, ra → rasante_a, rb → rasante_b), conclui, espera a sugestão e
confere as rotas do painel. Roda com o worker nulo (fase 3) ou real (fase 4).

    uv run python -I ferramentas/simular_cabine.py --api http://localhost:8000 \\
        --dados dev.json --sessao sessao.json --fotos prototipos/fotos --aparelho 1
"""

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

import httpx

LUZES = {"ambiente": "amb", "rasante_a": "ra", "rasante_b": "rb", "rasante_ab": "rab", "contraluz": "sil"}
FACE_ARQUIVO = {"frente": "frente", "traseira": "traseira"}
FORMATOS = {".heic": "heic", ".heif": "heic", ".jpg": "jpeg", ".jpeg": "jpeg", ".dng": "dng"}


def achar(pasta: Path, n: int, face: str, luz: str) -> Path | None:
    for ext in (".dng", ".heic", ".heif", ".jpg", ".jpeg"):
        p = pasta / f"ap{n}_{FACE_ARQUIVO[face]}_{LUZES[luz]}{ext}"
        if p.exists():
            return p
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--dados", type=Path, required=True, help="JSON de `python -m app.dev semear`")
    ap.add_argument("--sessao", type=Path, required=True, help="JSON de `python -m app.dev sessao`")
    ap.add_argument("--fotos", type=Path, required=True)
    ap.add_argument("--aparelho", type=int, default=1)
    ap.add_argument("--orientacao", default="topo_para_cima", help="posição do topo na imagem (perfil da cabine)")
    ap.add_argument("--espera-s", type=float, default=120)
    args = ap.parse_args()
    dados, sessao = json.loads(args.dados.read_text()), json.loads(args.sessao.read_text())
    cab = httpx.Client(base_url=args.api, timeout=60, headers={"Authorization": f"Bearer {dados['token_cabine']}"})
    tec = httpx.Client(base_url=args.api, timeout=60, headers={"Authorization": f"Bearer {dados['token_tecnico']}"})
    token = sessao["token_sessao"]

    cab.put("/cabine/perfil", json={"versao": 1, "orientacao": {"deitado": args.orientacao}}).raise_for_status()
    r = cab.get(f"/cabine/{token}")
    r.raise_for_status()
    roteiro = r.json()["roteiro"]
    print(f"Sessão aberta: {r.json()['aparelho']['nome']} · roteiro {roteiro['versao']}")
    enviadas, t_ultima = 0, None
    for passo in roteiro["passos"]:
        face = passo["faces"][0]
        for luz in passo["luzes"]:
            arq = achar(args.fotos, args.aparelho, face, luz)
            if arq is None:
                sys.exit(f"Falta foto: ap{args.aparelho}_{FACE_ARQUIVO.get(face, face)}_{LUZES[luz]}.*")
            formato = FORMATOS[arq.suffix.lower()]
            meta = {"formato": formato, "rotacao_graus": 0, "perfil_calibracao_versao": 1, "dimensoes_px": {}}
            r = cab.post(f"/cabine/{token}/fotos", headers={"Idempotency-Key": str(uuid.uuid4())},
                         data={"passo": passo["ordem"], "face": face, "luz": luz, "pose": passo["pose"],
                               "lado": passo.get("lado") or "", "tentativa": 1, "metadados": json.dumps(meta)},
                         files={"arquivo": (arq.name, arq.read_bytes())})
            r.raise_for_status()
            enviadas += 1
            t_ultima = time.monotonic()
            print(f"  passo {passo['ordem']} {face} {luz}: {arq.name} → {r.json()['foto_id'][:8]}")
    cab.post(f"/cabine/{token}/concluir", json={"fotos_enviadas": enviadas}).raise_for_status()

    limite = time.monotonic() + args.espera_s
    while time.monotonic() < limite:
        s = cab.get(f"/cabine/{token}/sugestao").json()
        if s["status"] in ("pronta", "erro"):
            break
        time.sleep(0.5)
    segundos = time.monotonic() - t_ultima
    print(f"\nSugestão: {json.dumps(s, ensure_ascii=False)}")
    print(f"Tempo após a última foto: {segundos:.1f} s (meta ≤ 10 s)")

    d = tec.get(f"/estetica/sessoes/{sessao['sessao_id']}").json()
    print(f"Painel: status {d['status']} · {len(d['fotos'])} fotos · {len(d['defeitos_propostos'])} defeitos propostos")
    for f in d["fotos"]:
        print(f"  {f['face']:9} {f['luz']:10} aceita={f['aceita']} qualidade={f['qualidade'] and f['qualidade'].get('motivo')}"
              f" retificadas={list(f['retificada'])}")
    for x in d["defeitos_propostos"]:
        print(f"  defeito {x['face']} {x['tipo']} {x['zona']} {x['visibilidade']} {x['comprimento_mm']} mm (fonte {x['fonte']})")
    if d.get("sugestao"):
        print("Justificativas:", json.dumps(d["sugestao"]["justificativas"], ensure_ascii=False))
        print("Pendências:", d["sugestao"]["pendencias"])
    ok = s["status"] == "pronta" and d["status"] in ("aguardando_tecnico", "avaliada")
    print("\nOK" if ok else "\nFALHOU")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
