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
