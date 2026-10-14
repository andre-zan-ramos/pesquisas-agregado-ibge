"""Round trips de consulta/exportação, usando somente fixtures existentes."""
import copy
import json

from django.test import SimpleTestCase
from . import test_consultas as queries
from .test_contract import fixture
from agregados.services.normalizacao import normalize


class SharingTests(SimpleTestCase):
    def setUp(self):
        queries.QueryTests.setUp(self)

    def test_import_roundtrip_revalidates_without_series(self):
        saved = json.loads(json.dumps({'version': 1, 'consulta': self.query}))
        response = self.client.post(queries.PREFIX + 'consultas/validar/', saved['consulta'], content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['consulta_resolvida'], self.query)
        self.assertTrue(all('/variaveis/' not in url.path for url in self.calls))
        # The versioned import wrapper itself is never an executable API payload.
        self.assertEqual(self.client.post(queries.PREFIX + 'consultas/validar/', saved, content_type='application/json').status_code, 400)

    def test_changed_dimensions_are_rejected_after_roundtrip(self):
        for field, value in [('agregado_id', True), ('nivel_id', 'N999'), ('localidade_ids', ['999']), ('variavel_ids', ['999']), ('periodo_ids', ['999']), ('classificacoes', [])]:
            with self.subTest(field=field):
                draft = copy.deepcopy(self.query); draft[field] = value
                restored = json.loads(json.dumps(draft))
                response = self.client.post(queries.PREFIX + 'consultas/validar/', restored, content_type='application/json')
                self.assertEqual(response.status_code, 400)
        self.assertTrue(all('/variaveis/' not in url.path for url in self.calls))

    def test_exportable_json_keeps_all_occurrences_literals_raw_and_units(self):
        raw = fixture('series.json'); raw.append(copy.deepcopy(raw[0]))
        normalized = normalize(raw, self.query, fixture('metadados_normalizados.json'))
        envelope = {'data': normalized, 'sources': fixture('resultado_esperado.json')['sources']}
        exported = json.loads(json.dumps(envelope, ensure_ascii=False, allow_nan=False))
        self.assertEqual(exported, envelope)
        self.assertEqual(len(exported['data']['observacoes']), 22)
        self.assertEqual(exported['data']['corpo_original'], raw)
        literals = [r['valor_original'] for r in exported['data']['observacoes']]
        for literal in [None, '', 'X', '...', '-0.00']:
            self.assertIn(literal, literals)
        self.assertEqual(exported['data']['consulta_aplicada'], self.query)
