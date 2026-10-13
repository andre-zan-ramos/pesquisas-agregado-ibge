# Fixtures do contrato — fase 0

`synthetic/` contém somente dados inventados, inclusive códigos, nomes, datas, localidades e valores. IDs aparentemente válidos não demonstram existência no IBGE. Os exemplos não devem ser enviados à API oficial.

`manifest.json` identifica a origem sintética e contém SHA-256 de cada arquivo. Não inserir uma captura oficial nessa pasta, nem renomear uma fixture sintética como oficial.

Capturas documentais ficam separadas em `docs/evidencias/`, identificadas como `official_documentation`. `official/` contém oito corpos JSON efetivamente capturados, mais a consulta resolvida, com manifest próprio de URLs, horários, status e SHA-256. Os corpos são integrais e foram reserializados em JSON legível; o hash se refere ao arquivo salvo, não aos bytes HTTP originais.

`derived/` contém um exemplo normalizado criado a partir dessas capturas, identificado como `derived_example`. Não é uma resposta capturada da API interna. O exemplo registra dois conflitos reais de unidade: categoria Amendoim em casca usa Toneladas nos metadados e recebeu Mil frutos no campo de unidade das séries. Não corrigir os dados brutos.

## Casos disponíveis

| Arquivo | Uso |
| --- | --- |
| `acervos.json` | Formato de A/N/P observado no legado e no construtor documental |
| `catalogo.json` | Pesquisa com agregado numérico |
| `metadados.json` | IDs numéricos/string, zeros, três grupos territoriais e restrição de total |
| `periodos.json` | Períodos mensais e vários rótulos, com fevereiro ausente |
| `localidades.json` | Duas localidades com mesmo nome e IDs distintos |
| `municipios_enriquecimento.json` | Só uma das duas localidades possui UF auxiliar |
| `consulta.json` | Seleção com duas classificações completas |
| `series.json` | Duas variáveis × duas combinações × duas localidades; nível null e uma lacuna |
| `metadados_normalizados.json` | Exemplo do contrato interno, sem perder sumarização ou rótulos |
| `resultado_esperado.json` | 15 observações esperadas, fonte sintética e aviso de lacuna |
| `series_vazias.json` | Array vazio válido |
| `series_conflito.json` | Mesma identidade em duas ocorrências com valores divergentes |
| `erro.json` | Envelope de erro de seleção |
| `estatisticas_casos.json` | Exemplos de uma observação, média zero/negativa e empates |

Os testes desta fase validam esquemas, integridade e coerência dos exemplos. Eles não executam um normalizador, validador semântico ou calculador de estatísticas: essas implementações pertencem às fases 3 e 4.
