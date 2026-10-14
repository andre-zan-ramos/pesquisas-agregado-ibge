"""Medição limitada offline; nunca instancia transporte HTTP real."""
import json
import platform
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import serve_phase2_fixtures as fixtures
from django.core.cache import cache
from django.test import Client
from agregados.clients.ibge import IbgeClient
import httpx


def main():
    calls = []

    def handle(request):
        response = fixtures.handle(request)
        calls.append(len(response.content))
        return response

    fixtures.catalogo.IbgeClient = lambda: IbgeClient(transport=httpx.MockTransport(handle), sleep=lambda _: None)
    client = Client()
    query = fixtures.load('consulta.json')
    samples = []
    for _ in range(5):
        cache.clear()
        pair = {}
        bodies = []
        for mode in ('cold', 'warm'):
            start_calls = len(calls)
            start = time.perf_counter()
            response = client.post('/api/v1/agregados-ibge/consultas/executar/', query, content_type='application/json')
            elapsed = (time.perf_counter() - start) * 1000
            assert response.status_code == 200, response.content
            body = response.json()
            assert len(body['data']['observacoes']) == 15
            assert all(s['cache_hit'] == (mode == 'warm') for s in body['sources'])
            pair[mode] = {'ms': round(elapsed, 3), 'internal_bytes': len(response.content), 'mock_calls': len(calls) - start_calls, 'mock_bytes': sum(calls[start_calls:])}
            bodies.append(body)
        assert bodies[0]['data'] == bodies[1]['data']
        assert [s['fetched_at'] for s in bodies[0]['sources']] == [s['fetched_at'] for s in bodies[1]['sources']]
        assert pair['warm']['mock_calls'] == 0
        samples.append(pair)
    report = {'evidence': 'offline synthetic / Django test client / MockTransport; no socket, no IBGE', 'python': platform.python_version(), 'platform': platform.platform(), 'samples': samples, 'median_ms': {mode: statistics.median(s[mode]['ms'] for s in samples) for mode in ('cold', 'warm')}}
    target = fixtures.ROOT / 'var/phase6-backend.json'
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
