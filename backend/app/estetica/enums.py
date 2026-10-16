"""Enumerações dos contratos (guia, seção 7.1). Mudou aqui → mudar o guia, o design.md
e os dois lados do contrato no mesmo trabalho."""

from enum import StrEnum


class Face(StrEnum):
    frente = "frente"
    traseira = "traseira"
    lat_esq = "lat_esq"  # lado dos botões de volume
    lat_dir = "lat_dir"  # lado do botão lateral
    topo = "topo"
    base = "base"  # lado do conector


class Luz(StrEnum):
    ambiente = "ambiente"
    rasante_a = "rasante_a"  # barra paralela ao lado comprido do berço
    rasante_b = "rasante_b"  # barra paralela ao lado curto
    rasante_ab = "rasante_ab"
    contraluz = "contraluz"


class Pose(StrEnum):
    deitado = "deitado"
    lateral = "lateral"
    ponta = "ponta"


class Lado(StrEnum):
    tela_cima = "tela_cima"
    tela_baixo = "tela_baixo"


class TipoDefeito(StrEnum):
    risco = "risco"
    trinca = "trinca"
    lascado = "lascado"
    amassado = "amassado"
    descascado = "descascado"
    desgaste = "desgaste"
    mancha = "mancha"
    anomalia = "anomalia"


class Zona(StrEnum):
    tela = "tela"
    recorte_tela = "recorte_tela"  # notch ou Dynamic Island
    vidro_traseiro = "vidro_traseiro"
    ilha_camera = "ilha_camera"
    lente_camera = "lente_camera"
    moldura = "moldura"
    quina = "quina"
    botao = "botao"
    porta = "porta"


class Visibilidade(StrEnum):
    visivel = "visivel"
    so_rasante = "so_rasante"


class OrigemDefeito(StrEnum):
    maquina = "maquina"
    tecnico = "tecnico"


class EstadoDefeito(StrEnum):
    proposto = "proposto"
    confirmado = "confirmado"
    rejeitado = "rejeitado"


class OrigemNota(StrEnum):
    tecnico = "tecnico"
    sugerida = "sugerida"
    automatica = "automatica"


class Nota(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class ModoEstetica(StrEnum):
    desligado = "desligado"
    assistido = "assistido"
    automatico = "automatico"


class StatusSessaoEstetica(StrEnum):
    capturando = "capturando"
    processando = "processando"
    aguardando_tecnico = "aguardando_tecnico"
    avaliada = "avaliada"
    erro = "erro"


class TipoTarefa(StrEnum):
    foto = "foto"
    fusao = "fusao"


class StatusTarefa(StrEnum):
    pendente = "pendente"
    reservada = "reservada"
    concluida = "concluida"
    falhou = "falhou"


ORDEM_NOTA = {Nota.A: 0, Nota.B: 1, Nota.C: 2, Nota.D: 3}


def pior(*notas: Nota) -> Nota:
    return max(notas, key=ORDEM_NOTA.__getitem__)
