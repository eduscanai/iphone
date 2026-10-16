// Cliente da API da cabine (guia 7.3). Autenticação: token de pareamento (D10) no Keychain.
import Foundation

public enum ErroAPI: Error, Equatable {
    case http(Int, String)
    case resposta
}

public protocol APICabine: Sendable {
    func abrir(token: String, refazer: Bool) async throws -> RespostaAbrir
    func enviarFoto(_ item: ItemEnvio, dados: Data) async throws -> (fotoID: String, duplicada: Bool)
    func concluir(token: String, fotosEnviadas: Int) async throws -> [Int]  // passos faltando (vazio = ok)
    func pedirTela(token: String, acao: String) async throws
    func sugestao(token: String) async throws -> Sugestao
    func salvarPerfil(_ perfil: PerfilCamera) async throws
}

public struct ClienteAPI: APICabine {
    public let base: URL
    public let tokenCabine: String
    public let sessao: URLSession

    public init(base: URL, tokenCabine: String, sessao: URLSession = .shared) {
        self.base = base; self.tokenCabine = tokenCabine; self.sessao = sessao
    }

    /// Ativação (sem token ainda): POST /cabines/ativar com o código lido no QR do painel.
    public static func ativar(base: URL, codigo: String, nome: String, sessao: URLSession = .shared) async throws -> (cabineID: String, token: String) {
        var p = URLRequest(url: base.appendingPathComponent("cabines/ativar"))
        p.httpMethod = "POST"
        p.setValue("application/json", forHTTPHeaderField: "Content-Type")
        p.httpBody = try JSONEncoder().encode(["codigo": codigo, "nome": nome])
        let (d, r) = try await sessao.data(for: p)
        try verificar(r, d)
        struct R: Decodable { let cabine_id: String; let token: String }
        let x = try JSONDecoder().decode(R.self, from: d)
        return (x.cabine_id, x.token)
    }

    private func pedido(_ caminho: String, metodo: String = "GET") -> URLRequest {
        var p = URLRequest(url: URL(string: caminho, relativeTo: base)!)
        p.httpMethod = metodo
        p.setValue("Bearer \(tokenCabine)", forHTTPHeaderField: "Authorization")
        return p
    }

    static func verificar(_ r: URLResponse, _ d: Data) throws {
        let status = (r as? HTTPURLResponse)?.statusCode ?? 0
        guard (200..<300).contains(status) else { throw ErroAPI.http(status, String(decoding: d, as: UTF8.self)) }
    }

    private func json<T: Decodable>(_ p: URLRequest) async throws -> T {
        let (d, r) = try await sessao.data(for: p)
        try Self.verificar(r, d)
        return try JSONDecoder().decode(T.self, from: d)
    }

    private static func caminhoToken(_ token: String) -> String {
        token.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? token
    }

    public func abrir(token: String, refazer: Bool) async throws -> RespostaAbrir {
        try await json(pedido("cabine/\(Self.caminhoToken(token))\(refazer ? "?refazer=1" : "")"))
    }

    public func enviarFoto(_ item: ItemEnvio, dados: Data) async throws -> (fotoID: String, duplicada: Bool) {
        var p = pedido("cabine/\(Self.caminhoToken(item.token))/fotos", metodo: "POST")
        let fronteira = "morecheck-\(item.idempotencyKey)"
        p.setValue("multipart/form-data; boundary=\(fronteira)", forHTTPHeaderField: "Content-Type")
        p.setValue(item.idempotencyKey, forHTTPHeaderField: "Idempotency-Key")
        p.httpBody = try Multipart.corpo(item: item, dados: dados, fronteira: fronteira)
        struct R: Decodable { let foto_id: String; let duplicada: Bool }
        let r: R = try await json(p)
        return (r.foto_id, r.duplicada)
    }

    public func concluir(token: String, fotosEnviadas: Int) async throws -> [Int] {
        var p = pedido("cabine/\(Self.caminhoToken(token))/concluir", metodo: "POST")
        p.setValue("application/json", forHTTPHeaderField: "Content-Type")
        p.httpBody = try JSONEncoder().encode(["fotos_enviadas": fotosEnviadas])
        let (d, r) = try await sessao.data(for: p)
        if (r as? HTTPURLResponse)?.statusCode == 409 {
            struct Falta: Decodable { struct Det: Decodable { struct F: Decodable { let passo: Int }; let faltando: [F] }; let detail: Det }
            if let f = try? JSONDecoder().decode(Falta.self, from: d) { return Array(Set(f.detail.faltando.map(\.passo))).sorted() }
        }
        try Self.verificar(r, d)
        return []
    }

    public func pedirTela(token: String, acao: String) async throws {
        var p = pedido("cabine/\(Self.caminhoToken(token))/tela", metodo: "POST")
        p.setValue("application/json", forHTTPHeaderField: "Content-Type")
        p.httpBody = try JSONEncoder().encode(["acao": acao])
        let (d, r) = try await sessao.data(for: p)
        try Self.verificar(r, d)
    }

    public func sugestao(token: String) async throws -> Sugestao {
        try await json(pedido("cabine/\(Self.caminhoToken(token))/sugestao"))
    }

    public func salvarPerfil(_ perfil: PerfilCamera) async throws {
        var p = pedido("cabine/perfil", metodo: "PUT")
        p.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let enc = JSONEncoder()
        enc.dateEncodingStrategy = .iso8601
        p.httpBody = try enc.encode(perfil)
        let (d, r) = try await sessao.data(for: p)
        try Self.verificar(r, d)
    }
}

public enum Multipart {
    public static func corpo(item: ItemEnvio, dados: Data, fronteira: String) throws -> Data {
        var c = Data()
        func campo(_ nome: String, _ valor: String) {
            c.append("--\(fronteira)\r\nContent-Disposition: form-data; name=\"\(nome)\"\r\n\r\n\(valor)\r\n".data(using: .utf8)!)
        }
        campo("passo", String(item.passo))
        campo("face", item.face.rawValue)
        campo("luz", item.luz.rawValue)
        campo("pose", item.pose.rawValue)
        if let lado = item.lado { campo("lado", lado) }
        campo("tentativa", String(item.tentativa))
        let enc = JSONEncoder()
        enc.outputFormatting = .sortedKeys
        campo("metadados", String(decoding: try enc.encode(item.metadados), as: UTF8.self))
        let ext = item.metadados.formato == "jpeg" ? "jpg" : item.metadados.formato
        let tipo = ["heic": "image/heic", "jpeg": "image/jpeg", "dng": "image/x-adobe-dng"][item.metadados.formato] ?? "application/octet-stream"
        c.append("--\(fronteira)\r\nContent-Disposition: form-data; name=\"arquivo\"; filename=\"foto.\(ext)\"\r\nContent-Type: \(tipo)\r\n\r\n".data(using: .utf8)!)
        c.append(dados)
        c.append("\r\n--\(fronteira)--\r\n".data(using: .utf8)!)
        return c
    }
}
