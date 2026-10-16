"""Gate do modo automático (guia 13.1, RF11), modo sombra (13.2) e monitoramento (13.3)."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..base import auditoria
from ..config import config
from . import concordancia
from .enums import ModoEstetica

MIN_APARELHOS = 200
MIN_EXATA = 0.90
MIN_RECALL = 0.80
DIAS_SOMBRA = 14


def _checar(m: dict, kappa_base: float | None) -> list[str]:
    motivos = []
    n = m.get("n", 0)
    if n < MIN_APARELHOS:
        return [f"aparelhos avaliados: {n} (mínimo {MIN_APARELHOS})"]
    if m["exata"] < MIN_EXATA:
        motivos.append(f"concordância exata {m['exata']:.1%} (mínimo {MIN_EXATA:.0%})")
    if m["a_2_ou_mais"] > 0:
        motivos.append(f"{m['a_2_ou_mais']} caso(s) a 2 ou mais notas de distância (máximo 0)")
    if kappa_base is None:
        motivos.append("linha de base técnico × técnico não registrada (ESTETICA_KAPPA_TECNICOS)")
    elif m["kappa_quadratico"] is None or m["kappa_quadratico"] < kappa_base:
        motivos.append(f"kappa ponderado {m['kappa_quadratico']} abaixo da linha de base {kappa_base}")
    for nota, r in m["recall"].items():
        if r is None:
            motivos.append(f"sem casos de nota {nota} na amostra (recall não medido)")
        elif r < MIN_RECALL:
            motivos.append(f"recall da nota {nota}: {r:.1%} (mínimo {MIN_RECALL:.0%})")
    return motivos


def avaliar(db: Session, loja_id, sombra_iniciada_em: datetime | None) -> dict:
    """Para ligar: só sessões cegas do conjunto de teste (holdout), últimos aparelhos da loja."""
    lista = concordancia.pares(db, loja_id=loja_id, so_teste=True)
    m = concordancia.metricas([p.maquina for p in lista], [p.tecnico for p in lista])
    motivos = _checar(m, config().estetica_kappa_tecnicos)
    if sombra_iniciada_em is None:
        motivos.append("modo sombra (100% cego) não iniciado")
    elif datetime.now(timezone.utc) - sombra_iniciada_em < timedelta(days=DIAS_SOMBRA):
        dias = (datetime.now(timezone.utc) - sombra_iniciada_em).days
        motivos.append(f"modo sombra há {dias} dia(s) (mínimo {DIAS_SOMBRA})")
    n = m.get("n", 0)
    observacao = ("Ainda não há aparelhos cegos do conjunto de teste avaliados." if n == 0 else
                  f"Com {n} aparelhos e zero erros de 2 notas, a taxa real desse erro fica abaixo de "
                  f"~{100 * 3 / n:.1f}% (95%, regra de três).".replace(".", ",", 1))
    return {"passou": not motivos, "motivos": motivos, "metricas": m, "observacao": observacao}


def monitorar(db: Session, loja_id) -> bool:
    """Janela dos últimos 200 aparelhos cegos. Abaixo do gate → volta para `assistido` e avisa."""
    from .sessoes import config_loja

    lista = concordancia.pares(db, loja_id=loja_id, limite=MIN_APARELHOS)
    if len(lista) < MIN_APARELHOS:
        return True
    m = concordancia.metricas([p.maquina for p in lista], [p.tecnico for p in lista], bootstrap=0)
    motivos = _checar(m, config().estetica_kappa_tecnicos)
    if motivos:
        cfg = config_loja(db, loja_id)
        cfg.modo = ModoEstetica.assistido
        cfg.atualizado_em = datetime.now(timezone.utc)
        # O painel mostra o último aviso desta ação na tela de configuração.
        auditoria.registrar(db, "sistema", None, "estetica.automatico_desligado", "loja", loja_id, motivos=motivos)
        return False
    return True
