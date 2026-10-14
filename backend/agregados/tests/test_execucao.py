import copy
import json
from unittest.mock import patch

import httpx
import jsonschema
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from agregados.clients.ibge import IbgeClient
from agregados.errors import ServiceError
from agregados.services.normalizacao import normalize, value
from agregados.services.estatisticas import summarize, period_order
from .test_contract import fixture, FIXTURES, ROOT


class ExecutionTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.query = fixture('consulta.json')
        self.metadata = fixture('metadados_normalizados.json')
        self.raw = fixture('series.json')

    def normalize(self):
        return normalize(self.raw, self.query, self.metadata)

    def test_all_groups_exact_observations_and_gaps(self):
        result = self.normalize()
        self.assertEqual(result['observacoes'], fixture('resultado_esperado.json')['data']['observacoes'])
        self.assertEqual(len(result['observacoes']), 15)
        self.assertEqual(len(result['analises']), 8)
        self.assertEqual(result['corpo_original'], self.raw)
        self.assertTrue(result['ordem_cronologica'])
        gap = result['analises'][3]
        self.assertEqual((gap['n'], gap['sem_numero']), (0, 1))
        self.assertTrue(gap['pontos'][1]['lacuna'])

    def test_values_are_literal_and_finite(self):
        for literal, expected in [('X','marcador'), ('x','marcador'), ('..','marcador'), ('...','marcador'), ('-','marcador'), ('','vazio'), (None,'nulo'), ('1,25','nao_reconhecido'), ('NaN','nao_reconhecido'), ('1e3','nao_reconhecido'), ('-0.00','numerico'), (2,'numerico'), ('0.25','numerico')]:
            self.assertEqual(value(literal)[1], expected)
        for literal in [True, [], {}]:
            with self.assertRaises(ServiceError): value(literal)

    def test_statistics_cases_and_sample_deviation(self):
        base = self.normalize()['observacoes'][0]
        for case in fixture('estatisticas_casos.json'):
            rows = [{**base, 'periodo_id': p, 'valor_numerico': v} for p, v in zip(case['periodos'], case['valores'])]
            result = summarize(rows, case['periodos'], True)[0]
            for key, expected in case['esperado'].items():
                self.assertEqual(result[key], expected, case['caso'])
        rows = [{**base, 'periodo_id': str(i), 'valor_numerico': v} for i,v in enumerate([1, 3])]
        self.assertAlmostEqual(summarize(rows, ['0','1'], True)[0]['desvio'], 2 ** .5)

    def test_duplicate_preserved_without_double_count_and_conflict_rejected(self):
        self.raw.append(copy.deepcopy(self.raw[0]))
        self.raw[-1]['resultados'][0]['classificacoes'].reverse()
        result = self.normalize()
        self.assertEqual(len(result['observacoes']), 22)
        self.assertEqual(result['analises'][0]['n'], 2)
        self.assertIn('duplicate_observation', [w['code'] for w in result['warnings']])
        self.raw[-1]['resultados'][0]['series'][0]['serie']['202401'] = '11'
        with self.assertRaises(ServiceError) as raised: self.normalize()
        self.assertEqual(raised.exception.error_code, 'upstream_inconsistent_data')
        self.assertEqual(len(raised.exception.error_details['indices']), 2)

    def test_invalid_dimensions_and_structures_block_partial_results(self):
        original = copy.deepcopy(self.raw)
        changes = [lambda r: r[0].update(id='101'), lambda r: r[0]['resultados'][0]['classificacoes'][0]['categoria'].update({'02':'extra'}), lambda r: r[0]['resultados'][0]['series'][0]['localidade'].update(nivel={'id':'N1'}), lambda r: r[0]['resultados'][0]['series'][0]['localidade'].update(id='1'), lambda r: r[0]['resultados'][0]['series'][0].update(serie=[]), lambda r: r[0]['resultados'][0]['series'][0]['serie'].update({'202402':'2'}), lambda r: r[0]['resultados'][0].update(classificacoes=[]), lambda r: r[0].pop('unidade')]
        for change in changes:
            self.raw = copy.deepcopy(original); change(self.raw)
            with self.assertRaises(ServiceError): self.normalize()

    def test_empty_unknown_fields_and_actual_limit(self):
        self.raw = []
        self.assertEqual(self.normalize()['observacoes'], [])
        self.raw = fixture('series.json'); self.raw[0]['notas'] = ['nota literal']
        result = self.normalize()
        self.assertEqual(result['corpo_original'][0]['notas'], ['nota literal'])
        self.assertEqual(result['warnings'][0]['code'], 'unmapped_fields')
        with override_settings(IBGE_MAX_OBSERVATIONS=14):
            with self.assertRaises(ServiceError) as raised: self.normalize()
            self.assertEqual(raised.exception.status_code, 422)

    def test_unknown_periodicity_does_not_infer_chronology(self):
        self.metadata['periodicidade']['frequencia'] = 'Trimestral'
        self.metadata['periodos'].reverse()
        order, chronological = period_order(self.metadata, self.query)
        self.assertEqual(order, ['202403', '202401']); self.assertFalse(chronological)
        self.assertFalse(self.normalize()['analises'][0]['grafico_linhas'])

    def test_units_suspend_analysis_without_reinterpreting(self):
        self.raw[0]['unidade'] = 'Outra unidade'
        result = self.normalize()
        self.assertIsNone(result['observacoes'][0]['unidade'])
        self.assertEqual(result['observacoes'][0]['valor_numerico'], 10)
        self.assertTrue(result['analises'][0]['suspensa'])
        self.assertIsNone(result['analises'][0]['media'])
        self.metadata['variaveis'][0]['unidade'] = None
        self.assertEqual(self.normalize()['observacoes'][0]['unidade_status'], 'nao_confirmada')

    def test_category_units_apply_only_to_referenced_classification(self):
        self.metadata['classificacoes'][0]['categorias'][0]['unidade'] = 'Toneladas'
        self.assertEqual(self.normalize()['observacoes'][0]['unidade_status'], 'coerente')
        self.metadata['variaveis'][0]['unidade'] = "Vide categorias da classificação 'Grupo sintético'"
        self.assertEqual(self.normalize()['observacoes'][0]['unidade_status'], 'conflitante')
        self.metadata['classificacoes'][0]['nome'] = 'Outro nome'
        self.assertEqual(self.normalize()['observacoes'][0]['unidade_status'], 'nao_confirmada')

    def test_extreme_finite_values_do_not_crash_statistics(self):
        self.raw[0]['resultados'][0]['series'][0]['serie'] = {'202401': -1.7e308, '202403': 1.7e308}
        result = self.normalize()
        self.assertEqual(result['analises'][0]['n'], 2)
        self.assertIsNone(result['analises'][0]['desvio'])
        json.dumps(result, allow_nan=False)

    def test_official_capture_unit_conflict_and_expected_observations(self):
        def load(folder, name): return json.loads((FIXTURES / folder / name).read_text(encoding='utf-8'))
        from agregados.services.catalogo import CatalogService
        payloads = {'/api/v3/agregados/1712/metadados': load('official','metadados_1712.json'), '/api/v3/agregados/1712/periodos': load('official','periodos_1712.json'), '/api/v3/agregados': load('official','acervo_N.json')}
        client = IbgeClient(transport=httpx.MockTransport(lambda request: httpx.Response(200,json=payloads[request.url.path])))
        self.metadata = CatalogService(client).metadata('1712')
        self.query = load('official', 'consulta_1712.json'); self.raw = load('official', 'series_1712.json')
        result = self.normalize()
        expected = load('derived','resultado_1712_esperado.json')['data']['observacoes']
        self.assertEqual(result['observacoes'], expected)
        self.assertEqual(sum(a['suspensa'] for a in result['analises']), 2)
        self.assertEqual(sum(a['n'] for a in result['analises']), 4)
        self.assertTrue(result['ordem_cronologica'])

    def test_endpoint_semantics_cache_provenance_schema_and_errors(self):
        calls = []
        def handle(request):
            calls.append(request.url)
            path = request.url.path
            if '/variaveis/' in path: body = self.raw
            elif path.endswith('/metadados'): body = fixture('metadados.json')
            elif path.endswith('/periodos'): body = fixture('periodos.json')
            elif '/localidades/' in path: body = fixture('localidades.json')
            else: body = fixture('acervos.json')['N']
            return httpx.Response(200, json=body)
        with patch('agregados.services.catalogo.IbgeClient', side_effect=lambda: IbgeClient(transport=httpx.MockTransport(handle))):
            def post(q): return self.client.post('/api/v1/agregados-ibge/consultas/executar/', q, content_type='application/json')
            invalid = {**self.query, 'variavel_ids': ['101']}
            self.assertEqual(post(invalid).status_code, 400)
            self.assertFalse(any('/variaveis/' in u.path for u in calls))
            response = post(self.query)
            self.assertEqual(response.status_code, 200, response.content)
            schema = json.loads((ROOT / 'docs/schemas/contrato-v1.schema.json').read_text(encoding='utf-8'))
            jsonschema.validate(response.json(), {**schema, '$ref':'#/$defs/resultado'})
            self.assertEqual(len(response.json()['sources']), 5)
            count = len(calls)
            repeated = post(self.query)
            self.assertEqual(len(calls), count)
            self.assertTrue(all(s['cache_hit'] for s in repeated.json()['sources']))
            self.assertEqual(repeated.json()['sources'][-1]['fetched_at'], response.json()['sources'][-1]['fetched_at'])
