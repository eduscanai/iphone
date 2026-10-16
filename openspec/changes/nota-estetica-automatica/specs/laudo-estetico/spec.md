## ADDED Requirements

### Requirement: Bloco "Estado estético" no laudo
O laudo PDF SHALL trazer nota final em destaque, origem (`tecnico`, `sugerida` ou `automatica`), miniaturas das faces na luz ambiente, lista de defeitos (tipo, face, zona, medida) e versão do critério.

#### Scenario: Laudo de sessão avaliada
- **WHEN** a sessão tem avaliação final
- **THEN** o laudo gerado contém o bloco com esses campos

### Requirement: Página pública de verificação
A página do QR do laudo SHALL mostrar miniaturas das faces e lista de defeitos, sem fotos originais (conforme D11).

#### Scenario: Acesso público
- **WHEN** alguém abre o QR do laudo
- **THEN** vê miniaturas e defeitos, e nenhuma URL de foto original é exposta

### Requirement: Retenção de fotos
Uma rotina diária SHALL apagar originais com mais de `ESTETICA_RETENCAO_MESES`, exceto fotos com defeito confirmado, registrando o que foi apagado.

#### Scenario: Foto antiga com defeito confirmado
- **WHEN** a retenção encontra uma foto vencida ligada a defeito confirmado
- **THEN** a foto é mantida
