# Testar o app no seu iPhone

Roteiro para quem vai testar o app da nota estética num iPhone de verdade, **sem a cabine montada**
(sem barras de luz nem ESP32). O backend roda no seu Mac; o iPhone conversa com ele pelo Wi-Fi.

Tempo: ~1 h para preparar e ~1 h de testes. No fim você manda um pacote com os resultados (Parte C).

## O que você precisa

- **Mac** com macOS 15 ou mais novo, Apple Silicon de preferência (8 GB de memória serve).
- **Xcode 16+** (App Store).
- **iPhone com iOS 17+.** O ideal é câmera de 48 MP (14 Pro ou mais novo, ou 15/16/17), que é o que a
  cabine vai usar. Outro iPhone serve, e anote o modelo.
- **Apple ID.** A conta gratuita basta para instalar no seu próprio iPhone.
- **Mac e iPhone no mesmo Wi-Fi**, numa rede que deixe os aparelhos se enxergarem (redes de
  visitantes costumam bloquear).
- Para os testes de câmera:
  - um apoio para deixar o iPhone **olhando para baixo**, parado, a ~25 cm da mesa (tripé com garra
    de celular ou uma pilha de livros);
  - a folha de marcadores impressa em 100%: `hardware/cabine-a/marcadores-aruco.pdf`;
  - um pano ou cartolina preta fosca;
  - um "aparelho avaliado": outro celular qualquer, de preferência um iPhone.

---

## Parte A — Preparar (uma vez)

1. **Baixar o projeto** e preparar o ambiente (instala o que faltar com Homebrew):

   ```bash
   git clone https://github.com/eduscanai/iphone.git morecheck && cd morecheck
   scripts/configurar_dev.sh --instalar
   ```
   _Esperado:_ termina com "Pronto. Próximos passos".

2. **Plataforma iOS no Xcode:** Xcode → Settings → Components → instalar **iOS** (~8 GB).

3. **Subir o backend para a rede:**

   ```bash
   scripts/subir_dev.sh --rede
   ```
   Anote o endereço que aparece em "no app do iPhone, use: http://<nome-do-mac>.local:8000" e os
   tokens do **técnico** e do **admin**. Se o macOS perguntar sobre conexões de entrada para o
   Python, clique em **Permitir**.
   _Confira:_ no Safari do **iPhone**, abra `http://<nome-do-mac>.local:8000/saude`. Deve aparecer
   `{"ok":true}`. Se não abrir, veja "Problemas comuns".

4. **Instalar o app no iPhone:**
   - Xcode → Settings → Accounts → entre com seu Apple ID e anote o **Team ID** (10 caracteres).
   - Rode o script abaixo; ele abre o Xcode já configurado:

     ```bash
     scripts/preparar_iphone.sh <TEAM_ID>
     ```
   - Conecte o iPhone no cabo, escolha-o no topo do Xcode e aperte **⌘R**.
   - Na primeira vez, no iPhone:
     - Ajustes → Privacidade e Segurança → **Modo de Desenvolvedor** → ligar e reiniciar;
     - Ajustes → Geral → **VPN e Gerenciamento de Dispositivos** → confiar no seu Apple ID.

   _Esperado:_ o app **Morecheck** abre com o menu "Modo Cabine" e "Tela Estética".

---

## Parte B — Testes

Anote o resultado de cada teste (ok, falhou ou observação) no relato da Parte C.

### B1. Painel no Mac

Abra o painel no navegador do Mac (endereço impresso pelo `subir_dev.sh`) e entre com o token do **técnico**.
Rode `scripts/simular_aparelho.sh` no Terminal.
_Esperado:_ aparece um iPhone 13 na fila; dá para abrir, ver a frente retificada e os riscos.

### B2. Tela QR + preto (o iPhone faz o papel do aparelho avaliado)

1. No Mac: `scripts/nova_sessao.sh`. Anote o **token** que aparece.
2. No iPhone: app → **Tela Estética** → API = o endereço da etapa A3; Token = o token → abrir.
   _Esperado:_ QR em tela cheia, fundo branco.
3. No Mac: `scripts/comando_tela.sh <token> preto`
   _Esperado:_ em até **2 s**, a tela fica preta, o brilho vai ao mínimo e somem a barra de status e
   o indicador de início. Cronometre.
4. No Mac: `scripts/comando_tela.sh <token> qr`
   _Esperado:_ o QR volta e o brilho volta ao que era.
5. Desligue o Wi-Fi do iPhone com a tela aberta.
   _Esperado:_ aparece a mensagem para travar o aparelho manualmente.
6. Se tiver um iPhone com tela **LCD** (SE, XR, 11), repita o passo 3 nele: a tela fica preta de verdade?

### B3. Pareamento da cabine

1. Painel no Mac, entrando com o token do **admin** → Concordância → **Cabines** → "Parear nova cabine".
2. No iPhone: app → **Modo Cabine** → permita a câmera → em "API" ponha o endereço da etapa A3 → digite
   o código → **Parear**.
   _Esperado:_ a cabine aparece na lista do painel e o app vai para a calibração.

### B4. Calibração

Monte o "berço" improvisado: iPhone no apoio, olhando para baixo, ~25 cm acima da mesa, com o pano
preto e a folha de marcadores embaixo. Sem ESP32, as etapas de luz passam sem acender nada (normal).

No app, execute os 6 passos do assistente. Anote, para cada passo, a mensagem que aparece:
exposição e ISO, foco, px/mm e se achou os marcadores.
_Esperado:_ termina com "Perfil v1 salvo" e a tela "Aponte para o QR".

### B5. Uma avaliação completa (o teste principal)

1. No Mac: `scripts/nova_sessao.sh` (ou `scripts/nova_sessao.sh iPhone16,1` se o "aparelho avaliado"
   for um 15 Pro; a lista de modelos está em `backend/app/estetica/dimensoes.py`). O QR abre na tela
   do Mac. Mande a imagem para outro celular (AirDrop) ou imprima, e ponha o QR embaixo da câmera.
2. _Esperado:_ o app lê o QR, mostra o nome do modelo e "FRENTE".
3. Tire o QR e ponha o "aparelho avaliado" de **tela para cima** no lugar. Não mexa.
   _Esperado:_ "Aguardando imagem parada…" → 3 fotos (ambiente, rasante A, rasante B) → "TRASEIRA".
   Se ficar mais de 10 s em "Aguardando imagem parada", o app não achou o contorno do aparelho:
   anote isso (com o modelo e a cor do aparelho) e toque em **"Fotografar agora"**.
4. Vire o aparelho (**traseira para cima**). _Esperado:_ mais 3 fotos → "Processando…" → nota sugerida.
5. No painel do Mac (técnico), abra a sessão: as fotos aparecem retificadas?
6. Anote:
   - o tempo total, do QR lido até a nota;
   - quantas vezes alguma foto foi repetida e qual motivo apareceu embaixo, na tela do app.

**Se o app ficar repetindo a mesma foto** ("Foto reprovada: tremida/estourada/contorno não
encontrado"): anote os motivos e ligue em Ajustes (na tela "Aponte para o QR") a opção **"Não reprovar
pela qualidade local (teste)"**. Repita o B5. As medidas continuam sendo gravadas e servem para calibrar.

### B6. Câmera e robustez (checklist)

| # | Teste | Como conferir |
|---|---|---|
| 1 | Fotos de 8064×6048 | no pacote da Parte C (fotos.tsv, colunas largura e altura) |
| 2 | Exposição, ISO, foco e balanço iguais entre fotos da mesma luz | fotos.tsv, coluna de metadados |
| 3 | Sem faixas horizontais com as lâmpadas da sala | olhe as fotos no painel |
| 4 | Wi-Fi do iPhone desligado no meio da captura | as fotos ficam "na fila" (barra de baixo) e sobem quando o Wi-Fi volta |
| 5 | App para o segundo plano e volta | a captura retoma |
| 6 | 10 avaliações seguidas (B5) | o iPhone esquenta? aparece "Pausado: quente demais"? |
| 7 | Tempo por avaliação | meta da cabine: ≤ 60 s |

---

## Parte C — Mandar os resultados

```bash
scripts/exportar_teste.sh            # pacote leve: metadados, qualidade, logs e capturas
scripts/exportar_teste.sh --fotos    # com as fotos originais (grande), só se pedirem
```

O arquivo vai para a Mesa. Abra uma issue no GitHub com o modelo **"Relato de teste no iPhone"**,
preencha a lista e anexe o .zip. Prints e vídeos curtos da tela do iPhone ajudam muito.

Para desligar tudo no Mac: `scripts/parar_dev.sh`.

---

## Problemas comuns

| Sintoma | O que fazer |
|---|---|
| Safari do iPhone não abre `…local:8000/saude` | Mac e iPhone na mesma rede? Rede de visitantes isola os aparelhos. Tente `scripts/parar_dev.sh && scripts/subir_dev.sh --rede --ip` e use o endereço com IP. Confira o Firewall do macOS (Ajustes → Rede → Firewall). |
| Xcode: "Signing requires a development team" | rode `scripts/preparar_iphone.sh <TEAM_ID>` de novo |
| Xcode: bundle ID indisponível | `scripts/preparar_iphone.sh <TEAM_ID> com.seunome.morecheck2` |
| iPhone: "Desenvolvedor não confiável" | Ajustes → Geral → VPN e Gerenciamento de Dispositivos → confiar |
| App: "Modelo … sem dimensões cadastradas" | use em `nova_sessao.sh` um identificador de `backend/app/estetica/dimensoes.py` |
| App: "Câmera indisponível" | Ajustes → Morecheck → Câmera ligada |
| App não acha o servidor depois de trocar de rede | Ajustes da cabine → API com o endereço novo |
