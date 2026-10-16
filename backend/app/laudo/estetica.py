"""Bloco "Estado estético" do laudo e dados da página pública de verificação (guia 11.4, D11)."""

import html
import io

from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..estetica.armazenamento import armazenamento
from ..estetica.enums import Face, OrigemNota
from ..estetica.modelos import AvaliacaoEstetica, DefeitoEstetico, FotoEstetica

NOMES_FACE = {"frente": "Frente", "traseira": "Traseira", "lat_esq": "Lateral esquerda", "lat_dir": "Lateral direita",
              "topo": "Topo", "base": "Base"}
NOMES_ORIGEM = {OrigemNota.tecnico: "Avaliada pelo técnico", OrigemNota.sugerida: "Sugerida pela máquina e confirmada pelo técnico",
                OrigemNota.automatica: "Automática"}
LADO_MINIATURA = 480


def avaliacao_vigente(db: Session, sessao_id) -> AvaliacaoEstetica | None:
    substituidas = select(AvaliacaoEstetica.substitui_id).where(AvaliacaoEstetica.substitui_id.is_not(None))
    return db.scalar(select(AvaliacaoEstetica).where(AvaliacaoEstetica.sessao_id == sessao_id,
                                                     AvaliacaoEstetica.id.not_in(substituidas))
                     .order_by(AvaliacaoEstetica.criada_em.desc()))


def miniaturas(db: Session, sessao_id) -> dict[str, str]:
    """Chave da miniatura de cada face, a partir da retificada com luz ambiente. Gera e guarda na 1ª vez."""
    arm = armazenamento()
    out = {}
    fotos = db.scalars(select(FotoEstetica).where(FotoEstetica.sessao_id == sessao_id, FotoEstetica.luz == "ambiente",
                                                  FotoEstetica.chave_retificada.is_not(None))
                       .order_by(FotoEstetica.criada_em.desc())).all()
    for face in Face:
        f = next((x for x in fotos if face.value in [g.get("face") for g in (x.geometria or [])]), None)
        if f is None:
            continue
        chave = f"sessoes/{sessao_id}/miniaturas/{face.value}.jpg"
        if not arm.existe(chave):
            origem = f"{f.chave_retificada}_{face.value}.jpg"
            if not arm.existe(origem):
                continue
            img = Image.open(io.BytesIO(arm.ler(origem))).convert("RGB")
            img.thumbnail((LADO_MINIATURA, LADO_MINIATURA))
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=82)
            arm.salvar(chave, buf.getvalue(), "image/jpeg")
        out[face.value] = chave
    return out


def _mm(x):
    return f"{x:.1f}".replace(".", ",") if x is not None else "—"


def bloco(db: Session, sessao_id) -> dict | None:
    av = avaliacao_vigente(db, sessao_id)
    if av is None:
        return None
    defeitos = db.scalars(select(DefeitoEstetico).where(DefeitoEstetico.avaliacao_id == av.id,
                                                        DefeitoEstetico.estado == "confirmado")
                          .order_by(DefeitoEstetico.face)).all()
    arm = armazenamento()
    return {
        "nota_final": av.nota_final,
        "origem": av.origem,
        "origem_texto": NOMES_ORIGEM.get(av.origem, av.origem),
        "notas_por_face": av.notas_por_face,
        "versao_criterio": av.versao_criterio,
        "versao_visao": av.versao_visao,
        "avaliada_em": av.criada_em.isoformat(),
        "miniaturas": {f: arm.url_leitura(k, expira_s=3600) for f, k in miniaturas(db, sessao_id).items()},
        "defeitos": [{"face": d.face, "face_nome": NOMES_FACE[d.face], "tipo": d.tipo, "zona": d.zona,
                      "visibilidade": d.visibilidade,
                      "medida": (f"{_mm(d.comprimento_mm)} mm" if d.tipo == "risco" and d.comprimento_mm is not None
                                 else f"{_mm(d.maior_dimensao_mm)} mm" if d.maior_dimensao_mm is not None
                                 else f"{_mm(d.area_mm2)} mm²" if d.area_mm2 is not None else "—")}
                     for d in defeitos],
    }


def html_bloco(dados: dict) -> str:
    """Fragmento HTML para o gerador de PDF do laudo (estilo a alinhar com o laudo atual)."""
    e = html.escape
    faces = "".join(
        f'<figure><img src="{e(url)}" alt="{e(NOMES_FACE[f])}"><figcaption>{e(NOMES_FACE[f])} · '
        f'{e(dados["notas_por_face"].get(f, "—"))}</figcaption></figure>'
        for f, url in dados["miniaturas"].items())
    linhas = "".join(
        f"<tr><td>{e(d['face_nome'])}</td><td>{e(d['tipo'])}</td><td>{e(d['zona'])}</td><td>{e(d['medida'])}</td></tr>"
        for d in dados["defeitos"]) or '<tr><td colspan="4">Nenhum defeito estético registrado.</td></tr>'
    return f"""<section class="estado-estetico">
  <h2>Estado estético</h2>
  <p class="nota">Nota <strong>{e(dados['nota_final'])}</strong></p>
  <p class="origem">{e(dados['origem_texto'])} · critério {e(dados['versao_criterio'])}</p>
  <div class="faces">{faces}</div>
  <table><thead><tr><th>Face</th><th>Defeito</th><th>Zona</th><th>Medida</th></tr></thead><tbody>{linhas}</tbody></table>
</section>"""
