// Quadro em tons de cinza (plano Y), pequeno: ~320×240 para estabilidade, 1024×768 para qualidade.
import Foundation

public struct QuadroLuma: Sendable {
    public let largura: Int
    public let altura: Int
    public let pixels: [UInt8]

    public init(largura: Int, altura: Int, pixels: [UInt8]) {
        precondition(pixels.count == largura * altura, "tamanho do quadro não confere")
        self.largura = largura; self.altura = altura; self.pixels = pixels
    }

    @inline(__always) public subscript(x: Int, y: Int) -> UInt8 { pixels[y * largura + x] }
}

/// Quadrilátero em coordenadas normalizadas (0…1) do quadro, na ordem do contorno.
public struct Quadrilatero: Equatable, Sendable {
    public var pontos: [(Double, Double)]
    public init(_ pontos: [(Double, Double)]) { self.pontos = pontos }

    public static func == (a: Quadrilatero, b: Quadrilatero) -> Bool {
        zip(a.pontos, b.pontos).allSatisfy { $0.0 == $1.0 && $0.1 == $1.1 } && a.pontos.count == b.pontos.count
    }

    /// Ponto dentro (regra do número de cruzamentos), em px do quadro.
    func contem(_ x: Double, _ y: Double, largura: Int, altura: Int) -> Bool {
        var dentro = false
        let p = pontos.map { ($0.0 * Double(largura), $0.1 * Double(altura)) }
        var j = p.count - 1
        for i in 0..<p.count {
            let (xi, yi) = p[i], (xj, yj) = p[j]
            if (yi > y) != (yj > y), x < (xj - xi) * (y - yi) / (yj - yi) + xi { dentro.toggle() }
            j = i
        }
        return dentro
    }

    /// Distância (px) do ponto até a borda mais próxima.
    func distanciaBorda(_ x: Double, _ y: Double, largura: Int, altura: Int) -> Double {
        let p = pontos.map { ($0.0 * Double(largura), $0.1 * Double(altura)) }
        var melhor = Double.infinity
        for i in 0..<p.count {
            let (ax, ay) = p[i], (bx, by) = p[(i + 1) % p.count]
            let dx = bx - ax, dy = by - ay
            let t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / max(dx * dx + dy * dy, 1e-9)))
            melhor = min(melhor, hypot(x - (ax + t * dx), y - (ay + t * dy)))
        }
        return melhor
    }

    /// Proporção lado longo ÷ lado curto, medida em px (coordenadas normalizadas distorcem
    /// num quadro que não é quadrado).
    public func proporcao(largura: Int, altura: Int) -> Double {
        guard pontos.count == 4 else { return 0 }
        let p = pontos.map { ($0.0 * Double(largura), $0.1 * Double(altura)) }
        let l = (0..<4).map { i in hypot(p[(i + 1) % 4].0 - p[i].0, p[(i + 1) % 4].1 - p[i].1) }
        let a = (l[0] + l[2]) / 2, b = (l[1] + l[3]) / 2
        return max(a, b) / max(min(a, b), 1e-9)
    }
}
