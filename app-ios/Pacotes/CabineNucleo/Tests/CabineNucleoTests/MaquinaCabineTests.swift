import XCTest
@testable import CabineNucleo

final class MaquinaCabineTests: XCTestCase {
    /// Aplica eventos em sequência, guardando os efeitos.
    func rodar(_ inicio: EstadoCabine, _ eventos: [EventoCabine]) -> (EstadoCabine, [EfeitoCabine]) {
        var e = inicio, todos: [EfeitoCabine] = []
        for ev in eventos {
            let (novo, ef) = MaquinaCabine.transicao(e, ev)
            e = novo
            todos += ef
        }
        return (e, todos)
    }

    let abrir: [EventoCabine] = [.qrLido("tk"), .sessaoAberta(abertura), .telaApagada]

    func testFluxoCompletoAteResultado() {
        var eventos = abrir
        for _ in 0..<2 {  // dois passos
            eventos += [.tecnicoPronto, .estavel, .fotoCapturada(ok: true), .fotoCapturada(ok: true), .fotoCapturada(ok: true)]
        }
        let (e, ef) = rodar(.aguardandoQR, eventos)
        guard case .concluindo(let c) = e else { return XCTFail("estado \(e)") }
        XCTAssertEqual(c.fotosEnfileiradas, 6)
        XCTAssertEqual(ef.filter { if case .capturar = $0 { true } else { false } }.count, 6)
        XCTAssertTrue(ef.contains(.pedirTela(token: "tk", acao: "preto")))
        XCTAssertTrue(ef.contains(.concluir(token: "tk", fotos: 6)))
        XCTAssertEqual(ef.compactMap { if case .acenderLuz(let l) = $0 { l } else { nil } }, luzes3 + luzes3)

        let (f, ef2) = rodar(e, [.conclusaoAceita, .sugestao(Sugestao(status: "processando", mostrar: false)),
                                 .sugestao(Sugestao(status: "pronta", mostrar: true, nota_final: "B"))])
        guard case .resultado(_, let s) = f else { return XCTFail("estado \(f)") }
        XCTAssertEqual(s.nota_final, "B")
        XCTAssertTrue(ef2.contains(.pedirTela(token: "tk", acao: "normal")))
        XCTAssertEqual(rodar(f, [.proximoAparelho]).0, .aguardandoQR)
    }

    func testFotoReprovadaRepeteOPassoEPedeAjudaNaTerceira() {
        let (e1, _) = rodar(.aguardandoQR, abrir + [.tecnicoPronto, .estavel, .fotoCapturada(ok: true), .fotoCapturada(ok: false)])
        guard case .aguardandoEstabilidade(let c) = e1 else { return XCTFail("\(e1)") }
        XCTAssertEqual(c.luz, 0, "repete o passo desde a luz ambiente")
        let (e3, ef) = rodar(e1, [.estavel, .fotoCapturada(ok: false), .estavel, .fotoCapturada(ok: false)])
        guard case .pausado(.precisaAjuda, let retomar) = e3 else { return XCTFail("\(e3)") }
        XCTAssertTrue(ef.contains(.desligarLuzes))
        guard case .posicionar = retomar else { return XCTFail("\(retomar)") }
    }

    func testLuzSemRespostaPausaERetoma() {
        let (e, _) = rodar(.aguardandoQR, abrir + [.tecnicoPronto, .estavel, .luzFalhou])
        guard case .pausado(.luzSemResposta, _) = e else { return XCTFail("\(e)") }
        let (r, _) = rodar(e, [.retomar])
        guard case .aguardandoEstabilidade = r else { return XCTFail("\(r)") }
    }

    func testTemperaturaCriticaPausa() {
        let (e, _) = rodar(.aguardandoQR, abrir + [.tecnicoPronto, .temperaturaCritica])
        guard case .pausado(.temperaturaAlta, _) = e else { return XCTFail("\(e)") }
    }

    func testConclusaoRecusadaVoltaAoPassoQueFalta() {
        var eventos = abrir
        for _ in 0..<2 { eventos += [.tecnicoPronto, .estavel] + Array(repeating: EventoCabine.fotoCapturada(ok: true), count: 3) }
        let (e, _) = rodar(.aguardandoQR, eventos + [.conclusaoRecusada(faltando: [2])])
        guard case .posicionar(let c) = e else { return XCTFail("\(e)") }
        XCTAssertEqual(c.passoAtual.ordem, 2)
    }

    func testRefazerSoAsFacesPedidas() {
        let res = EstadoCabine.resultado(Captura(token: "tk", abertura: abertura), Sugestao(status: "pronta", mostrar: true, refazer: [.traseira]))
        let (e, ef) = rodar(res, [.refazerFaces([.traseira])])
        guard case .apagandoTela(let c) = e else { return XCTFail("\(e)") }
        XCTAssertEqual(c.passosPendentes, [1])
        XCTAssertEqual(c.passoAtual.ordem, 2)
        XCTAssertTrue(ef.contains(.pedirTela(token: "tk", acao: "preto")))
    }

    func testEventoForaDeHoraEIgnorado() {
        XCTAssertEqual(MaquinaCabine.transicao(.aguardandoQR, .estavel).0, .aguardandoQR)
        XCTAssertEqual(MaquinaCabine.transicao(.naoPareado, .qrLido("x")).0, .naoPareado)
    }
}
