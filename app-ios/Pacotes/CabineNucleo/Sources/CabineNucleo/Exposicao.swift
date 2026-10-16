// Exposição travada (guia 14.3 e R17): tempo múltiplo de 1/120 s (rede de 60 Hz: as lâmpadas
// oscilam a 120 Hz) e ISO ajustado para manter o brilho da exposição automática.
import Foundation

public enum CalculoExposicao {
    public static let periodoRede: Double = 1.0 / 120.0

    /// Arredonda a duração para o múltiplo de 1/120 s mais próximo (mínimo 1/120 s).
    public static func duracaoSemFaixas(_ duracao: Double) -> Double {
        max(1, (duracao / periodoRede).rounded()) * periodoRede
    }

    /// `iso_novo = iso_auto × duração_auto ÷ duração_alvo`, limitado ao minISO…maxISO do formato.
    public static func iso(paraDuracao alvo: Double, isoAuto: Double, duracaoAuto: Double,
                           faixa: ClosedRange<Double>) -> Double {
        min(max(isoAuto * duracaoAuto / alvo, faixa.lowerBound), faixa.upperBound)
    }
}
