# Fase 5 — compartilhamento, restauração e exportação

Data: 14/10/2026. Escopo exclusivamente fase 5, sem commit ou publicação automática. Preservados os documentos das fases 0–4, contratos, capturas e manifests. Nenhuma nova consulta real ao IBGE, carga, migração, banco ou alteração em projetos vizinhos. Fase 6 pendente.

O commit e a sincronização Git foram autorizados separadamente após a entrega. Revisão para versionamento corrigiu também o próximo pedido sugerido no plano, que ainda apontava para a fase 4; agora indica a fase 6. Sem publicação da aplicação.

## Entregas

- Consulta validada compartilhável pela URL da aplicação. O fragmento `#consulta=…` contém JSON codificado por `URLSearchParams`, no formato versionado `{"version":1,"consulta":{…}}`. O link inclui agregado, nível, localidades, variáveis, períodos e todas as classificações/categorias. IDs continuam strings literais. Filtros de descoberta e controles de apresentação não são dimensões da consulta e não são serializados.
- Restauração na abertura, mudança de fragmento e navegação do histórico. Carrega metadados diretamente pelo agregado, sem depender da página ou dos filtros do catálogo de descoberta. Reutiliza `consultas/validar/`, incluindo pertinência de todas as dimensões, total/exceções, orçamento e erros. Não executa séries: apenas **Buscar** chama `executar/`. Rejeições não geram URL validada e bloqueiam Buscar até correção/revalidação. Há retorno explícito à descoberta.
- Rascunho, validação submetida e resultado aplicado continuam separados. Restaurar/importar substitui o rascunho; o último resultado permanece, com aviso de mudanças pendentes. Alterações removem a validação anterior e abortam execução ativa; desmontagem por troca de consulta também aborta. Chaves completas e identidade/signal protegem contra respostas obsoletas. Importação inválida mantém o rascunho e o resultado anteriores.
- URL oficial copiável no editor validado e, independentemente do rascunho, no resultado aplicado, a partir da source real de séries. Campos selecionáveis permitem cópia manual se clipboard falhar. Links apenas gerados não recebem horários fictícios.
- Limite prático de **2.000 caracteres** para a URL completa da aplicação. Acima dele, não oferece um link incompleto: mostra orientação e exportação do JSON de consulta. Exportação/importação usa a mesma estrutura versionada, sem links curtos persistidos. O limite do link da aplicação é independente dos limites existentes da URL oficial e do orçamento.
- Importação por arquivo local, até **64 KiB UTF-8**. Rejeita JSON malformado, versão diferente de 1, campos faltantes/extras, tipos coercíveis, IDs fora da gramática, listas obrigatórias vazias, IDs repetidos, classificações repetidas e chaves JSON repetidas, inclusive escapadas. Depois da validação estrutural, passa pelo mesmo validador semântico do backend. Não aceita URL arbitrária, resultado exportado ou wrapper versionado como payload direto da API.
- CSV completo de `observacoes` recebidas, na ordem da resposta, incluindo todas as variáveis, localidades, combinações e duplicatas, independentemente dos controles/página visíveis. Inclui todas as dimensões, categorias/unidades em JSON, unidade original/analítica/status, valor original/número/status, índices de origem, consulta aplicada, sources e versão do normalizador. Uma linha por ocorrência efetivamente recebida; não exporta pontos analíticos fabricando observações para lacunas. Resultado vazio exporta somente cabeçalho.
- JSON do resultado exporta o envelope completo `{data,sources}` recebido, incluindo corpo original, metadados, períodos, análises, avisos, índices e proveniência. Não reconstrói observações a partir da tabela ou do gráfico, não converte unidades conflitantes e não aplica proteção de planilha aos literais JSON. Serialização preserva também o sinal do zero negativo numérico; strings como `-0.00`, marcadores, null e vazio permanecem exatamente como recebidos.
- Downloads via Blob local; URLs temporárias são revogadas. Nenhum endpoint, dependência ou persistência adicional.

## CSV: codificação, literalidade e planilhas

UTF-8 com BOM, separador vírgula e término de registros CRLF. Todas as células são delimitadas por aspas duplas; aspas internas são duplicadas. Vírgulas, acentos e quebras de linha dentro de valores são preservados. IDs são escritos como texto literal, inclusive zeros à esquerda; ao importar em uma planilha, definir essas colunas como **Texto**, pois aspas CSV não controlam a inferência de tipos do aplicativo.

Para impedir interpretação como fórmula, prefixar com apóstrofo células que começam com `=`, `+`, `-` ou `@`, inclusive após espaços/controles, ou começam com TAB/CR/LF. A proteção se aplica a todas as colunas textuais e é conservadora: também prefixa números negativos e o marcador `-`. O apóstrofo é parte do CSV entregue; alguns aplicativos o exibem. Escape de aspas sozinho não protege contra fórmulas. Não remover esse prefixo e reabrir o arquivo automaticamente como planilha. Nenhuma dessas alterações é aplicada ao JSON, que é a exportação literal completa de referência.

`null` é escrito como texto `null`, vazio como célula vazia, e `valor_original_tipo` distingue null/string/number (inclusive a string literal `null`). Categorias, índices, consulta e proveniência são células JSON, conservando estruturas e nulls internos. As duas informações de unidade e seu status permanecem explícitos. CSV é a tabela completa de ocorrências; corpo bruto e estruturas adicionais completas ficam no JSON.

## Critérios de aceite e evidências offline

| Critério | Evidência |
| --- | --- |
| Ida e volta de todas as dimensões e zeros | Navegador integrado restaura link, compara payload de validação, checkboxes e clipboard; JSON de consulta importado/exportado |
| Revalidação sem executar | Navegador rejeita variável, localidade, período, nível, classificações/categorias e excesso; backend valida round trip sem séries |
| Importação estrita | Tipos, campos extras, versão, listas vazias, duplicatas, chaves repetidas, JSON malformado e tamanho testados |
| Resultado preservado e respostas antigas descartadas | Importação inválida mantém resultado; mudança de fragmento durante execução conserva resultado anterior; regressões de edição/troca de agregado |
| Exportação aplicada completa | Download JSON comparado ao envelope efetivamente enviado; CSV lido com parser de aspas/quebras, mais de 50 ocorrências e duas variáveis, após trocar página/variável e editar rascunho |
| Literais e fórmulas | CSV testa `=`, `+`, `-`, `@`, espaços/controles, aspas, vírgulas, newline, vazio e null; JSON preserva literais e zero negativo |
| Duplicatas, origem, categorias e proveniência | Backend mantém 22 ocorrências após duplicação sintética; navegador confere categorias, cada índice e sources exportados |
| Link longo | Fallback acima de 2.000 caracteres e round trip do JSON; tela e download verificados com resposta mock |
| Preservação das fases anteriores | Suítes anteriores e hashes/manifests; diff sem alteração em capturas ou registros das fases 0–4 |

## Validação reproduzível

```powershell
.\.venv\Scripts\python.exe backend\manage.py check --settings=config.test_settings
.\.venv\Scripts\python.exe backend\manage.py test agregados.tests --settings=config.test_settings
cd web
npm run typecheck
npm run build
npm run test:browser
```

Resultados finais: Django check sem problemas; **67 testes backend aprovados** (64 anteriores + 3 da fase 5); **31 testes Chromium aprovados** (24 anteriores + 7 da fase 5), um worker; **typecheck, build e `git diff --check` aprovados**. Bundle JS 285,69 kB (88,38 kB gzip), CSS 3,34 kB (1,32 kB gzip). Suíte de contrato confirmou hashes/manifests existentes; diff sem alteração em capturas, schemas ou documentos das fases 0–4. Inspeção da captura mobile de 390 px: exportações e áreas expansíveis legíveis, tabela contida na região rolável; teste anterior de mobile/teclado aprovado. Artefato visual local em `var/phase4-mobile.png`, ignorado pelo Git e com nome histórico preservado.

Testes usam somente fixtures existentes, transporte MockTransport e interceptações locais no Chromium; não executam launcher produtivo nem novas requisições ao IBGE. Revisão com a skill `vercel:react-best-practices`: componentes fora da renderização, execução em evento, cleanup/cancelamento, consultas com chaves completas, campos rotulados e controles de apresentação separados da exportação. O desenvolvimento com StrictMode pode iniciar validação de catálogo mais de uma vez; os testes conferem que todas recebem a mesma consulta e nenhuma executa séries automaticamente.

## Pendências e limites

- Mantidas as incertezas do contrato e da fase 4, incluindo divergência oficial de unidade. Testes não comprovam disponibilidade, cobertura, atualidade ou desempenho operacional do IBGE.
- Limites de 2.000 caracteres/64 KiB são política da aplicação. Recortes maiores que o limite de importação precisam ser reduzidos; importar JSON não contorna o orçamento nem o teto da URL oficial.
- JSON de consulta compartilha dimensões; não carrega resultados, histórico, usuários, descoberta ou preferências visuais. JSON de resultado é exportação de evidência e não importação de consulta.
- CSV/JSON são gerados em memória a partir do último resultado completo recebido. Não houve benchmark de memória, carga ou compatibilidade operacional em diferentes planilhas. A proteção de CSV foi validada sobre bytes/conteúdo; inferência de tipos depende do importador.
- Cancelamento do navegador não garante interrupção upstream. Cache permanece local por processo; não há novos mecanismos de cache ou persistência.
- Fase 6, medições operacionais e publicação continuam sob autorização própria.
