// Máquina de estados do roteiro (guia 14.5) como função pura:
// `transicao(estado, evento) → (novo estado, efeitos)`. O CabineModelo (app) executa os efeitos
// (câmera, luzes, rede) e devolve os resultados como eventos. Assim o fluxo inteiro é testável.
import Foundation

public struct Captura: Equatable, Sendable {
    public var token: String
    public var abertura: RespostaAbrir
    public var passo: Int = 0  // índice em roteiro.passos
    public var luz: Int = 0  // índice em passo.luzes
    public var tentativas: Int = 0  // tentativas do passo atual
    public var fotosEnfileiradas: Int = 0
    /// Faces a refazer (pedido do worker): só os passos que contêm essas faces.
    public var passosPendentes: [Int]

    public init(token: String, abertura: RespostaAbrir) {
        self.token = token
        self.abertura = abertura
        passosPendentes = Array(abertura.roteiro.passos.indices)
    }

    public var passoAtual: Passo { abertura.roteiro.passos[passo] }
    public var luzAtual: Luz { passoAtual.luzes[luz] }
    public var progresso: Double {
        let total = Double(abertura.roteiro.totalFotos)
        return total > 0 ? Double(fotosEnfileiradas) / total : 0
    }
}

public enum MotivoPausa: String, Equatable, Sendable {
    case luzSemResposta = "As luzes não respondem: confira o ESP32 e o Wi-Fi."
    case cameraInterrompida = "Câmera interrompida."
    case temperaturaAlta = "iPhone da cabine quente demais: deixe esfriar."
    case precisaAjuda = "A foto falhou 3 vezes neste passo: confira a posição, a limpeza e as luzes."
}

public indirect enum EstadoCabine: Equatable, Sendable {
    case naoPareado
    case semCalibracao
    case aguardandoQR
    case abrindoSessao(token: String)
    case apagandoTela(Captura)
    case posicionar(Captura)
    case aguardandoEstabilidade(Captura)
    case capturando(Captura)
    case verificando(Captura)
    case concluindo(Captura)
    case aguardandoSugestao(Captura)
    case resultado(Captura, Sugestao)
    case pausado(MotivoPausa, retomar: EstadoCabine)
    case erro(String)
}

public enum EventoCabine: Equatable, Sendable {
    case pareada
    case calibrada
    case qrLido(String)
    case sessaoAberta(RespostaAbrir)
    case falhaAbrir(String)
    case telaApagada  // confirmado pela imagem escurecendo, ou tempo-limite de 5 s
    case tecnicoPronto  // posicionou o aparelho (ou detector viu aparelho na área)
    case estavel
    case fotoCapturada(ok: Bool)  // qualidade local
    case luzFalhou
    case cameraInterrompida
    case temperaturaCritica
    case retomar
    case conclusaoAceita
    case conclusaoRecusada(faltando: [Int])  // passos (ordem) que faltam
    case sugestao(Sugestao)
    case refazerFaces([Face])
    case proximoAparelho
    case cancelar
}

public enum EfeitoCabine: Equatable, Sendable {
    case abrirSessao(token: String)
    case pedirTela(token: String, acao: String)
    case falar(String)
    case aplicarFoco(Pose)
    case acenderLuz(Luz)
    case capturar(passo: Int, luz: Luz)
    case desligarLuzes
    case concluir(token: String, fotos: Int)
    case consultarSugestao(token: String)
}

public enum MaquinaCabine {
    public static let tentativasMax = 3

    public static func transicao(_ estado: EstadoCabine, _ evento: EventoCabine) -> (EstadoCabine, [EfeitoCabine]) {
        switch (estado, evento) {
        case (.naoPareado, .pareada):
            return (.semCalibracao, [])
        case (.semCalibracao, .calibrada), (.aguardandoQR, .calibrada):
            return (.aguardandoQR, [])

        case (.aguardandoQR, .qrLido(let token)):
            return (.abrindoSessao(token: token), [.abrirSessao(token: token)])
        case (.abrindoSessao(let token), .sessaoAberta(let r)):
            let c = Captura(token: token, abertura: r)
            return (.apagandoTela(c), [.pedirTela(token: token, acao: "preto")])
        case (.abrindoSessao, .falhaAbrir(let msg)):
            return (.erro(msg), [.falar("Não foi possível abrir a sessão.")])

        case (.apagandoTela(let c), .telaApagada):
            return posicionar(c)

        case (.posicionar(let c), .tecnicoPronto):
            return (.aguardandoEstabilidade(c), [])
        case (.aguardandoEstabilidade(let c), .estavel):
            return (.capturando(c), [.acenderLuz(c.luzAtual), .capturar(passo: c.passoAtual.ordem, luz: c.luzAtual)])

        case (.capturando(var c), .fotoCapturada(let ok)):
            if ok {
                c.fotosEnfileiradas += 1
                return proximaFoto(c)
            }
            c.tentativas += 1
            if c.tentativas >= tentativasMax {
                c.tentativas = 0
                c.luz = 0
                return (.pausado(.precisaAjuda, retomar: .posicionar(c)), [.desligarLuzes, .falar("Preciso de ajuda neste passo.")])
            }
            // repete o passo inteiro: o técnico pode ter mexido no aparelho
            c.luz = 0
            return (.aguardandoEstabilidade(c), [.desligarLuzes, .falar("Repetindo.")])

        case (.capturando, .luzFalhou):
            return (.pausado(.luzSemResposta, retomar: estado), [.desligarLuzes])
        case (_, .cameraInterrompida) where estado.emCaptura:
            return (.pausado(.cameraInterrompida, retomar: estado.retomavel), [.desligarLuzes])
        case (_, .temperaturaCritica) where estado.emCaptura:
            return (.pausado(.temperaturaAlta, retomar: estado.retomavel), [.desligarLuzes, .falar("Cabine quente: pausando.")])
        case (.pausado(_, let retomar), .retomar):
            if case .capturando(let c) = retomar { return (.aguardandoEstabilidade(c), []) }
            return (retomar, [])

        case (.concluindo(let c), .conclusaoAceita):
            return (.aguardandoSugestao(c), [.consultarSugestao(token: c.token)])
        case (.concluindo(var c), .conclusaoRecusada(let faltando)):
            c.passosPendentes = c.abertura.roteiro.passos.indices.filter { faltando.contains(c.abertura.roteiro.passos[$0].ordem) }
            guard let primeiro = c.passosPendentes.first else { return (.erro("Conclusão recusada sem passos faltando"), []) }
            c.passo = primeiro
            c.luz = 0
            return posicionar(c)

        case (.aguardandoSugestao(let c), .sugestao(let s)):
            if s.status == "pronta" || s.status == "erro" {
                return (.resultado(c, s), [.pedirTela(token: c.token, acao: "normal"), .falar(s.mostrar ? "Nota \(s.nota_final ?? "")." : "Pronto.")])
            }
            return (estado, [.consultarSugestao(token: c.token)])

        case (.resultado(var c, _), .refazerFaces(let faces)) where !faces.isEmpty:
            c.passosPendentes = c.abertura.roteiro.passos.indices.filter {
                !Set(c.abertura.roteiro.passos[$0].faces).isDisjoint(with: faces)
            }
            guard let primeiro = c.passosPendentes.first else { return (estado, []) }
            c.passo = primeiro
            c.luz = 0
            c.tentativas = 0
            return (.apagandoTela(c), [.pedirTela(token: c.token, acao: "preto")])

        case (.resultado, .proximoAparelho), (.erro, .proximoAparelho), (_, .cancelar):
            return (.aguardandoQR, [.desligarLuzes])

        default:
            break
        }
        return (estado, [])  // evento fora de hora: ignorado
    }

    private static func posicionar(_ c: Captura) -> (EstadoCabine, [EfeitoCabine]) {
        (.posicionar(c), [.aplicarFoco(c.passoAtual.pose), .falar(c.passoAtual.instrucao)])
    }

    private static func proximaFoto(_ c0: Captura) -> (EstadoCabine, [EfeitoCabine]) {
        var c = c0
        if c.luz + 1 < c.passoAtual.luzes.count {
            c.luz += 1
            return (.capturando(c), [.acenderLuz(c.luzAtual), .capturar(passo: c.passoAtual.ordem, luz: c.luzAtual)])
        }
        // fim do passo
        c.tentativas = 0
        c.luz = 0
        c.passosPendentes.removeAll { $0 == c.passo }
        if let proximo = c.passosPendentes.first {
            c.passo = proximo
            return (.posicionar(c), [.desligarLuzes, .aplicarFoco(c.passoAtual.pose), .falar(c.passoAtual.instrucao)])
        }
        return (.concluindo(c), [.desligarLuzes, .concluir(token: c.token, fotos: c.fotosEnfileiradas)])
    }
}

extension EstadoCabine {
    var emCaptura: Bool {
        switch self {
        case .posicionar, .aguardandoEstabilidade, .capturando, .verificando: true
        default: false
        }
    }

    /// Ao retomar uma captura interrompida, volta a esperar estabilidade (a cena pode ter mudado).
    var retomavel: EstadoCabine {
        if case .capturando(let c) = self { return .aguardandoEstabilidade(c) }
        return self
    }

    public var captura: Captura? {
        switch self {
        case .apagandoTela(let c), .posicionar(let c), .aguardandoEstabilidade(let c), .capturando(let c),
             .verificando(let c), .concluindo(let c), .aguardandoSugestao(let c), .resultado(let c, _):
            c
        default: nil
        }
    }
}
