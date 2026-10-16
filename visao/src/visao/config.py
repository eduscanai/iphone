"""Limiares e parâmetros do pipeline de visão.

Os valores são pontos de partida (guia, seção 15). A fase 0 recalibra cada um;
anote ao lado de onde veio o valor sempre que mudar.
"""

from dataclasses import dataclass

# Folha de marcadores (guia, 8.3 passo 2)
DICIONARIO_ARUCO = "DICT_4X4_50"
LADO_ARUCO_MM = 30.0


@dataclass(frozen=True)
class ParamRiscos:
    """Camada (a), guia 15.4."""

    largura_max_mm: float = 0.4  # o elemento do top-hat tem 4× essa largura
    k_mad: float = 8.0  # limiar = mediana + k × MAD
    emenda_mm: float = 1.0  # fechamento que junta fragmentos do mesmo risco
    comp_min_mm: float = 0.5
    alongamento_min: float = 4.0  # comprimento ÷ largura; rejeita poeira e pontos
    borda_excluida_mm: float = 0.5  # faixa da borda que conta como moldura
    perto_borda_mm: float = 2.0  # só marca no relatório; não filtra
    # Faixa da borda fora da busca da camada (a) no worker. A zona `moldura` continua com 0,5 mm
    # (guia 15.9); aqui é só onde não se procura risco, porque o friso da moldura e a borda
    # curva do vidro brilham na rasante. Provisório: a fase 0 mede (`perto_borda`) e decide.
    faixa_busca_mm: float = 1.5


PARAM_RISCOS = ParamRiscos()

# Geometria (guia 15.3)
TOLERANCIA_PROPORCAO = 0.15  # erro relativo aceito na proporção da face
TOLERANCIA_AREA = 0.35  # erro relativo aceito na área, quando a escala ArUco é conhecida
RAIO_CANTO_PADRAO_MM = 9.0  # a Apple não publica; MEDIR por modelo
RESIDUO_BORDAS_MAX_MM = 0.3
DESLOCAMENTO_MAX_PX = 2.0  # entre fotos da mesma face (amb × rasante)

# Altura da câmera usada na fase 0 (lente até a mesa), para corrigir a escala
# dos ArUco (na mesa) para a face do aparelho (alguns mm acima).
ALTURA_CAMERA_MM_PADRAO = 250.0

# Worker (fase 4)
VERSAO_PIPELINE = "0.2.0"
JPEG_QUALIDADE_RETIFICADA = 90  # guia 15.10
T_VISIVEL = 6.0  # contraste na foto ambiente (em MADs) acima do qual o risco é `visivel` (calibrar, 15.5)
T_NITIDEZ = 4.5  # nitidez normalizada na borda do aparelho; sintético: nítida 6–9,5, σ ≥ 0,7 px ≤ 3,3 (recalibrar na fase 2)
ESTOURO_MAX_PCT = {"ambiente": 0.5, "rasante": 2.0, "contraluz": 100.0}  # guia 14.6
FUSAO_HAUSDORFF_MM = 1.0  # guia 15.8
FUSAO_SOBREPOSICAO_MIN = 0.5
FUSAO_IOU_MIN = 0.3
RENOVAR_A_CADA_S = 60
