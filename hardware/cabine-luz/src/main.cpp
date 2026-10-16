// Firmware da cabine de luz (guia 7.10).
// HTTP na rede local: GET /estado, POST /luz, POST /desligar.
// Cabeçalho X-Chave-Cabine obrigatório. PWM a 20 kHz. Apaga tudo após 120 s sem comando.

#include <Arduino.h>
#include <ArduinoJson.h>
#include <ESPmDNS.h>
#include <WebServer.h>
#include <WiFi.h>

#include "segredos.h"

#ifndef VERSAO_FIRMWARE
#define VERSAO_FIRMWARE "dev"
#endif

// ---------------------------------------------------------------- configuração

struct Canal {
  const char *nome;
  uint8_t pino;
  uint8_t ledc;  // canal LEDC (só na API 2.x do arduino-esp32)
  uint8_t pct;   // 0 a 100
};

Canal canais[] = {
    {"a", 25, 0, 0},
    {"b", 26, 1, 0},
    {"difusa", 27, 2, 0},
    {"contraluz", 14, 3, 0},
};
const size_t N_CANAIS = sizeof(canais) / sizeof(canais[0]);

const uint8_t PINO_LED_PLACA = 2;
const uint32_t PWM_FREQ_HZ = 20000;  // ≥ 20 kHz: sem faixas na foto
const uint8_t PWM_BITS = 10;
const uint32_t PWM_MAX = (1u << PWM_BITS) - 1;
const uint32_t DESLIGAR_APOS_MS = 120000;

WebServer servidor(80);
uint32_t ultimoComandoMs = 0;

// ---------------------------------------------------------------- PWM

void pwmIniciar(Canal &c) {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcAttach(c.pino, PWM_FREQ_HZ, PWM_BITS);
#else
  ledcSetup(c.ledc, PWM_FREQ_HZ, PWM_BITS);
  ledcAttachPin(c.pino, c.ledc);
#endif
}

void aplicar(Canal &c, uint8_t pct) {
  c.pct = pct;
  uint32_t duty = (uint32_t)pct * PWM_MAX / 100;
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcWrite(c.pino, duty);
#else
  ledcWrite(c.ledc, duty);
#endif
}

void desligarTudo() {
  for (auto &c : canais) aplicar(c, 0);
}

// ---------------------------------------------------------------- HTTP

bool autorizado() {
  if (servidor.header("X-Chave-Cabine") == CHAVE_CABINE) {
    ultimoComandoMs = millis();
    return true;
  }
  servidor.send(401, "application/json", "{\"erro\":\"chave inválida\"}");
  return false;
}

void responderEstado(int status = 200) {
  JsonDocument doc;
  JsonObject obj = doc["canais"].to<JsonObject>();
  for (auto &c : canais) obj[c.nome] = c.pct;
  doc["versao"] = VERSAO_FIRMWARE;
  doc["uptime_s"] = millis() / 1000;
  String corpo;
  serializeJson(doc, corpo);
  servidor.send(status, "application/json", corpo);
}

void erro(int status, const char *mensagem) {
  JsonDocument doc;
  doc["erro"] = mensagem;
  String corpo;
  serializeJson(doc, corpo);
  servidor.send(status, "application/json", corpo);
}

void rotaEstado() {
  if (autorizado()) responderEstado();
}

void rotaLuz() {
  if (!autorizado()) return;
  JsonDocument doc;
  if (deserializeJson(doc, servidor.arg("plain")) || !doc.is<JsonObject>()) {
    erro(400, "JSON inválido");
    return;
  }
  // Valida tudo antes de aplicar: ou muda tudo, ou nada.
  int novo[N_CANAIS];
  for (size_t i = 0; i < N_CANAIS; i++) novo[i] = -1;  // -1 = sem mudança
  for (JsonPair par : doc.as<JsonObject>()) {
    size_t i = 0;
    while (i < N_CANAIS && strcmp(canais[i].nome, par.key().c_str()) != 0) i++;
    if (i == N_CANAIS) {
      erro(400, "canal desconhecido");
      return;
    }
    if (!par.value().is<int>() || par.value().as<int>() < 0 || par.value().as<int>() > 100) {
      erro(400, "valor deve ser inteiro de 0 a 100");
      return;
    }
    novo[i] = par.value().as<int>();
  }
  for (size_t i = 0; i < N_CANAIS; i++)
    if (novo[i] >= 0) aplicar(canais[i], novo[i]);
  responderEstado();  // estado depois de aplicar (resposta síncrona)
}

void rotaDesligar() {
  if (!autorizado()) return;
  desligarTudo();
  responderEstado();
}

// ---------------------------------------------------------------- Wi-Fi

void conectarWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);  // latência baixa nas respostas
  WiFi.begin(WIFI_SSID, WIFI_SENHA);
  bool aceso = false;
  while (WiFi.status() != WL_CONNECTED) {
    aceso = !aceso;
    digitalWrite(PINO_LED_PLACA, aceso);  // pisca até conectar
    delay(250);
  }
  digitalWrite(PINO_LED_PLACA, HIGH);
  Serial.printf("Wi-Fi conectado: %s\n", WiFi.localIP().toString().c_str());
}

void setup() {
  Serial.begin(115200);
  pinMode(PINO_LED_PLACA, OUTPUT);
  for (auto &c : canais) {
    pwmIniciar(c);
    aplicar(c, 0);
  }
  conectarWifi();

  if (MDNS.begin(NOME_MDNS)) {
    MDNS.addService("http", "tcp", 80);
    MDNS.addServiceTxt("http", "tcp", "tipo", "cabine-luz");
    Serial.printf("mDNS: %s.local\n", NOME_MDNS);
  }

  const char *cabecalhos[] = {"X-Chave-Cabine"};
  servidor.collectHeaders(cabecalhos, 1);
  servidor.on("/estado", HTTP_GET, rotaEstado);
  servidor.on("/luz", HTTP_POST, rotaLuz);
  servidor.on("/desligar", HTTP_POST, rotaDesligar);
  servidor.onNotFound([] { erro(404, "rota inexistente"); });
  servidor.begin();
  ultimoComandoMs = millis();
}

void loop() {
  servidor.handleClient();

  if (millis() - ultimoComandoMs > DESLIGAR_APOS_MS) {
    bool algumAceso = false;
    for (auto &c : canais) algumAceso |= c.pct > 0;
    if (algumAceso) {
      desligarTudo();
      Serial.println("Sem comando há 120 s: luzes apagadas");
    }
  }

  if (WiFi.status() != WL_CONNECTED) {
    desligarTudo();
    conectarWifi();
  }
}
