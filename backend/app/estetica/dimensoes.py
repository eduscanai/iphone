"""Dimensões e zonas por modelo (guia, Apêndice A).

Chave = identificador do modelo (ProductType, ex.: iPhone14,5), lido pela estação no
cabo. Dimensões externas: páginas de especificações técnicas da Apple. **VERIFICAR** cada
valor antes de marcar `verificado=True`; raio de canto e zonas: **MEDIR** numa foto
retificada (visao/ferramentas/marcar_zonas.py) e conferir com o técnico.
"""

from dataclasses import dataclass, field


FONTE_DIMENSOES = ("Dimensões: https://www.apple.com/iphone/compare/ (conferido em 2026-10-16). "
                   "Identificadores: https://ipsw.io/public/blog/iphone-17-firmware e everymac.com. "
                   "Materiais: VERIFICAR na página de especificações de cada modelo.")


@dataclass(frozen=True)
class Retangulo:  # mm, no referencial da face (guia 7.2)
    x: float
    y: float
    w: float
    h: float
    raio: float = 0.0

    def como_lista(self) -> list[float]:
        return [self.x, self.y, self.w, self.h]


@dataclass(frozen=True)
class Modelo:
    identificadores: tuple[str, ...]
    nome: str
    largura_mm: float
    altura_mm: float
    espessura_mm: float
    raio_canto_mm: float  # a Apple não publica: MEDIR (0 = ainda não medido)
    tela: str  # oled ou lcd
    moldura: str  # aluminio, aco ou titanio
    traseira: str  # vidro_brilhante ou vidro_fosco
    zonas: dict[str, dict[str, tuple[Retangulo, ...]]] = field(default_factory=dict)
    fonte: str = FONTE_DIMENSOES
    verificado: bool = False

    @property
    def dimensoes_mm(self) -> dict[str, float]:
        return {"largura": self.largura_mm, "altura": self.altura_mm, "espessura": self.espessura_mm}

    def zonas_mm(self) -> dict[str, dict[str, list[list[float]]]]:
        return {face: {z: [r.como_lista() for r in rs] for z, rs in zs.items() if rs} for face, zs in self.zonas.items()}


RAIO_PADRAO_MM = 9.0  # enquanto não medido; o worker usa só para excluir os cantos do ajuste


def _m(ids, nome, larg, alt, esp, tela, moldura, traseira):
    return Modelo(identificadores=ids, nome=nome, largura_mm=larg, altura_mm=alt, espessura_mm=esp,
                  raio_canto_mm=0.0, tela=tela, moldura=moldura, traseira=traseira)


# Dimensões conferidas na Apple em 2026-10-16. `verificado` continua False até as zonas e o raio
# de canto serem medidos numa foto retificada e conferidos com o técnico (Apêndice A, passo 4).
_LISTA = [
    _m(("iPhone11,8",), "iPhone XR", 75.7, 150.9, 8.3, "lcd", "aluminio", "vidro_brilhante"),
    _m(("iPhone12,1",), "iPhone 11", 75.7, 150.9, 8.3, "lcd", "aluminio", "vidro_brilhante"),
    _m(("iPhone12,3",), "iPhone 11 Pro", 71.4, 144.0, 8.1, "oled", "aco", "vidro_fosco"),
    _m(("iPhone12,5",), "iPhone 11 Pro Max", 77.8, 158.0, 8.1, "oled", "aco", "vidro_fosco"),
    _m(("iPhone12,8",), "iPhone SE (2ª geração)", 67.3, 138.4, 7.3, "lcd", "aluminio", "vidro_brilhante"),
    _m(("iPhone14,6",), "iPhone SE (3ª geração)", 67.3, 138.4, 7.3, "lcd", "aluminio", "vidro_brilhante"),
    _m(("iPhone13,1",), "iPhone 12 mini", 64.2, 131.5, 7.4, "oled", "aluminio", "vidro_brilhante"),
    _m(("iPhone13,2",), "iPhone 12", 71.5, 146.7, 7.4, "oled", "aluminio", "vidro_brilhante"),
    _m(("iPhone13,3",), "iPhone 12 Pro", 71.5, 146.7, 7.4, "oled", "aco", "vidro_fosco"),
    _m(("iPhone13,4",), "iPhone 12 Pro Max", 78.1, 160.8, 7.4, "oled", "aco", "vidro_fosco"),
    _m(("iPhone14,4",), "iPhone 13 mini", 64.2, 131.5, 7.65, "oled", "aluminio", "vidro_brilhante"),
    _m(("iPhone14,5",), "iPhone 13", 71.5, 146.7, 7.65, "oled", "aluminio", "vidro_brilhante"),
    _m(("iPhone14,2",), "iPhone 13 Pro", 71.5, 146.7, 7.65, "oled", "aco", "vidro_fosco"),
    _m(("iPhone14,3",), "iPhone 13 Pro Max", 78.1, 160.8, 7.65, "oled", "aco", "vidro_fosco"),
    _m(("iPhone14,7",), "iPhone 14", 71.5, 146.7, 7.8, "oled", "aluminio", "vidro_brilhante"),
    _m(("iPhone14,8",), "iPhone 14 Plus", 78.1, 160.8, 7.8, "oled", "aluminio", "vidro_brilhante"),
    _m(("iPhone15,2",), "iPhone 14 Pro", 71.5, 147.5, 7.85, "oled", "aco", "vidro_fosco"),
    _m(("iPhone15,3",), "iPhone 14 Pro Max", 77.6, 160.7, 7.85, "oled", "aco", "vidro_fosco"),
    _m(("iPhone15,4",), "iPhone 15", 71.6, 147.6, 7.8, "oled", "aluminio", "vidro_fosco"),
    _m(("iPhone15,5",), "iPhone 15 Plus", 77.8, 160.9, 7.8, "oled", "aluminio", "vidro_fosco"),
    _m(("iPhone16,1",), "iPhone 15 Pro", 70.6, 146.6, 8.25, "oled", "titanio", "vidro_fosco"),
    _m(("iPhone16,2",), "iPhone 15 Pro Max", 76.7, 159.9, 8.25, "oled", "titanio", "vidro_fosco"),
    _m(("iPhone17,3",), "iPhone 16", 71.6, 147.6, 7.8, "oled", "aluminio", "vidro_fosco"),
    _m(("iPhone17,4",), "iPhone 16 Plus", 77.8, 160.9, 7.8, "oled", "aluminio", "vidro_fosco"),
    _m(("iPhone17,1",), "iPhone 16 Pro", 71.5, 149.6, 8.25, "oled", "titanio", "vidro_fosco"),
    _m(("iPhone17,2",), "iPhone 16 Pro Max", 77.6, 163.0, 8.25, "oled", "titanio", "vidro_fosco"),
    _m(("iPhone17,5",), "iPhone 16e", 71.5, 146.7, 7.8, "oled", "aluminio", "vidro_fosco"),
    _m(("iPhone18,3",), "iPhone 17", 71.5, 149.6, 7.95, "oled", "aluminio", "vidro_fosco"),
    _m(("iPhone18,4",), "iPhone Air", 74.7, 156.2, 5.64, "oled", "titanio", "vidro_fosco"),
    # 17 Pro: corpo de alumínio com traseira de vidro só em parte (VERIFICAR as zonas da traseira)
    _m(("iPhone18,1",), "iPhone 17 Pro", 71.9, 150.0, 8.75, "oled", "aluminio", "vidro_fosco"),
    _m(("iPhone18,2",), "iPhone 17 Pro Max", 78.0, 163.4, 8.75, "oled", "aluminio", "vidro_fosco"),
    _m(("iPhone18,5",), "iPhone 17e", 71.5, 146.7, 7.8, "oled", "aluminio", "vidro_fosco"),
    # Linha 18 e iPhone Duo: cadastrar quando os identificadores estiverem confirmados.
]

MODELOS: dict[str, Modelo] = {i: m for m in _LISTA for i in m.identificadores}

_CORES_CLARAS = ("branc", "prata", "estelar", "dourad", "ouro", "rosa", "azul-claro", "amarel", "verde-claro",
                 "branco", "natural", "deserto", "starlight", "silver", "gold", "white")
_CORES_ESCURAS = ("pret", "meia-noite", "grafite", "cinza-espacial", "preto", "black", "midnight", "graphite",
                  "space", "azul-pacifico", "azul-profundo", "roxo-profundo", "verde-meia-noite")


def tom_da_cor(cor: str | None) -> str | None:
    if not cor:
        return None
    c = cor.lower().replace(" ", "-")
    if any(k in c for k in _CORES_ESCURAS):
        return "escuro"
    if any(k in c for k in _CORES_CLARAS):
        return "claro"
    return None


def familia(m: Modelo, cor: str | None) -> dict[str, str]:
    """Família de acabamento para o PatchCore (guia 15.6): traseira e moldura × tom da cor.
    Cor desconhecida → `*_desconhecido` (o worker não aplica PatchCore nesse caso)."""
    tom = tom_da_cor(cor) or "desconhecido"
    moldura = m.moldura if m.moldura in ("aco", "titanio") else f"aluminio_{tom}"
    return {"traseira": f"{m.traseira}_{tom}", "moldura": moldura}
