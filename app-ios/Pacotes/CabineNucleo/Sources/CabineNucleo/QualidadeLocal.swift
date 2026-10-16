// Qualidade local da foto, no preview de ~1024 px (guia 14.6). Os mesmos critérios rodam no
// servidor em resolução total (visao/pipeline.py); estes são pontos de partida a calibrar na fase 2.
import Foundation

public enum QualidadeLocal {
    /// Nitidez normalizada na faixa da borda do aparelho (Laplaciano ÷ energia do gradiente × 100).
    /// Igual ao servidor: a tela apagada é lisa, então a nitidez é medida no contorno.
    /// Sintético: nítida 6–9,5; borrada (σ ≥ 0,7 px) ≤ 3,3.
    public static let limiarNitidez = 4.5
    /// Pixels ≥ 250 dentro do aparelho (%): guia 14.6.
    public static let estouroMaxAmbiente = 0.5
    public static let estouroMaxRasante = 2.0
    /// Proporção do contorno: ± 10% da esperada (guia 14.6).
    public static let toleranciaProporcao = 0.10
    /// Luminância média da tela (0–255) acima disso = tela acesa (só frente, luz ambiente).
    public static let limiarTelaAcesa = 90.0
    /// Faixa da borda usada na nitidez, em px do preview.
    public static let faixaBordaPx = 4.0

    public struct Resultado: Equatable, Sendable {
        public var ok: Bool
        public var motivo: String?
        public var nitidez: Double
        public var estouroPct: Double
        public var contornoOk: Bool
    }

    public static func avaliar(_ q: QuadroLuma, aparelho: Quadrilatero?, proporcaoEsperada: Double, luz: Luz,
                               exigirTelaApagada: Bool) -> Resultado {
        guard let ap = aparelho, abs(ap.proporcao(largura: q.largura, altura: q.altura) / proporcaoEsperada - 1) <= toleranciaProporcao else {
            return Resultado(ok: false, motivo: "contorno não encontrado", nitidez: 0, estouroPct: 0, contornoOk: false)
        }
        var somaLap = 0.0, somaLap2 = 0.0, somaGrad = 0.0, nBorda = 0
        var estourados = 0, nDentro = 0, somaDentro = 0.0
        for y in 1..<(q.altura - 1) {
            for x in 1..<(q.largura - 1) {
                let fx = Double(x) + 0.5, fy = Double(y) + 0.5
                let dentro = ap.contem(fx, fy, largura: q.largura, altura: q.altura)
                if dentro {
                    nDentro += 1
                    let v = q[x, y]
                    somaDentro += Double(v)
                    if v >= 250 { estourados += 1 }
                }
                if ap.distanciaBorda(fx, fy, largura: q.largura, altura: q.altura) <= faixaBordaPx {
                    let c = Double(q[x, y])
                    let lap = Double(q[x - 1, y]) + Double(q[x + 1, y]) + Double(q[x, y - 1]) + Double(q[x, y + 1]) - 4 * c
                    let gx = (Double(q[x + 1, y]) - Double(q[x - 1, y])) / 2
                    let gy = (Double(q[x, y + 1]) - Double(q[x, y - 1])) / 2
                    somaLap += lap; somaLap2 += lap * lap; somaGrad += gx * gx + gy * gy
                    nBorda += 1
                }
            }
        }
        let media = nBorda > 0 ? somaLap / Double(nBorda) : 0
        let variancia = nBorda > 0 ? somaLap2 / Double(nBorda) - media * media : 0
        // Sobel 3×3 (servidor) = 8 × diferença central → energia 64×: dividir por 64 para casar com o servidor
        let nitidez = variancia / (somaGrad / Double(max(nBorda, 1)) * 64 + 1e-6) * 100
        let estouro = nDentro > 0 ? Double(estourados) / Double(nDentro) * 100 : 0
        let limiteEstouro = luz == .ambiente ? estouroMaxAmbiente : (luz == .contraluz ? 100 : estouroMaxRasante)
        var r = Resultado(ok: true, motivo: nil, nitidez: nitidez, estouroPct: estouro, contornoOk: true)
        if nitidez < limiarNitidez {
            r.ok = false; r.motivo = "tremida"
        } else if estouro > limiteEstouro {
            r.ok = false; r.motivo = "estourada"
        } else if exigirTelaApagada, luz == .ambiente, nDentro > 0, somaDentro / Double(nDentro) > limiarTelaAcesa {
            r.ok = false; r.motivo = "tela acesa"
        }
        return r
    }
}
