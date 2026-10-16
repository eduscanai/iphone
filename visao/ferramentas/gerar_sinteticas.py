"""Gera fotos sintéticas no padrão da fase 0 (2 aparelhos, todas as fotos do protocolo e a
anotação), para testar os protótipos e o fluxo ponta a ponta sem fotos reais.

    uv run python -I ferramentas/gerar_sinteticas.py <pasta>

Os riscos são conhecidos (lista APARELHOS): servem de gabarito. Não substituem a fase 0.
"""
import sys
from pathlib import Path
import cv2, numpy as np

saida = Path(sys.argv[1]); saida.mkdir(parents=True, exist_ok=True)
W, H = 4032, 3024
PXMM_MESA, ALT = 12.0, 250.0
rng = np.random.default_rng(0)
dic = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)

def pxmm(z): return PXMM_MESA * ALT / (ALT - z)

def cena_base(nivel=0.04):
    img = np.full((H, W), nivel, np.float32) + rng.normal(0, 0.006, (H, W)).astype(np.float32)
    # folha de marcadores (branca) à direita, na mesa
    s = PXMM_MESA
    x0, y0 = 2900, 700
    img[y0:y0 + int(110 * s), x0:x0 + int(85 * s)] = 0.85
    for i in range(4):
        m = cv2.aruco.generateImageMarker(dic, i, int(30 * s)).astype(np.float32) / 255 * 0.8 + 0.03
        mx, my = x0 + int(5 * s) + (i % 2) * int(40 * s), y0 + int(10 * s) + (i // 2) * int(50 * s)
        img[my:my + m.shape[0], mx:mx + m.shape[1]] = m
    return img

def face_mm(larg, alt, raio, s, corpo, moldura, riscos=(), poeira=0, blur=0):
    sub = 2; ss = s * sub
    m = np.zeros((round(alt * ss), round(larg * ss)), np.uint8)
    r = round(raio * ss); w, h = m.shape[1], m.shape[0]
    cv2.rectangle(m, (r, 0), (w - r, h), 255, -1); cv2.rectangle(m, (0, r), (w, h - r), 255, -1)
    for c in [(r, r), (w - r, r), (w - r, h - r), (r, h - r)]: cv2.circle(m, c, r, 255, -1)
    m = cv2.resize(m, (round(larg * s), round(alt * s)), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    anel = m - cv2.erode((m > 0.5).astype(np.uint8), np.ones((int(s) | 1, int(s) | 1), np.uint8))
    f = corpo * m + moldura * np.clip(anel, 0, 1)
    for (p0, p1, k) in riscos:
        camada = np.zeros_like(f)
        cv2.line(camada, tuple(int(v * s * 8) for v in p0), tuple(int(v * s * 8) for v in p1), k, 1, cv2.LINE_AA, shift=3)
        f += cv2.GaussianBlur(camada, (0, 0), 0.6)
    for _ in range(poeira):
        x, y = rng.uniform(5, larg - 5) * s, rng.uniform(5, alt - 5) * s
        cv2.circle(f, (int(x), int(y)), int(rng.integers(1, 3)), 0.35, -1, cv2.LINE_AA)
    if blur:
        pad = int(4 * blur) + 2
        f = cv2.GaussianBlur(np.pad(f, pad), (0, 0), blur); m = cv2.GaussianBlur(np.pad(m, pad), (0, 0), blur)
    return f, m

def colocar(img, f, m, cx, cy, ang, dx=0, dy=0):
    h, w = f.shape
    M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1.0)
    M[:, 2] += [cx - w / 2 + dx, cy - h / 2 + dy]
    fw = cv2.warpAffine(f, M, (W, H)); mw = cv2.warpAffine(m, M, (W, H))
    return img * (1 - mw) + fw

def salvar(nome, img):
    cv2.imwrite(str(saida / nome), np.clip(img * 255 + 0.5, 0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 95])

def riscos_luz(riscos, luz):
    """ra: luz ao longo do eixo longo (y): risco paralelo a y some. rb: ao longo de x."""
    out = []
    for p0, p1, vis in riscos:
        ang = np.arctan2(p1[1] - p0[1], p1[0] - p0[0])
        k = abs(np.cos(ang)) if luz == "ra" else abs(np.sin(ang)) if luz == "rb" else (0.25 if vis else 0)
        out.append((p0, p1, 0.16 * k if luz != "amb" else 0.03 * k))
    return out

APARELHOS = {
    1: dict(modelo="iPhone 13", dims=(71.5, 146.7, 7.65), cor="meia-noite", ang=2.0,
            riscos=[((10, 30), (10, 50), False), ((20, 60), (35, 60), False), ((40, 90), (52, 105), True),
                    ((15, 120), (17, 121.5), False), ((30, 20), (30, 26), False)]),
    2: dict(modelo="iPhone 11", dims=(75.7, 150.9, 8.3), cor="preto", ang=-3.0,
            riscos=[((20, 40), (50, 41), True), ((60, 70), (60, 90), False)]),
}
anot = ["aparelho,modelo,cor,face,tipo,local,tamanho_mm_aprox,visivel_olho_nu,nota_tecnico"]
for n, a in APARELHOS.items():
    larg, alt, esp = a["dims"]
    s = pxmm(esp); cx, cy = 1500, 1500
    for face in ("frente", "traseira"):
        rs = a["riscos"] if face == "frente" else a["riscos"][:1]
        for luz in ("amb", "ra", "rb"):
            img = cena_base(0.04 if luz == "amb" else 0.02)
            f, m = face_mm(larg, alt, 9, s, 0.06, 0.18 if luz == "amb" else 0.3, riscos_luz(rs, luz))
            d = (1.5, -1.0) if luz == "rb" else (0, 0)
            salvar(f"ap{n}_{face}_{luz}.jpg", colocar(img, f, m, cx, cy, a["ang"], *d))
        if face == "frente":
            img = cena_base(0.9); f, m = face_mm(larg, alt, 9, s, 0.02, 0.02)
            salvar(f"ap{n}_frente_sil.jpg", colocar(img, f, m, cx, cy, a["ang"]))
            img = cena_base(0.02); f, m = face_mm(larg, alt, 9, s, 0.06, 0.3, riscos_luz(rs, "ra"), poeira=150)
            salvar(f"ap{n}_sujo_ra.jpg", colocar(img, f, m, cx, cy, a["ang"]))
    for nome, (fl, fa, z, blur) in {"lat_amb": (esp, alt, larg, 3), "lat_ra": (esp, alt, larg, 3),
                                    "foco_lateral": (esp, alt, larg, 3), "foco_ponta": (esp, larg, alt, 7)}.items():
        img = cena_base(0.04); f, m = face_mm(fl, fa, 3, pxmm(z), 0.1, 0.25, blur=blur)
        salvar(f"ap{n}_{nome}.jpg", colocar(img, f, m, cx, cy, a["ang"]))
    for luz in ("amb", "ra"):
        img = cena_base(0.04); f, m = face_mm(larg, alt, 9, s, 0.06, 0.2)
        img = colocar(img, f, m, cx, cy, 0)
        f2, m2 = face_mm(esp * 1.0, alt, 2, s, 0.1, 0.3, blur=1.5)
        salvar(f"ap{n}_espelho_{luz}.jpg", colocar(img, f2, m2, cx + larg * s / 2 + 120, cy, 0))
    for i, (p0, p1, vis) in enumerate(a["riscos"]):
        comp = float(np.hypot(p1[0] - p0[0], p1[1] - p0[1]))
        anot.append(f"ap{n},{a['modelo']},{a['cor']},frente,risco,x{p0[0]} y{p0[1]},{comp:.0f},{'sim' if vis else 'nao'},{'B' if n == 1 else 'C'}")
(saida / "anotacao.csv").write_text("\n".join(anot) + "\n", encoding="utf-8")
print("ok", len(list(saida.glob('*.jpg'))))
