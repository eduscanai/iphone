import XCTest
@testable import CabineNucleo

final class LuzCabineTests: XCTestCase {
    override func setUp() { ProtocoloFalso.pedidos = [] }

    func testMapaDeCanais() {
        XCTAssertEqual(LuzCabine.canais(para: .rasante_ab, temDifusa: false), ["a": 100, "b": 100, "difusa": 0, "contraluz": 0])
        XCTAssertEqual(LuzCabine.canais(para: .ambiente, temDifusa: true)["difusa"], 100)
        XCTAssertEqual(LuzCabine.canais(para: .ambiente, temDifusa: false).values.reduce(0, +), 0)
    }

    func testConfirmaEstadoEMandaChave() async throws {
        ProtocoloFalso.responder = { p in
            let corpo = try JSONSerialization.jsonObject(with: p.httpBody ?? Data()) as? [String: Int] ?? [:]
            return (200, try JSONSerialization.data(withJSONObject: ["canais": corpo, "versao": "1.0.0", "uptime_s": 1]))
        }
        let luz = LuzCabine(base: URL(string: "http://esp32.local")!, chave: "k1", sessao: ProtocoloFalso.sessao())
        try await luz.acender(.rasante_a)
        XCTAssertEqual(ProtocoloFalso.pedidos.last?.value(forHTTPHeaderField: "X-Chave-Cabine"), "k1")
        XCTAssertEqual(ProtocoloFalso.pedidos.last?.url?.path, "/luz")
    }

    func testTresFalhasViramErro() async {
        ProtocoloFalso.responder = { _ in throw URLError(.timedOut) }
        let luz = LuzCabine(base: URL(string: "http://esp32.local")!, chave: "k", sessao: ProtocoloFalso.sessao())
        do { try await luz.acender(.ambiente); XCTFail("devia falhar") } catch {
            XCTAssertEqual(error as? ErroLuz, .semResposta)
        }
        XCTAssertEqual(ProtocoloFalso.pedidos.count, 3)
    }

    func testEstadoDiferenteEChaveInvalida() async {
        ProtocoloFalso.responder = { _ in (200, try JSONSerialization.data(withJSONObject: ["canais": ["a": 0, "b": 0, "difusa": 0, "contraluz": 0]])) }
        let luz = LuzCabine(base: URL(string: "http://esp32.local")!, chave: "k", sessao: ProtocoloFalso.sessao())
        do { try await luz.acender(.rasante_b); XCTFail() } catch { XCTAssertNotNil(error as? ErroLuz) }
        ProtocoloFalso.responder = { _ in (401, Data()) }
        do { try await luz.desligar(); XCTFail() } catch { XCTAssertEqual(error as? ErroLuz, .chaveInvalida) }
    }
}

/// API falsa para a fila: falha nas primeiras N chamadas.
actor APIFalsa: APICabine {
    var falhar: Int
    var recebidas: [String] = []
    var status4xx = false
    init(falhar: Int) { self.falhar = falhar }
    func enviarFoto(_ item: ItemEnvio, dados: Data) async throws -> (fotoID: String, duplicada: Bool) {
        if status4xx { throw ErroAPI.http(422, "luz fora do passo") }
        if falhar > 0 { falhar -= 1; throw URLError(.notConnectedToInternet) }
        recebidas.append(item.idempotencyKey)
        return ("f", false)
    }
    func definir4xx() { status4xx = true }
    func abrir(token: String, refazer: Bool) async throws -> RespostaAbrir { abertura }
    func concluir(token: String, fotosEnviadas: Int) async throws -> [Int] { [] }
    func pedirTela(token: String, acao: String) async throws {}
    func sugestao(token: String) async throws -> Sugestao { Sugestao(status: "pronta", mostrar: true) }
    func salvarPerfil(_ perfil: PerfilCamera) async throws {}
}

final class FilaEnvioTests: XCTestCase {
    func pasta() -> URL { FileManager.default.temporaryDirectory.appendingPathComponent("fila-\(UUID().uuidString)") }

    func testSemRedeGuardaEReenviaEmOrdem() async throws {
        let dir = pasta()
        let api = APIFalsa(falhar: 1)
        let fila = try FilaEnvio(pasta: dir, api: api)
        var chaves: [String] = []
        for (i, luz) in luzes3.enumerated() {
            let item = ItemEnvio(token: "tk", passo: 1, face: .frente, luz: luz, pose: .deitado, lado: nil, tentativa: 1,
                                 metadados: metadadosTeste(), criadoEm: Date(timeIntervalSince1970: Double(i)))
            chaves.append(item.idempotencyKey)
            try await fila.enfileirar(item, dados: Data([0xFF, 0xD8, UInt8(i)]))
        }
        let primeira = await fila.enviarPendentes()
        XCTAssertEqual(primeira, 0)
        let espera = await fila.espera
        XCTAssertEqual(espera, 1)
        // app reiniciado: nova instância lê a mesma pasta
        let fila2 = try FilaEnvio(pasta: dir, api: api)
        let quantas = await fila2.quantidade
        XCTAssertEqual(quantas, 3)
        let enviadas = await fila2.enviarPendentes()
        XCTAssertEqual(enviadas, 3)
        let recebidas = await api.recebidas
        XCTAssertEqual(recebidas, chaves, "mesma Idempotency-Key e mesma ordem")
        let restantes = await fila2.quantidade
        XCTAssertEqual(restantes, 0)
    }

    func testRecusaDoServidorSaiDaFila() async throws {
        let api = APIFalsa(falhar: 0)
        await api.definir4xx()
        let fila = try FilaEnvio(pasta: pasta(), api: api)
        try await fila.enfileirar(ItemEnvio(token: "tk", passo: 1, face: .frente, luz: .ambiente, pose: .deitado, lado: nil,
                                            tentativa: 1, metadados: metadadosTeste()), dados: Data([1]))
        _ = await fila.enviarPendentes()
        let q = await fila.quantidade
        let erro = await fila.ultimoErro
        XCTAssertEqual(q, 0)
        XCTAssertTrue(erro?.contains("422") ?? false)
    }
}

final class ClienteAPITests: XCTestCase {
    func testMultipartTemCamposDoContrato() throws {
        let item = ItemEnvio(token: "tk", passo: 2, face: .traseira, luz: .rasante_b, pose: .deitado, lado: "tela_baixo",
                             tentativa: 1, metadados: metadadosTeste())
        let corpo = String(decoding: try Multipart.corpo(item: item, dados: Data("FOTO".utf8), fronteira: "XX"), as: UTF8.self)
        for trecho in ["name=\"passo\"\r\n\r\n2", "name=\"face\"\r\n\r\ntraseira", "name=\"luz\"\r\n\r\nrasante_b",
                       "name=\"lado\"\r\n\r\ntela_baixo", "\"formato\":\"heic\"", "filename=\"foto.heic\"", "Content-Type: image/heic", "FOTO", "--XX--"] {
            XCTAssertTrue(corpo.contains(trecho), trecho)
        }
    }

    func testConcluirDevolvePassosFaltando() async throws {
        ProtocoloFalso.responder = { _ in (409, Data(#"{"detail":{"mensagem":"Faltam","faltando":[{"passo":2,"luz":"ambiente"},{"passo":2,"luz":"rasante_a"}]}}"#.utf8)) }
        let api = ClienteAPI(base: URL(string: "http://api")!, tokenCabine: "t", sessao: ProtocoloFalso.sessao())
        let faltando = try await api.concluir(token: "tk", fotosEnviadas: 3)
        XCTAssertEqual(faltando, [2])
    }
}
