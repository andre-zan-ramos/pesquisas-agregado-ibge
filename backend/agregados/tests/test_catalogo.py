import copy
import json
from unittest.mock import patch

import httpx
from django.core.cache import cache
from django.test import SimpleTestCase

from agregados.clients.ibge import IbgeClient
from .test_contract import FIXTURES, fixture, validator

PREFIX = "/api/v1/agregados-ibge/"


class CatalogApiTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.domains = fixture("acervos.json")
        self.catalog = fixture("catalogo.json")
        self.metadata = fixture("metadados.json")
        self.periods = fixture("periodos.json")
        self.requests = []
        self.failure = None

        def handle(request):
            self.requests.append(request)
            self.assertNotIn("/variaveis/", request.url.path)
            if self.failure:
                raise self.failure
            if request.url.path.endswith("/metadados"):
                body = self.metadata
            elif request.url.path.endswith("/periodos"):
                body = self.periods
            elif "acervo" in request.url.params:
                body = self.domains[request.url.params["acervo"]]
            else:
                body = self.catalog
            return httpx.Response(200, json=body)

        self.transport = httpx.MockTransport(handle)
        self.patcher = patch("agregados.services.catalogo.IbgeClient", side_effect=lambda: IbgeClient(transport=self.transport, sleep=lambda _: None))
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def get(self, path, **params):
        return self.client.get(PREFIX + path, params)

    def test_domains_and_cache_provenance(self):
        first = self.get("dominios/")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["data"]["assuntos"], [{"id": "001", "nome": "Assunto sintético"}])
        second = self.get("dominios/").json()
        self.assertEqual(len(self.requests), 3)
        self.assertTrue(all(source["cache_hit"] for source in second["sources"]))
        self.assertEqual(first.json()["sources"][0]["fetched_at"], second["sources"][0]["fetched_at"])

    def test_metadata_matches_complete_contract(self):
        response = self.get("agregados/900001/metadados/")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        validator("metadados").validate(data)
        self.assertEqual(data, fixture("metadados_normalizados.json"))
        self.assertEqual(len(response.json()["sources"]), 3)

    def test_official_capture_without_network(self):
        def load(name):
            return json.loads((FIXTURES / "official" / name).read_text(encoding="utf-8"))
        self.metadata = load("metadados_1712.json")
        self.periods = load("periodos_1712.json")
        self.domains["N"] = load("acervo_N.json")
        response = self.get("agregados/1712/metadados/")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        validator("metadados").validate(data)
        self.assertEqual(len(data["classificacoes"]), 6)
        self.assertEqual(data["periodicidade"]["inicio"], "2006")
        self.assertEqual(sum(len(v) for v in self.metadata["nivelTerritorial"].values()), len(data["niveis"]))

    def test_unknown_group_and_missing_label_are_preserved(self):
        self.metadata["nivelTerritorial"]["Novo"] = ["N999"]
        data = self.get("agregados/900001/metadados/").json()["data"]
        self.assertIn({"id": "N999", "nome": None, "grupo": "Novo"}, data["niveis"])

    def test_search_code_name_and_pagination(self):
        self.catalog.append({"id": "OUTRA", "nome": "Outra pesquisa", "agregados": [{"id": "0002", "nome": "Outro"}]})
        for query in ("900001", "classificações", "sintética"):
            with self.subTest(query=query):
                data = self.get("pesquisas/", q=query).json()["data"]
                self.assertEqual(data["pagination"]["total_count"], 1)
                self.assertEqual(data["items"][0]["agregados"][0]["id"], "900001")
        data = self.get("pesquisas/", page=2, page_size=1).json()["data"]
        self.assertEqual(data["items"][0]["agregados"][0]["id"], "0002")
        self.assertFalse(data["pagination"]["has_next"])
        self.assertEqual(self.get("pesquisas/", q="inexistente").json()["data"]["items"], [])

    def test_filters_are_published_and_forwarded(self):
        response = self.get("pesquisas/", assunto="001", nivel="N6", periodo="202401")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(dict(self.requests[-1].url.params), {"assunto": "001", "nivel": "N6", "periodo": "202401"})
        self.assertEqual(self.get("pesquisas/", assunto="1").status_code, 400)
        self.assertEqual(len([request for request in self.requests if not request.url.params.get("acervo")]), 1)

    def test_invalid_inputs_do_not_fetch(self):
        for params in ({"url": "https://evil.test"}, {"nivel": "N6|N3"}, {"page": 0}, {"page_size": 201}, {"q": "a" * 201}, {"page": [1, 2]}):
            with self.subTest(params=params):
                self.assertEqual(self.get("pesquisas/", **params).status_code, 400)
        self.assertEqual(self.get("dominios/", q="x").status_code, 400)
        self.assertEqual(self.requests, [])

    def test_empty_and_timeout_are_distinct(self):
        self.catalog = []
        self.assertEqual(self.get("pesquisas/").json()["data"]["items"], [])
        cache.clear()
        self.failure = httpx.ReadTimeout("mock")
        response = self.get("pesquisas/")
        self.assertEqual(response.status_code, 504)
        self.assertEqual(response.json()["error"]["code"], "upstream_timeout")

    def test_malformed_metadata_ids_and_types_fail(self):
        original = copy.deepcopy(self.metadata)
        for field, value in (("id", True), ("id", 900001.5), ("id", "900002"), ("variaveis", {}), ("nivelTerritorial", {"IBGE": ["N6|N3"]})):
            with self.subTest(field=field, value=value):
                cache.clear()
                self.metadata = {**copy.deepcopy(original), field: value}
                response = self.get("agregados/900001/metadados/")
                self.assertEqual(response.status_code, 502)
                self.assertEqual(response.json()["error"]["code"], "upstream_inconsistent_data")

    def test_no_query_editor_routes(self):
        for path in ("consultas/validar/", "consultas/executar/", "agregados/900001/localidades/", "agregados/900001/periodos/"):
            self.assertEqual(self.get(path).status_code, 404)
        self.assertEqual(self.requests, [])
