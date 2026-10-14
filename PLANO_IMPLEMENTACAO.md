# Explorador de agregados do IBGE — análise e implementação por fases

Atualização: 14/10/2026. Situação: fases 0–4 concluídas mediante solicitações explícitas; a fase 0 foi executada após a base da fase 1. Fases 5–6 pendentes. Contrato em [docs/contrato-api.md](docs/contrato-api.md); evidências em [docs/FASE_0.md](docs/FASE_0.md), [docs/FASE_1.md](docs/FASE_1.md), [docs/FASE_2.md](docs/FASE_2.md), [docs/FASE_3.md](docs/FASE_3.md) e [docs/FASE_4.md](docs/FASE_4.md).

## 1. Objetivo e escopo

Recriar em Django e React o explorador atualmente em Streamlit, preservando a navegação por pesquisas e agregados, a comparação de localidades, as tabelas e os gráficos. A geração de URLs oficiais copiáveis é uma funcionalidade central: o README do legado destaca seu uso em outros aplicativos.

Este documento define o planejamento; a execução depende da solicitação de cada fase. As fases 0 e 1 foram autorizadas separadamente em 13/10/2026. Cada fase deve ser entregue com evidências e encerrada antes da seguinte. Não executar cargas, migrações em bancos compartilhados, downloads massivos ou alterações nos projetos vizinhos como consequência deste plano.

Diretório de destino: `azdata/agregados_ibge`, vazio na inspeção. Origem analisada: `C:/Users/andre/Documents/Projetos Python/Streamlit/pesquisas-agregado-ibge-main`.

## 2. O que existe no legado

| Arquivo | Responsabilidade observada | Destino proposto |
| --- | --- | --- |
| `app.py` | Orquestra a página, quatro etapas e um rerun inicial | Página React com estado explícito |
| `parametros.py` | Consulta acervos A/N/P; filtra por assunto, nível e ano; N6 inicial | Catálogo e filtros de descoberta |
| `pesquisas.py` | Lista pesquisas e seus agregados; contém outra função de metadados | Serviços de catálogo e seleção encadeada |
| `agregado.py` | Metadados, variáveis, localidades, enriquecimento municipal com UF e botão Buscar | Editor de consulta e metadados |
| `resposta.py` | Consulta séries, gráficos Altair e estatísticas por localidade | Normalização no backend e resultados React |
| `session.py` | Inicializador de estado que não é importado pelo fluxo principal | Não migrar como módulo; substituir por estado tipado |
| `requirements.txt` | Streamlit, pandas, numpy, requests e altair sem versões | Dependências mínimas e versões fixadas na implementação |

Fluxo atual: assunto/nível/ano → pesquisa → agregado → variáveis/localidades → Buscar → gráficos e resumo. Até seis variáveis e cinco localidades podem ser selecionadas. A consulta de resultados sempre usa `periodos/all`; o ano do catálogo não restringe as séries exibidas.

O projeto não contém testes automatizados entre os arquivos inspecionados. A análise foi estática: não executei o Streamlit, não medi consumo de recursos e não consultei séries reais. A percepção de lentidão relatada pelo usuário ainda precisa de medição para identificar os custos dominantes.

## 3. Problemas e limites encontrados

| Evidência no código | Consequência | Tratamento |
| --- | --- | --- |
| `requests.get(...).json()` sem timeout, verificação HTTP ou tratamento de exceção | Uma requisição lenta ou resposta inválida pode bloquear ou quebrar a página | Cliente IBGE central, timeout, erros estruturados e tentativas limitadas |
| `st.cache_data` sem TTL explícito | Não há política explícita de atualização e validade dos dados | Cache com chave, validade, origem e horário identificáveis |
| `periodos = "all"` em `resposta.carregar` | Histórico inteiro mesmo quando desnecessário | Seleção de períodos publicados e orçamento de consulta |
| `resposta["resultados"][0]` | Só o primeiro grupo de classificações é processado | Preservar todos os grupos e suas categorias |
| `astype(float)` sobre valores da série | Valores especiais ou não numéricos podem interromper a apresentação | Manter valor original e conversão numérica separada |
| Colunas e associações baseadas no nome da localidade | Nomes repetidos ou enriquecidos com UF podem conflitar | Identidade por código e nível; nome apenas para apresentação |
| `pd.merge` municipal sem `how` | Join interno pode excluir localidades sem correspondência | Enriquecimento opcional sem remover registros oficiais |
| Resumo usa média, desvio e CV sem validação de tamanho ou média zero | Resultados indefinidos e interpretação inadequada | Estatísticas descritivas com regras e quantidade de observações |
| `respostas[k]` antes de verificar quantidade | Uma resposta vazia pode causar IndexError | Estado vazio explícito antes de renderizar |
| Territórios exibidos apenas de `Administrativo` | Metadados especiais/IBGE ficam incompletos | Apresentar todos os grupos publicados e validar suporte |
| Resultados dependem do valor momentâneo do botão | Uma nova interação pode retirar o resultado exibido | Separar rascunho, consulta aplicada e resultado |
| Inicialização/rerun e consultas misturadas com widgets | Acoplamento dificulta manutenção e testes | Separar transporte, domínio, estado e apresentação |

São limitações demonstráveis pelo código, não evidências de que todos esses erros aconteceram em uso. Não atribuir a lentidão exclusivamente ao Streamlit sem medir rede, volume retornado e renderização.

## 4. Referência oficial e limites da verificação

A [documentação oficial da API de agregados, versão 3](https://servicodados.ibge.gov.br/api/docs/agregados?versao=3), consultada nesta análise, publica catálogo, metadados, localidades por nível, períodos por agregado e séries com classificações. Ela também disponibiliza um Query Builder. Usar esses contratos como referência; a página não comprova disponibilidade operacional nem desempenho.

Chamadas observadas no legado:

```text
GET /api/v3/agregados?acervo=A|N|P
GET /api/v3/agregados?assunto=...&nivel=...&periodo=...
GET /api/v3/agregados/{agregado}/metadados
GET /api/v3/agregados/{agregado}/localidades/{nivel}
GET /api/v1/localidades/municipios?view=nivelado
GET /api/v3/agregados/{agregado}/periodos/all/variaveis/{ids}?localidades={nivel}[{ids}]
```

Endpoint adicional documentado para o novo editor: `/api/v3/agregados/{agregado}/periodos`. Os acervos, a gramática de classificações, os marcadores especiais e as formas exatas de resposta devem ser confirmados na fase 0 por documentação detalhada e amostras pequenas autorizadas. Não transportar silenciosamente as suposições do legado.

## 5. Arquitetura proposta

Projeto independente nesta pasta, com `backend/` e `web/`, nos moldes da organização observada em `azdata/api` e `azdata/etl`. React com TypeScript e Vite, cliente HTTP compartilhado e TanStack Query seguem as ferramentas presentes no `package.json` de B-Atlas. Esses são padrões locais observados, não uma prescrição para copiar versões antigas: fixar versões compatíveis no início da implementação.

```text
agregados_ibge/
  backend/
    config/
    agregados/
      clients/ibge.py
      services/catalogo.py
      services/consultas.py
      services/normalizacao.py
      services/estatisticas.py
      serializers.py
      views.py
      urls.py
      tests/fixtures/
  web/
    src/api/
    src/features/agregados/
    src/components/
    tests/
  docs/
  scripts/
  PLANO_IMPLEMENTACAO.md
```

Fluxo: React → API Django/DRF → APIs oficiais do IBGE. O backend concentra validação, montagem de URL, cache e normalização. O navegador não precisa baixar todos os municípios ou fazer chamadas diretas ao IBGE para cada seleção.

Começar sem ETL e sem cópia integral do SIDRA. Cache não é acervo permanente nem substitui a fonte oficial. Usar cache local no desenvolvimento; decidir Redis apenas se houver execução com múltiplos processos ou demanda medida. Não exigir banco de domínio no MVP; consultas salvas, usuários e histórico persistente são opcionais posteriores. Se o scaffold incluir tabelas internas do Django, suas migrações devem ser limitadas ao ambiente local do projeto e registradas na entrega.

Não reutilizar o banco compartilhado de `azdata/api` por conveniência. Não alterar API, ETL, B-Atlas ou Polling nesta implementação. Eventual integração precisa de contrato e escopo próprios.

## 6. Contratos de domínio e consulta

### Identidade e valores

- IDs de pesquisa, agregado, variável, classificação, categoria, período e localidade são strings, preservados literalmente.
- Identidade de uma observação: agregado + variável + nível/localidade + período + combinação de classificações/categorias. Não juntar séries apenas pelo nome.
- Preservar unidade, nomes oficiais, notas e metadados disponíveis. Não somar localidades ou unidades distintas automaticamente.
- Período não é necessariamente ano. Usar ID e rótulo publicados; ordenação deve respeitar o catálogo, sem inventar datas.
- Manter `valor_original` e `valor_numerico` anulável. Registrar marcador/status quando documentado; valores não reconhecidos permanecem identificáveis. Não converter ausência, supressão ou indisponibilidade em zero.
- Não deduplicar ocorrências conflitantes silenciosamente; sinalizar divergências de identidade e manter evidência para diagnóstico.

### Rascunho e aplicação

Seleções editam o rascunho. Apenas **Buscar** dispara séries. Carregamento de catálogo/metadados pode acontecer ao selecionar itens, mas não dispara a consulta de resultados. Manter o último resultado e identificar que existem alterações pendentes.

Trocar agregado invalida variáveis, períodos, classificações e localidades incompatíveis. Trocar nível invalida localidades incompatíveis. Revalidar os campos mesmo quando restaurados da URL. Cancelar chamadas obsoletas no cliente e impedir que uma resposta antiga substitua a seleção atual; cancelamento no navegador não garante interrupção da chamada upstream.

N6 é preferência inicial quando disponível, não obrigação para todos os agregados. Permitir somente níveis e localidades realmente publicados para a seleção. Enriquecimento municipal com UF é auxiliar e deve preservar localidades sem correspondência.

### Períodos e classificações

Distinguir filtro de descoberta do catálogo e períodos da consulta. Default proposto para séries: até seis períodos publicados mais recentes, exibidos explicitamente. Permitir seleção maior dentro do orçamento; `all` apenas como escolha explícita e validada.

Classificações e categorias devem estar disponíveis antes de declarar o explorador completo. Caso haja total publicado, oferecer esse total explicitamente; nunca assumir que a primeira categoria/grupo é total. Não produzir somas artificiais para substituir totais oficiais. Sem uma seleção resolvida e válida, não buscar séries.

### Estatísticas

Calcular por variável, localidade e combinação de categorias, sobre observações numéricas do recorte aplicado. Exibir quantidade válida e quantidade sem número. Média/mínimo/máximo exigem ao menos uma observação; desvio amostral exige duas. CV fica indisponível quando a média é zero ou negativa, com explicação contextual. Sinalizar cautela para interpretação em séries de unidades inadequadas. Informar todos os períodos empatados no mínimo/máximo, respeitando a ordem oficial. Não interpolar lacunas.

## 7. API interna proposta

Prefixo próprio: `/api/v1/agregados-ibge/`. Rotas abaixo são propostas novas, não endpoints já existentes.

| Método e rota | Função |
| --- | --- |
| `GET dominios/` | Assuntos, níveis e períodos de descoberta |
| `GET pesquisas/` | Catálogo agrupado por pesquisa, com filtros validados |
| `GET agregados/{id}/metadados/` | Variáveis, unidades, níveis, classificações e categorias |
| `GET agregados/{id}/periodos/` | Períodos publicados do agregado |
| `GET agregados/{id}/localidades/?nivel=...&q=...&page=...` | Localidades oficiais com busca/paginação interna |
| `POST consultas/validar/` | Valida rascunho e devolve URL oficial e orçamento; não busca séries |
| `POST consultas/executar/` | Executa consulta estruturada, normaliza e retorna dados e proveniência |

Os POSTs de consulta não implicam persistência ou alteração de dados. Não aceitar URL arbitrária para proxy. Construir caminhos apenas para hosts oficiais e operações permitidas; validar redirecionamentos, parâmetros, códigos e limites.

Formato de entrada a fechar na fase 0:

```json
{
  "agregado_id": "1705",
  "nivel_id": "N6",
  "localidade_ids": ["CODIGO_PUBLICADO"],
  "variavel_ids": ["VARIAVEL_PUBLICADA"],
  "periodo_ids": ["PERIODO_PUBLICADO"],
  "classificacoes": [
    {"classificacao_id": "CLASSIFICACAO_PUBLICADA", "categoria_ids": ["CATEGORIA_PUBLICADA"]}
  ]
}
```

Exemplo estrutural, não consulta executável nem prova de disponibilidade desses campos para o agregado indicado. A resposta deve conter consulta aplicada, URL oficial, dados normalizados, metadados necessários, horário da obtenção e situação do cache. Separar horário de obtenção de eventual data oficial de atualização. Chave de cache inclui todas as dimensões e versão do normalizador; não inclui apenas agregado.

Erros propostos: 400 para seleção inválida, 422 para orçamento excedido, 502 para resposta upstream inválida e 504 para timeout. Se houver rate limit local, usar 429. Vazio válido é 200 com lista vazia; indisponibilidade não é resultado vazio. Não devolver sucesso com dados truncados sem avisar; preferir rejeição explícita ou resposta completa dentro do limite.

## 8. Desempenho e experiência

Manter inicialmente os limites de seis variáveis e cinco localidades como política da aplicação, não como limite do IBGE. Orçamento considera também períodos e combinações de categorias, além de teto de bytes de resposta. Estimativa prévia não garante tamanho real: impor limite durante a leitura e retornar erro claro quando excedido. Valores exatos de timeout, TTL, orçamento e concorrência devem ser fixados na fase 1 e revistos com evidência da fase 6.

Cachear catálogos/metadados separadamente das consultas. Aplicar tentativas limitadas apenas a falhas transitórias; não repetir consultas inválidas. Deduplicar chamadas simultâneas equivalentes quando necessário. Evitar renderizar todas as linhas e todos os gráficos de uma vez: paginação/virtualização conforme volume e gráficos por variável/categorias selecionadas.

Página com seleção progressiva, metadados em área recolhível, controles pesquisáveis, estados de carregamento/vazio/erro, resultado persistente e ação de tentar novamente. Ajuda contextual em vez de explicações permanentes extensas. Exibir códigos de maneira legível junto dos nomes.

Gráfico de linhas para séries ordenadas; tabela como alternativa acessível e obrigatória. Não ligar lacunas nem misturar unidades em um mesmo eixo por padrão. Escolher a biblioteca de gráficos na fase 4 pelo volume, acessibilidade e custo de manutenção, sem carregar Altair/pandas no navegador.

## 9. Plano de execução e critérios de aceite

### Fase 0 — fechar contratos e amostras

Entregas: `docs/contrato-api.md`, matriz legado → novo, regras de dimensões/valores/períodos e fixtures de formatos conhecidos. Separar respostas oficiais capturadas de fixtures sintéticas. Confirmar acervos, sintaxe de classificações, sinais especiais e níveis territoriais. Definir o recorte do primeiro agregado de referência, incluindo ao menos um caso com classificações.

Aceite: seleção completa expressável sem perder dimensão; lista explícita de incertezas; contrato revisável de entrada/saída. Capturas oficiais pequenas dependem de autorização para consultas reais; não bloquear a preparação de fixtures sintéticas e contrato preliminar enquanto essa evidência estiver pendente.

### Fase 1 — base Django/React e cliente IBGE

Entregas: scaffold local, configuração por ambiente, `.env.example`, dependências fixadas, README de execução Windows, cliente HTTP, cache e contrato de erros. Fixar limites e documentar seus motivos. Preparar launcher com processos identificáveis, sem terminar processos alheios.

Aceite: backend inicia, frontend compila, configuração não contém segredos e testes isolados cobrem timeout, HTTP inválido, JSON inválido, cache e host permitido. Não depender do banco dos outros projetos.

### Fase 2 — descoberta de pesquisas e agregados

Situação: concluída em 13/10/2026. API de domínios/pesquisas/metadados, serializers, seleção React encadeada e metadados completos entregues. Validação offline: 44 testes de backend (incluindo fases 0/1), 10 testes Chromium, typecheck e build aprovados. Hashes das capturas preservados; nenhuma nova consulta ao IBGE. Critérios, limites e handoff em [docs/FASE_2.md](docs/FASE_2.md).

Entregas: API de domínio/catálogo/metadados e tela de assunto, nível, período de descoberta, pesquisa e agregado. Busca por código/nome e seleção encadeada. Exibir níveis e metadados completos.

Aceite: N6 inicial quando disponível; filtros não deixam seleções incompatíveis; catálogo vazio e falha têm estados distintos; respostas obsoletas não sobrescrevem estado; selecionar catálogo não chama séries.

### Fase 3 — editor completo e URL oficial

Situação: concluída exclusivamente no escopo autorizado. API de períodos/localidades e validação, editor React e URL copiável entregues; evidências, limites e pendências em [docs/FASE_3.md](docs/FASE_3.md). Validação offline com fixtures/mocks, sem novas consultas ao IBGE ou execução de séries. Fases 4–6 não implementadas. Commit e sincronização Git autorizados separadamente após a entrega inicial; sem publicação da aplicação.

Entregas: variáveis, localidades, períodos, classificações/categorias; validação no backend; orçamento; URL oficial copiável; rascunho separado da consulta validada. Localidades oficiais sem enriquecimento de UF, conforme solicitação desta fase; IDs e nomes preservados.

Aceite: todos os parâmetros relevantes aparecem na URL gerada; seleção inválida ou excessiva é rejeitada; total é escolhido explicitamente quando existente; mudar campos dependentes limpa seleções inválidas; gerar URL não executa séries.

### Fase 4 — execução, tabela, gráficos e estatísticas

Situação: concluída exclusivamente no escopo autorizado em 14/10/2026. Endpoint `consultas/executar/`, normalização de todos os grupos/ocorrências, tabela longa paginada, SVG por combinação e estatísticas descritivas entregues. Somente Buscar executa séries; rascunho, consulta aplicada e último resultado permanecem separados, com proteção de respostas obsoletas. Conflitos/unidades não confirmadas suspendem análise; cronologia desconhecida suspende linhas. Validação offline: 64 testes backend, 24 testes Chromium, typecheck e build; hashes preservados, sem novas consultas ao IBGE. Entregas, critérios, comandos, regras aditivas do schema e pendências em [docs/FASE_4.md](docs/FASE_4.md). A entrega inicial não incluiu commit; versionamento e sincronização Git autorizados separadamente após a entrega. Sem publicação da aplicação; fases 5–6 não antecipadas.

Entregas: endpoint de execução, normalizador de todos os grupos, tabela longa, apresentação por variável, gráficos e resumo. Fonte, unidade, recorte e marcadores visíveis. Esta é a fase que conclui o MVP funcional.

Aceite: resultado vazio não quebra; todas as classificações retornadas são preservadas; valores especiais permanecem literais; nomes iguais não fundem séries; períodos não anuais e lacunas são tratados; estatísticas cobrem uma observação, média zero, negativos e empates. Fixture conhecida deve produzir valores e identidades conferíveis manualmente.

### Fase 5 — compartilhamento e exportação

Entregas: URL da aplicação restaura consulta validada, botão copiar link oficial, exportação CSV dos dados completos recebidos e JSON com proveniência. Links compartilhados não executam séries automaticamente; usuário confirma com Buscar. Se URL exceder limite prático, oferecer JSON de consulta para importar; link curto persistente fica para escopo posterior.

Aceite: ida e volta mantém IDs, classificações e períodos; códigos com zeros são preservados nos dados exportados; CSV possui codificação e escape corretos, incluindo tratamento de fórmulas em planilhas sem alterar o JSON literal; metadados distinguem recorte e origem. Exportação não depende apenas das linhas visíveis da tabela.

### Fase 6 — verificação integrada e entrega operacional

Entregas: testes de navegador com fixtures, medição limitada de tempos/bytes/renderização, documentação operacional, limites finais e lista de pendências. Consultas reais pequenas apenas quando autorizadas e registradas. Validar configuração de publicação quando o destino estiver definido.

Aceite: fluxo completo catálogo → editor → Buscar → resultado → exportação; editar rascunho não busca; repetição usa cache; falha permite recuperação; teclado e visualização móvel funcionam. Registrar exatamente quais cenários foram verificados offline e quais foram confirmados no IBGE. Evidência de fixtures não comprova disponibilidade ou desempenho upstream.

## 10. Matriz mínima de validação

| Cenário | Evidência exigida |
| --- | --- |
| Resposta de classificação com vários grupos | Nenhum grupo desaparece no normalizador |
| Localidades de mesmo nome | Séries distintas por código e nível |
| Município sem enriquecimento de UF | Registro preservado com nome oficial |
| Marcador, valor vazio e número | Literal mantido; conversão numérica apenas quando válida |
| Períodos mensais/trimestrais e lacunas | Ordem oficial e ausência sem interpolação |
| Requisição lenta/HTTP inválido/JSON inválido | Erro estruturado e recuperação pela UI |
| Uma observação/média zero/empate | Estatísticas definidas conforme contrato |
| Mudança rápida de agregado ou nível | Sem resultado obsoleto nem consulta implícita |
| Consulta acima do limite | Bloqueio explícito, sem truncamento silencioso |
| Copiar URL/restaurar/exportar | Consulta e proveniência consistentes |

Rodar testes proporcionais à fase: unidades de domínio e transporte no backend; comportamento de estado e fluxo com Vitest/Playwright no frontend; build/typecheck. Não exigir execução real do IBGE para testes automatizados comuns.

## 11. Fora do MVP

Mapas, banco histórico de todas as pesquisas, carga integral, agendamentos, comparação entre agregados de unidades diferentes, indicadores derivados, conversões territoriais históricas, autenticação própria, favoritos persistidos e integração automática com outros projetos. Nenhum desses itens é necessário para substituir o explorador atual.

## 12. Handoff ao fim de cada fase

Registrar: fase concluída; arquivos e contratos alterados; comportamento entregue; validação e resultados; evidências oficiais versus sintéticas; limitações; decisões pendentes; próxima fase. Não marcar fase concluída por mera existência dos arquivos se os critérios de aceite não passaram.

Próximo pedido sugerido: **“Implementar apenas a fase 4 do PLANO_IMPLEMENTACAO.md, seguindo docs/contrato-api.md e docs/FASE_3.md.”** A fase 3 concluiu o editor e a validação/geração de URL com fixtures/mocks e preservou as oito capturas oficiais limitadas da fase 0. A próxima fase depende de autorização própria; não executar séries ou ampliar consultas automaticamente.
