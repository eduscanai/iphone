// Visão no iPhone da cabine: plano Y reduzido e contorno do aparelho com Vision (guia 14.6).
import CabineNucleo
import CoreVideo
import Vision

enum VisaoDispositivo {
    /// Plano Y (luminância) reduzido para `largura` px, mantendo a proporção.
    static func luma(_ buf: CVPixelBuffer, largura alvo: Int) -> QuadroLuma {
        CVPixelBufferLockBaseAddress(buf, .readOnly)
        defer { CVPixelBufferUnlockBaseAddress(buf, .readOnly) }
        let plano = CVPixelBufferIsPlanar(buf) ? 0 : -1
        let w = plano == 0 ? CVPixelBufferGetWidthOfPlane(buf, 0) : CVPixelBufferGetWidth(buf)
        let h = plano == 0 ? CVPixelBufferGetHeightOfPlane(buf, 0) : CVPixelBufferGetHeight(buf)
        let linha = plano == 0 ? CVPixelBufferGetBytesPerRowOfPlane(buf, 0) : CVPixelBufferGetBytesPerRow(buf)
        guard let base = (plano == 0 ? CVPixelBufferGetBaseAddressOfPlane(buf, 0) : CVPixelBufferGetBaseAddress(buf)) else {
            return QuadroLuma(largura: 1, altura: 1, pixels: [0])
        }
        let bytesPorPixel = plano == 0 ? 1 : 4  // BGRA no preview da foto: usa o canal verde
        let src = base.assumingMemoryBound(to: UInt8.self)
        let escala = max(1, w / alvo)
        let ow = w / escala, oh = h / escala
        var px = [UInt8](repeating: 0, count: ow * oh)
        for y in 0..<oh {
            let ys = y * escala
            for x in 0..<ow {
                px[y * ow + x] = src[ys * linha + x * escala * bytesPorPixel + (bytesPorPixel == 4 ? 1 : 0)]
            }
        }
        return QuadroLuma(largura: ow, altura: oh, pixels: px)
    }

    /// Retângulo do aparelho (coordenadas normalizadas, origem no canto superior esquerdo), com a
    /// proporção esperada ± 10%. Faixas finas (laterais em pé) podem falhar: VERIFICAR na fase 2.
    static func aparelho(_ buf: CVPixelBuffer, proporcao: Double, regiao: CGRect? = nil) -> Quadrilatero? {
        let pedido = VNDetectRectanglesRequest()
        pedido.maximumObservations = 3
        pedido.minimumAspectRatio = VNAspectRatio(max(0.05, 1 / (proporcao * 1.1)))
        pedido.maximumAspectRatio = VNAspectRatio(min(1, 1 / (proporcao * 0.9)))
        pedido.minimumConfidence = 0.6
        pedido.quadratureTolerance = 15
        if let regiao { pedido.regionOfInterest = regiao }
        try? VNImageRequestHandler(cvPixelBuffer: buf, orientation: .up).perform([pedido])
        guard let r = pedido.results?.max(by: { $0.boundingBox.width * $0.boundingBox.height < $1.boundingBox.width * $1.boundingBox.height })
        else { return nil }
        // Vision usa origem embaixo à esquerda
        return Quadrilatero([r.topLeft, r.topRight, r.bottomRight, r.bottomLeft].map { (Double($0.x), 1 - Double($0.y)) })
    }
}
