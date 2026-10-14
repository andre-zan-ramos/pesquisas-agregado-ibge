from unittest.mock import patch

import httpx
from django.core.cache import cache
from django.test import SimpleTestCase

from agregados.clients.ibge import IbgeClient
from .test_contract import fixture


class IntegratedRecoveryTests(SimpleTestCase):
    def test_catalog_validation_failure_recovery_and_cache_without_network(self):
        for failure, status in [('timeout', 504), ('invalid_json', 502), ('http', 502)]:
            with self.subTest(failure=failure):
                cache.clear()
                series_calls = []
                failing = True

                def handle(request):
                    path = request.url.path
                    if '/variaveis/' in path:
                        series_calls.append(str(request.url))
                        if failing:
                            if failure == 'timeout':
                                raise httpx.ReadTimeout('synthetic', request=request)
                            if failure == 'invalid_json':
                                return httpx.Response(200, content=b'{', headers={'Content-Type': 'application/json'})
                            return httpx.Response(503)
                        body = fixture('series.json')
                    elif path.endswith('/metadados'):
                        body = fixture('metadados.json')
                    elif path.endswith('/periodos'):
                        body = fixture('periodos.json')
                    elif '/localidades/' in path:
                        body = fixture('localidades.json')
                    else:
                        body = fixture('acervos.json')[request.url.params['acervo']] if 'acervo' in request.url.params else fixture('catalogo.json')
                    return httpx.Response(200, json=body)

                with patch('agregados.services.catalogo.IbgeClient', side_effect=lambda: IbgeClient(transport=httpx.MockTransport(handle), sleep=lambda _: None)):
                    prefix = '/api/v1/agregados-ibge/'
                    self.assertEqual(self.client.get(prefix + 'dominios/').status_code, 200)
                    self.assertEqual(self.client.get(prefix + 'pesquisas/?nivel=N6').status_code, 200)
                    query = fixture('consulta.json')
                    self.assertEqual(self.client.post(prefix + 'consultas/validar/', query, content_type='application/json').status_code, 200)
                    self.assertEqual(series_calls, [])
                    failed = self.client.post(prefix + 'consultas/executar/', query, content_type='application/json')
                    self.assertEqual(failed.status_code, status)
                    self.assertIn('error', failed.json())
                    self.assertEqual(len(series_calls), 1 if failure == 'invalid_json' else 2)
                    failing = False
                    recovered = self.client.post(prefix + 'consultas/executar/', query, content_type='application/json')
                    self.assertEqual(recovered.status_code, 200, recovered.content)
                    self.assertEqual(recovered.json()['data']['observacoes'], fixture('resultado_esperado.json')['data']['observacoes'])
                    self.assertFalse(recovered.json()['sources'][-1]['cache_hit'])
                    calls = len(series_calls)
                    repeated = self.client.post(prefix + 'consultas/executar/', query, content_type='application/json')
                    self.assertEqual(repeated.json()['data'], recovered.json()['data'])
                    self.assertTrue(all(s['cache_hit'] for s in repeated.json()['sources']))
                    self.assertEqual(len(series_calls), calls)
