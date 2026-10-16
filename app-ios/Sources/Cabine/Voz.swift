// Voz curta em pt-BR (opcional, guia 10.3 passo 5).
@preconcurrency import AVFoundation

final class Voz {
    private let sintetizador = AVSpeechSynthesizer()
    var ligada = true

    func falar(_ texto: String) {
        guard ligada, !texto.isEmpty else { return }
        sintetizador.stopSpeaking(at: .word)
        let u = AVSpeechUtterance(string: texto)
        u.voice = AVSpeechSynthesisVoice(language: "pt-BR")
        u.rate = 0.55
        sintetizador.speak(u)
    }
}
