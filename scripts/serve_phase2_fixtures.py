"""Servidor exclusivo de testes de navegador, sem transporte de rede ao IBGE."""
import json
import os
from pathlib import Path
import sys

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["DJANGO_SETTINGS_MODULE"] = "config.test_settings"
import django
django.setup()
from django.core.management import call_command
from agregados.clients.ibge import IbgeClient
from agregados.services import catalogo

FIXTURES = ROOT / "backend/agregados/tests/fixtures/synthetic"


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def handle(request):
    path = request.url.path
    if path.endswith("/metadados"):
        body = load("metadados.json")
    elif "/localidades/" in path:
        level = path.rsplit("/", 1)[-1]
        body = [{**v, "nivel": {"id": level}} for v in load("localidades.json")]
    elif path.endswith("/periodos"):
        body = load("periodos.json")
    elif path == "/api/v3/agregados":
        acervo = request.url.params.get("acervo")
        body = load("acervos.json")[acervo] if acervo else load("catalogo.json")
    else:
        raise AssertionError(f"Operação fora da fase 2: {path}")
    return httpx.Response(200, json=body)


catalogo.IbgeClient = lambda: IbgeClient(transport=httpx.MockTransport(handle), sleep=lambda _: None)
if __name__ == "__main__":
    call_command("runserver", "127.0.0.1:8828", use_reloader=False, skip_checks=True)
