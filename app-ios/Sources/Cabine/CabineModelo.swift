// Executa os efeitos da MaquinaCabine (CabineNucleo) com a câmera, as luzes e a rede, e
// devolve os resultados como eventos. Toda a lógica de fluxo está na máquina (testada).
@preconcurrency import AVFoundation
import CabineNucleo
import SwiftUI

@MainActor
final class CabineModelo: ObservableObject {
    @Published private(set) var estado: EstadoCabine
    @Published private(set) var naFila = 0
    @Published var aviso: String?
    @Published private(set) var ultimoQuadro: QuadroLuma?

    let camera = CameraCabine()
    private(set) var perfil: PerfilCamera?
    private var api: ClienteAPI?
    private var luz: LuzCabine?
    private var fila: FilaEnvio?
    private let voz = Voz()
    private var detector = DetectorEstabilidade()
    private var bercoVazio: QuadroLuma?
    private var analisando = false
    private var tarefaEnvio: Task<Void, Never>?

    init() {
        estado = Pareamento.token == nil ? .naoPareado : (Self.carregarPerfil() == nil ? .semCalibracao : .aguardandoQR)
        perfil = Self.carregarPerfil()
        bercoVazio = Self.carregarBercoVazio()
        prepararServicos()
        observarSistema()
    }

    // MARK: serviços

    func prepararServicos() {
        let cfg = ConfigCabine.atual
        voz.ligada = cfg.vozLigada
        guard let token = Pareamento.token, let base = URL(string: cfg.api) else { return }
        let api = ClienteAPI(base: base, tokenCabine: token)
        self.api = api
        if let esp = URL(string: cfg.esp32), let chave = Pareamento.chaveLuz {
            luz = LuzCabine(base: esp, chave: chave, temDifusa: cfg.temDifusa)
        }
        let pasta = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("fila-envio")
        fila = try? FilaEnvio(pasta: pasta, api: api)
        tarefaEnvio?.cancel()
        tarefaEnvio = Task { [weak self] in await self?.lacoEnvio() }
    }

    private func lacoEnvio() async {
        while !Task.isCancelled {
            guard let fila else { return }
            await fila.enviarPendentes()
            naFila = await fila.quantidade
            if let erro = await fila.ultimoErro { aviso = erro }
            let espera = await fila.espera
            try? await Task.sleep(nanoseconds: UInt64(max(espera, 0.5) * 1_000_000_000))
        }
    }

    func iniciarCamera() {
        do {
            try camera.configurar()
            try camera.modoAutomatico()
        } catch {
            aviso = "Câmera indisponível: \(error)"
            return
        }
        camera.aoLerQR = { [weak self] texto in Task { @MainActor in self?.qrLido(texto) } }
        camera.aoReceberQuadro = { [weak self] quadro, buffer in
            Task { @MainActor in self?.quadro(quadro, buffer) }
        }
        let sessao = camera.sessao
        DispatchQueue.global(qos: .userInitiated).async { sessao.startRunning() }
        UIApplication.shared.isIdleTimerDisabled = true
    }

    private func observarSistema() {
        NotificationCenter.default.addObserver(forName: ProcessInfo.thermalStateDidChangeNotification, object: nil, queue: .main) { [weak self] _ in
            Task { @MainActor in
                if ProcessInfo.processInfo.thermalState == .critical { self?.enviar(.temperaturaCritica) }
            }
        }
        NotificationCenter.default.addObserver(forName: AVCaptureSession.wasInterruptedNotification, object: nil, queue: .main) { [weak self] _ in
            Task { @MainActor in self?.enviar(.cameraInterrompida) }
        }
    }

    // MARK: máquina

    func enviar(_ evento: EventoCabine) {
        let (novo, efeitos) = MaquinaCabine.transicao(estado, evento)
        estado = novo
        if case .aguardandoEstabilidade = novo { detector.reiniciar() }
        guard !efeitos.isEmpty else { return }
        Task { for e in efeitos { await executar(e) } }  // efeitos de uma transição, em ordem
    }

    private func executar(_ e: EfeitoCabine) async {
        switch e {
        case .abrirSessao(let token):
            do {
                try camera.modoAutomatico()
                enviar(.sessaoAberta(try await api!.abrir(token: token, refazer: false)))
            } catch ErroAPI.http(409, _) {
                // já avaliada: refaz a captura (o técnico leu o QR de novo de propósito)
                if let r = try? await api!.abrir(token: token, refazer: true) { enviar(.sessaoAberta(r)) }
                else { enviar(.falhaAbrir("Sessão já avaliada")) }
            } catch {
                enviar(.falhaAbrir(Self.mensagem(error)))
            }
        case .pedirTela(let token, let acao):
            try? await api?.pedirTela(token: token, acao: acao)
            if acao == "preto" { await esperarTelaApagar() }
        case .falar(let texto):
            voz.falar(texto)
        case .aplicarFoco(let pose):
            await aplicarPerfil(pose: pose)
        case .acenderLuz(let l):
            do {
                try await luz?.acender(l)
                if let exp = perfil?.exposicao(para: l) { try await camera.travarExposicao(exp) }
                try await Task.sleep(nanoseconds: 70_000_000)  // mais 2 quadros (14.4 passo 3)
            } catch {
                enviar(.luzFalhou)
            }
        case .capturar(let passo, let luzAtual):
            await capturar(passo: passo, luz: luzAtual)
        case .desligarLuzes:
            try? await luz?.desligar()
        case .concluir(let token, let fotos):
            await concluir(token: token, fotos: fotos)
        case .consultarSugestao(let token):
            try? await Task.sleep(nanoseconds: 1_000_000_000)
            if let s = try? await api?.sugestao(token: token) { enviar(.sugestao(s)) }
            else { enviar(.sugestao(Sugestao(status: "processando", mostrar: false))) }
        }
    }

    private func aplicarPerfil(pose: Pose) async {
        guard let p = perfil else { return }
        try? camera.travarBalanco(p.balanco_branco)
        if let f = p.foco[pose.rawValue] ?? p.foco["deitado"] { try? await camera.travarFoco(f) }
        if let e = p.exposicao["ambiente"] { try? await camera.travarExposicao(e) }
    }

    private func esperarTelaApagar() async {
        // confirma vendo a região central escurecer; segue em 5 s de qualquer jeito
        let limite = Date().addingTimeInterval(5)
        while Date() < limite {
            if let q = ultimoQuadro, Self.mediaCentro(q) < 40 { break }
            try? await Task.sleep(nanoseconds: 200_000_000)
        }
        enviar(.telaApagada)
    }

    private func capturar(passo: Int, luz luzAtual: Luz) async {
        guard let c = estado.captura, let fila else { return }
        do {
            let foto = try await camera.capturar()
            let p = c.passoAtual
            let dims = c.abertura.aparelho.dimensoes_mm
            let proporcao = p.pose == .ponta ? dims.largura / dims.espessura : p.pose == .lateral ? dims.altura / dims.espessura : dims.altura / dims.largura
            var q: QualidadeLocal.Resultado? = nil
            if let prev = foto.previewLuma {
                q = QualidadeLocal.avaliar(prev, aparelho: aparelhoNoQuadro, proporcaoEsperada: proporcao, luz: luzAtual,
                                           exigirTelaApagada: p.facePrincipal == .frente)
            }
            if let q, !q.ok {
                aviso = "Foto reprovada: \(q.motivo ?? "")"
                enviar(.fotoCapturada(ok: false))
                return
            }
            let meta = MetadadosFoto(
                camera: .init(modelo: Self.modeloAparelho, lente: "grande_angular_1x", app_versao: Self.versaoApp),
                exposicao: foto.exposicao, foco: .init(lens_position: foto.lensPosition), balanco_branco: foto.ganhos,
                dimensoes_px: ["largura": foto.dimensoes.0, "altura": foto.dimensoes.1], formato: foto.formato, rotacao_graus: 0,
                perfil_calibracao_versao: perfil?.versao ?? 0, capturada_em: ISO8601DateFormatter().string(from: Date()),
                qualidade_local: q.map { .init(nitidez: $0.nitidez, estouro_pct: $0.estouroPct, contorno_ok: $0.contornoOk) })
            let item = ItemEnvio(token: c.token, passo: passo, face: p.facePrincipal, luz: luzAtual, pose: p.pose, lado: p.lado,
                                 tentativa: c.tentativas + 1, metadados: meta)
            try await fila.enfileirar(item, dados: foto.dados)
            naFila = await fila.quantidade
            enviar(.fotoCapturada(ok: true))
        } catch {
            aviso = "Falha na captura: \(Self.mensagem(error))"
            enviar(.fotoCapturada(ok: false))
        }
    }

    private func concluir(token: String, fotos: Int) async {
        // o backend só aceita depois que todas as fotos chegaram: espera a fila esvaziar (até 60 s)
        let limite = Date().addingTimeInterval(60)
        while let fila, await fila.quantidade > 0, Date() < limite {
            await fila.enviarPendentes()
            try? await Task.sleep(nanoseconds: 300_000_000)
        }
        do {
            let faltando = try await api!.concluir(token: token, fotosEnviadas: fotos)
            enviar(faltando.isEmpty ? .conclusaoAceita : .conclusaoRecusada(faltando: faltando))
        } catch {
            aviso = "Não foi possível concluir: \(Self.mensagem(error)). Confira a rede."
        }
    }

    // MARK: entradas da câmera

    private var aparelhoNoQuadro: Quadrilatero?

    private func qrLido(_ texto: String) {
        guard case .aguardandoQR = estado else { return }
        // QR da sessão: o token, ou uma URL que termina no token
        let token = URL(string: texto)?.lastPathComponent.nonEmpty ?? texto
        enviar(.qrLido(token))
    }

    private func quadro(_ q: QuadroLuma, _ buffer: CVPixelBuffer) {
        ultimoQuadro = q
        let emPosicao: Bool
        switch estado {
        case .posicionar, .aguardandoEstabilidade: emPosicao = true
        default: emPosicao = false
        }
        guard emPosicao, !analisando, let c = estado.captura else { return }
        analisando = true
        let d = c.abertura.aparelho.dimensoes_mm
        let pose = c.passoAtual.pose
        let proporcao = pose == .ponta ? d.largura / d.espessura : pose == .lateral ? d.altura / d.espessura : d.altura / d.largura
        let quad = VisaoDispositivo.aparelho(buffer, proporcao: proporcao)
        analisando = false
        aparelhoNoQuadro = quad
        let mao = bercoVazio.map { detector.maoNaCena(q, bercoVazio: $0, aparelho: quad) } ?? false
        if case .posicionar = estado, quad != nil, !mao { enviar(.tecnicoPronto) }
        if case .aguardandoEstabilidade = estado,
           detector.alimentar(q, em: Date().timeIntervalSinceReferenceDate, aparelhoPresente: quad != nil, maoNaCena: mao) {
            enviar(.estavel)
        }
    }

    // MARK: perfil

    func salvarPerfil(_ p: PerfilCamera, bercoVazio: QuadroLuma?) async {
        perfil = p
        let enc = JSONEncoder()
        enc.dateEncodingStrategy = .iso8601
        try? enc.encode(p).write(to: Self.arquivo("perfil.json"), options: .atomic)
        if let b = bercoVazio {
            self.bercoVazio = b
            try? (withUnsafeBytes(of: Int32(b.largura)) { Data($0) } + withUnsafeBytes(of: Int32(b.altura)) { Data($0) } + Data(b.pixels))
                .write(to: Self.arquivo("berco-vazio.bin"), options: .atomic)
        }
        do { try await api?.salvarPerfil(p) } catch { aviso = "Perfil salvo só no aparelho: \(Self.mensagem(error))" }
        enviar(.calibrada)
    }

    func pareou() {
        prepararServicos()
        enviar(.pareada)
    }

    func luzesParaCalibrar() -> LuzCabine? { luz }

    private static func arquivo(_ nome: String) -> URL {
        let pasta = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        try? FileManager.default.createDirectory(at: pasta, withIntermediateDirectories: true)
        return pasta.appendingPathComponent(nome)
    }

    static func carregarPerfil() -> PerfilCamera? {
        let dec = JSONDecoder()
        dec.dateDecodingStrategy = .iso8601
        return (try? Data(contentsOf: arquivo("perfil.json"))).flatMap { try? dec.decode(PerfilCamera.self, from: $0) }
    }

    private static func carregarBercoVazio() -> QuadroLuma? {
        guard let d = try? Data(contentsOf: arquivo("berco-vazio.bin")), d.count > 8 else { return nil }
        let w = Int(d.prefix(4).withUnsafeBytes { $0.load(as: Int32.self) })
        let h = Int(d.dropFirst(4).prefix(4).withUnsafeBytes { $0.load(as: Int32.self) })
        let px = [UInt8](d.dropFirst(8))
        return px.count == w * h ? QuadroLuma(largura: w, altura: h, pixels: px) : nil
    }

    static func mediaCentro(_ q: QuadroLuma) -> Double {
        var s = 0, n = 0
        for y in (q.altura / 3)..<(2 * q.altura / 3) { for x in (q.largura / 3)..<(2 * q.largura / 3) { s += Int(q[x, y]); n += 1 } }
        return n > 0 ? Double(s) / Double(n) : 0
    }

    static func mensagem(_ e: Error) -> String {
        if case ErroAPI.http(let s, let m) = e { return "HTTP \(s): \(m.prefix(200))" }
        return e.localizedDescription
    }

    static var modeloAparelho: String {
        var s = utsname()
        uname(&s)
        return withUnsafeBytes(of: &s.machine) { String(decoding: $0.prefix { $0 != 0 }, as: UTF8.self) }
    }

    static var versaoApp: String { Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "0" }
}

private extension String {
    var nonEmpty: String? { isEmpty ? nil : self }
}
