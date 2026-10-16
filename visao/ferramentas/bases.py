"""Bases públicas permitidas (guia 18.2) e unificação de classes para o enum TipoDefeito.
Usado por baixar_bases.py. Licença conferida na página: VERIFICAR na data do download."""

# situacao: "usar" (licença comercial ok, com atribuição) | "conferir" (licença não confirmada)
BASES = {
    "mobile-damage-diagnosis": {
        "nome": "Mobile Damage Diagnosis",
        "url": "https://universe.roboflow.com/abhinavpoc/mobile-damage-diagnosis",
        "workspace": "abhinavpoc", "projeto": "mobile-damage-diagnosis",
        "licenca": "CC BY 4.0", "situacao": "usar",
        "classes": {"crack": "trinca", "scratch": "risco", "dent": "amassado", "dead pixel": None},
    },
    "smartphone-crack": {
        "nome": "Smartphone crack",
        "url": "VERIFICAR (Roboflow Universe)", "workspace": None, "projeto": None,
        "licenca": "CC BY 4.0", "situacao": "usar",
        "classes": {"crack": "trinca"},
    },
    "mobile-phone-defects-3": {
        "nome": "Mobile phone defects 3",
        "url": "VERIFICAR", "workspace": None, "projeto": None,
        "licenca": "conferir na página", "situacao": "conferir",
        "classes": {"scratch": "risco", "stain": "mancha", "oil": None},
    },
    "glass-defect-detection": {
        "nome": "Glass defect detection / Crackedscreen / Scratches-and-dents",
        "url": "VERIFICAR", "workspace": None, "projeto": None,
        "licenca": "conferir na página", "situacao": "conferir",
        "classes": {"chipping": "lascado", "broken": "trinca", "shatter": "trinca", "bubble": None, "dislocation": None},
    },
}

# Nunca usar (guia 18.2): GPL ou não comercial
PROIBIDAS = {"MSD": "GPL-3.0", "SSGD": "não comercial", "MVTec AD": "não comercial", "CarDD": "não comercial",
             "AI4Manufacturing 188": "não comercial"}

CLASSES_DESTINO = ["risco", "trinca", "lascado", "amassado", "descascado", "desgaste", "mancha"]


def mapear_classe(base: str, classe: str) -> str | None:
    """Classe da base → TipoDefeito (None = descartar a anotação)."""
    c = classe.strip().lower()
    mapa = BASES[base]["classes"]
    if c not in mapa:
        raise KeyError(f"Classe '{classe}' da base {base} sem mapeamento: decidir e registrar em bases.py")
    return mapa[c]
