"""Roteiro de captura (guia 7.3). Vem do backend: mudar o roteiro não exige nova versão do app.
Escolhido por ESTETICA_ROTEIRO (D3) e pelas luzes de D1/D4."""

from ..config import config
from .enums import Face, Luz, Pose

TODAS_AS_BORDAS = [Face.lat_esq, Face.lat_dir, Face.topo, Face.base]


def luzes() -> list[str]:
    c = config()
    rasantes = [Luz.rasante_ab] if c.estetica_rasante_juntas else [Luz.rasante_a, Luz.rasante_b]
    return [Luz.ambiente, *rasantes] + ([Luz.contraluz] if c.estetica_contraluz else [])


def roteiro(versao: str | None = None) -> dict:
    versao = versao or config().estetica_roteiro
    lz = [str(l) for l in luzes()]
    if versao == "roteiro-v1":  # espelhos a 45°, sempre deitado (D3 = espelhos)
        passos = [
            {"ordem": 1, "pose": Pose.deitado, "lado": "tela_cima", "faces": [Face.frente, *TODAS_AS_BORDAS],
             "luzes": lz, "instrucao": "Tela para cima, topo encostado no batente."},
            {"ordem": 2, "pose": Pose.deitado, "lado": "tela_baixo", "faces": [Face.traseira, *TODAS_AS_BORDAS],
             "luzes": lz, "instrucao": "Vire: traseira para cima."},
        ]
    elif versao == "roteiro-v1-em-pe":  # suportes em pé (D3 = suportes)
        sem_contraluz = [l for l in lz if l != Luz.contraluz]
        passos = [
            {"ordem": 1, "pose": Pose.deitado, "lado": "tela_cima", "faces": [Face.frente], "luzes": lz,
             "instrucao": "Tela para cima, topo encostado no batente."},
            {"ordem": 2, "pose": Pose.deitado, "lado": "tela_baixo", "faces": [Face.traseira], "luzes": lz,
             "instrucao": "Vire: traseira para cima."},
            {"ordem": 3, "pose": Pose.lateral, "lado": None, "faces": [Face.lat_esq], "luzes": sem_contraluz,
             "instrucao": "Em pé de lado: botões de volume para cima."},
            {"ordem": 4, "pose": Pose.lateral, "lado": None, "faces": [Face.lat_dir], "luzes": sem_contraluz,
             "instrucao": "Em pé de lado: botão lateral para cima."},
            {"ordem": 5, "pose": Pose.ponta, "lado": None, "faces": [Face.topo], "luzes": sem_contraluz,
             "instrucao": "Em pé na ponta: topo para cima."},
            {"ordem": 6, "pose": Pose.ponta, "lado": None, "faces": [Face.base], "luzes": sem_contraluz,
             "instrucao": "Em pé na ponta: conector para cima."},
        ]
    else:
        raise ValueError(f"roteiro desconhecido: {versao}")
    for p in passos:
        p["pose"] = str(p["pose"])
        p["faces"] = [str(f) for f in p["faces"]]
    return {"versao": versao, "passos": passos}


def fotos_exigidas(r: dict) -> set[tuple[int, str]]:
    return {(p["ordem"], l) for p in r["passos"] for l in p["luzes"]}
