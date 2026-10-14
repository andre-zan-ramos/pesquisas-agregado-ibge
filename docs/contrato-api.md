# Contrato de domínio e API — explorador IBGE v1

Data: 13/10/2026. Fase 0 concluída para contratos e fixtures. Este contrato define o comportamento das fases seguintes; não afirma que as rotas de pesquisa já existem. A fase 1 permanece operante com seu endpoint `health/`.

## 1. Fontes e graus de evidência

| Evidência | Localização | O que comprova |
| --- | --- | --- |
| Documentação oficial de agregados v3, inclusive JavaScript do construtor | [IBGE](https://servicodados.ibge.gov.br/api/docs/agregados?versao=3) e `evidencias/manifest.json` | Operações, parâmetros, modelos e regras publicadas |
| Extração estrutural dos modelos embutidos | `evidencias/api-v3-definitions.json` | Campos e tipos declarados; preserva inconsistências da documentação |
| Convenções de publicações IBGE | [Notas técnicas de Contas Nacionais](https://biblioteca.ibge.gov.br/visualizacao/livros/liv102075_notas_tecnicas.pdf) | Significado dos sinais nessas publicações; não comprova a codificação de toda resposta v3 |
| Código Streamlit inspecionado | Caminho da origem no plano; matriz na seção 12 | Comportamento implementado no legado, sem prova de execução atual |
| Fixtures `synthetic/` | `backend/agregados/tests/fixtures/` | Exemplos inventados e casos de aceitação; não são estatísticas oficiais |
| Oito capturas de dados oficiais | `fixtures/official/manifest.json` | Corpos efetivamente obtidos na fase 0, sem extrapolar sua cobertura |
| Exemplo normalizado derivado da captura | `fixtures/derived/manifest.json` | Resultado esperado do contrato; não é resposta de uma API interna já implementada |

Foram lidas páginas/documentação oficial e capturadas oito respostas JSON em um lote limitado autorizado pela execução desta fase, com uma única tentativa por operação. O lote incluiu A/N/P, metadados/períodos/localidade Brasil do agregado 1712, catálogo filtrado e uma consulta de quatro observações. Os pedidos a páginas auxiliares SIDRA `/ajuda` e API SIDRA `/home/ajuda` retornaram 403 na ferramenta de navegação. A consulta ao PDF `liv95987.pdf` não ficou acessível por essa ferramenta; foi usada outra referência institucional encontrada na pesquisa. Essas falhas não bloquearam o contrato e não foram contornadas por chamadas massivas.

O arquivo de evidências diferencia `official_documentation` de `official_dataset`; os exemplos distinguem `synthetic` de `official`. SHA-256 assegura integridade do artefato salvo, não autenticidade ou completude dos dados de uma pesquisa.

## 2. Operações oficiais utilizadas

Base: `https://servicodados.ibge.gov.br`.

| Operação upstream | Uso do explorador |
| --- | --- |
| `/api/v3/agregados?acervo=A` | Assuntos |
| `/api/v3/agregados?acervo=N` | Níveis territoriais |
| `/api/v3/agregados?acervo=P` | Períodos para descoberta |
| `/api/v3/agregados?assunto=...&nivel=...&periodo=...` | Pesquisas e agregados filtrados |
| `/api/v3/agregados/{id}/metadados` | Variáveis, classificações, categorias e níveis |
| `/api/v3/agregados/{id}/periodos` | Períodos do agregado |
| `/api/v3/agregados/{id}/localidades/{nivel}` | Localidades do agregado no nível escolhido |
| `/api/v3/agregados/{id}/periodos/{periodos}/variaveis/{variaveis}` | Séries no formato padrão, sem `view` |
| `/api/v1/localidades/municipios?view=nivelado` | Enriquecimento auxiliar, condicionado a necessidade |

A/N/P são os acervos do MVP. O construtor documental também lista C, E e V para classificações, periodicidade e variáveis. Não carregar todos por antecipação. A forma `{id,literal}` de A/N/P foi confirmada nas três capturas desta fase; não existe entre os modelos oficiais extraídos um schema de resposta de acervo. Preservar esses campos e tratar divergências futuras explicitamente.

MVP usa IDs explícitos e um nível por consulta. A API oficial permite expressões mais amplas, localidades de níveis mistos, seleções contextuais, períodos negativos/intervalos e diferentes views; esse suporte não é automaticamente parte do explorador. Não aceitar expressões upstream como entrada livre.

## 3. Identidade e literalidade

- Dentro da API interna, IDs são strings. Pesquisa e domínio podem ter IDs não numéricos. IDs de agregado, variável, classificação, categoria, localidade e período usados na consulta v1 são strings de dígitos; níveis seguem `N` + dígitos.
- Na entrada, número JSON não substitui string. Não aplicar `int()` para comparar IDs já textuais; `"0"`, `"00"` e `"000101"` são literais diferentes.
- No upstream, alguns modelos documentam IDs numéricos. Um inteiro JSON pode ser convertido à sua representação decimal em string, sem completar zeros. Booleano, número fracionário ou ID malformado deve gerar erro de estrutura upstream, não uma conversão inferida. Zeros que a fonte não publicou não podem ser reconstruídos.
- A identidade de uma observação é agregado + variável + nível + localidade + período + pares classificação/categoria ordenados por ID. Nomes e unidades são atributos, não chaves.
- `origem_indice` aponta variável/resultado/série no corpo upstream, todos em base zero. Isso identifica ocorrências em diagnóstico; não substitui a identidade de domínio.
- Guardar o valor original e todos os grupos de resultados. Não assumir que `resultados[0]` é um total. Não deduplicar pelo nome.
- `localidade.nivel=null` é permitido pelo modelo documental quando só há um nível. Nesse caso, preencher o nível interno com o único `nivel_id` da consulta validada. Se a fonte informar outro nível, rejeitar como `upstream_inconsistent_data`; não sobrescrever o código explícito.
- Localidades de mesmo nome ficam separadas por ID. UF é enriquecimento auxiliar: usar associação por código oficial e manter o registro mesmo se o enriquecimento não existir. Não inferir município/UF pelo nome.

## 4. Períodos

Separar dois conceitos:

1. `periodo` no catálogo restringe a descoberta de agregados.
2. `periodo_ids` seleciona quais períodos efetivamente serão buscados nas séries.

Períodos são obtidos de `/agregados/{id}/periodos`. Preservar `id`, todos os `literals` e `modificacao`. `modificacao` é uma informação da fonte sobre aquele período, não data de coleta e não data de atualização de toda a consulta.

O metadado normalizado registra `ordem` como posição no catálogo upstream. Essa posição não comprova ordem cronológica. Para frequência mensal, o documento descreve IDs `YYYYMM`; validar meses e ordenar pelo calendário quando esse padrão for confirmado pelo metadado. Para anuais, admitir `YYYY` quando validado pela periodicidade. Na captura 1712, `periodicidade.inicio/fim` vieram como números inteiros 2006, embora o modelo documental declare string: convertê-los para strings decimais no contrato interno e manter o corpo original capturado. `modificacao` veio como `19/10/2012`; preservar esse literal. Em periodicidades não reconhecidas, preservar ordem/rótulos e exigir escolha explícita; não adivinhar datas trimestrais ou escolher os seis últimos elementos como se fossem os seis mais recentes.

Default desejado: até seis períodos cronologicamente mais recentes quando há ordenação verificável. A interface deve exibir o recorte. A opção Todos expande a lista de IDs publicados e passa pelo orçamento. A API interna v1 não recebe `all`, `-6` ou intervalos: recebe a lista resolvida de IDs. A montagem usa `|` entre períodos.

Período ausente na série não vira linha com zero. Pode ser apresentado como lacuna visual derivada do recorte; essa lacuna não é uma observação oficial. Valores especiais retornados para um período são observações e devem permanecer na tabela.

## 5. Classificações, categorias e total

Gramática oficial utilizada:

```text
classificacao=ID_CLASSIFICACAO[ID_CATEGORIA,ID_CATEGORIA]|OUTRA_CLASSIFICACAO[ID_CATEGORIA]
```

As categorias de uma mesma classificação são alternativas; classificações distintas definem combinações pelo produto cartesiano. Uma categoria da resposta é um objeto com uma chave ID e um valor nome. Mais de uma chave em uma mesma ocorrência viola o modelo documental usado por v1 e deve ser sinalizada como estrutura inconsistente, não escolhida pela primeira chave.

O documento descreve total especial `0` e seleção implícita de total quando classificações são omitidas. Nosso contrato exige resolução explícita: uma seleção para cada classificação publicada do agregado, inclusive quando a escolha for Total. Lista vazia só é válida para agregado sem classificações. IDs repetidos de classificação, categorias não pertencentes e listas vazias são erro 400. JSON Schema verifica estrutura; a existência e compatibilidade dependem do catálogo e do validador semântico da fase 3.

Preservar `sumarizacao.status`, `sumarizacao.excecao`, `categorias.unidade`, `categorias.nivel` e `variaveis.sumarizacao`. `nivel` da categoria é hierarquia organizacional, não nível territorial.

Total especial só é selecionável se `sumarizacao.status=true` e nenhuma variável escolhida estiver em `sumarizacao.excecao` daquela classificação. Se `0` não estiver listado em categorias, a UI pode oferecer a opção especial descrita pela API, identificada como Total especial da API e condicionada a essas regras. Não criar uma categoria persistida ou somar valores no cliente. Se a fonte publicar explicitamente outra categoria cujo nome seja Total, usar seu ID literal como categoria comum; o nome não a transforma no código especial `0`.

Uma combinação inválida para alguma variável exige ajuste da seleção antes de Buscar; não remover a variável silenciosamente ou consultar combinações diferentes sem mostrar o recorte. `"00"` não é o total especial `"0"`.

## 6. Níveis territoriais

Unir os grupos `Administrativo`, `Especial` e `IBGE` preservando a origem de cada nível. Não manter um catálogo fechado de quatro níveis. Rótulos vêm do acervo N, quando disponíveis; se não houver rótulo, mostrar o código e manter `nome=null`. Grupo novo desconhecido da fonte deve ser preservado e sinalizado, não descartado.

N6 é preferência inicial se publicado para aquele agregado. Caso contrário, solicitar escolha entre os níveis suportados. Validar localidades exclusivamente contra `/agregados/{id}/localidades/{nivel}`; o catálogo geral de municípios não prova cobertura desse agregado.

Uma consulta interna usa um único nível, no máximo cinco localidades explícitas. Para N1, Brasil é traduzido para `localidades=BR` apenas quando a localidade oficial resolvida é ID `1`, conforme modelo documental. Nos demais níveis: `localidades=N6[ID,ID]` etc. Não usar ID municipal como código de região metropolitana ou qualquer inferência pela aparência do código.

## 7. Valores e estatísticas

Cada observação contém `valor_original`, `valor_numerico` anulável e `valor_status`:

| Situação | Status interno | Número |
| --- | --- | --- |
| Número finito ou string decimal inequívoca, como `10`, `-1.25`, `0.25` | `numerico` | Valor numérico correspondente |
| `X`, `x`, `..`, `...`, `-` | `marcador` | null inicialmente |
| String vazia | `vazio` | null |
| JSON null | `nulo` | null |
| Outro texto, decimal ambíguo ou codificação desconhecida | `nao_reconhecido` | null |

Preservar sinais, zeros negativos e texto exatamente no original. `valor_numerico` serve ao gráfico e ao resumo, não substitui o literal para exportação. Decimal com vírgula não é interpretado automaticamente como número porque pode ser formatação ambígua; rejeitar a conversão e manter o literal até haver regra confirmada para a fonte. Não aceitar NaN/Infinity como valores numéricos finitos.

### Unidade por combinação e divergência observada

Não usar somente `Indicador.unidade` para rotular todas as categorias. Preservar `unidade_original` da resposta, `categoria_unidade` em cada classificação da observação e `unidade_status`. `unidade` é a unidade utilizável para apresentação analítica quando a fonte e os metadados forem coerentes.

Na captura de 1712, variáveis 214/1982 apontam nos metadados para unidades da classificação Produtos da lavoura temporária. Categoria 4844 é Abacaxi, unidade Mil frutos; 96608 é Amendoim em casca, unidade Toneladas. Entretanto, ambas as variáveis retornaram `unidade="Mil frutos"` em todos os resultados, inclusive o amendoim. Isso é uma divergência real deste recorte, não uma suposição de desempenho ou semântica.

Para a categoria do amendoim, o exemplo mantém o número e a unidade original, registra a unidade da categoria, atribui `unidade=null`, `unidade_status="conflitante"` e aviso `unit_metadata_conflict`. A tabela pode mostrar o literal e as duas informações de unidade; gráfico e resumo dessa combinação ficam suspensos até esclarecimento. Não reinterpretar ou converter o número como toneladas por conta própria. Para abacaxi, a unidade é coerente entre as duas fontes.

Essa comparação de unidade da categoria se aplica quando o metadado da variável remete àquela classificação. Não aplicar indiscriminadamente a variáveis percentuais ou monetárias porque uma categoria possui unidade própria. Se a referência não puder ser resolvida sem ambiguidade ou nenhum metadado confirmar a unidade aplicável, `unidade_status="nao_confirmada"`, `unidade=null` e informação contextual; `coerente` significa consistência de fontes neste recorte, não certificação estatística.

As publicações institucionais consultadas atribuem `..` a situação sem aplicabilidade, `...` à indisponibilidade e `x` à omissão por proteção da informação. Elas usam `-` para zero exato. Isso não comprova automaticamente que toda resposta v3 usa a mesma convenção ou capitalização. Por isso a política inicial mantém sinais como marcadores com número null; rótulo pode explicar a convenção e sua fonte. Uma futura regra que converta `-` em zero deve ser sustentada por documentação/notas do agregado, versionada e testada; não chamá-lo de dado ausente por suposição.

Estatísticas são descritivas do recorte, por variável/localidade/combinação de categorias:

- Contar observações numéricas e observações sem número separadamente; lacunas não retornadas não entram nessas contagens.
- Média, mínimo e máximo exigem ao menos um número; desvio padrão amostral usa `n-1` e exige dois números.
- CV (%) = desvio / média × 100 somente com pelo menos duas observações e média positiva. Média zero/negativa ou série sem números retorna null para CV.
- Informar todos os períodos empatados no mínimo/máximo, na ordenação de apresentação validada. Não substituir período por ano.
- Não misturar variáveis/unidades ou categorias em um resumo. Não interpolar, inferir total ou dar interpretação causal às estatísticas.
- Para units inadequadas ao CV ou escalas não comparáveis, expor cautela contextual; não inventar regra de domínio com base só no nome da variável.

## 8. Entrada de consulta e orçamento

Schema estruturado: [`schemas/contrato-v1.schema.json`](schemas/contrato-v1.schema.json), definição `consulta`. Exemplo válido estruturalmente, inteiramente sintético:

```json
{
  "agregado_id": "900001",
  "nivel_id": "N6",
  "localidade_ids": ["0000001", "0000002"],
  "variavel_ids": ["000101", "102"],
  "periodo_ids": ["202401", "202403"],
  "classificacoes": [
    {"classificacao_id": "9001", "categoria_ids": ["01", "02"]},
    {"classificacao_id": "9002", "categoria_ids": ["00"]}
  ]
}
```

Campos extras, URL livre, tipos incorretos, listas obrigatórias vazias e IDs repetidos são rejeitados. Todas as classificações precisam ser resolvidas pelo validador semântico, que também verifica pertinência de variáveis/localidades/períodos ao agregado.

Orçamento conservador da aplicação:

```text
combinações = produto das quantidades de categorias escolhidas por classificação
              (1 quando o agregado não tem classificações)
observações estimadas = variáveis × localidades × períodos × combinações
```

O exemplo estima `2 × 2 × 2 × 2 = 16`, mas a fixture retorna 15 por uma lacuna. O teto da aplicação é 10.000 observações, até seis variáveis, cinco localidades e 4 MiB de resposta, conforme fase 1. A FAQ oficial publica teto de 100.000 valores e fórmula com categorias, períodos e localidades; o multiplicador de variáveis da nossa política é conservador e não é apresentado como fórmula literal do IBGE.

Além da validação prévia, conferir bytes e quantidade real recebida. Metadados não garantem tamanho ou quantidade da resposta. Nunca devolver sucesso truncado. Se exceder, erro 422 com mensagem para reduzir o recorte.

## 9. API interna e formatos de saída

Prefixo `/api/v1/agregados-ibge/`. Apenas `health/` existe na fase 1; demais rotas são o contrato para próximas fases.

| Rota | Entrada | `data` da resposta |
| --- | --- | --- |
| `GET dominios/` | Sem query livre | `{assuntos:[{id,nome}], niveis:[{id,nome}], periodos:[{id,nome}]}` |
| `GET pesquisas/` | `assunto`, `nivel`, `periodo`, `q`, `page`, `page_size`, todos opcionais e validados | `{items:[{id,nome,agregados:[{id,nome}]}], pagination:{page,page_size,total_count,has_next}}` |
| `GET agregados/{id}/metadados/` | ID do agregado | Metadados normalizados conforme schema, incluindo catálogo de períodos |
| `GET agregados/{id}/periodos/` | ID do agregado | `{items:[{id,literals,modificacao,ordem}]}` |
| `GET agregados/{id}/localidades/` | `nivel` obrigatório; `q`, `page`, `page_size` opcionais | `{items:[{id,nome,nivel_id,uf_sigla}], pagination:{page,page_size,total_count,has_next}}` |
| `POST consultas/validar/` | JSON `consulta` | `{consulta_resolvida, source_url, estimated_observations, limites, warnings}` |
| `POST consultas/executar/` | JSON `consulta` | `dadosResultado` definido no schema |

As respostas novas usam envelope `{"data": ..., "sources": [...]}`. Cada source é `{source_url,fetched_at,expires_at,cache_hit}`. Para resposta composta, registrar cada requisição utilizada, inclusive períodos/metadados usados para validar e contextualizar o resultado. O cliente Python da fase 1 continua retornando um envelope por requisição; os serviços das fases seguintes fazem a composição, sem alterar esse transporte.

`consultas/validar/` pode carregar catálogos para validação, mas não requisita séries. `source_url` dentro de seu `data` é a URL de séries que seria executada; não é uma captura. `sources` identifica somente requisições de catálogo efetivamente usadas. Em `consultas/executar/`, a source de séries é uma das entradas de `sources`; não inventar `fetched_at` para uma URL apenas gerada.

Exemplo completo de séries: `fixtures/synthetic/resultado_esperado.json`, validado pela definição `resultado`. O `data` traz `consulta_aplicada`, `observacoes`, `metadados`, `warnings`, `truncated=false` e `normalizer_version="v1"`. O schema cobre entrada, resultado, metadados, observações, proveniência, erro e paginação. Estruturas de catálogo/domínios descritas acima deverão receber serializers e esquemas completos ao implementar a fase 2; não são rotas existentes ou respostas capturadas.

Implementação da fase 4: `consultas/executar/` preserva esse formato e acrescenta `corpo_original`, `periodos_apresentacao`, `ordem_cronologica` e `analises`, definidos no schema. Esses campos são sempre emitidos pelo endpoint e opcionais no schema para compatibilidade com exemplos históricos. Regras, validações e limites em [FASE_4.md](FASE_4.md). Não há cache de resultado normalizado; cada execução reaplica o normalizador v1 sobre o transporte/cache bruto existente.

Padrão de página: 1; tamanho: 50; teto: 200. Paginação é interna, sobre catálogo completo validado/cached, não uma capacidade presumida do IBGE. Filtrar antes de paginar. Nome/código são pesquisáveis; normalização de acentos só auxilia busca/ordenação, sem reescrever labels. IDs servem de desempate estável.

Em pesquisas, os filtros upstream definem pesquisas e seus agregados. `q` interno encontra pesquisa ou agregado: se encontrar apenas agregados, limitar `agregados` aos correspondentes; se o nome/ID da pesquisa corresponder, manter seus agregados do recorte. `total_count` conta pesquisas exibidas, não agregados. Contagem desconhecida é null, nunca zero inventado. `has_next=null` significa desconhecido; quando a lista completa tiver sido obtida, devolver contagem e booleano reais.

Para localidade sem enriquecimento, `uf_sigla=null` e o nome oficial permanece. O retorno de domínio é coleção, não lista editorial fechada.

## 10. Erros, consistência e estado da UI

Envelope de erro preserva a fase 1: `{"error":{"code":...,"message":...,"details":...}}`.

| Status | Situação |
| --- | --- |
| 400 `invalid_selection` | Campo, pertinência ou combinação inválida; detalhes identificam campo/IDs |
| 422 `query_too_large` / `response_too_large` | Orçamento, quantidade ou bytes excedidos |
| 429 `upstream_busy` | Concorrência local indisponível |
| 502 erros upstream da fase 1 | HTTP, conexão, JSON, redirecionamento ou indisponibilidade |
| 502 `upstream_inconsistent_data` | Resposta estrutural/dimensionalmente conflitante |
| 504 `upstream_timeout` | Tempo de resposta excedido |

HTTP 200 vazio é diferente de falha. Não reinterpretar 404 upstream como seleção vazia. Não repetir erro semântico ou um conflito de dados automaticamente. A FAQ do IBGE menciona erro 500 para consulta acima do teto; validar orçamento antes de acessar séries, pois transporte sozinho não distingue esse caso de falha transitória genérica.

Ocorrências idênticas não são eliminadas silenciosamente: preservar índices e emitir aviso, mantendo estatísticas sem dupla contagem por identidade após regra explícita documentada. Ocorrências com mesma identidade e valores conflitantes rejeitam a normalização com 502 e diagnóstico de índices, sem escolher o primeiro/último. A fixture de conflito mantém ambas como evidência. Não persistir payloads produtivos automaticamente para esse diagnóstico.

Campos novos da resposta upstream que não alteram a identidade devem ser preservados no corpo bruto e gerar aviso quando não mapeados. Campo obrigatório ausente, tipo incompatível ou dimensão inesperada é erro estruturado. Não esconder uma variável/grupo não solicitado; sinalizar inconsistência e bloquear resultado parcial.

Seleções editam rascunho. Apenas Buscar dispara séries; validação/geração de URL não implica execução. Último resultado aplicado permanece durante edições, com aviso de mudanças pendentes. Trocar agregado/nível limpa somente seleções incompatíveis. Restauro pela URL revalida os IDs e não executa séries automaticamente.

## 11. Agregado de referência e recorte inicial

**Referência documental e capturada: agregado 1712**, Censo Agropecuário. Recorte validado em uma consulta pequena:

- Brasil, N1, localidade 1 traduzida para `BR`.
- Variáveis 214 e 1982, citadas no exemplo documental.
- Classificação 226, categorias 4844 e 96608; classificação 218, categoria 4780, citadas nos exemplos.
- Período publicado 2006, confirmado pelo endpoint de períodos.
- Demais classificações 12517, 220, 12523 e 12617 resolvidas explicitamente para total especial 0 após conferir status/exceções.

Essa captura comprova disponibilidade desse recorte no horário registrado no manifest, não cobertura de todos os agregados nem disponibilidade futura. As seis classificações foram confirmadas nos metadados. A documentação textual identifica incorretamente 96608 como alho em um exemplo: usar o nome publicado nos metadados capturados, Amendoim em casca. A fixture sintética equivalente usa outro agregado (`900001`) para impedir confusão com dados oficiais.

O corpo retornou quatro valores literais: 214/4844 = `456692`; 214/96608 = `86804`; 1982/4844 = `424883`; 1982/96608 = `76216`. Esses valores não devem receber unidade reinterpretada quando houver conflito. A consulta resolvida integral está em `official/consulta_1712.json`; a resposta em `official/series_1712.json`.

## 12. Matriz legado → novo e evidência de aceite

| Legado | Regra do novo contrato | Evidência nesta fase |
| --- | --- | --- |
| `parametros.py`, acervos A/N/P | Domínios dinâmicos, período do catálogo separado do recorte de séries | `acervos.json`, seção 2 |
| `pesquisas.py`, pesquisa/agregado | IDs literais e listas aninhadas pesquisáveis | `catalogo.json`, seção 9 |
| `agregado.py`, metadados | Sumarização, exceções e todos os grupos de níveis | Fixtures de metadados |
| `agregado.py`, join municipal | Preservar localidade sem UF | Localidades e enriquecimento parcial |
| `agregado.py`, botão Buscar | Rascunho separado de execução | Seção 10; implementação na fase 3 |
| `resposta.py`, `periodos=all` | IDs publicados e orçamento explícito | Consulta mensal e lacuna |
| `resposta.py`, primeiro resultado | Todos os grupos e categorias entram na identidade | 15 observações em duas variáveis/combinações |
| `resposta.py`, `astype(float)` | Original + número nullable + status | Marcadores, null, vazio e texto desconhecido |
| `resposta.py`, nome como coluna | Identidade por nível/ID | Localidades homônimas com zeros |
| `resposta.py`, estatísticas automáticas | Regras para n, média zero/negativa e empates | `estatisticas_casos.json`; implementação na fase 4 |
| `README.md`, gerar links | Validar sem buscar e copiar URL oficial | Seções 8/9; implementação na fase 3 |

## 13. Incertezas que continuam explícitas

1. Formatos de IDs ou campos adicionais fora das oito respostas capturadas; não extrapolar uma amostra para todo o catálogo.
2. O schema documental de `Indicador_series.serie` declara array, mas sua descrição descreve um objeto período → valor, confirmado na captura 1712. O contrato usa o objeto; se outra resposta devolver array, rejeitar/diagnosticar em vez de adivinhar.
3. Nível null é documentado, mas ainda não foi observado em uma captura desta entrega.
4. Codificação concreta dos sinais especiais, casas decimais, dados nulos e notas em cada agregado. Convenções de publicação não comprovam universalidade na API.
5. Ordem cronológica dos períodos fora dos padrões reconhecidos; `modificacao` pode variar em formato.
6. Cobertura territorial de 1712 fora do Brasil e divergência de unidade entre séries e categorias; a captura limitada não valida todos os níveis ou combinações.
7. Regras de IDs novos ou variáveis percentuais geradas: o MVP usa variáveis explicitamente publicadas; `all/allxp` não é entrada interna.
8. Eficácia dos tempos/cache/limites da fase 1: escolhas locais, sem benchmark do IBGE.

Essas incertezas não impedem implementar domínio, UI e testes isolados conforme contrato. Impedem extrapolar aceitação operacional/estatística a toda a fonte. A fase 0 entrega contrato revisável, seleção sem perda de dimensões e um recorte oficial capturado; sua conclusão não equivale a comprovar todas as respostas oficiais ao vivo.
