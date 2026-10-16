// Estabilidade antes de disparar (guia 14.6): imagem parada por 500 ms, aparelho presente e
// sem mão na cena. Limiares são pontos de partida: calibrar na fase 2.
import Foundation

public struct DetectorEstabilidade: Sendable {
    /// Diferença absoluta média entre quadros consecutivos (níveis de cinza) abaixo da qual a
    /// imagem conta como parada. Guia 14.6: ponto de partida 1,5.
    public var limiarMovimento: Double = 1.5
    /// Tempo seguido parado para disparar.
    public var tempoParado: TimeInterval = 0.5
    /// Diferença média, fora do aparelho, em relação ao berço vazio: acima disso há mão na cena.
    public var limiarMao: Double = 8.0

    private var anterior: QuadroLuma?
    private var paradoDesde: TimeInterval?

    public init() {}

    public static func diferencaMedia(_ a: QuadroLuma, _ b: QuadroLuma, ignorar: Quadrilatero? = nil) -> Double {
        precondition(a.largura == b.largura && a.altura == b.altura)
        var soma = 0, n = 0
        for y in 0..<a.altura {
            for x in 0..<a.largura {
                if let q = ignorar, q.contem(Double(x) + 0.5, Double(y) + 0.5, largura: a.largura, altura: a.altura) { continue }
                soma += abs(Int(a[x, y]) - Int(b[x, y]))
                n += 1
            }
        }
        return n > 0 ? Double(soma) / Double(n) : 0
    }

    /// Mão (ou outro objeto) na cena: o berço fora do aparelho difere da referência vazia.
    public func maoNaCena(_ quadro: QuadroLuma, bercoVazio: QuadroLuma, aparelho: Quadrilatero?) -> Bool {
        Self.diferencaMedia(quadro, bercoVazio, ignorar: aparelho) > limiarMao
    }

    /// Alimenta um quadro; devolve true quando pode disparar.
    public mutating func alimentar(_ quadro: QuadroLuma, em t: TimeInterval, aparelhoPresente: Bool, maoNaCena: Bool) -> Bool {
        defer { anterior = quadro }
        guard aparelhoPresente, !maoNaCena, let ant = anterior, ant.largura == quadro.largura, ant.altura == quadro.altura else {
            paradoDesde = nil
            return false
        }
        if Self.diferencaMedia(ant, quadro) < limiarMovimento {
            if paradoDesde == nil { paradoDesde = t }
            return t - paradoDesde! >= tempoParado
        }
        paradoDesde = nil
        return false
    }

    public mutating func reiniciar() {
        anterior = nil
        paradoDesde = nil
    }
}
