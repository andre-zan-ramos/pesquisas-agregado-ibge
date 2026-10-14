# Fase 4 — execução, tabela, gráficos e estatísticas

Data: 14/10/2026. Escopo exclusivamente fase 4. Sem novas consultas ao IBGE, banco, migrações, cargas ou alterações em projetos vizinhos. A entrega inicial não incluiu commit ou publicação; o versionamento e a sincronização Git foram autorizados separadamente após a entrega. Sem publicação da aplicação. Documentos das fases 0–3, capturas e manifests preservados. Fases 5–6 continuam pendentes.

## Entregas

- `POST /api/v1/agregados-ibge/consultas/executar/`: recebe o mesmo JSON estrito de `validar/`, reutiliza integralmente validação semântica, orçamento, construtor restrito, cliente, cache bruto, limites de bytes e erros existentes. Seleção inválida não consulta séries. GET retorna 405 sem upstream. Não há persistência.
- `services/normalizacao.py`: percorre todas as variáveis, resultados, classificações, localidades e períodos. Identidade usa agregado, variável, nível, localidade, período e pares classificação/categoria ordenados por ID. IDs textuais e zeros permanecem literais; nomes não são chaves. Nível null usa somente o nível único validado; nível explícito incompatível, dimensão inesperada ou estrutura inválida bloqueiam a resposta com 502.
- Observações conservam campos do contrato, valores originais, unidades da resposta e das categorias, número nullable, status e índices base zero. Marcadores, vazio, null, vírgula decimal e texto desconhecido nunca viram zero. Não há interpolação, somas, totais ou conversões de unidades. Lacunas ausentes não são inseridas em `observacoes`.
- Duplicatas exatamente iguais ficam na tabela, com warning e ambos os índices; a análise conta uma observação por identidade. Conflito de valor/atributos da mesma identidade retorna 502 com índices, sem escolher uma ocorrência ou devolver resultado parcial. Quantidade real, incluindo duplicatas, também está limitada a 10.000 observações (configurável); excesso retorna 422 sem truncamento.
- Unidade analítica só é utilizável quando confirmada pelos metadados. Referência textual explícita `Vide categorias da classificação '…'` exige uma classificação unívoca e a unidade da categoria escolhida. Outras variáveis usam sua própria unidade, sem herdar a unidade de uma categoria arbitrária. Divergência ou referência não resolvida conserva o número/literal e suspende gráfico e estatísticas da combinação. Unidades distintas dentro da mesma série também suspendem sua análise.
- `services/estatisticas.py`: análise por variável/nível/localidade/combinação, quantidades numéricas e sem número, média, desvio amostral, CV, extremos e todos os períodos empatados. Uma observação não tem desvio/CV; média zero/negativa não tem CV. Lacunas não entram nas contagens. Cautela explícita sobre escala e adequação do CV; estouro da representação finita não quebra a resposta.
- Ordenação cronológica somente para frequência publicada anual/mensal (sem distinção de caixa), com todos os IDs do recorte válidos como YYYY ou YYYYMM. Para outras frequências/formatos, preserva a ordem do catálogo, permite estatística descritiva e suspende linhas; não adivinha datas. Períodos precisam continuar escolhidos explicitamente como na fase 3.
- React: somente **Buscar** executa séries. Validação e geração de URL continuam separadas. Rascunho editável, consulta aplicada e resultado independentes. Último resultado fica no nível da aplicação, inclusive ao trocar agregado, durante nova busca ou falha. Edições sinalizam pendências e abortam a chamada ativa; identidade da chamada e signal impedem substituição obsoleta. Desmontar o editor também aborta. Não há execução em efeito, montagem, foco, reconnect ou retry automático.
- Resultado por variável, seleção de uma combinação por vez, tabela longa paginada em 50 ocorrências, todas as dimensões/unidades/status/índices visíveis. Tabela com caption e cabeçalhos, região rolável focável por teclado; mobile sem overflow da página. Gráfico SVG local, sem biblioteca nova: uma série/unidade por eixo, rótulo acessível, títulos nos pontos e tabela obrigatória. Cada marcador ou lacuna interrompe o path; lacunas são informadas mesmo sem números para desenhar.
- Consulta aplicada, todas as URLs e horários reais de obtenção/expiração/cache disponíveis em área expansível. Horários não são apresentados como atualização oficial. Metadados aplicados incluem os rótulos e modificações dos períodos.

## Saída e compatibilidade

Envelope `{data, sources}` e campos originais de `dadosResultado` preservados: `consulta_aplicada`, `observacoes`, `metadados`, `warnings`, `truncated=false`, `normalizer_version="v1"`.

Extensões aditivas documentadas no JSON Schema, sem reescrever fixtures anteriores:

| Campo de `data` | Conteúdo |
| --- | --- |
| `corpo_original` | Corpo completo de séries recebido; inclui notas/campos extras não mapeados, que também geram warning |
| `periodos_apresentacao` | IDs selecionados na ordem validada ou na ordem do catálogo quando cronologia desconhecida |
| `ordem_cronologica` | Se a frequência/IDs permitem ordenação cronológica |
| `analises` | Resumos independentes, suspensão/avisos e pontos com `valor` nullable e `lacuna` explícita |

O endpoint sempre entrega essas extensões. O schema as mantém opcionais para continuar validando os exemplos históricos das fases anteriores; `analise` possui campos obrigatórios/tipos definidos. `sources` contém as quatro requisições de catálogo necessárias e a requisição de séries. Normalização é refeita a cada execução sobre o cache bruto existente; nenhum cache de resultado normalizado foi introduzido, portanto não há chave normalizada sem versão. O corpo bruto apenas transita na resposta e no cache existente; não se grava payload produtivo em disco.

## Critérios de aceite e evidências

| Critério | Evidência offline |
| --- | --- |
| Todos os grupos e IDs preservados | Igualdade exata das 15 observações sintéticas com `resultado_esperado.json`; oito análises, dois IDs de localidades homônimas e categorias `01`, `02`, `00` |
| Valores especiais e lacunas | Testes de todos os status, zero negativo, vírgula e texto desconhecido; 15 valores retornados para orçamento de 16; sem linha fabricada |
| Unidades conflitantes | Igualdade exata das quatro observações da captura 1712 com o exemplo derivado; duas análises suspensas; navegador verifica suspensão e valor literal `86804` |
| Estatísticas corretas | Casos existentes de uma observação, média zero, média negativa e empates; desvio amostral conferido; extremos finitos sem JSON NaN/Infinity |
| Sem perda silenciosa | Testes de dimensões inesperadas, campos obrigatórios ausentes, categoria com múltiplas chaves, nível divergente, duplicatas, conflito e limite real |
| Buscar é a única execução | Navegador não chama execução ao selecionar/editar/validar; cliente faz POST apenas no evento Buscar |
| Resultado persistente e obsolescência | Navegador cobre edição, troca de agregado durante execução, falha/recuperação, vazio distinto e preservação do último resultado |
| Apresentação e cache | Navegador integrado via proxy/Django/MockTransport, repetição em cache, troca de variável/combinação, paginação, SVG com dois segmentos separados por lacuna, mobile |
| Fases anteriores e hashes | Suíte completa de contrato/manifests e descoberta/editor anteriores; diff sem alterações em capturas/manifests ou `FASE_0.md`–`FASE_3.md` |

## Validação reproduzível

```powershell
.\.venv\Scripts\python.exe backend\manage.py check --settings=config.test_settings
.\.venv\Scripts\python.exe backend\manage.py test agregados.tests --settings=config.test_settings
cd web
npm run typecheck
npm run build
npm run test:browser
```

Resultados finais: Django check sem problemas; **64 testes backend aprovados** (52 anteriores + 12 da fase 4); **24 testes Chromium aprovados** (17 anteriores + 7 de resultados), um worker; **typecheck e build aprovados**. Bundle JS: 278,62 kB (86,28 kB gzip), CSS: 3,34 kB (1,32 kB gzip). `git diff --check` sem erros. Suíte de hashes/manifests aprovada; nenhum arquivo de captura/manifest ou registro das fases 0–3 alterado. Inspeção mobile em 390 px e navegação por teclado da tabela aprovadas; servidores de fixtures encerrados após os testes. Aviso de pendências compara dimensões literais, independentemente da ordem de escolha, e desaparece quando o rascunho volta ao recorte aplicado.

Servidor de navegador `scripts/serve_phase2_fixtures.py` ampliado para séries filtradas exclusivamente sobre JSON sintético, com `httpx.MockTransport`. O nome histórico do script foi preservado. Os 17 testes de navegador anteriores continuam proibindo execução, e os novos testes a autorizam somente por Buscar. O teste antigo de rota inexistente passou a verificar 405 para GET sem upstream. Testes de contrato continuam conferindo os mesmos hashes.

Revisão pela skill `vercel:react-best-practices`: componentes definidos fora da renderização, execução em evento, abort no cleanup, proteção de resposta, estado derivado para filtros de apresentação, paginação e uma análise renderizada por vez, controles rotulados e nenhuma dependência nova. Inspeção visual mobile em `var/phase4-mobile.png` (artefato ignorado no Git).

## Pendências e limites

- Fixtures/capturas comprovam este comportamento; não comprovam disponibilidade, cobertura, atualidade ou desempenho operacional do IBGE. Mantidas as incertezas da seção 13 do contrato.
- Sem cronologia confirmada, gráfico de linhas permanece suspenso. Não foi introduzida seleção implícita dos seis períodos recentes.
- SVG usa posições igualmente espaçadas dos períodos do recorte, ordenados quando confirmados, sem interpolação e sem inferir períodos fora da seleção. Renderiza uma combinação por vez; não houve benchmark de 10.000 observações.
- Cache segue local por processo, sem deduplicação de chamadas simultâneas. Cancelar no navegador não garante interromper o pedido upstream síncrono.
- O teto de 4 MiB se aplica à leitura upstream, conforme transporte existente. A resposta interna inclui corpo original e observações normalizadas, podendo ser maior; não houve medição de memória/rendimento em carga.
- O conflito de unidade real da captura 1712 continua sem esclarecimento oficial; não foi convertido ou resolvido por inferência.
- Compartilhamento/restauração e exportação continuam exclusivamente na fase 5. Verificação operacional, medições e publicação continuam na fase 6, sob autorização própria. Nenhuma dessas fases foi implementada.
