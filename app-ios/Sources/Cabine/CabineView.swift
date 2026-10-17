// Tela do modo Cabine (guia 10.3): face pedida em letras grandes, progresso, estado das luzes e
// da fila de envio. A confirmação da nota fica no painel (D9); aqui só o resumo.
@preconcurrency import AVFoundation
import CabineNucleo
import SwiftUI

struct CabineView: View {
    @StateObject private var m = CabineModelo()
    @State private var codigo = ""
    @State private var nome = "Cabine 1"
    @State private var chaveLuz = Pareamento.chaveLuz ?? ""
    @State private var cfg = ConfigCabine.atual
    @State private var erroPareamento: String?
    @State private var mostrarAjustes = false

    var body: some View {
        ZStack(alignment: .bottom) {
            PreviaCamera(sessao: m.camera.sessao).ignoresSafeArea().opacity(0.35)
            conteudo.padding().frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
            barraInferior
        }
        .background(Color.black)
        .foregroundStyle(.white)
        .onAppear {
            m.iniciarCamera()
            #if DEBUG
            if case .naoPareado = m.estado, let c = UserDefaults.standard.string(forKey: "testeCodigo") {
                codigo = c
                Task {
                    do { try await Pareamento.ativar(qr: c, nome: "Cabine simulador"); m.pareou() }
                    catch { erroPareamento = CabineModelo.mensagem(error) }
                }
            }
            #endif
        }
        .onDisappear { UIApplication.shared.isIdleTimerDisabled = false }
        .statusBarHidden()
        .sheet(isPresented: $mostrarAjustes) { ajustes }
    }

    private var ajustes: some View {
        NavigationStack {
            Form {
                Section("Servidor") {
                    TextField("API", text: $cfg.api).textInputAutocapitalization(.never).keyboardType(.URL)
                }
                Section("Luzes (ESP32)") {
                    TextField("http://morecheck-cabine-1.local", text: $cfg.esp32).textInputAutocapitalization(.never).keyboardType(.URL)
                    SecureField("Chave da cabine", text: $chaveLuz)
                    Toggle("Tem luz difusa de cima", isOn: $cfg.temDifusa)
                }
                Section("Captura") {
                    Toggle("Voz", isOn: $cfg.vozLigada)
                    Toggle("Não reprovar pela qualidade local (teste)", isOn: $cfg.ignorarQualidadeLocal)
                }
                Section {
                    Button("Refazer calibração") { mostrarAjustes = false; m.refazerCalibracao() }
                    Button("Esquecer pareamento", role: .destructive) { mostrarAjustes = false; m.esquecerPareamento() }
                }
            }
            .navigationTitle("Ajustes da cabine")
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Salvar") {
                        ConfigCabine.atual = cfg
                        if !chaveLuz.isEmpty { Cofre.guardar(chaveLuz, conta: "chave-luz") }
                        m.prepararServicos()
                        mostrarAjustes = false
                    }
                }
            }
        }
        .foregroundStyle(.primary)
    }

    @ViewBuilder private var conteudo: some View {
        switch m.estado {
        case .naoPareado:
            VStack(alignment: .leading, spacing: 12) {
                Text("Parear cabine").font(.largeTitle.bold())
                Text("No painel: Concordância → Cabines → Parear. Leia o QR ou digite o código.")
                TextField("API", text: $cfg.api).textFieldStyle(.roundedBorder).foregroundStyle(.black)
                TextField("Código (ex.: K7PQ-3XWD)", text: $codigo).textFieldStyle(.roundedBorder).foregroundStyle(.black)
                    .textInputAutocapitalization(.characters)
                TextField("Nome da cabine", text: $nome).textFieldStyle(.roundedBorder).foregroundStyle(.black)
                Button("Parear") {
                    ConfigCabine.atual = cfg
                    Task {
                        do { try await Pareamento.ativar(qr: codigo, nome: nome); m.pareou() }
                        catch { erroPareamento = CabineModelo.mensagem(error) }
                    }
                }.buttonStyle(.borderedProminent).disabled(codigo.isEmpty)
                if let erroPareamento { Text(erroPareamento).foregroundStyle(.red) }
            }
        case .semCalibracao:
            VStack(alignment: .leading, spacing: 12) {
                configuracaoLuzes
                CalibracaoView(calibrador: Calibrador(modelo: m))
            }
        case .aguardandoQR:
            VStack(spacing: 24) {
                Grande(titulo: "Aponte para o QR", subtitulo: "Tela do aparelho avaliado, depois dos testes funcionais.")
                Button { mostrarAjustes = true } label: { Label("Ajustes", systemImage: "gearshape") }
                    .buttonStyle(.bordered).tint(.white)
            }
        case .abrindoSessao:
            Grande(titulo: "Abrindo sessão…", subtitulo: nil)
        case .apagandoTela(let c):
            Grande(titulo: c.abertura.aparelho.nome, subtitulo: "Apagando a tela do aparelho…")
        case .posicionar(let c), .aguardandoEstabilidade(let c), .capturando(let c), .verificando(let c):
            VStack(spacing: 10) {
                Text(c.abertura.aparelho.nome).font(.title2)
                Text(c.passoAtual.facePrincipal.nome.uppercased()).font(.system(size: 64, weight: .heavy))
                Text(c.passoAtual.instrucao).font(.title3).multilineTextAlignment(.center)
                ProgressView(value: c.progresso).tint(.yellow)
                Text(rotulo(m.estado, c)).font(.headline).foregroundStyle(.yellow)
                if case .capturando = m.estado {} else {
                    // Sem esperar o detector: o técnico garante que o aparelho está parado e no lugar.
                    Button("Fotografar agora") { m.fotografarAgora() }.buttonStyle(.bordered).tint(.white)
                }
            }
        case .concluindo, .aguardandoSugestao:
            Grande(titulo: "Processando…", subtitulo: "Pode tirar o aparelho do berço.")
        case .resultado(_, let s):
            VStack(spacing: 12) {
                if s.mostrar, let nota = s.nota_final {
                    Text("Nota sugerida").font(.title2)
                    Text(nota).font(.system(size: 120, weight: .heavy)).foregroundStyle(.yellow)
                    ForEach(s.resumo ?? [], id: \.self) { Text($0).font(.callout) }
                    Text("Confirmação no painel.").font(.footnote).foregroundStyle(.secondary)
                } else {
                    Grande(titulo: "Fotos enviadas", subtitulo: s.status == "erro" ? "Erro no processamento: veja no painel." : "Avaliação no painel.")
                }
                if let refazer = s.refazer, !refazer.isEmpty {
                    Button("Refazer: \(refazer.map(\.nome).joined(separator: ", "))") { m.enviar(.refazerFaces(refazer)) }
                        .buttonStyle(.borderedProminent).tint(.orange)
                }
                Button("Próximo aparelho") { m.enviar(.proximoAparelho) }.buttonStyle(.borderedProminent).tint(.yellow).foregroundStyle(.black)
            }
        case .pausado(let motivo, _):
            VStack(spacing: 16) {
                Grande(titulo: "Pausado", subtitulo: motivo.rawValue)
                Button("Retomar") { m.enviar(.retomar) }.buttonStyle(.borderedProminent)
                Button("Cancelar aparelho") { m.enviar(.cancelar) }
            }
        case .erro(let msg):
            VStack(spacing: 16) {
                Grande(titulo: "Erro", subtitulo: msg)
                Button("Voltar") { m.enviar(.proximoAparelho) }.buttonStyle(.borderedProminent)
            }
        }
    }

    private var configuracaoLuzes: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Luzes (ESP32)").font(.headline)
            TextField("http://morecheck-cabine-1.local ou IP", text: $cfg.esp32).textFieldStyle(.roundedBorder).foregroundStyle(.black)
            SecureField("Chave da cabine (segredos.h)", text: $chaveLuz).textFieldStyle(.roundedBorder).foregroundStyle(.black)
            Toggle("Tem luz difusa de cima", isOn: $cfg.temDifusa)
            Button("Salvar luzes") {
                ConfigCabine.atual = cfg
                Cofre.guardar(chaveLuz, conta: "chave-luz")
                m.prepararServicos()
            }
        }
    }

    private var barraInferior: some View {
        HStack {
            Label("\(m.naFila) na fila", systemImage: m.naFila > 0 ? "arrow.up.circle" : "checkmark.circle")
            Spacer()
            if let aviso = m.aviso { Text(aviso).font(.caption).lineLimit(2) }
        }
        .padding(10).background(.black.opacity(0.7))
    }

    private func rotulo(_ e: EstadoCabine, _ c: Captura) -> String {
        switch e {
        case .posicionar: "Posicione o aparelho"
        case .aguardandoEstabilidade: "Aguardando imagem parada…"
        case .capturando: "Foto: \(c.luzAtual.rawValue.replacingOccurrences(of: "_", with: " "))"
        default: ""
        }
    }
}

private struct Grande: View {
    let titulo: String
    let subtitulo: String?
    var body: some View {
        VStack(spacing: 8) {
            Text(titulo).font(.system(size: 44, weight: .heavy)).multilineTextAlignment(.center)
            if let subtitulo { Text(subtitulo).font(.title3).multilineTextAlignment(.center) }
        }.padding(.top, 60)
    }
}

struct PreviaCamera: UIViewRepresentable {
    let sessao: AVCaptureSession
    func makeUIView(context: Context) -> VisaoPrevia {
        let v = VisaoPrevia()
        v.camada.session = sessao
        v.camada.videoGravity = .resizeAspect
        return v
    }
    func updateUIView(_ uiView: VisaoPrevia, context: Context) {}

    final class VisaoPrevia: UIView {
        override class var layerClass: AnyClass { AVCaptureVideoPreviewLayer.self }
        var camada: AVCaptureVideoPreviewLayer { layer as! AVCaptureVideoPreviewLayer }
    }
}
