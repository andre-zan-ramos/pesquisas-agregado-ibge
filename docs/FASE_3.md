# Fase 3 — editor de consulta e URL oficial

Data: 13/10/2026. Escopo: exclusivamente fase 3. Preservadas as entregas das fases 0–2 e as capturas existentes. Nenhuma nova consulta real ao IBGE, migração, carga ou execução de séries. A entrega inicial não incluiu commit ou publicação; o commit e a sincronização Git foram autorizados posteriormente pelo usuário. Projetos vizinhos não alterados.

## Entregas

- `GET agregados/{id}/periodos/`: envelope `{data:{items},sources}`, IDs literais, todos os rótulos, modificação e ordem na fonte. Ordem não representa cronologia. Sem query livre.
- `GET agregados/{id}/localidades/?nivel=...&q=...&page=...&page_size=...`: somente níveis publicados em todos os grupos do agregado; localidades exclusivamente do endpoint daquele agregado/nível. Busca por ID/nome sem distinguir caixa ou acentos; labels originais preservados. Filtragem antes da paginação interna, página inicial 1, tamanho 50, teto 200, página máxima 1.000.000. Contagem e próxima página conhecidas; página além do fim é vazia. Sem enriquecimento: `uf_sigla=null`; homônimos e zeros preservados. Nível null na fonte é resolvido pelo único nível solicitado; nível explícito divergente é 502.
- `POST consultas/validar/`: entrada estrita conforme contrato, sem coerção de números em strings, IDs duplicados, dimensões vazias, expressões livres, URL arbitrária ou campos extras. Valida variáveis, períodos, nível e localidades; exige exatamente uma seleção não vazia para cada classificação publicada. Detalhes do erro semântico identificam o campo. Sem séries e sem persistência.
- Total especial `0` somente com status permitido e sem variável nas exceções daquela classificação, inclusive se a fonte listar `0` nas categorias. `00` é categoria comum. Categoria cujo nome seja Total conserva seu ID comum. Nenhum total é inferido ou calculado.
- Orçamento: variáveis × localidades × períodos × produto das quantidades de categorias, com fator 1 sem classificações. Limites configuráveis existentes de seis variáveis, cinco localidades e 10.000 observações; excesso retorna 422. Resposta informa estimativa, limites e warnings. URL usa o construtor restrito existente, host oficial fixo, períodos/variáveis explícitos, todas as classificações, localidades do nível e `BR` somente para N1/ID `1`. URL excessiva também é rejeitada. Limite de 4 MiB continua no transporte, não é estimativa garantida de séries.
- `sources` registra somente catálogos efetivamente obtidos para validar; `data.source_url` é URL gerada e não possui horário fictício de captura. Cliente IBGE, cache e erros anteriores reutilizados. `ServiceError` recebeu detalhes opcionais mantendo envelope e comportamento anterior.
- Editor React com busca por código/nome, variáveis e unidades, nível publicado, localidades pesquisáveis/paginadas, seleção acumulada entre páginas e remoção explícita, períodos e todas as classificações/categorias. Mostra unidade/hierarquia das categorias e condiciona total às variáveis. Sem seleção implícita de classificação, categoria, localidade ou período. Todos os períodos podem ser escolhidos explicitamente; envia IDs resolvidos e passa pelo mesmo orçamento.
- Período de descoberta permanece separado dos períodos da consulta. Nesta fase o recorte inicial de períodos é vazio e exige escolha explícita; nenhuma ordenação cronológica é inferida. A preferência N6 só se aplica quando publicada. Grupos territoriais completos continuam visíveis nos metadados.
- Rascunho e seleção submetida separados. Alterar qualquer dimensão remove imediatamente a URL/validação anterior. Trocar agregado reinicia o editor; trocar nível limpa localidades; variável incompatível remove apenas o total especial, preservando categorias comuns. Alteração dos metadados reinicia o editor para revalidação. Buscar/paginar localidades muda somente o catálogo de opções e preserva as escolhas.
- URL completa em campo acessível, selecionável e copiável apenas após resposta válida do backend. Falha de clipboard orienta cópia pelo campo. Carregamento, vazio e erro têm mensagens distintas, com recuperação. Chaves TanStack Query incluem agregado, nível, busca/página ou seleção submetida; sinais de cancelamento e remoção da seleção submetida impedem respostas antigas de restaurar URL ou opções de outro nível. Cancelamento do navegador não garante cancelamento upstream.

## Critérios de aceite e evidências

| Critério | Validação |
| --- | --- |
| URL contém todas as dimensões, preservando IDs | Backend sintético com zeros e recorte oficial 1712/N1, seis classificações; navegador integrado com cópia |
| Seleções inválidas e orçamento rejeitados | Backend: tipo, campos extras, duplicação, pertinência, classificações ausentes, total/exceções e tetos; navegador: 422 sem URL |
| Total explicitamente escolhido | Checkbox específico; teste de remoção quando variável 102 é marcada, sem reintrodução automática |
| Rascunho invalida validação anterior | Edição de período e resposta de validação atrasada testadas |
| Dependências e localidades | Troca de nível, paginação com seleção entre páginas e resposta obsoleta testadas |
| Estados distintos e recuperáveis | Catálogo, metadados, localidades e períodos; vazio e falha nunca produzem URL |
| Sem séries ou avanço de fases | MockTransport aceita apenas catálogos; testes recusam séries; rota executar permanece 404 |
| Fases anteriores e hashes preservados | Suíte completa inclui contratos/manifests; nenhuma captura, manifest ou documento de fase anterior alterado |

## Validação reproduzível

Na raiz, com dependências locais já instaladas:

```powershell
.\.venv\Scripts\python.exe backend\manage.py check --settings=config.test_settings
.\.venv\Scripts\python.exe backend\manage.py test agregados.tests --settings=config.test_settings
cd web
npm run typecheck
npm run build
npm run test:browser
```

Resultados finais: Django check sem problemas; **52 testes backend aprovados** (44 anteriores + 8 da fase 3); **17 testes Chromium aprovados** (10 de descoberta + 7 do editor), um worker; typecheck e build aprovados. Bundle JS: 270,26 kB, gzip 83,72 kB. `git diff --check` sem erros. Integridade das capturas e manifests aprovada pela suíte de contrato; diff sem alterações nesses artefatos e nos documentos das fases 0–2. Inspeção visual da captura mobile de 390 px: editor e grupos completos legíveis, sem overflow horizontal, também verificado pelo navegador.

Servidor de fixtures existente ampliado apenas para localidades, usando `httpx.MockTransport`. Chromium executa com um worker e mocks, incluindo fluxo navegador → proxy → Django → cliente mock → validação. Testes antigos de fase 2 foram ajustados somente para permitir as novas rotas e restringir seletores aos metadados, mantendo seus critérios. A antiga expectativa de ausência das rotas fase 3 foi substituída pela ausência de execução.

Revisão React conforme skill `vercel:react-best-practices`: componentes definidos fora da renderização, estado atualizado por eventos, opções derivadas, chaves com dependências completas, cancelamento, controles rotulados e mensagens acessíveis; sem novas dependências. Captura mobile local em `var/phase2-mobile.png` inclui agora o editor e continua ignorada no Git.

## Pendências e limites

Mocks/capturas comprovam comportamento do contrato, não cobertura ou disponibilidade atual do IBGE. Continuam as incertezas da seção 13 do contrato. Paginação é interna sobre o corpo completo, sujeito ao limite do transporte; desempenho de localidades grandes não medido. Cache permanece local por processo e não deduplica requisições simultâneas equivalentes.

O default desejado de até seis períodos mais recentes não foi aplicado: nesta entrega todos exigem seleção explícita, sem inferir cronologia. Enriquecimento UF excluído por instrução do usuário. Resultado, normalização, estatísticas, gráficos, execução, exportação e restauração de consulta pela URL permanecem nas fases 4–6. Não executar a URL gerada como teste desta fase.
