// STUB do app Morecheck: no app real, o modo Cabine fica nas configurações (fora do fluxo
// normal de testes) e a tela QR + preto aparece no fim dos testes funcionais (guia 10.3 e 10.4).
import SwiftUI

@main
struct MorecheckApp: App {
    var body: some Scene {
        WindowGroup { Inicio() }
    }
}

struct Inicio: View {
    @State private var api = ConfigCabine.atual.api
    @State private var token = ""

    var body: some View {
        #if DEBUG
        // Testes no simulador sem tocar na tela (argumentos de inicialização viram UserDefaults):
        //   -testeTela qr -testeApi http://127.0.0.1:8000 -testeToken <token da sessão>
        //   -testeTela cabine [-testeApi …] [-testeCodigo K7PQ-3XWD]
        let d = UserDefaults.standard
        if d.string(forKey: "testeTela") == "qr", let a = URL(string: d.string(forKey: "testeApi") ?? ""), let t = d.string(forKey: "testeToken") {
            return AnyView(TelaQRPreto(api: a, token: t))
        }
        if d.string(forKey: "testeTela") == "cabine" {
            if let a = d.string(forKey: "testeApi") { var c = ConfigCabine.atual; c.api = a; ConfigCabine.atual = c }
            return AnyView(CabineView())
        }
        #endif
        return AnyView(menu)
    }

    private var menu: some View {
        NavigationStack {
            List {
                Section("iPhone da empresa") {
                    NavigationLink("Modo Cabine") { CabineView() }
                }
                Section("Aparelho avaliado (teste)") {
                    TextField("API", text: $api)
                    TextField("Token da sessão", text: $token)
                    NavigationLink("Tela Estética (QR + preto)") {
                        if let u = URL(string: api) { TelaQRPreto(api: u, token: token) }
                    }.disabled(token.isEmpty)
                }
            }
            .navigationTitle("Morecheck")
        }
    }
}
