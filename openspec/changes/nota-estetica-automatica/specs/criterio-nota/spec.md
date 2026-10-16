## ADDED Requirements

### Requirement: Critério versionado em YAML
O critério SHALL ficar em `criterios/criterio-v<n>.yaml`, validado por esquema que recusa chaves desconhecidas e valores fora dos enums. Mudança de regra MUST gerar nova versão.

#### Scenario: Chave desconhecida
- **WHEN** o YAML contém uma chave que o esquema não conhece
- **THEN** o carregamento falha com erro de validação

### Requirement: Motor puro
`avaliar(defeitos, modelo, criterio)` SHALL ser função pura (sem banco, rede ou relógio) e devolver notas por face, nota final, justificativas, margens e pendências.

#### Scenario: Face sem defeitos
- **WHEN** uma face não tem defeitos
- **THEN** a nota da face é A

#### Scenario: Nota final
- **WHEN** as faces têm notas A, B e C
- **THEN** a nota final é C (pior face)

#### Scenario: Trinca na tela
- **WHEN** há um defeito `trinca` na zona `tela`
- **THEN** a face frente recebe D

### Requirement: Propriedades de monotonia
O motor MUST respeitar: acrescentar defeito nunca melhora a nota; retirar nunca piora; a ordem dos defeitos não muda o resultado.

#### Scenario: Teste de propriedades
- **WHEN** listas aleatórias de defeitos são avaliadas com `hypothesis`
- **THEN** todas as propriedades valem

### Requirement: Regras "a definir" e margens
Regras marcadas `a_definir` acionadas SHALL aparecer em `pendencias`; a margem SHALL ser a menor distância relativa entre medida e limite.

#### Scenario: Medida perto do limite
- **WHEN** um risco só rasante mede 5,3 mm e o limite é 5 mm
- **THEN** a margem é 6% e o resultado não pode virar nota automática

### Requirement: Linha de base humana
Antes de aprovar `criterio-v1`, dois técnicos SHALL avaliar os mesmos 20 aparelhos às cegas, atingindo concordância exata ≥ 85% e kappa ponderado quadrático ≥ 0,80.

#### Scenario: Estudo aprovado
- **WHEN** o estudo atinge as metas
- **THEN** o kappa obtido é guardado como linha de base do gate do modo automático
