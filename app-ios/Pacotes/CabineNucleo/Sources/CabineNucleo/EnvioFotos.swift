// Fila de envio persistida em disco (guia 10.3 passo 8 e R19): cada foto sobe durante a
// captura, com Idempotency-Key própria; sem rede, fica na fila e sobe quando a rede volta.
import Foundation

public struct ItemEnvio: Codable, Equatable, Sendable {
    public var id: String
    public var idempotencyKey: String
    public var token: String
    public var passo: Int
    public var face: Face
    public var luz: Luz
    public var pose: Pose
    public var lado: String?
    public var tentativa: Int
    public var metadados: MetadadosFoto
    public var criadoEm: Date

    public init(token: String, passo: Int, face: Face, luz: Luz, pose: Pose, lado: String?, tentativa: Int,
                metadados: MetadadosFoto, criadoEm: Date = Date()) {
        id = UUID().uuidString
        idempotencyKey = UUID().uuidString
        self.token = token; self.passo = passo; self.face = face; self.luz = luz; self.pose = pose; self.lado = lado
        self.tentativa = tentativa; self.metadados = metadados; self.criadoEm = criadoEm
    }
}

public actor FilaEnvio {
    public let pasta: URL
    private let api: APICabine
    private var falhasSeguidas = 0
    public private(set) var ultimoErro: String?

    public init(pasta: URL, api: APICabine) throws {
        self.pasta = pasta
        self.api = api
        try FileManager.default.createDirectory(at: pasta, withIntermediateDirectories: true)
    }

    private func arquivos(_ id: String) -> (dados: URL, item: URL) {
        (pasta.appendingPathComponent("\(id).foto"), pasta.appendingPathComponent("\(id).json"))
    }

    /// Grava a foto e os metadados (atômico: o JSON só aparece depois da foto).
    public func enfileirar(_ item: ItemEnvio, dados: Data) throws {
        let a = arquivos(item.id)
        try dados.write(to: a.dados, options: .atomic)
        let enc = JSONEncoder()
        enc.dateEncodingStrategy = .iso8601
        try enc.encode(item).write(to: a.item, options: .atomic)
    }

    public func pendentes() -> [ItemEnvio] {
        let dec = JSONDecoder()
        dec.dateDecodingStrategy = .iso8601
        let urls = (try? FileManager.default.contentsOfDirectory(at: pasta, includingPropertiesForKeys: nil)) ?? []
        return urls.filter { $0.pathExtension == "json" }
            .compactMap { try? dec.decode(ItemEnvio.self, from: Data(contentsOf: $0)) }
            .sorted { $0.criadoEm < $1.criadoEm }
    }

    public var quantidade: Int { pendentes().count }

    /// Envia o que der, em ordem. Devolve quantos subiram. Na falha, para e espera (backoff).
    @discardableResult
    public func enviarPendentes() async -> Int {
        var enviados = 0
        for item in pendentes() {
            let a = arquivos(item.id)
            guard let dados = try? Data(contentsOf: a.dados) else {
                try? FileManager.default.removeItem(at: a.item)
                continue
            }
            do {
                _ = try await api.enviarFoto(item, dados: dados)
                try? FileManager.default.removeItem(at: a.item)
                try? FileManager.default.removeItem(at: a.dados)
                enviados += 1
                falhasSeguidas = 0
                ultimoErro = nil
            } catch ErroAPI.http(let status, let msg) where (400..<500).contains(status) && status != 408 && status != 429 {
                // erro do pedido (não da rede): reenviar não resolve; tira da fila e registra
                ultimoErro = "Foto recusada (\(status)): \(msg)"
                try? FileManager.default.removeItem(at: a.item)
                try? FileManager.default.removeItem(at: a.dados)
            } catch {
                falhasSeguidas += 1
                ultimoErro = String(describing: error)
                break
            }
        }
        return enviados
    }

    /// Espera antes da próxima tentativa: 1, 2, 4… até 30 s.
    public var espera: TimeInterval { falhasSeguidas == 0 ? 0 : min(30, pow(2, Double(falhasSeguidas - 1))) }
}
