"""Transporte restrito aos endpoints oficiais; sem normalização de domínio."""
import hashlib
import json
import math
import re
import threading
import time
from datetime import timedelta

import httpx
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from agregados.errors import ServiceError

HOST = "https://servicodados.ibge.gov.br"
VERSION = "transport-v1"
PATHS = (
    re.compile(r"/api/v3/agregados"),
    re.compile(r"/api/v3/agregados/[0-9]+/(?:metadados|periodos)"),
    re.compile(r"/api/v3/agregados/[0-9]+/localidades/N[0-9]+"),
    re.compile(r"/api/v3/agregados/[0-9]+/periodos/(?:all|[0-9]+(?:\|[0-9]+)*)/variaveis/[0-9]+(?:\|[0-9]+)*"),
    re.compile(r"/api/v1/localidades/municipios"),
)
_slots = threading.BoundedSemaphore(settings.IBGE_MAX_CONCURRENT)


def reject_nonfinite_json(value):
    raise ValueError(f"Constante JSON inválida: {value}")


def parse_finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Número JSON excede a representação finita")
    return number


def build_url(path, params=None):
    if not isinstance(path, str) or not any(pattern.fullmatch(path) for pattern in PATHS):
        raise ServiceError("invalid_operation", "Operação IBGE não permitida.", 400)
    params = dict(params or {})
    if path == "/api/v3/agregados":
        allowed = {"acervo", "assunto", "nivel", "periodo", "classificacao", "periodicidade"}
    elif "/variaveis/" in path:
        allowed = {"localidades", "classificacao", "view"}
    elif path == "/api/v1/localidades/municipios":
        allowed = {"view"}
    else:
        allowed = set()
    for key, value in params.items():
        if key not in allowed or not isinstance(value, str) or not value or len(value) > 8192:
            raise ServiceError("invalid_parameters", "Parâmetros IBGE inválidos.", 400)
        if any(ord(char) < 32 for char in value):
            raise ServiceError("invalid_parameters", "Parâmetros IBGE inválidos.", 400)
    url = httpx.URL(HOST + path, params=sorted(params.items()))
    if len(str(url)) > 16384:
        raise ServiceError("query_too_large", "A consulta excede o limite de URL.", 422)
    return str(url)


class IbgeClient:
    def __init__(self, *, transport=None, sleep=time.sleep, clock=time.monotonic):
        self.transport = transport
        self.sleep = sleep
        self.clock = clock

    def get_json(self, path, params=None):
        url = build_url(path, params)
        key = VERSION + ":" + hashlib.sha256(url.encode()).hexdigest()
        cached = cache.get(key)
        if cached is not None:
            return {**cached, "cache_hit": True}
        if not _slots.acquire(blocking=False):
            raise ServiceError("upstream_busy", "Há consultas em andamento. Tente novamente.", 429)
        try:
            return self._fetch(url, key, series="/variaveis/" in path)
        finally:
            _slots.release()

    def _fetch(self, url, key, *, series):
        deadline = self.clock() + settings.IBGE_TOTAL_TIMEOUT
        timeout = httpx.Timeout(settings.IBGE_READ_TIMEOUT, connect=settings.IBGE_CONNECT_TIMEOUT)
        with httpx.Client(transport=self.transport, timeout=timeout, follow_redirects=False, trust_env=False) as client:
            for attempt in range(settings.IBGE_MAX_ATTEMPTS):
                remaining = deadline - self.clock()
                if remaining <= 0:
                    raise ServiceError("upstream_timeout", "O IBGE excedeu o tempo de resposta.", 504)
                request_timeout = httpx.Timeout(min(settings.IBGE_READ_TIMEOUT, remaining), connect=min(settings.IBGE_CONNECT_TIMEOUT, remaining))
                try:
                    with client.stream("GET", url, timeout=request_timeout, headers={"Accept": "application/json"}) as response:
                        if 300 <= response.status_code < 400:
                            raise ServiceError("upstream_redirect", "O IBGE retornou um redirecionamento não permitido.")
                        if response.status_code in (429, 500, 502, 503, 504):
                            raise ServiceError("upstream_unavailable", "O IBGE está temporariamente indisponível.")
                        if response.status_code != 200:
                            raise ServiceError("upstream_http_error", "O IBGE retornou uma resposta HTTP inválida.")
                        media_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                        if media_type != "application/json" and not media_type.endswith("+json"):
                            raise ServiceError("upstream_invalid_json", "O IBGE não retornou JSON.")
                        content = bytearray()
                        for chunk in response.iter_bytes(chunk_size=16384):
                            if self.clock() >= deadline:
                                raise ServiceError("upstream_timeout", "O IBGE excedeu o tempo de resposta.", 504)
                            content.extend(chunk)
                            if len(content) > settings.IBGE_MAX_RESPONSE_BYTES:
                                raise ServiceError("response_too_large", "A resposta excede o limite de tamanho.", 422)
                        try:
                            data = json.loads(content, parse_constant=reject_nonfinite_json, parse_float=parse_finite_float)
                        except (ValueError, UnicodeError) as exc:
                            raise ServiceError("upstream_invalid_json", "O IBGE retornou JSON inválido.") from exc
                        if not isinstance(data, (list, dict)):
                            raise ServiceError("upstream_invalid_json", "O IBGE retornou uma estrutura JSON inválida.")
                        ttl = settings.IBGE_SERIES_TTL if series else settings.IBGE_CATALOG_TTL
                        now = timezone.now()
                        result = {"data": data, "source_url": url, "fetched_at": now.isoformat(), "expires_at": (now + timedelta(seconds=ttl)).isoformat()}
                        cache.set(key, result, timeout=ttl)
                        return {**result, "cache_hit": False}
                except httpx.TimeoutException as exc:
                    error = ServiceError("upstream_timeout", "O IBGE excedeu o tempo de resposta.", 504)
                    error.__cause__ = exc
                except httpx.RequestError as exc:
                    error = ServiceError("upstream_connection_error", "Não foi possível conectar ao IBGE.")
                    error.__cause__ = exc
                except ServiceError as exc:
                    if exc.error_code != "upstream_unavailable":
                        raise
                    error = exc
                if attempt + 1 >= settings.IBGE_MAX_ATTEMPTS:
                    raise error
                delay = 0.25 * (attempt + 1)
                if self.clock() + delay >= deadline:
                    raise ServiceError("upstream_timeout", "O IBGE excedeu o tempo de resposta.", 504)
                self.sleep(delay)
        raise AssertionError("Tentativas devem ser positivas")
