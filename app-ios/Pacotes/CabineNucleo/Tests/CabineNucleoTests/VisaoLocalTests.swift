import XCTest
@testable import CabineNucleo

/// Quadro sintético: aparelho escuro com borda clara num fundo escuro.
func quadroAparelho(largura: Int = 256, altura: Int = 192, borrar: Int = 0, tela: UInt8 = 20, extra: ((inout [UInt8]) -> Void)? = nil) -> (QuadroLuma, Quadrilatero) {
    var p = [UInt8](repeating: 10, count: largura * altura)
    // aparelho em pé: 60×120 px, centro do quadro
    let l0 = 98, l1 = 158, t0 = 36, t1 = 156
    for y in t0..<t1 { for x in l0..<l1 { p[y * largura + x] = (x < l0 + 3 || x >= l1 - 3 || y < t0 + 3 || y >= t1 - 3) ? 120 : tela } }
    extra?(&p)
    if borrar > 0 {
        for _ in 0..<borrar {
            var q = p
            for y in 1..<(altura - 1) { for x in 1..<(largura - 1) {
                var s = 0
                for dy in -1...1 { for dx in -1...1 { s += Int(p[(y + dy) * largura + x + dx]) } }
                q[y * largura + x] = UInt8(s / 9)
            } }
            p = q
        }
    }
    let quad = Quadrilatero([(Double(l0) / Double(largura), Double(t0) / Double(altura)), (Double(l1) / Double(largura), Double(t0) / Double(altura)),
                             (Double(l1) / Double(largura), Double(t1) / Double(altura)), (Double(l0) / Double(largura), Double(t1) / Double(altura))])
    return (QuadroLuma(largura: largura, altura: altura, pixels: p), quad)
}

final class QualidadeLocalTests: XCTestCase {
    func testNitidaPassaBorradaReprova() {
        let (nitida, q) = quadroAparelho()
        let r = QualidadeLocal.avaliar(nitida, aparelho: q, proporcaoEsperada: 2, luz: .ambiente, exigirTelaApagada: true)
        XCTAssertTrue(r.ok, "\(r)")
        let (borrada, _) = quadroAparelho(borrar: 3)
        let b = QualidadeLocal.avaliar(borrada, aparelho: q, proporcaoEsperada: 2, luz: .ambiente, exigirTelaApagada: true)
        XCTAssertEqual(b.motivo, "tremida", "nitidez \(b.nitidez) × nítida \(r.nitidez)")
    }

    func testTelaAcesaEContorno() {
        let (acesa, q) = quadroAparelho(tela: 200)
        XCTAssertEqual(QualidadeLocal.avaliar(acesa, aparelho: q, proporcaoEsperada: 2, luz: .ambiente, exigirTelaApagada: true).motivo, "tela acesa")
        XCTAssertTrue(QualidadeLocal.avaliar(acesa, aparelho: q, proporcaoEsperada: 2, luz: .ambiente, exigirTelaApagada: false).ok)
        let (n, _) = quadroAparelho()
        XCTAssertEqual(QualidadeLocal.avaliar(n, aparelho: q, proporcaoEsperada: 1.4, luz: .ambiente, exigirTelaApagada: false).motivo, "contorno não encontrado")
        XCTAssertEqual(QualidadeLocal.avaliar(n, aparelho: nil, proporcaoEsperada: 2, luz: .ambiente, exigirTelaApagada: false).contornoOk, false)
    }

    func testEstouroNaRasante() {
        let (q, quad) = quadroAparelho { p in for y in 60..<100 { for x in 110..<140 { p[y * 256 + x] = 255 } } }
        let r = QualidadeLocal.avaliar(q, aparelho: quad, proporcaoEsperada: 2, luz: .rasante_a, exigirTelaApagada: false)
        XCTAssertEqual(r.motivo, "estourada")
        XCTAssertGreaterThan(r.estouroPct, 2)
    }
}

final class DetectorEstabilidadeTests: XCTestCase {
    func testDisparaDepoisDe500msParado() {
        var d = DetectorEstabilidade()
        let (q, _) = quadroAparelho()
        XCTAssertFalse(d.alimentar(q, em: 0, aparelhoPresente: true, maoNaCena: false))
        XCTAssertFalse(d.alimentar(q, em: 0.1, aparelhoPresente: true, maoNaCena: false))
        XCTAssertFalse(d.alimentar(q, em: 0.5, aparelhoPresente: true, maoNaCena: false))
        XCTAssertTrue(d.alimentar(q, em: 0.61, aparelhoPresente: true, maoNaCena: false))
    }

    func testMovimentoMaoEAusenciaReiniciam() {
        var d = DetectorEstabilidade()
        let (q, quad) = quadroAparelho()
        let (mexido, _) = quadroAparelho { p in for i in 0..<p.count where i % 3 == 0 { p[i] = p[i] &+ 40 } }
        _ = d.alimentar(q, em: 0, aparelhoPresente: true, maoNaCena: false)
        _ = d.alimentar(q, em: 0.3, aparelhoPresente: true, maoNaCena: false)
        XCTAssertFalse(d.alimentar(mexido, em: 0.4, aparelhoPresente: true, maoNaCena: false))
        XCTAssertFalse(d.alimentar(mexido, em: 0.8, aparelhoPresente: true, maoNaCena: false), "recomeça a contar")
        XCTAssertFalse(d.alimentar(mexido, em: 2, aparelhoPresente: false, maoNaCena: false))
        XCTAssertFalse(d.alimentar(mexido, em: 3, aparelhoPresente: true, maoNaCena: true))
        // mão: berço fora do aparelho diferente da referência vazia
        let vazio = QuadroLuma(largura: 256, altura: 192, pixels: [UInt8](repeating: 10, count: 256 * 192))
        XCTAssertFalse(d.maoNaCena(q, bercoVazio: vazio, aparelho: quad))
        let (comMao, _) = quadroAparelho { p in for y in 0..<192 { for x in 0..<80 { p[y * 256 + x] = 150 } } }
        XCTAssertTrue(d.maoNaCena(comMao, bercoVazio: vazio, aparelho: quad))
    }
}

final class ExposicaoTests: XCTestCase {
    func testMultiploDe120Hz() {
        XCTAssertEqual(CalculoExposicao.duracaoSemFaixas(1.0 / 50), 2.0 / 120, accuracy: 1e-9)
        XCTAssertEqual(CalculoExposicao.duracaoSemFaixas(1.0 / 1000), 1.0 / 120, accuracy: 1e-9)
        XCTAssertEqual(CalculoExposicao.iso(paraDuracao: 1.0 / 60, isoAuto: 400, duracaoAuto: 1.0 / 120, faixa: 32...3200), 200, accuracy: 1e-6)
        XCTAssertEqual(CalculoExposicao.iso(paraDuracao: 1.0 / 60, isoAuto: 50, duracaoAuto: 1.0 / 240, faixa: 32...3200), 32)
    }
}
