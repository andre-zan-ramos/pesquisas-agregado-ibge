# Fase 1 — infraestrutura e transporte

Data: 13/10/2026. Escopo: backend local, frontend inicial, cliente de transporte IBGE, cache, erros e launcher Windows. No momento desta entrega, a fase 0 ainda não havia sido executada; ela foi concluída posteriormente, conforme [FASE_0.md](FASE_0.md). Não foram implementados catálogo, editor ou resultados.

## Fluxo entregue

Página React → `GET /api/v1/agregados-ibge/health/` → Django → resposta JSON → status na página. Falha apresenta mensagem e ação de tentar novamente. O health não faz chamada ao IBGE.

Cliente Python interno `IbgeClient.get_json(path, params)` retorna `data`, `source_url`, `fetched_at`, `expires_at` e `cache_hit`. O JSON é preservado; não há conversão ou normalização de observações. A URL é construída no host fixo `https://servicodados.ibge.gov.br`; não aceita URLs livres. Aceita apenas caminhos e nomes de parâmetros listados no código. Valores são codificados pela biblioteca HTTP e chaves ordenadas para cache consistente. Validação semântica de IDs publicados e dimensões é responsabilidade das fases seguintes.

Redirecionamentos são rejeitados, inclusive para o host oficial. `trust_env=False` evita alteração implícita de proxy por variáveis globais da máquina. Apenas HTTP 200 com JSON objeto/lista é aceito; `[]` é uma resposta válida. O cliente ainda não está exposto em rota de consulta nesta fase.

## Limites iniciais

| Parâmetro | Padrão | Motivo |
| --- | --- | --- |
| Conexão | 5 s | Falhar em conexão indisponível sem longa espera |
| Leitura sem dados | 15 s | Limitar espera por chunk upstream |
| Orçamento total | 25 s | Limitar tentativas e leitura acumulada |
| Tentativas | 2; máximo configurável 3 | Uma recuperação independente para falha transitória |
| Pausa entre tentativas | 250 ms, depois 500 ms | Evitar repetição imediata contínua |
| Resposta descomprimida | 4 MiB | Limitar memória e rejeitar respostas excessivas |
| Concorrência upstream | 2 por processo | Evitar excesso de requisições no desenvolvimento |
| Cache catálogo/metadados | 1 hora | Reduzir tráfego de seleções repetidas |
| Cache séries | 5 minutos | Validade menor para resultados |
| Cache local | Até 64 entradas | Limitar crescimento inicial; não é orçamento de RSS |
| URL construída | Até 16.384 caracteres | Bloquear consultas excessivas antes da rede |
| Variáveis/localidades | 6 / 5 | Política inicial herdada do explorador |
| Observações estimadas | 10.000 | Parâmetro para o validador da fase 3 |

Timeout total é verificado antes de tentativa e durante a leitura; chamadas síncronas só podem ser interrompidas pelo timeout de I/O. Portanto pode haver ultrapassagem de até um timeout de leitura em um chunk que bloqueie próximo do fim do orçamento. Não é um deadline de execução rígido. O cliente de navegador tem timeout de 60 s para comportar esse envelope. Limites são escolhas conservadoras locais, não limites oficiais nem medições do IBGE.

Limite de bytes é aplicado durante a leitura com chunks de 16 KiB, sem depender de `Content-Length`. Conexão, timeout e HTTP 429/500/502/503/504 podem ser repetidos até o limite; demais erros HTTP, redirecionamento, JSON inválido e resposta excessiva não são repetidos. Falhas não são cacheadas.

Cache local é compartilhado entre threads do mesmo processo, perdido ao reiniciar e independente entre processos. A chave inclui versão do transporte, caminho e todos os parâmetros codificados. Fases futuras devem incluir também a versão do normalizador em qualquer cache de dados normalizados. Obtenção de dados não é data de atualização oficial. Deduplicação de chamadas simultâneas equivalentes e cache multiprocesso continuam pendentes até demanda justificada.

Os limites de variáveis, localidades e observações estão configurados para a fase 3; ainda não há endpoint que receba ou valide esses recortes. A fase 1 aplica apenas limites do transporte.

## Erros

Formato das exceções atendidas pelo DRF:

```json
{"error": {"code": "upstream_timeout", "message": "O IBGE excedeu o tempo de resposta.", "details": null}}
```

| Status | Códigos |
| --- | --- |
| 400 | `invalid_operation`, `invalid_parameters` |
| 422 | `query_too_large`, `response_too_large` |
| 429 | `upstream_busy` (concorrência local esgotada) |
| 502 | `upstream_http_error`, `upstream_unavailable`, `upstream_connection_error`, `upstream_redirect`, `upstream_invalid_json` |
| 504 | `upstream_timeout` |

Erros padrão do DRF também usam envelope com código e detalhes. Não expor exceções de transporte ou conteúdo upstream ao usuário. Erros fora do ciclo DRF, como URL desconhecida e falhas de configuração, não fazem parte desse envelope nesta fase.

## Verificação e handoff

Fase 1 concluída. Evidências locais:

- `manage.py check`: sem problemas.
- `manage.py test agregados.tests --settings=config.test_settings -v 2`: 16 testes aprovados, sem uso de banco.
- `pip check`: dependências compatíveis.
- `npm run build`: TypeScript e Vite aprovados; bundle JS de 258,50 kB (80,28 kB gzip).
- Navegador Chromium/Playwright: página desktop e móvel renderizada, mobile de 390 px sem overflow horizontal, API pelo proxy Vite retornando HTTP 200, falha de conexão simulada e recuperação por Tentar novamente; nenhuma exceção JavaScript e nenhuma chamada ao IBGE.
- Launcher: inicialização com logs e PIDs, rejeição de segunda execução nas portas ocupadas, encerramento por Ctrl+C e confirmação de que os dois PIDs e listeners da execução foram removidos.
- Inicializador de ambiente: segunda execução preservou ambos os arquivos existentes.
- `scripts/setup.ps1`: instalação a partir dos locks concluída; `npm ci` resolveu 73 pacotes e a auditoria automática reportou zero vulnerabilidades naquele momento. Nenhum ambiente existente foi sobrescrito.

Capturas e relatório de navegador ficam em `var/phase1-desktop.png`, `var/phase1-mobile.png` e `var/phase1-browser.json`, como evidências locais ignoradas. A verificação pontual usou a instalação Playwright já disponível no projeto vizinho, somente como ferramenta de teste; os arquivos desse projeto não foram alterados e não existe dependência dele para executar ou compilar esta aplicação.

Revisão React: QueryClient criado fora da renderização, uma consulta local com cancelamento, sem cadeias de requisições ou efeitos de sincronização de estado; status anunciado por região viva, ação de recuperação acessível e layout móvel validado.

Revisão para versionamento em 13/10/2026: o transporte passou a rejeitar constantes `NaN`/`Infinity` e números cujo expoente excede a representação finita, retornando `upstream_invalid_json` sem retry ou cache. O teste de regressão cobre essas cinco representações; a suíte completa das fases 0 e 1 soma 34 testes. Build React/TypeScript e verificação de dependências permanecem aprovados.

Na entrega da fase 1, os testes foram sintéticos e isolados; não provaram desempenho, disponibilidade nem conteúdo oficial do IBGE. Naquela fase não foram executadas consultas de dados oficiais, migrações ou cargas. Na entrega original, esta pasta ainda não possuía repositório Git local; o histórico remoto do legado foi conectado posteriormente. A fase 0 foi concluída posteriormente com contrato e capturas limitadas, registrados em [FASE_0.md](FASE_0.md). Próxima etapa prevista: fase 2, seguindo esse contrato.

Referências técnicas consultadas: [cache Django](https://docs.djangoproject.com/en/5.2/topics/cache/), [timeouts HTTPX](https://www.python-httpx.org/advanced/timeouts/), [Vite](https://vite.dev/guide/). Versões instaladas foram verificadas nos registros de pacotes e serão mantidas nos locks locais.
