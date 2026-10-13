# Fase 2 — descoberta de pesquisas e agregados

Data: 13/10/2026. Situação: concluída exclusivamente no escopo autorizado. Fases 0 e 1 preservadas; fases 3–6 pendentes. Nenhuma nova consulta real ao IBGE, migração ou carga. A entrega inicial não incluiu commit ou publicação; o versionamento e a sincronização foram autorizados posteriormente pelo usuário.

## Entregas e contrato

- `GET /api/v1/agregados-ibge/dominios/`: assuntos, níveis e períodos de descoberta, a partir dos acervos A/N/P.
- `GET /api/v1/agregados-ibge/pesquisas/`: pesquisas e agregados aninhados. Filtros opcionais `assunto`, `nivel`, `periodo` precisam existir no domínio publicado; são enviados ao IBGE somente após validação. `q` busca por código/nome de pesquisa ou agregado, sem distinção de caixa. Quando a pesquisa corresponde, mantém todos os seus agregados; quando apenas agregados correspondem, mantém os agregados encontrados.
- Paginação interna de pesquisas após busca: `page` a partir de 1 (máximo 1.000.000), `page_size` de 1 a 200 (padrão 50), total e indicação de próxima página conhecidos. Todos os agregados das pesquisas selecionadas são preservados. Página além do fim retorna lista vazia; não há truncamento silencioso.
- `GET /api/v1/agregados-ibge/agregados/{id}/metadados/`: composição de metadados, acervo N para rótulos e períodos do agregado. Inclui IDs string, unidades, sumarização das variáveis, classificações, categorias, hierarquia, total/status e exceções, todos os níveis de todos os grupos, periodicidade, todos os rótulos dos períodos, modificação e ordem na fonte.
- Serializers de entrada/saída e serviço `backend/agregados/services/catalogo.py`. Parâmetros desconhecidos/repetidos, filtros vazios e limites inválidos são rejeitados. Domínios/metadados não aceitam query livre. IDs fracionários, booleanos e estruturas incompatíveis da fonte geram `upstream_inconsistent_data`/502; IDs textuais com zeros permanecem literais.
- Transporte `IbgeClient`, cache, TTL, limites e erros da fase 1 reutilizados sem alterações. Cada resposta nova usa `{data, sources}`; cada chamada utilizada possui URL, horário de obtenção/expiração e indicador de cache. Não confundir esses horários com `modificacao` publicada pelo IBGE.
- React: seleção de assunto, nível, período de descoberta, pesquisa e agregado; controles com busca local por código/nome e busca global no catálogo. Mudanças de filtro/busca/página limpam pesquisa e agregado; trocar pesquisa limpa agregado. N6 inicial somente se publicado; agregado sem N6 exige escolha entre seus níveis.
- Metadados em áreas expansíveis, com total especial apenas descrito, sem seleção de categorias nem cálculo de total. Grupos adicionais são preservados e identificados; nível sem nome no acervo continua visível pelo código. Não há editor, consulta de localidades ou execução de séries.
- TanStack Query usa chaves que incluem filtros/página ou agregado, sinais de cancelamento e nenhuma reutilização visual de dados da consulta anterior. Pesquisa/agregado são resolvidos contra o catálogo atual antes de mostrar metadados; metadados precisam corresponder ao ID atual. O nível escolhido é revalidado contra os níveis publicados. Cancelamento no cliente não garante interrupção da chamada upstream.

## Critérios de aceite

| Critério | Evidência |
| --- | --- |
| N6 preferido quando disponível | Testes Chromium de descoberta e metadados; sem N6, seleção vazia |
| Seleções incompatíveis limpas | Trocas de filtro, busca, página, pesquisa e agregado testadas |
| Busca por código e nome | Backend cobre código/nome de pesquisa/agregado, zeros e paginação; Chromium cobre controles e busca global |
| Carregamento, vazio e erro distintos | Requisição pendente, catálogo vazio, timeout e recuperação testados; falhas de domínios/metadados também recuperáveis |
| Respostas obsoletas não substituem seleção | Catálogo e metadados atrasados testados em mudanças rápidas |
| Metadados completos e IDs literais | Igualdade com fixture normalizada sintética, JSON Schema, captura 1712 com seis classificações e todos os níveis, grupo desconhecido sem rótulo |
| Selecionar catálogo não consulta séries | Transporte mock recusa operações fora do escopo; navegador verifica ausência de chamadas de séries/consultas/localidades; rotas das fases posteriores permanecem ausentes |
| Fases anteriores e capturas preservadas | Suíte completa de 44 testes aprovada, incluindo integridade dos manifests; nenhum arquivo de captura ou das fases anteriores alterado |

## Validação reproduzível

Na raiz, com dependências de testes instaladas por `scripts/setup.ps1 -WithTests`:

```powershell
.\.venv\Scripts\python.exe backend\manage.py check --settings=config.test_settings
.\.venv\Scripts\python.exe backend\manage.py test agregados.tests --settings=config.test_settings
cd web
npm run typecheck
npm run build
npm run test:browser
```

Resultados: check sem problemas; 44 testes backend aprovados (34 anteriores + 10 de catálogo); 10 testes Chromium aprovados, um worker; typecheck e build aprovados. Build final: JS 264,27 kB, gzip 82,17 kB. `git diff --check` sem problemas.

Playwright 1.63.0 foi adicionado ao lock local, sem dependência de projeto vizinho. Para instalar seu Chromium em uma máquina nova: `npx playwright install chromium`. A suíte inicia Django em 8828 e Vite em 5198 com proxy para esse Django. O servidor exclusivo de fixtures troca o cliente por `httpx.MockTransport`; operações imprevistas são rejeitadas. Alguns testes interceptam respostas da API no navegador para simular falhas e atrasos; o teste integrado percorre navegador → proxy → Django → transporte mock → metadados renderizados. Não há acesso a banco ou IBGE.

Inspeção visual da captura local `var/phase2-mobile.png`: 390 px, controles e metadados renderizados, sem overflow horizontal. A imagem é ignorada no Git. Erros JavaScript falham a suíte. Os servidores de teste encerraram após a execução; não foi iniciado o launcher de consultas reais.

## Limites e pendências

Esta entrega comprova comportamento e contrato com mocks e capturas existentes, não disponibilidade, desempenho ou cobertura atual do IBGE. Permanecem as incertezas da seção 13 do contrato e da fase 0. Cache continua local por processo, conforme fase 1; chamadas concorrentes equivalentes podem ocorrer antes do primeiro cache preenchido.

Busca/paginação de pesquisas acontecem no backend sobre o catálogo retornado; o backend recebe o corpo completo dentro do teto de transporte. Não foi medido desempenho de catálogos grandes. Os períodos mostrados nesta tela descrevem descoberta e metadados; não são seleção de períodos de séries. Ordem na fonte não é apresentada como prova de cronologia.

Próxima fase autorizável: fase 3, editor completo e geração/validação de URL oficial. Consumir metadados e preservar a resolução explícita de todas as classificações, regras de total/exceções, identidade territorial e unidades. Localidades, escolha de variáveis/categorias/períodos de consulta, orçamento, URL copiável, execução, gráficos, estatísticas, restauração e exportação continuam pendentes nas fases previstas. Nenhuma dessas funcionalidades foi antecipada.
