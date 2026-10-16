// Assistente de calibração (guia 14.3). Refazer sempre que a cabine for mexida.
// Passos: rede local (provoca a permissão) → exposição e balanço com o berço vazio → foco por
// pose → exposição da rasante → escala e orientação → referência do berço vazio → salvar.
@preconcurrency import AVFoundation
import CabineNucleo
import SwiftUI
import Vision

@MainActor
final class Calibrador: ObservableObject {
    enum Passo: Int, CaseIterable { case redeLocal, bercoVazio, foco, rasante, geometria, salvar }

    @Published var passo: Passo = .redeLocal
    @Published var mensagem = ""
    @Published var orientacao = "topo_para_cima"
    @Published var trabalhando = false
    private var ambiente: Exposicao?
    private var rasante: Exposicao?
    private var ganhos: GanhosBalanco?
    private var foco: [String: Double] = [:]
    private var pxPorMm: Double?
    private var referencia: QuadroLuma?
    let modelo: CabineModelo
    var poses: [Pose] = [.deitado]  // com suportes em pé (D3): [.deitado, .lateral, .ponta]

    init(modelo: CabineModelo) { self.modelo = modelo }

    func executar() async {
        trabalhando = true
        defer { trabalhando = false }
        let cam = modelo.camera
        do {
            switch passo {
            case .redeLocal:
                // A primeira chamada ao ESP32 dispara o pedido de permissão de rede local (14.7).
                try await modelo.luzesParaCalibrar()?.desligar()
                mensagem = "Luzes respondendo. Deixe o berço vazio com a folha de marcadores."
            case .bercoVazio:
                try cam.modoAutomatico()
                try await Task.sleep(nanoseconds: 2_000_000_000)
                let auto = cam.exposicaoAtual
                let duracao = CalculoExposicao.duracaoSemFaixas(1.0 / 60)
                ambiente = Exposicao(duracao_s: duracao, iso: CalculoExposicao.iso(paraDuracao: duracao, isoAuto: auto.iso,
                                                                                    duracaoAuto: auto.duracao_s, faixa: cam.faixaISO))
                ganhos = cam.ganhosAtuais
                try cam.travarBalanco(ganhos!)
                try await cam.travarExposicao(ambiente!)
                referencia = modelo.ultimoQuadro
                mensagem = String(format: "Ambiente: 1/%.0f s, ISO %.0f. Balanço travado.", 1 / duracao, ambiente!.iso)
            case .foco:
                for pose in poses {
                    foco[pose.rawValue] = try await cam.focarELer(ponto: CGPoint(x: 0.5, y: 0.5))
                }
                mensagem = "Foco: " + foco.map { "\($0.key) \(String(format: "%.2f", $0.value))" }.joined(separator: ", ")
            case .rasante:
                try await modelo.luzesParaCalibrar()?.acender(.rasante_a)
                var iso = ambiente!.iso
                for _ in 0..<6 {
                    try await cam.travarExposicao(Exposicao(duracao_s: ambiente!.duracao_s, iso: iso))
                    let foto = try await cam.capturar(formatoHEIC: false)
                    let estouro = foto.previewLuma.map { q in Double(q.pixels.filter { $0 >= 250 }.count) / Double(q.pixels.count) * 100 } ?? 0
                    if estouro < 0.5 { break }
                    iso = max(cam.faixaISO.lowerBound, iso * 0.7)
                }
                rasante = Exposicao(duracao_s: ambiente!.duracao_s, iso: iso)
                try await modelo.luzesParaCalibrar()?.desligar()
                mensagem = String(format: "Rasante: ISO %.0f (< 0,5%% estourado).", iso)
            case .geometria:
                let foto = try await cam.capturar(formatoHEIC: false)
                pxPorMm = Self.pxPorMmArUco(foto)
                mensagem = pxPorMm.map { String(format: "Escala no berço: %.1f px/mm (ArUco, aproximada).", $0) }
                    ?? "Marcadores não encontrados: confira a folha e a luz."
            case .salvar:
                let dims = cam.camera.activeFormat.supportedMaxPhotoDimensions.max { $0.width < $1.width }
                let perfil = PerfilCamera(
                    versao: (modelo.perfil?.versao ?? 0) + 1, criado_em: Date(), camera_modelo: CabineModelo.modeloAparelho,
                    dimensoes_px: ["largura": Int(dims?.width ?? 0), "altura": Int(dims?.height ?? 0)],
                    exposicao: ["ambiente": ambiente!, "rasante": rasante ?? ambiente!], balanco_branco: ganhos!,
                    foco: foco, px_por_mm_berco: pxPorMm, orientacao: Dictionary(uniqueKeysWithValues: poses.map { ($0.rawValue, orientacao) }))
                await modelo.salvarPerfil(perfil, bercoVazio: referencia)
                mensagem = "Perfil v\(perfil.versao) salvo."
                return
            }
            passo = Passo(rawValue: passo.rawValue + 1) ?? .salvar
        } catch {
            mensagem = "Falhou: \(CabineModelo.mensagem(error))"
        }
    }

    /// px/mm pelos quadrados ArUco de 30 mm, com Vision (sem OpenCV no iOS). Aproximação: o
    /// worker mede de novo, no servidor, com o contorno do aparelho.
    static func pxPorMmArUco(_ foto: FotoCapturada) -> Double? {
        guard let img = CIImage(data: foto.dados) else { return nil }
        let pedido = VNDetectRectanglesRequest()
        pedido.minimumAspectRatio = 0.9
        pedido.maximumAspectRatio = 1.0
        pedido.maximumObservations = 8
        pedido.minimumSize = 0.03
        try? VNImageRequestHandler(ciImage: img).perform([pedido])
        let w = Double(foto.dimensoes.0), h = Double(foto.dimensoes.1)
        let lados = (pedido.results ?? []).map { r in
            (hypot((r.topRight.x - r.topLeft.x) * w, (r.topRight.y - r.topLeft.y) * h)
             + hypot((r.bottomLeft.x - r.topLeft.x) * w, (r.bottomLeft.y - r.topLeft.y) * h)) / 2
        }.sorted()
        guard !lados.isEmpty else { return nil }
        return lados[lados.count / 2] / 30.0
    }
}

struct CalibracaoView: View {
    @StateObject var calibrador: Calibrador
    private let textos: [Calibrador.Passo: String] = [
        .redeLocal: "1. Testar as luzes (o iOS pede permissão de rede local).",
        .bercoVazio: "2. Berço vazio com a folha de marcadores: exposição e balanço de branco.",
        .foco: "3. Aparelho deitado no berço: medir o foco.",
        .rasante: "4. Aparelho com risco conhecido: exposição da luz rasante.",
        .geometria: "5. Berço com os 4 marcadores visíveis: escala e orientação.",
        .salvar: "6. Salvar o perfil.",
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Calibração da cabine").font(.largeTitle.bold())
            ForEach(Calibrador.Passo.allCases, id: \.self) { p in
                Text(textos[p]!).foregroundStyle(p == calibrador.passo ? .primary : .secondary)
                    .fontWeight(p == calibrador.passo ? .bold : .regular)
            }
            if calibrador.passo == .geometria {
                Picker("Topo do aparelho na imagem", selection: $calibrador.orientacao) {
                    Text("para cima").tag("topo_para_cima"); Text("para baixo").tag("topo_para_baixo")
                    Text("para a esquerda").tag("topo_para_esquerda"); Text("para a direita").tag("topo_para_direita")
                }.pickerStyle(.segmented)
            }
            Button(calibrador.trabalhando ? "Medindo…" : "Executar passo") { Task { await calibrador.executar() } }
                .buttonStyle(.borderedProminent).disabled(calibrador.trabalhando)
            Text(calibrador.mensagem).font(.callout)
            Spacer()
        }.padding()
    }
}
