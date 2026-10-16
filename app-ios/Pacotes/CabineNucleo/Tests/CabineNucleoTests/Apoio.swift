import Foundation
@testable import CabineNucleo

let luzes3: [Luz] = [.ambiente, .rasante_a, .rasante_b]
let roteiroEspelhos = Roteiro(versao: "roteiro-v1", passos: [
    Passo(ordem: 1, pose: .deitado, lado: "tela_cima", faces: [.frente, .lat_esq, .lat_dir, .topo, .base], luzes: luzes3, instrucao: "Tela para cima."),
    Passo(ordem: 2, pose: .deitado, lado: "tela_baixo", faces: [.traseira, .lat_esq, .lat_dir, .topo, .base], luzes: luzes3, instrucao: "Vire."),
])
let abertura = RespostaAbrir(
    sessao_id: "s1",
    aparelho: Aparelho(identificador: "iPhone14,5", nome: "iPhone 13", cor: "meia-noite", tela: "oled",
                       dimensoes_mm: Dimensoes(largura: 71.5, altura: 146.7, espessura: 7.65)),
    roteiro: roteiroEspelhos, mostrar_sugestao: true)

func metadadosTeste(formato: String = "heic") -> MetadadosFoto {
    MetadadosFoto(camera: .init(modelo: "iPhone15,3", lente: "grande_angular_1x", app_versao: "0.1.0"),
                  exposicao: Exposicao(duracao_s: 1 / 60, iso: 125), foco: .init(lens_position: 0.62),
                  balanco_branco: GanhosBalanco(r: 1.9, g: 1, b: 1.7), dimensoes_px: ["largura": 8064, "altura": 6048],
                  formato: formato, rotacao_graus: 0, perfil_calibracao_versao: 3, capturada_em: "2026-10-20T14:03:11-03:00",
                  qualidade_local: .init(nitidez: 8, estouro_pct: 0.02, contorno_ok: true))
}

/// URLProtocol falso: cada teste define como responder.
final class ProtocoloFalso: URLProtocol, @unchecked Sendable {
    nonisolated(unsafe) static var responder: (URLRequest) throws -> (Int, Data) = { _ in (200, Data()) }
    nonisolated(unsafe) static var pedidos: [URLRequest] = []

    static func sessao() -> URLSession {
        let c = URLSessionConfiguration.ephemeral
        c.protocolClasses = [ProtocoloFalso.self]
        return URLSession(configuration: c)
    }

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        var p = request
        if p.httpBody == nil, let s = request.httpBodyStream {
            s.open(); var d = Data(); var buf = [UInt8](repeating: 0, count: 4096)
            while s.hasBytesAvailable { let n = s.read(&buf, maxLength: buf.count); if n <= 0 { break }; d.append(buf, count: n) }
            s.close(); p.httpBody = d
        }
        Self.pedidos.append(p)
        do {
            let (status, dados) = try Self.responder(p)
            client?.urlProtocol(self, didReceive: HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil, headerFields: nil)!, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: dados)
            client?.urlProtocolDidFinishLoading(self)
        } catch {
            client?.urlProtocol(self, didFailWithError: error)
        }
    }
    override func stopLoading() {}
}
