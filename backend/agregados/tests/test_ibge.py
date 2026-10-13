from unittest.mock import Mock, patch

import httpx
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIClient

from agregados.clients.ibge import IbgeClient, build_url, _slots
from agregados.errors import ServiceError, exception_handler

PATH = "/api/v3/agregados/1705/metadados"


class IbgeClientTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def ibge_client(self, handler):
        return IbgeClient(transport=httpx.MockTransport(handler), sleep=lambda _: None)

    def test_cache_preserves_empty_data_source_and_timestamp(self):
        handler = Mock(return_value=httpx.Response(200, json=[]))
        client = self.ibge_client(handler)
        first = client.get_json(PATH)
        second = client.get_json(PATH)
        self.assertEqual(first["data"], [])
        self.assertFalse(first["cache_hit"])
        self.assertTrue(second["cache_hit"])
        self.assertEqual(first["fetched_at"], second["fetched_at"])
        self.assertEqual(first["source_url"], build_url(PATH))
        self.assertEqual(handler.call_count, 1)

    def test_expired_cache_refetches(self):
        handler = Mock(return_value=httpx.Response(200, json={"id": "1705"}))
        client = self.ibge_client(handler)
        client.get_json(PATH)
        with patch("django.core.cache.backends.locmem.time.time", return_value=10**12):
            self.assertFalse(client.get_json(PATH)["cache_hit"])
        self.assertEqual(handler.call_count, 2)

    def test_cache_keys_include_query_and_are_order_independent(self):
        handler = Mock(return_value=httpx.Response(200, json=[]))
        client = self.ibge_client(handler)
        client.get_json("/api/v3/agregados", {"nivel": "N6", "periodo": "2020"})
        self.assertTrue(client.get_json("/api/v3/agregados", {"periodo": "2020", "nivel": "N6"})["cache_hit"])
        self.assertFalse(client.get_json("/api/v3/agregados", {"nivel": "N3", "periodo": "2020"})["cache_hit"])
        self.assertEqual(handler.call_count, 2)

    def test_timeout_retries_with_limit_and_does_not_cache_failure(self):
        handler = Mock(side_effect=httpx.ReadTimeout("simulado"))
        with self.assertRaises(ServiceError) as ctx:
            self.ibge_client(handler).get_json(PATH)
        self.assertEqual(ctx.exception.status_code, 504)
        self.assertEqual(handler.call_count, 2)
        good = Mock(return_value=httpx.Response(200, json=[]))
        self.assertFalse(self.ibge_client(good).get_json(PATH)["cache_hit"])

    def test_connection_error_is_structured(self):
        with self.assertRaises(ServiceError) as ctx:
            self.ibge_client(Mock(side_effect=httpx.ConnectError("simulado"))).get_json(PATH)
        self.assertEqual(ctx.exception.error_code, "upstream_connection_error")

    def test_http_error_is_not_retried(self):
        handler = Mock(return_value=httpx.Response(404))
        with self.assertRaises(ServiceError) as ctx:
            self.ibge_client(handler).get_json(PATH)
        self.assertEqual(ctx.exception.error_code, "upstream_http_error")
        self.assertEqual(handler.call_count, 1)

    def test_transient_error_can_recover(self):
        handler = Mock(side_effect=[httpx.Response(503), httpx.Response(200, json={})])
        self.assertEqual(self.ibge_client(handler).get_json(PATH)["data"], {})
        self.assertEqual(handler.call_count, 2)

    def test_invalid_json_html_and_scalar_are_rejected_without_retry(self):
        for response in [
            httpx.Response(200, content=b"{", headers={"content-type": "application/json"}),
            httpx.Response(200, text="<html/>", headers={"content-type": "text/html"}),
            httpx.Response(200, json=None),
        ]:
            with self.subTest(response=response):
                handler = Mock(return_value=response)
                with self.assertRaises(ServiceError) as ctx:
                    self.ibge_client(handler).get_json(PATH)
                self.assertEqual(ctx.exception.error_code, "upstream_invalid_json")
                self.assertEqual(handler.call_count, 1)

    def test_nonfinite_json_numbers_are_rejected_and_not_cached(self):
        for constant in ["NaN", "Infinity", "-Infinity", "1e999", "-1e999"]:
            with self.subTest(constant=constant):
                cache.clear()
                response = httpx.Response(
                    200,
                    content=('{"valor": ' + constant + '}').encode(),
                    headers={"content-type": "application/json"},
                )
                handler = Mock(return_value=response)
                with self.assertRaises(ServiceError) as ctx:
                    self.ibge_client(handler).get_json(PATH)
                self.assertEqual(ctx.exception.error_code, "upstream_invalid_json")
                self.assertEqual(handler.call_count, 1)
                good = self.ibge_client(lambda _: httpx.Response(200, json={"valor": 0}))
                self.assertFalse(good.get_json(PATH)["cache_hit"])

    def test_arbitrary_hosts_paths_and_parameters_are_blocked_before_network(self):
        handler = Mock()
        for path in ["https://example.org", "//example.org", "/api/v3/agregados/../secret", PATH + "?x=1", "/api/v3/agregados%2fsecret"]:
            with self.subTest(path=path), self.assertRaises(ServiceError):
                self.ibge_client(handler).get_json(path)
        with self.assertRaises(ServiceError):
            self.ibge_client(handler).get_json(PATH, {"url": "https://example.org"})
        handler.assert_not_called()

    def test_redirect_is_never_followed_even_to_official_host(self):
        handler = Mock(return_value=httpx.Response(302, headers={"location": "https://example.org/"}))
        with self.assertRaises(ServiceError) as ctx:
            self.ibge_client(handler).get_json(PATH)
        self.assertEqual(ctx.exception.error_code, "upstream_redirect")
        self.assertEqual(handler.call_count, 1)

    @override_settings(IBGE_MAX_RESPONSE_BYTES=10)
    def test_response_size_limit(self):
        with self.assertRaises(ServiceError) as ctx:
            self.ibge_client(lambda _: httpx.Response(200, json={"large": "x" * 100})).get_json(PATH)
        self.assertEqual(ctx.exception.status_code, 422)

    def test_total_deadline_stops_retry(self):
        handler = Mock(side_effect=httpx.ReadTimeout("simulado"))
        clock = Mock(side_effect=[0, 0, 30])
        with self.assertRaises(ServiceError) as ctx:
            IbgeClient(transport=httpx.MockTransport(handler), clock=clock).get_json(PATH)
        self.assertEqual(ctx.exception.status_code, 504)
        self.assertEqual(handler.call_count, 1)

    def test_saturated_client_returns_429_and_releases_slots(self):
        self.assertTrue(_slots.acquire(blocking=False))
        self.assertTrue(_slots.acquire(blocking=False))
        try:
            with self.assertRaises(ServiceError) as ctx:
                self.ibge_client(Mock()).get_json(PATH)
            self.assertEqual(ctx.exception.status_code, 429)
        finally:
            _slots.release()
            _slots.release()
        self.assertFalse(self.ibge_client(lambda _: httpx.Response(200, json=[])).get_json(PATH)["cache_hit"])

    def test_error_envelope(self):
        response = exception_handler(ServiceError("upstream_timeout", "Tempo excedido.", 504), {})
        self.assertEqual(response.status_code, 504)
        self.assertEqual(response.data, {"error": {"code": "upstream_timeout", "message": "Tempo excedido.", "details": None}})

    def test_health_does_not_call_upstream_or_database(self):
        with patch("httpx.Client", side_effect=AssertionError("Sem rede")):
            response = APIClient().get("/api/v1/agregados-ibge/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_unsupported_method_has_error_envelope(self):
        response = APIClient().post("/api/v1/agregados-ibge/health/", {})
        self.assertEqual(response.status_code, 405)
        self.assertIn("error", response.json())
