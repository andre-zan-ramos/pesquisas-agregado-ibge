# Fase 6 — verificação integrada e documentação operacional

Data: 14/10/2026. Concluída exclusivamente no escopo autorizado: verificação e medições offline, sem novas consultas reais ao IBGE, publicação ou commit. Destino de publicação não definido. Fases 0–5 e contrato preservados; as menções históricas a fases futuras em seus registros não foram reescritas.

Após a entrega inicial, o usuário autorizou separadamente revisão, commit e sincronização Git. A revisão não exigiu mudanças no comportamento da aplicação; os 68 testes backend foram novamente aprovados. Essa autorização de versionamento não inclui publicação nem novas consultas reais executadas pelo agente.

## Entregas e critérios de aceite

Não foi necessária alteração do comportamento da aplicação. Adicionados `web/tests/integrated.spec.ts`, `backend/agregados/tests/test_integracao.py` e `scripts/measure_phase6.py`; atualizados somente plano e README, além deste registro. Todos os transportes usados nesta fase são mocks ou servidores locais. Capturas, manifests, schemas, literais e regras de proveniência permanecem intactos.

| Critério | Evidência offline |
| --- | --- |
| Catálogo → editor → Buscar → resultado → compartilhamento/restauração → exportação | Novo percurso Chromium usa catálogo real da API local/Django com MockTransport, escolhe todas as dimensões, gera link/JSON, executa, edita, restaura e compara resultado/exportações |
| Somente Buscar executa séries | Contagem de POSTs: zero após catálogo, seleção, validação e geração do link; uma execução após Buscar; edição não executa; restauro não executa; segundo Buscar produz segunda execução |
| Cache e proveniência | Restauro e repetição mantêm dados e fetched_at, com cache_hit; backend integrado e medição conferem ausência de novo transporte em cache. Testes anteriores cobrem expiração e chaves completas |
| Falhas e recuperação | Backend integrado: timeout/504 e HTTP 503/502 com duas tentativas limitadas; JSON inválido/502 com uma tentativa. Falha não é cacheada; próximo POST válido recupera e repetição usa cache. Chromium cobre rede interrompida, JSON inválido e HTTP 503, preservando exportação anterior e recuperando por Buscar; regressão anterior cobre 504 e vazio válido |
| Respostas obsoletas | Suítes anteriores cobrem catálogo, metadados, validação, localidades, edição/troca de agregado e mudança do fragmento durante execução; resposta atrasada não substitui estado atual |
| Literais, origem e exportação completa | Compara consulta aplicada e envelope completo antes/depois de edição e restauro, 15 observações sintéticas; suíte anterior confere zeros, CSV/fórmulas, null/vazio, duplicatas, índices e captura oficial derivada |
| Teclado e móvel | Novo percurso em 390 × 844: Space em checkboxes, Enter em validar/Buscar, foco e ArrowRight na tabela; sem overflow da página. Captura inspecionada em `var/phase6-mobile.png` |
| Renderização limitada | Tabela de 10.000 ocorrências mockadas mantém 50 linhas de dados no DOM; JSON exporta 10.000. Uma análise por vez; lacunas/gráfico acessível e troca de variável cobertos nas regressões |
| Preservação das fases anteriores | Suíte completa backend inclui manifests/hashes. Diff restrito a arquivos desta fase, plano e README; nenhum projeto vizinho alterado |

## Validação reproduzível

Pré-requisitos: `.venv` local com `backend/requirements-dev.txt`, `web/node_modules` pelo lock e Chromium Playwright instalado. Preparação em máquina nova: `scripts/setup.ps1 -WithTests` e, em `web`, `npx playwright install chromium`. Instalação de ferramentas exige rede para pacotes, mas não consulta dados do IBGE.

Na raiz, PowerShell:

```powershell
.\.venv\Scripts\python.exe backend\manage.py check --settings=config.test_settings
.\.venv\Scripts\python.exe backend\manage.py test agregados.tests --settings=config.test_settings
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts\measure_phase6.py
cd web
npm run typecheck
npm run build
npm run test:browser
```

Resultados: **68 testes backend aprovados**, Django check sem problemas, pip check sem incompatibilidades; typecheck e build aprovados. **36 cenários Chromium aprovados**, um worker: 31 regressões anteriores e 5 cenários novos. A primeira execução completa passou 33 testes; após adicionar três cenários de recuperação, a segunda execução do arquivo integrado passou seus cinco testes (incluindo novamente fluxo e medição). `git diff --check` aprovado. Bundle preservado: JS **285,69 kB / 88,38 kB gzip**, CSS **3,34 kB / 1,32 kB gzip**. Não foi iniciado o launcher operacional.

Playwright inicia servidores exclusivos em 8828 e 5198, com `reuseExistingServer:false`, encerrados ao terminar. O backend de fixtures usa exclusivamente MockTransport; as interceptações de navegador simulam falhas/volume sem atingir IBGE. Erros JavaScript falham os testes. Relatórios e captura são artefatos locais ignorados pelo Git; este documento conserva resultados e método revisáveis.

## Método e resultados das medições limitadas

Ambiente: Windows 11, Python 3.12.3, Node 22.14.0, Chromium via Playwright 1.63.0, dependências fixadas nos locks. Uma rodada backend e duas rodadas navegador (a segunda junto à verificação dos novos testes de recuperação), sem carga concorrente intencional, com variabilidade da máquina; não são SLA nem benchmark de produção. A tabela de navegador registra a última rodada, correspondente ao relatório local atual.

**Backend:** `scripts/measure_phase6.py` realiza cinco pares de POSTs da mesma consulta sintética (15 observações). Limpa apenas o cache de testes antes de cada par. Primeiro POST frio e segundo quente medidos com perf_counter, incluindo validação, normalização, estatísticas e serialização DRF, via Django Test Client, sem socket. A primeira amostra inclui inicialização/importações; não é descartada. Todas as chamadas usam MockTransport. Relatório completo: `var/phase6-backend.json`.

| Medida | Frio | Quente |
| --- | --- | --- |
| Mediana do POST | 33,235 ms | 11,274 ms |
| Intervalo das cinco amostras | 24,946–167,528 ms | 7,803–13,718 ms |
| Bytes da resposta interna UTF-8 | 22.661 | 22.656 |
| Chamadas ao mock por POST | 5 | 0 |
| Soma dos corpos recebidos do mock | 3.126 bytes | 0 bytes |

Diferença de cinco bytes vem de cinco flags `cache_hit:false` → `true`; dados e horários permanecem iguais. Os bytes são corpos JSON descomprimidos, sem headers, TLS ou compressão. A normalização é refeita mesmo no cache; não existe cache de resultado normalizado.

**Navegador:** novo teste mede três repetições com 15 observações e três com 10.000. O cenário pequeno passa pela API local e transporte mock. O cenário grande duplica uma ocorrência no interceptador Chromium, mantendo metadados/análises originais: mede somente consumo/apresentação/exportação desse envelope ampliado, não a aceitação semântica, estatísticas ou normalização backend de 10.000 observações. Resposta grande de 7.090.884 bytes é interna, não resposta upstream; não contorna nem exercita o teto upstream de 4 MiB.

Cronômetro no processo de teste: antes do click, após `response.body()`, após heading visível e duas requestAnimationFrame, e durante download/leitura do JSON. Inclui actionability, IPC, interceptação, leitura do corpo e polling Playwright. O intervalo após corpo não é perfil puro de CPU React e pode excluir trabalho que ocorreu antes de `response.body()` resolver. Não mede heap, RSS, long tasks, FPS, concorrência, compressão, rede externa, primeiro carregamento frio nem experiência em aparelho físico. Relatório completo: `var/phase6-browser.json`.

| Medida (mediana; mínimo–máximo) | 15 observações | 10.000 ocorrências mockadas |
| --- | --- | --- |
| Click até corpo disponível | 195,5 ms; 186,4–267,7 | 1.567,2 ms; 1.192,7–1.737,5 |
| Corpo até heading + duas frames | 77,0 ms; 47,4–141,9 | 137,9 ms; 103,1–1.141,6 |
| Click até heading + duas frames | 263,4 ms; 242,8–409,6 | 1.705,1 ms; 1.295,8–2.879,1 |
| JSON: download e leitura local | 441,4 ms; 390,5–488,0 | 839,9 ms; 587,7–6.923,8 |
| Bytes de resposta / JSON exportado | 22.617 / 22.617 | 7.090.884 / 7.090.884 |
| Linhas DOM, incluindo cabeçalho | 8 (variável inicial: 7 ocorrências) | 51 (50 dados) |

Corpo de navegador reserializado pelo interceptador e corpo DRF têm tamanhos ligeiramente diferentes; são métodos distintos, não perda de observações. Exportação JSON foi conferida por contagem e testes de igualdade; paginação não restringe exportação. A dispersão observada impede afirmar ganho operacional ou escolher novos limites de timeout com esses números. Mantidos todos os limites existentes.

## Instruções operacionais

### Verificação offline e operação local

Para verificar sem consultar IBGE, executar apenas os comandos de testes/medição acima. Para exploração manual offline, executar em uma janela ` .\.venv\Scripts\python.exe scripts\serve_phase2_fixtures.py` e em outra, no diretório `web`:

```powershell
$env:VITE_BACKEND_PROXY_TARGET = 'http://127.0.0.1:8828'
npm run dev -- --port 5198
```

Abrir `http://127.0.0.1:5198`; Ctrl+C nas duas janelas encerra os servidores. Nesse modo só existem dados sintéticos. O script conserva seu nome histórico de fase 2, mas serve o fluxo completo com mocks. Não executar `capture_phase0.py --execute` para validação.

O launcher normal `servers.bat` / `scripts/dev.ps1` é para operação local com fonte real e **não foi executado nesta fase**. Na operação real, abrir a aplicação já pode consultar catálogo/metadados; apenas Buscar consulta séries. Usar somente quando esse acesso estiver autorizado. Setup preserva ambientes existentes; backend independente sem banco de domínio/migrações. Portas padrão 8817/5187, proxy Vite `/api/`. Portas alternativas via parâmetros do launcher, conforme README. Ctrl+C encerra somente os processos iniciados pelo launcher, registrados com logs/PIDs em `var/dev`; porta ocupada exige escolher outra, sem encerrar processos alheios.

Selecionar catálogo/agregado, revisar variáveis, nível/localidades, períodos e todas as classificações. Período de descoberta não restringe séries. Validar seleção gera URL sem séries; Buscar executa. Editar mantém resultado aplicado e avisa pendências. Reabrir link/importar JSON revalida e exige Buscar. Exportar refere-se sempre ao resultado aplicado, incluindo proveniência, nunca somente à página visível. Não seguir URLs oficiais durante verificação offline.

### Falhas, cache e diagnóstico

| Situação | Ação operacional |
| --- | --- |
| Erro de catálogo/metadados/períodos/localidades | Usar Tentar novamente naquele contexto; não interpretar indisponibilidade como catálogo vazio |
| Falha de execução, 502/504 ou conexão | Resultado anterior permanece. Conferir erro, seleção e recorte; usar Buscar para nova tentativa. Sem retry automático de séries no navegador |
| 400 / seleção importada rejeitada | Corrigir IDs/dimensões e revalidar; não forçar coerção ou alterar códigos |
| 422 / orçamento ou bytes | Reduzir variáveis, localidades, períodos ou categorias; não aceitar resultado parcial/truncado |
| 429 / concorrência local | Aguardar chamadas em andamento e tentar novamente por Buscar; limite por processo |
| Vazio 200 | Resultado válido sem observações; distinto de falha. CSV contém cabeçalho e JSON envelope completo |
| Unidade conflitante ou cronologia desconhecida | Manter literal/tabela/proveniência; análise ou linhas ficam suspensas. Não converter unidade ou interpolar |
| Clipboard indisponível / link longo | Copiar campo manualmente; acima de 2.000 caracteres, exportar/importar JSON de consulta (até 64 KiB), sem contornar validação |

Para diagnóstico registrar rota/status/código do erro, consulta JSON, URL oficial gerada/aplicada, normalizer_version, sources/fetched_at/expires_at/cache_hit e logs locais do processo. URL gerada não é captura; fetched_at não é atualização oficial. Não alterar capturas/manifests para resolver divergências. JSON de resultado é evidência completa; CSV tem proteção de fórmulas e requer importação dos IDs como Texto em planilhas, conforme fase 5.

Cache é bruto e local por processo: catálogos 3.600 s, séries 300 s, até 64 entradas; reinício perde cache e múltiplos processos não o compartilham. Não existe endpoint de limpeza nem deduplicação de chamadas simultâneas. Sem stale fallback após expiração. Cancelamento no navegador não garante interrupção upstream. Padrões mantidos: conexão 5 s, leitura 15 s, orçamento total 25 s (pode ultrapassar durante I/O síncrono), duas tentativas, duas chamadas upstream concorrentes por processo, resposta upstream 4 MiB, seis variáveis/cinco localidades, estimativa e quantidade real até 10.000, URL oficial até 16.384 caracteres. Timeout navegador 60 s. Não ampliar limites com base só no benchmark mock.

### Publicação e pendências

**Destino de publicação não definido; nada publicado.** Build apenas gera `web/dist`. Proxy de `vite dev` não configura hospedagem e `vite preview` não possui o proxy `/api/` deste projeto. Não tratar preview como aplicação completa em produção.

Antes de uma publicação autorizada, definir hospedagem do Django/WSGI e arquivos estáticos, domínio/TLS, roteamento de `/api/` na mesma origem e fallback SPA (links usam fragmento), segredo próprio, DEBUG=false, ALLOWED_HOSTS, configuração do proxy confiável e limites/concorrência/cache para a topologia real. Runserver e test_settings não são configurações de produção. Deployment check e validação integrada na hospedagem permanecem pendentes porque o destino não existe; não foi criada configuração especulativa.

Aceitação operacional continua pendente: disponibilidade/latência atual do IBGE, cobertura de outros agregados/níveis/formatos, divergência de unidade de 1712, desempenho de catálogos/localidades grandes, custo de normalização e memória no teto, exportação CSV/JSON em volume/planilhas reais, cache multiprocesso e concorrência, Firefox/WebKit, leitor de tela e dispositivos físicos. Teclado e viewport Chromium não certificam acessibilidade completa.

As únicas respostas oficiais usadas são as oito capturas históricas da fase 0, verificadas por hashes e usadas nas regressões; não são consultas realizadas nesta fase nem prova de disponibilidade atual. Incertezas da seção 13 do contrato e fases anteriores mantidas. Qualquer nova captura/consulta real ou publicação exige autorização e escopo explícitos. Não há commit automático nem alterações nos projetos vizinhos.
