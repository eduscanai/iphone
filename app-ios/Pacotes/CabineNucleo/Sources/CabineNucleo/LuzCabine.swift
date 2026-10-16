// Cliente HTTP do ESP32 das luzes (guia 7.10 e 14.4): POST /luz e espera a confirmação com o
// estado pedido. Sem resposta em 1 s: tenta de novo; na terceira falha, erro (a cabine pausa).
import Foundation

public enum ErroLuz: Error, Equatable {
    case semResposta
    case estadoDiferente([String: Int])
    case chaveInvalida
}

public protocol ControleLuz: Sendable {
    func acender(_ luz: Luz) async throws
    func desligar() async throws
}

public struct LuzCabine: ControleLuz {
    public let base: URL  // http://morecheck-cabine-1.local ou IP fixo (redes com isolamento de clientes)
    public let chave: String
    public let temDifusa: Bool
    public let sessao: URLSession
    public var tempoLimite: TimeInterval = 1.0
    public var tentativas = 3

    public init(base: URL, chave: String, temDifusa: Bool = false, sessao: URLSession = .shared) {
        self.base = base; self.chave = chave; self.temDifusa = temDifusa; self.sessao = sessao
    }

    /// Mapa luz → canais (7.10). Manda os 4 canais sempre: canal omitido não muda no ESP32.
    public static func canais(para luz: Luz, temDifusa: Bool) -> [String: Int] {
        var c = ["a": 0, "b": 0, "difusa": 0, "contraluz": 0]
        switch luz {
        case .ambiente: if temDifusa { c["difusa"] = 100 }
        case .rasante_a: c["a"] = 100
        case .rasante_b: c["b"] = 100
        case .rasante_ab: c["a"] = 100; c["b"] = 100
        case .contraluz: c["contraluz"] = 100
        }
        return c
    }

    public func acender(_ luz: Luz) async throws {
        try await enviar(caminho: "luz", corpo: Self.canais(para: luz, temDifusa: temDifusa))
    }

    public func desligar() async throws {
        try await enviar(caminho: "desligar", corpo: nil)
    }

    private func enviar(caminho: String, corpo: [String: Int]?) async throws {
        var pedido = URLRequest(url: base.appendingPathComponent(caminho), timeoutInterval: tempoLimite)
        pedido.httpMethod = "POST"
        pedido.setValue(chave, forHTTPHeaderField: "X-Chave-Cabine")
        pedido.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let corpo { pedido.httpBody = try JSONEncoder().encode(corpo) }
        var ultimo: Error = ErroLuz.semResposta
        for _ in 0..<tentativas {
            do {
                let (dados, resposta) = try await sessao.data(for: pedido)
                let status = (resposta as? HTTPURLResponse)?.statusCode ?? 0
                if status == 401 { throw ErroLuz.chaveInvalida }
                guard status == 200 else { ultimo = ErroLuz.semResposta; continue }
                struct Estado: Decodable { let canais: [String: Int] }
                let estado = try JSONDecoder().decode(Estado.self, from: dados).canais
                let esperado = corpo ?? ["a": 0, "b": 0, "difusa": 0, "contraluz": 0]
                guard esperado.allSatisfy({ estado[$0.key] == $0.value }) else { throw ErroLuz.estadoDiferente(estado) }
                return
            } catch let e as ErroLuz where e == .chaveInvalida {
                throw e
            } catch {
                ultimo = error
            }
        }
        throw ultimo is ErroLuz ? ultimo : ErroLuz.semResposta
    }
}
