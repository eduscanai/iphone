// Aparelho avaliado (guia 10.4): QR da sessão em tela cheia; sob comando, tela preta com brilho
// 0 (LCD não fica preto só com preto, R18) e sem barra de status. Eventos por long-poll (7.4).
import CoreImage.CIFilterBuiltins
import SwiftUI

@MainActor
final class EventosSessao: ObservableObject {
    enum Modo { case qr, preto }
    @Published var modo: Modo = .qr
    @Published var semRede = false
    private var seq = 0
    private var tarefa: Task<Void, Never>?

    func iniciar(api: URL, token: String) {
        tarefa?.cancel()
        tarefa = Task { [weak self] in
            while !Task.isCancelled {
                guard let self else { return }
                var c = URLComponents(url: api.appendingPathComponent("pagina/\(token)/eventos"), resolvingAgainstBaseURL: false)!
                c.queryItems = [URLQueryItem(name: "apos", value: String(self.seq))]
                do {
                    var p = URLRequest(url: c.url!)
                    p.timeoutInterval = 35  // long-poll de até 25 s
                    let (d, _) = try await URLSession.shared.data(for: p)
                    struct R: Decodable { struct E: Decodable { let seq: Int; let tipo: String; let dados: [String: String] }; let eventos: [E] }
                    let r = try JSONDecoder().decode(R.self, from: d)
                    self.semRede = false
                    for e in r.eventos {
                        self.seq = max(self.seq, e.seq)
                        if e.tipo == "tela" { self.aplicar(e.dados["acao"] ?? "") }
                    }
                } catch {
                    self.semRede = true
                    try? await Task.sleep(nanoseconds: 2_000_000_000)
                }
            }
        }
    }

    func parar() { tarefa?.cancel() }

    private func aplicar(_ acao: String) {
        switch acao {
        case "preto": modo = .preto
        case "qr", "normal": modo = .qr
        default: break
        }
    }
}

struct TelaQRPreto: View {
    let api: URL
    let token: String
    @StateObject private var eventos = EventosSessao()
    @State private var brilhoAnterior: CGFloat?

    var body: some View {
        ZStack {
            switch eventos.modo {
            case .qr:
                Color.white.ignoresSafeArea()
                VStack(spacing: 16) {
                    Image(uiImage: Self.qr(token)).interpolation(.none).resizable().scaledToFit().padding(24)
                    Text("Estética").font(.title.bold()).foregroundStyle(.black)
                    if eventos.semRede {
                        Text("Sem rede: quando a cabine pedir, trave o aparelho (botão lateral) para apagar a tela.")
                            .multilineTextAlignment(.center).foregroundStyle(.red).padding()
                    }
                }
            case .preto:
                Color.black.ignoresSafeArea()
            }
        }
        .statusBarHidden(eventos.modo == .preto)
        .persistentSystemOverlays(eventos.modo == .preto ? .hidden : .automatic)
        .onChange(of: eventos.modo) { _, modo in modo == .preto ? apagar() : restaurar() }
        .onAppear {
            UIApplication.shared.isIdleTimerDisabled = true
            eventos.iniciar(api: api, token: token)
        }
        .onDisappear {
            eventos.parar()
            restaurar()
            UIApplication.shared.isIdleTimerDisabled = false
        }
    }

    private var tela: UIScreen? {
        (UIApplication.shared.connectedScenes.first { $0 is UIWindowScene } as? UIWindowScene)?.screen
    }

    private func apagar() {
        guard let tela else { return }
        if brilhoAnterior == nil { brilhoAnterior = tela.brightness }
        tela.brightness = 0
    }

    private func restaurar() {
        if let b = brilhoAnterior { tela?.brightness = b }
        brilhoAnterior = nil
    }

    static func qr(_ texto: String) -> UIImage {
        let f = CIFilter.qrCodeGenerator()
        f.message = Data(texto.utf8)
        f.correctionLevel = "M"
        guard let saida = f.outputImage?.transformed(by: CGAffineTransform(scaleX: 12, y: 12)),
              let cg = CIContext().createCGImage(saida, from: saida.extent) else { return UIImage() }
        return UIImage(cgImage: cg)
    }
}
