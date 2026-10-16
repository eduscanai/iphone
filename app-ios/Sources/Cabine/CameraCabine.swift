// Câmera da cabine (guia 14.1, 14.2 e 14.4). Lente principal 1x física (nunca câmera virtual),
// 48 MP quando houver, exposição/foco/balanço travados pelo perfil, rotação fixa em 0°.
// VERIFICAR cada assinatura na versão do SDK; não roda no simulador.
@preconcurrency import AVFoundation
import CabineNucleo
import CoreImage
import UIKit

enum ErroCabine: Error { case semCamera, configuracao, captura(String) }

struct FotoCapturada {
    let dados: Data
    let formato: String  // heic, jpeg ou dng
    let dimensoes: (Int, Int)
    let previewLuma: QuadroLuma?
    let exposicao: Exposicao
    let lensPosition: Double
    let ganhos: GanhosBalanco
}

final class CameraCabine: NSObject, @unchecked Sendable {
    let sessao = AVCaptureSession()
    private let saidaFoto = AVCapturePhotoOutput()
    private let saidaVideo = AVCaptureVideoDataOutput()
    private let saidaMetadados = AVCaptureMetadataOutput()
    private let filaVideo = DispatchQueue(label: "cabine.video")
    private(set) var camera: AVCaptureDevice!
    private var delegados: [Int64: DelegadoFoto] = [:]  // referência forte até terminar (como no AVCam)
    private var contadorQuadros = 0

    /// Quadros pequenos (~320×240) para estabilidade; 1 a cada 2 (guia 14.6).
    var aoReceberQuadro: ((QuadroLuma, CVPixelBuffer) -> Void)?
    var aoLerQR: ((String) -> Void)?

    func configurar() throws {
        guard let camera = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back) else {
            throw ErroCabine.semCamera
        }
        self.camera = camera
        sessao.beginConfiguration()
        defer { sessao.commitConfiguration() }
        sessao.sessionPreset = .photo
        let entrada = try AVCaptureDeviceInput(device: camera)
        guard sessao.canAddInput(entrada), sessao.canAddOutput(saidaFoto), sessao.canAddOutput(saidaVideo),
              sessao.canAddOutput(saidaMetadados) else { throw ErroCabine.configuracao }
        sessao.addInput(entrada)
        sessao.addOutput(saidaFoto)
        sessao.addOutput(saidaVideo)
        sessao.addOutput(saidaMetadados)
        saidaMetadados.setMetadataObjectsDelegate(self, queue: .main)
        saidaMetadados.metadataObjectTypes = [.qr]
        saidaVideo.videoSettings = [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_420YpCbCr8BiPlanarFullRange]
        saidaVideo.alwaysDiscardsLateVideoFrames = true
        saidaVideo.setSampleBufferDelegate(self, queue: filaVideo)

        try camera.lockForConfiguration()
        defer { camera.unlockForConfiguration() }
        if let formato = camera.formats.last(where: { f in
            f.supportedMaxPhotoDimensions.contains { $0.width == 8064 && $0.height == 6048 }
        }) {
            camera.activeFormat = formato
        }
        camera.isSubjectAreaChangeMonitoringEnabled = false
        if let dims = camera.activeFormat.supportedMaxPhotoDimensions.max(by: { $0.width < $1.width }) {
            saidaFoto.maxPhotoDimensions = dims
        }
        saidaFoto.maxPhotoQualityPrioritization = .quality
        // Câmera apontada para baixo: a orientação do aparelho não é confiável. Fixar a rotação (R21).
        saidaFoto.connection(with: .video)?.videoRotationAngle = 0
        saidaVideo.connection(with: .video)?.videoRotationAngle = 0
    }

    // MARK: modos

    /// Leitura do QR com exposição automática (tela do aparelho avaliado acesa e brilhante).
    func modoAutomatico() throws {
        try camera.lockForConfiguration()
        defer { camera.unlockForConfiguration() }
        camera.exposureMode = .continuousAutoExposure
        camera.focusMode = .continuousAutoFocus
        camera.whiteBalanceMode = .continuousAutoWhiteBalance
    }

    var faixaISO: ClosedRange<Double> { Double(camera.activeFormat.minISO)...Double(camera.activeFormat.maxISO) }

    /// Exposição travada; devolve quando o primeiro quadro com os novos valores chegar.
    func travarExposicao(_ e: Exposicao) async throws {
        try camera.lockForConfiguration()
        let iso = Float(min(max(e.iso, faixaISO.lowerBound), faixaISO.upperBound))
        await withCheckedContinuation { (c: CheckedContinuation<Void, Never>) in
            camera.setExposureModeCustom(duration: CMTime(seconds: e.duracao_s, preferredTimescale: 1_000_000), iso: iso) { _ in
                c.resume()
            }
        }
        camera.unlockForConfiguration()
    }

    func travarFoco(_ lensPosition: Double) async throws {
        try camera.lockForConfiguration()
        await withCheckedContinuation { (c: CheckedContinuation<Void, Never>) in
            camera.setFocusModeLocked(lensPosition: Float(lensPosition)) { _ in c.resume() }
        }
        camera.unlockForConfiguration()
    }

    func travarBalanco(_ g: GanhosBalanco) throws {
        try camera.lockForConfiguration()
        defer { camera.unlockForConfiguration() }
        let maximo = camera.maxWhiteBalanceGain
        let ganhos = AVCaptureDevice.WhiteBalanceGains(redGain: min(max(Float(g.r), 1), maximo),
                                                       greenGain: min(max(Float(g.g), 1), maximo),
                                                       blueGain: min(max(Float(g.b), 1), maximo))
        camera.setWhiteBalanceModeLocked(with: ganhos, completionHandler: nil)
    }

    var exposicaoAtual: Exposicao {
        Exposicao(duracao_s: camera.exposureDuration.seconds, iso: Double(camera.iso))
    }
    var ganhosAtuais: GanhosBalanco {
        let g = camera.deviceWhiteBalanceGains
        return GanhosBalanco(r: Double(g.redGain), g: Double(g.greenGain), b: Double(g.blueGain))
    }

    /// Foco automático num ponto e leitura do lensPosition (calibração por pose, 14.3 passo 3).
    func focarELer(ponto: CGPoint) async throws -> Double {
        try camera.lockForConfiguration()
        camera.focusPointOfInterest = ponto
        camera.focusMode = .autoFocus
        camera.unlockForConfiguration()
        try await Task.sleep(nanoseconds: 300_000_000)
        while camera.isAdjustingFocus { try await Task.sleep(nanoseconds: 50_000_000) }
        return Double(camera.lensPosition)
    }

    // MARK: captura (14.4)

    func capturar(formatoHEIC: Bool = true) async throws -> FotoCapturada {
        let ajustes = formatoHEIC && saidaFoto.availablePhotoCodecTypes.contains(.hevc)
            ? AVCapturePhotoSettings(format: [AVVideoCodecKey: AVVideoCodecType.hevc])
            : AVCapturePhotoSettings(format: [AVVideoCodecKey: AVVideoCodecType.jpeg])
        ajustes.maxPhotoDimensions = saidaFoto.maxPhotoDimensions
        ajustes.photoQualityPrioritization = .speed  // menos fusão de quadros (VERIFICAR na fase 2)
        ajustes.flashMode = .off
        if let tipo = ajustes.availablePreviewPhotoPixelFormatTypes.first {
            ajustes.previewPhotoFormat = [kCVPixelBufferPixelFormatTypeKey as String: tipo,
                                          kCVPixelBufferWidthKey as String: 1024, kCVPixelBufferHeightKey as String: 768]
        }
        let exposicao = exposicaoAtual, lens = Double(camera.lensPosition), ganhos = ganhosAtuais
        return try await withCheckedThrowingContinuation { c in
            let d = DelegadoFoto { [weak self] resultado in
                self?.delegados[ajustes.uniqueID] = nil
                switch resultado {
                case .success(let foto):
                    guard let dados = foto.fileDataRepresentation() else { return c.resume(throwing: ErroCabine.captura("sem dados")) }
                    let dims = foto.resolvedSettings.photoDimensions
                    let preview = foto.previewPixelBuffer.map { VisaoDispositivo.luma($0, largura: 1024) }
                    c.resume(returning: FotoCapturada(dados: dados, formato: formatoHEIC ? "heic" : "jpeg",
                                                      dimensoes: (Int(dims.width), Int(dims.height)), previewLuma: preview,
                                                      exposicao: exposicao, lensPosition: lens, ganhos: ganhos))
                case .failure(let e):
                    c.resume(throwing: e)
                }
            }
            delegados[ajustes.uniqueID] = d
            saidaFoto.capturePhoto(with: ajustes, delegate: d)
        }
    }
}

extension CameraCabine: AVCaptureVideoDataOutputSampleBufferDelegate {
    func captureOutput(_ output: AVCaptureOutput, didOutput sampleBuffer: CMSampleBuffer, from connection: AVCaptureConnection) {
        contadorQuadros += 1
        guard contadorQuadros % 2 == 0, let buf = CMSampleBufferGetImageBuffer(sampleBuffer), let f = aoReceberQuadro else { return }
        f(VisaoDispositivo.luma(buf, largura: 320), buf)
    }
}

extension CameraCabine: AVCaptureMetadataOutputObjectsDelegate {
    func metadataOutput(_ output: AVCaptureMetadataOutput, didOutput metadataObjects: [AVMetadataObject], from connection: AVCaptureConnection) {
        if let qr = metadataObjects.compactMap({ $0 as? AVMetadataMachineReadableCodeObject }).first?.stringValue {
            aoLerQR?(qr)
        }
    }
}

private final class DelegadoFoto: NSObject, AVCapturePhotoCaptureDelegate {
    let terminar: (Result<AVCapturePhoto, Error>) -> Void
    init(_ terminar: @escaping (Result<AVCapturePhoto, Error>) -> Void) { self.terminar = terminar }
    func photoOutput(_ output: AVCapturePhotoOutput, didFinishProcessingPhoto photo: AVCapturePhoto, error: Error?) {
        if let error { terminar(.failure(error)) } else { terminar(.success(photo)) }
    }
}
