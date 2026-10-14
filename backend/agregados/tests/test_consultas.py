import copy
import json
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs

import httpx
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from agregados.clients.ibge import IbgeClient
from .test_contract import fixture, FIXTURES

PREFIX = '/api/v1/agregados-ibge/'


class QueryTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.metadata = fixture('metadados.json')
        self.periods = fixture('periodos.json')
        self.locations = fixture('localidades.json')
        self.query = fixture('consulta.json')
        self.calls = []
        self.domains = fixture('acervos.json')
        def handle(request):
            self.calls.append(request.url)
            path = request.url.path
            if path.endswith('/metadados'): body = self.metadata
            elif path.endswith('/periodos'): body = self.periods
            elif '/localidades/' in path: body = self.locations
            elif path == '/api/v3/agregados': body = self.domains[request.url.params['acervo']]
            else: raise AssertionError('Network/series forbidden')
            return httpx.Response(200, json=body)
        self.patcher = patch('agregados.services.catalogo.IbgeClient', side_effect=lambda: IbgeClient(transport=httpx.MockTransport(handle), sleep=lambda _: None))
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def post(self, query=None):
        return self.client.post(PREFIX + 'consultas/validar/', query if query is not None else self.query, content_type='application/json')

    def test_valid_literal_url_and_provenance(self):
        response = self.post()
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()['data']
        self.assertEqual(data['consulta_resolvida'], self.query)
        self.assertEqual(data['estimated_observations'], 16)
        parsed = urlparse(data['source_url'])
        self.assertIn('/202401|202403/variaveis/000101|102', parsed.path)
        self.assertEqual(parse_qs(parsed.query), {'localidades': ['N6[0000001,0000002]'], 'classificacao': ['9001[01,02]|9002[00]']})
        self.assertEqual(len(response.json()['sources']), 4)

    def test_structure_and_all_dimensions(self):
        for field, value in [('agregado_id', 900001), ('variavel_ids', ['101']), ('periodo_ids', ['all']), ('localidade_ids', ['1']), ('nivel_id', 'N1'), ('classificacoes', []), ('variavel_ids', ['102', '102']), ('periodo_ids', []), ('url', 'https://evil.test')]:
            with self.subTest(field=field):
                query = copy.deepcopy(self.query); query[field] = value
                response = self.post(query)
                self.assertEqual(response.status_code, 400, response.content)
                self.assertEqual(response.json()['error']['code'], 'invalid_selection')
        query = copy.deepcopy(self.query)
        query['classificacoes'].append(copy.deepcopy(query['classificacoes'][0]))
        self.assertEqual(self.post(query).status_code, 400)

    def test_special_total_exceptions_and_literal_double_zero(self):
        self.query['classificacoes'][0]['categoria_ids'] = ['0']
        self.assertEqual(self.post().status_code, 400)
        self.query['variavel_ids'] = ['000101']
        self.assertEqual(self.post().status_code, 200)
        self.query['classificacoes'][1]['categoria_ids'] = ['0']
        self.assertEqual(self.post().status_code, 400)

    def test_budget(self):
        with override_settings(IBGE_MAX_OBSERVATIONS=15):
            self.assertEqual(self.post().status_code, 422)
        with override_settings(IBGE_MAX_VARIABLES=1):
            self.assertEqual(self.post().status_code, 422)
        with override_settings(IBGE_MAX_LOCALITIES=1):
            self.assertEqual(self.post().status_code, 422)

    def test_locations_search_pages_empty_and_invalid_level(self):
        path = PREFIX + 'agregados/900001/localidades/'
        response = self.client.get(path, {'nivel': 'N6', 'q': 'HOMONIMA', 'page_size': 1, 'page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['items'], [{'id': '0000002', 'nome': 'Localidade homônima', 'nivel_id': 'N6', 'uf_sigla': None}])
        self.assertEqual(self.client.get(path, {'nivel': 'N6', 'q': 'absent'}).json()['data']['items'], [])
        for params in ({'nivel': 'N1'}, {'nivel': 'N6', 'page_size': 201}, {'nivel': 'N6', 'extra': 1}, {}):
            self.assertEqual(self.client.get(path, params).status_code, 400)
        self.locations[0]['nivel']['id'] = 'N1'; cache.clear()
        self.assertEqual(self.client.get(path, {'nivel': 'N6'}).status_code, 502)

    def test_periods_preserve_order_labels(self):
        response = self.client.get(PREFIX + 'agregados/900001/periodos/')
        self.assertEqual(response.json()['data']['items'], fixture('metadados_normalizados.json')['periodos'])

    def test_no_classifications_and_null_location_level(self):
        self.metadata['classificacoes'] = []
        self.query['classificacoes'] = []
        self.locations[0]['nivel'] = None
        response = self.post()
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()['data']
        self.assertEqual(data['estimated_observations'], 8)
        self.assertNotIn('classificacao', parse_qs(urlparse(data['source_url']).query))

    def test_official_six_classifications_and_brazil(self):
        def load(name): return json.loads((FIXTURES / 'official' / name).read_text(encoding='utf-8'))
        self.metadata = load('metadados_1712.json'); self.periods = load('periodos_1712.json')
        self.locations = load('localidades_1712_N1.json'); self.domains['N'] = load('acervo_N.json')
        self.query = load('consulta_1712.json')
        response = self.post()
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(parse_qs(urlparse(response.json()['data']['source_url']).query)['localidades'], ['BR'])
        self.assertEqual(len(response.json()['data']['consulta_resolvida']['classificacoes']), 6)
