// Contratos da API da cabine (guia 7.3) e do perfil de calibração (7.11).
import Foundation

public enum Luz: String, Codable, CaseIterable, Sendable {
    case ambiente, rasante_a, rasante_b, rasante_ab, contraluz
}

public enum Face: String, Codable, CaseIterable, Sendable {
    case frente, traseira, lat_esq, lat_dir, topo, base

    public var nome: String {
        switch self {
        case .frente: "Frente"
        case .traseira: "Traseira"
        case .lat_esq: "Lateral esquerda"
        case .lat_dir: "Lateral direita"
        case .topo: "Topo"
        case .base: "Base"
        }
    }
}

public enum Pose: String, Codable, Sendable { case deitado, lateral, ponta }

public struct Passo: Codable, Equatable, Sendable {
    public var ordem: Int
    public var pose: Pose
    public var lado: String?
    public var faces: [Face]
    public var luzes: [Luz]
    public var instrucao: String

    public init(ordem: Int, pose: Pose, lado: String?, faces: [Face], luzes: [Luz], instrucao: String) {
        self.ordem = ordem; self.pose = pose; self.lado = lado; self.faces = faces; self.luzes = luzes; self.instrucao = instrucao
    }

    public var facePrincipal: Face { faces[0] }
}

public struct Roteiro: Codable, Equatable, Sendable {
    public var versao: String
    public var passos: [Passo]
    public init(versao: String, passos: [Passo]) { self.versao = versao; self.passos = passos }
    public var totalFotos: Int { passos.reduce(0) { $0 + $1.luzes.count } }
}

public struct Dimensoes: Codable, Equatable, Sendable {
    public var largura: Double
    public var altura: Double
    public var espessura: Double
}

public struct Aparelho: Codable, Equatable, Sendable {
    public var identificador: String
    public var nome: String
    public var cor: String?
    public var tela: String
    public var dimensoes_mm: Dimensoes
}

public struct RespostaAbrir: Codable, Equatable, Sendable {
    public var sessao_id: String
    public var aparelho: Aparelho
    public var roteiro: Roteiro
    public var mostrar_sugestao: Bool
}

public struct Sugestao: Codable, Equatable, Sendable {
    public var status: String  // pendente, processando, pronta, erro
    public var mostrar: Bool
    public var nota_final: String?
    public var notas_por_face: [String: String]?
    public var resumo: [String]?
    public var refazer: [Face]?

    public init(status: String, mostrar: Bool, nota_final: String? = nil, notas_por_face: [String: String]? = nil,
                resumo: [String]? = nil, refazer: [Face]? = nil) {
        self.status = status; self.mostrar = mostrar; self.nota_final = nota_final
        self.notas_por_face = notas_por_face; self.resumo = resumo; self.refazer = refazer
    }
}

public struct Exposicao: Codable, Equatable, Sendable {
    public var duracao_s: Double
    public var iso: Double
    public init(duracao_s: Double, iso: Double) { self.duracao_s = duracao_s; self.iso = iso }
}

public struct GanhosBalanco: Codable, Equatable, Sendable {
    public var r: Double, g: Double, b: Double
    public init(r: Double, g: Double, b: Double) { self.r = r; self.g = g; self.b = b }
}

/// Perfil de calibração (guia 7.11). Refazer sempre que a cabine for mexida.
public struct PerfilCamera: Codable, Equatable, Sendable {
    public var versao: Int
    public var criado_em: Date
    public var camera_modelo: String
    public var dimensoes_px: [String: Int]
    public var exposicao: [String: Exposicao]  // ambiente, rasante, contraluz
    public var balanco_branco: GanhosBalanco
    public var foco: [String: Double]  // por pose: lensPosition
    public var px_por_mm_berco: Double?
    public var orientacao: [String: String]  // pose → topo_para_cima…
    public var regiao_berco_px: [Int]?
    public var regioes_espelho_px: [String: [[Double]]]?

    public init(versao: Int, criado_em: Date, camera_modelo: String, dimensoes_px: [String: Int],
                exposicao: [String: Exposicao], balanco_branco: GanhosBalanco, foco: [String: Double],
                px_por_mm_berco: Double?, orientacao: [String: String], regiao_berco_px: [Int]? = nil,
                regioes_espelho_px: [String: [[Double]]]? = nil) {
        self.versao = versao; self.criado_em = criado_em; self.camera_modelo = camera_modelo
        self.dimensoes_px = dimensoes_px; self.exposicao = exposicao; self.balanco_branco = balanco_branco
        self.foco = foco; self.px_por_mm_berco = px_por_mm_berco; self.orientacao = orientacao
        self.regiao_berco_px = regiao_berco_px; self.regioes_espelho_px = regioes_espelho_px
    }

    public func exposicao(para luz: Luz) -> Exposicao? {
        switch luz {
        case .ambiente: exposicao["ambiente"]
        case .rasante_a, .rasante_b, .rasante_ab: exposicao["rasante"]
        case .contraluz: exposicao["contraluz"]
        }
    }
}

/// Metadados enviados com cada foto (guia 7.3).
public struct MetadadosFoto: Codable, Equatable, Sendable {
    public struct Camera: Codable, Equatable, Sendable {
        public var modelo: String; public var lente: String; public var app_versao: String
        public init(modelo: String, lente: String, app_versao: String) { self.modelo = modelo; self.lente = lente; self.app_versao = app_versao }
    }
    public struct Foco: Codable, Equatable, Sendable {
        public var lens_position: Double
        public init(lens_position: Double) { self.lens_position = lens_position }
    }
    public struct Qualidade: Codable, Equatable, Sendable {
        public var nitidez: Double; public var estouro_pct: Double; public var contorno_ok: Bool
        public init(nitidez: Double, estouro_pct: Double, contorno_ok: Bool) {
            self.nitidez = nitidez; self.estouro_pct = estouro_pct; self.contorno_ok = contorno_ok
        }
    }
    public var camera: Camera
    public var exposicao: Exposicao
    public var foco: Foco
    public var balanco_branco: GanhosBalanco
    public var dimensoes_px: [String: Int]
    public var formato: String
    public var rotacao_graus: Int
    public var perfil_calibracao_versao: Int
    public var capturada_em: String
    public var qualidade_local: Qualidade?

    public init(camera: Camera, exposicao: Exposicao, foco: Foco, balanco_branco: GanhosBalanco, dimensoes_px: [String: Int],
                formato: String, rotacao_graus: Int, perfil_calibracao_versao: Int, capturada_em: String, qualidade_local: Qualidade?) {
        self.camera = camera; self.exposicao = exposicao; self.foco = foco; self.balanco_branco = balanco_branco
        self.dimensoes_px = dimensoes_px; self.formato = formato; self.rotacao_graus = rotacao_graus
        self.perfil_calibracao_versao = perfil_calibracao_versao; self.capturada_em = capturada_em; self.qualidade_local = qualidade_local
    }
}
