// Pareamento da cabine (D10): o painel mostra um QR com o código; o app chama /cabines/ativar e
// guarda o token no Keychain. O backend guarda só o hash.
import CabineNucleo
import Foundation
import Security

enum Cofre {
    private static let servico = "com.morecheck.cabine"

    static func guardar(_ valor: String, conta: String) {
        let base: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: servico,
                                   kSecAttrAccount as String: conta]
        SecItemDelete(base as CFDictionary)
        var novo = base
        novo[kSecValueData as String] = Data(valor.utf8)
        novo[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        SecItemAdd(novo as CFDictionary, nil)
    }

    static func ler(_ conta: String) -> String? {
        let q: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: servico,
                                kSecAttrAccount as String: conta, kSecReturnData as String: true]
        var item: CFTypeRef?
        guard SecItemCopyMatching(q as CFDictionary, &item) == errSecSuccess, let d = item as? Data else { return nil }
        return String(data: d, encoding: .utf8)
    }

    static func apagar(_ conta: String) {
        SecItemDelete([kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: servico,
                       kSecAttrAccount as String: conta] as CFDictionary)
    }
}

/// Configuração local da cabine: API, ESP32 (mDNS ou IP fixo) e chave das luzes.
struct ConfigCabine: Codable, Equatable {
    var api: String = "https://api-check.more-megastore.com"
    var esp32: String = "http://morecheck-cabine-1.local"
    var temDifusa = false
    var vozLigada = true
    /// Teste: não reprova foto pela qualidade local (as medidas continuam indo nos metadados).
    /// Útil enquanto os limiares não foram calibrados num iPhone real (fase 2).
    var ignorarQualidadeLocal = false

    init() {}

    // Decodifica arquivos antigos (sem os campos novos) sem perder a configuração.
    init(from d: Decoder) throws {
        let c = try d.container(keyedBy: CodingKeys.self)
        api = try c.decodeIfPresent(String.self, forKey: .api) ?? api
        esp32 = try c.decodeIfPresent(String.self, forKey: .esp32) ?? esp32
        temDifusa = try c.decodeIfPresent(Bool.self, forKey: .temDifusa) ?? false
        vozLigada = try c.decodeIfPresent(Bool.self, forKey: .vozLigada) ?? true
        ignorarQualidadeLocal = try c.decodeIfPresent(Bool.self, forKey: .ignorarQualidadeLocal) ?? false
    }

    static var atual: ConfigCabine {
        get { (UserDefaults.standard.data(forKey: "cabine.config")).flatMap { try? JSONDecoder().decode(Self.self, from: $0) } ?? .init() }
        set { UserDefaults.standard.set(try? JSONEncoder().encode(newValue), forKey: "cabine.config") }
    }
}

enum Pareamento {
    static var token: String? { Cofre.ler("token") }
    static var chaveLuz: String? { Cofre.ler("chave-luz") }

    /// QR do painel: JSON {"api": "...", "codigo": "K7PQ-3XWD"} ou só o código.
    static func lerQR(_ texto: String) -> (api: String?, codigo: String) {
        if let d = texto.data(using: .utf8), let j = try? JSONSerialization.jsonObject(with: d) as? [String: String], let c = j["codigo"] {
            return (j["api"], c)
        }
        return (nil, texto.trimmingCharacters(in: .whitespacesAndNewlines).uppercased())
    }

    static func ativar(qr: String, nome: String) async throws {
        let (api, codigo) = lerQR(qr)
        var cfg = ConfigCabine.atual
        if let api { cfg.api = api; ConfigCabine.atual = cfg }
        let r = try await ClienteAPI.ativar(base: URL(string: cfg.api)!, codigo: codigo, nome: nome)
        Cofre.guardar(r.token, conta: "token")
    }

    static func esquecer() {
        Cofre.apagar("token")
    }
}
