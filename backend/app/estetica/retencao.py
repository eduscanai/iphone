"""Retenção das fotos originais (guia 11.1 passo 11). Rodar uma vez por dia:

    uv run python -m app.estetica.retencao [--simular]

Apaga originais com mais de ESTETICA_RETENCAO_MESES, exceto fotos com defeito confirmado
(viram dados de treino). Retificadas, anotadas e miniaturas ficam. Tudo vai para a auditoria.
"""

import argparse
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text

from ..base import auditoria
from ..config import config
from ..db import nova_sessao
from .armazenamento import armazenamento
from .modelos import FotoEstetica

_COM_DEFEITO_CONFIRMADO = text("""
    SELECT 1 FROM defeito_estetico d
     WHERE d.estado = 'confirmado'
       AND (d.foto_id = :foto_id OR d.fotos ? CAST(:foto_id AS text))
     LIMIT 1
""")


def rodar(simular: bool = False, agora: datetime | None = None) -> dict:
    agora = agora or datetime.now(timezone.utc)
    limite = agora - timedelta(days=30 * config().estetica_retencao_meses)
    apagadas, mantidas = [], 0
    with nova_sessao() as db:
        fotos = db.scalars(select(FotoEstetica).where(FotoEstetica.criada_em < limite,
                                                      FotoEstetica.original_apagada_em.is_(None))).all()
        for f in fotos:
            if db.execute(_COM_DEFEITO_CONFIRMADO, {"foto_id": str(f.id)}).first():
                mantidas += 1
                continue
            if not simular:
                armazenamento().apagar(f.chave)
                f.original_apagada_em = agora
            apagadas.append(str(f.id))
        if not simular:
            auditoria.registrar(db, "sistema", None, "estetica.retencao", "foto_estetica", None,
                                apagadas=len(apagadas), mantidas_com_defeito=mantidas, limite=limite.isoformat(),
                                ids=apagadas[:1000])
            db.commit()
    return {"apagadas": len(apagadas), "mantidas_com_defeito": mantidas, "simulado": simular}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--simular", action="store_true")
    print(rodar(ap.parse_args().simular))
