# Fase 0 — contrato e amostras

Data: 13/10/2026. Situação: concluída. Executada após a infraestrutura da fase 1, por solicitação do usuário.

## Entregas

- [Contrato de domínio/API v1](contrato-api.md), com matriz legado → novo e regras de identidade, períodos, classificações, total, unidades, valores, erros, orçamento e estado da UI.
- [JSON Schema](schemas/contrato-v1.schema.json) para consulta, resultado, metadados normalizados, observações, proveniência, paginação e erros. A estrutura dos demais endpoints está descrita no contrato e receberá serializers na fase 2.
- Extração de 18 modelos estruturais da documentação oficial, com manifest de origem e integridade, em `docs/evidencias/`.
- Quatorze fixtures sintéticas, separadas e identificadas como inventadas: códigos com zeros, homônimos, unidades, exceção de total, todos os grupos de níveis, períodos mensais, lacunas, marcadores, vazio/null, conflito de identidade e exemplos estatísticos.
- Oito capturas reais do IBGE, em `backend/agregados/tests/fixtures/official/`, cada uma com URL, horário, HTTP 200 e SHA-256 do JSON reserializado. A consulta resolvida possui hash próprio e não é tratada como uma resposta capturada.
- Exemplo normalizado derivado da captura oficial, identificado em `fixtures/derived/`, com quatro observações e dois avisos de conflito de unidade. O envelope é um exemplo esperado, não uma API de resultados já implementada.
- Dezessete testes de contrato, adicionais aos 16 testes de transporte da fase 1.
- Dependências de validação de schema fixadas em `backend/requirements-dev.txt`, separadas das dependências de execução. `scripts/setup.ps1 -WithTests` instala esse conjunto.
- Script manual `scripts/capture_phase0.py`, que limita chamadas e recusa sobrescrever capturas existentes. Sem `--execute`, mostra ajuda; setup e testes não o executam.

## Recorte oficial capturado

| Requisição | Limite do recorte |
| --- | --- |
| Acervos A/N/P | Três respostas de catálogo, sem séries |
| Metadados 1712 | Um agregado |
| Períodos 1712 | Um catálogo de períodos |
| Localidades 1712/N1 | Brasil |
| Catálogo filtrado | Classificação 226, N1 e período 2006 |
| Séries 1712 | Duas variáveis, um período, Brasil, duas combinações de categoria: quatro valores |

Foram oito chamadas upstream, com uma tentativa por chamada, sem download massivo, banco, migração ou ETL. Todos os corpos JSON retornaram dentro do limite de 4 MiB por resposta; os oito arquivos reserializados somam 114.716 bytes. As consultas ocorreram entre 15:22:37 e 15:22:45 de 13/10/2026, no fuso America/Sao_Paulo; o manifest guarda horários com offset UTC. Os limites aplicados são os da fase 1, não um benchmark operacional.

Consulta de séries: variáveis 214/1982; período 2006; Brasil; classificação 226 com categorias 4844/96608, classificação 218 com 4780 e classificações 12517/220/12523/12617 com total especial 0, após conferência de status/exceções nos metadados. Nenhuma classificação foi omitida implicitamente.

## Achados que alteram as próximas fases

1. A/N/P retornam `{id,literal}`. Os metadados podem usar inteiros para IDs e início/fim de periodicidade; o contrato interno usa strings preservando os IDs textuais existentes.
2. O corpo real de `serie` é objeto período → literal. O schema documental declara array, em conflito com a descrição e com a captura. Preservar essa divergência na evidência; não validar os corpos reais cegamente pelo schema documental extraído.
3. O nível de localidade veio explicitamente N1 na captura. O nível null está documentado e coberto por fixture sintética, mas não foi observado nessa chamada.
4. O agregado 1712 possui seis classificações. Não tratar as duas citadas no exemplo documental como catálogo completo.
5. Categoria 96608 é Amendoim em casca nos metadados atuais, embora um exemplo textual da documentação a descreva como alho. O nome publicado nos metadados orienta a interface.
6. As variáveis 214/1982 remetem a unidades das categorias. Abacaxi usa Mil frutos; amendoim usa Toneladas nos metadados, mas as séries retornaram Mil frutos para ambos. O contrato mantém essa divergência visível e suspende gráfico/resumo da combinação conflitante; não corrige ou converte valores por inferência.
7. A amostra contém apenas valores numéricos. Marcadores, valores nulos e convenções continuam cobertos por exemplos sintéticos e referências de publicação, sem prova universal de codificação em todas as respostas v3.

## Validação

```text
manage.py check: sem problemas
manage.py test agregados.tests --settings=config.test_settings: 33 testes aprovados
pip check: sem dependências incompatíveis
capture_phase0.py sem --execute: apenas ajuda, sem novas chamadas
```

Os testes confirmam esquemas, hashes, literalidade, cobertura de grupos nos exemplos, pertinência e total no recorte oficial, quatro valores retornados e visibilidade dos dois conflitos de unidade. Não testam um normalizador, estatísticas ou API de catálogo produtivos, que ainda não existem. Não foi necessário reconstruir o frontend porque esta fase não mudou seus arquivos ou dependências.

## Critérios de aceite

| Critério da fase 0 | Evidência |
| --- | --- |
| Seleção completa sem perda de dimensão | Schema de consulta e recorte oficial com seis classificações resolvidas |
| Contrato revisável de entrada/saída | `contrato-api.md`, schema e exemplos normalizados |
| Amostras oficiais e sintéticas separadas | Três manifests distintos: synthetic, official e derived; evidência documental separada |
| Períodos e valores especiais definidos | Regras explícitas de literalidade, números nullable e lacunas |
| Níveis e classificações definidos | Grupos dinâmicos, hierarquia da categoria, total e exceções |
| Agregado de referência escolhido | 1712, período 2006, Brasil, quatro valores capturados |
| Incertezas registradas | Seção 13 do contrato e achados acima |

## Handoff

Próxima fase autorizável: fase 2, descoberta de pesquisas e agregados. Consumir `contrato-api.md` e as fixtures existentes. Implementar serializers, serviços e UI de catálogo sem antecipar execução de séries. Levar para a fase 3 a resolução explícita de classificações e total; para a fase 4, literalidade, conflitos de unidade e identidade por combinação.

Permanecem sem comprovação: todos os outros agregados, níveis territoriais fora do recorte N1 de 1712, distribuição real dos marcadores, ordenação de períodos de outras periodicidades e desempenho sob demanda. A captura confirma somente o recorte e o momento registrados. As demais fases não foram executadas automaticamente.
