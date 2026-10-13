# Pesquisas por agregados do IBGE

Base independente em Django/DRF e React/TypeScript/Vite. Fase 0: contrato, esquemas e amostras. Fase 1: infraestrutura, cliente IBGE e tela inicial. Catálogo, filtros e séries serão entregues nas próximas fases do [plano](PLANO_IMPLEMENTACAO.md).

## Preparação no Windows

Requisitos validados: Python 3.12 e Node 22.14. Node 22 precisa ser ao menos 22.12 para a versão de Vite fixada. Não usar ambientes Python ou bancos dos projetos vizinhos.

Na raiz, em PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1
.\servers.bat
```

O setup cria `.venv`, instala o lock Python e executa `npm ci`, cria `backend/.env` com chave aleatória local e copia `web/.env.local.example` quando esses arquivos não existem. Configurações existentes são preservadas. Arquivos de ambiente e artefatos locais estão no `.gitignore`.

Frontend: `http://127.0.0.1:5187`. Backend: `http://127.0.0.1:8817/api/v1/agregados-ibge/health/`. O launcher roda em primeiro plano, cria servidores ocultos e registra os PIDs e logs em `var/dev/`. Ctrl+C encerra apenas os processos que ele iniciou. Portas ocupadas causam erro; não há encerramento por nome ou por porta.

Para mudar portas:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 -BackendPort 8818 -WebPort 5188
```

O launcher configura o proxy Vite para a mesma porta do Django. Não precisa de CORS: o navegador acessa `/api/` na origem do frontend e Vite encaminha para o backend.

Para iniciar separadamente, em duas janelas PowerShell:

```powershell
cd backend
..\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8817 --noreload
```

```powershell
cd web
npm run dev
```

Nesse modo, ajustar `VITE_WEB_PORT` e `VITE_BACKEND_PROXY_TARGET` em `web/.env.local` se necessário.

## Verificação

Na raiz:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1 -WithTests
.\.venv\Scripts\python.exe backend\manage.py check
.\.venv\Scripts\python.exe backend\manage.py test agregados.tests --settings=config.test_settings -v 2
cd web
npm run build
```

`-WithTests` instala também `backend/requirements-dev.txt` para validar JSON Schema. Os testes do transporte usam `httpx.MockTransport`; os testes de contrato leem capturas já salvas e fixtures sintéticas, sem rede ou banco. O endpoint `health/` confirma somente que Django responde; não verifica disponibilidade do IBGE. Não há modelos ou migrações nesta fase; o backend de banco configurado é `dummy`.

## Configuração e contratos

`backend/.env.example` contém os parâmetros suportados. `DJANGO_SECRET_KEY` é obrigatório; não há segredo padrão de execução. `DJANGO_DEBUG=true` é destinado ao desenvolvimento local. A produção ainda requer definição de hospedagem, proxy `/api/`, TLS e configuração própria.

Dependências Python diretas em `backend/requirements.in`; versões resolvidas, inclusive transitivas, em `backend/requirements.txt`. Frontend usa versões exatas em `web/package.json` e lock em `web/package-lock.json`.

O [contrato de domínio/API](docs/contrato-api.md) fecha seleções, identidade, períodos, classificações, unidades, valores e respostas das próximas fases. O [registro da fase 0](docs/FASE_0.md) descreve capturas e limitações. O [registro da fase 1](docs/FASE_1.md) descreve infraestrutura e limites. Esquemas e fixtures não significam que as rotas futuras já foram implementadas.

`scripts/capture_phase0.py` é uma ferramenta manual de captura limitada, separada dos testes e do setup. Sem `--execute`, apenas mostra ajuda. A execução original já está registrada; o script recusa sobrescrever um manifest existente. Repetir capturas requer escopo explícito e preservação da evidência anterior.
