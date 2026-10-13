"""Verifica exemplos de contrato; não implementa normalizador ou consulta."""
import hashlib
import json
from pathlib import Path

from django.test import SimpleTestCase
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = Path(__file__).parent / "fixtures"
SCHEMA = json.loads((ROOT / "docs/schemas/contrato-v1.schema.json").read_text(encoding="utf-8"))


def fixture(name):
    return json.loads((FIXTURES / "synthetic" / name).read_text(encoding="utf-8"))


def validator(name):
    schema = {"$schema": SCHEMA["$schema"], "$defs": SCHEMA["$defs"], "$ref": "#/$defs/" + name}
    return Draft202012Validator(schema, format_checker=FormatChecker())


class ContractFixtureTests(SimpleTestCase):
    def test_schema_and_main_examples_are_valid(self):
        Draft202012Validator.check_schema(SCHEMA)
        for name, definition in [
            ("consulta.json", "consulta"), ("metadados_normalizados.json", "metadados"),
            ("resultado_esperado.json", "resultado"), ("erro.json", "erro"),
        ]:
            with self.subTest(name=name):
                validator(definition).validate(fixture(name))

    def test_query_rejects_url_wildcards_numeric_ids_and_unknown_fields(self):
        for changes in [
            {"agregado_id": 900001}, {"periodo_ids": ["all"]}, {"periodo_ids": ["-6"]},
            {"url": "https://example.org/"}, {"nivel_id": "N6|N3"},
            {"variavel_ids": ["000101", "000101"]}, {"localidade_ids": []},
            {"variavel_ids": [str(i) for i in range(7)]},
        ]:
            with self.subTest(changes=changes):
                query = {**fixture("consulta.json"), **changes}
                self.assertFalse(validator("consulta").is_valid(query))

    def test_synthetic_manifest_has_no_official_claim_and_matches_files(self):
        manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["kind"], "synthetic")
        self.assertFalse(manifest["captured_from_ibge"])
        files = {item["path"] for item in manifest["files"]}
        self.assertEqual(files, {"synthetic/" + file.name for file in (FIXTURES / "synthetic").glob("*.json")})
        for item in manifest["files"]:
            with self.subTest(path=item["path"]):
                self.assertEqual(hashlib.sha256((FIXTURES / item["path"]).read_bytes()).hexdigest(), item["sha256"])

    def test_documentation_capture_is_separate_and_has_integrity(self):
        manifest = json.loads((ROOT / "docs/evidencias/manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["kind"], "official_documentation")
        self.assertEqual(manifest["official_dataset_captures"], 0)
        path = ROOT / "docs/evidencias" / manifest["extract"]
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), manifest["extract_sha256"])

    def test_example_includes_all_groups_and_preserves_literal_observations(self):
        raw = fixture("series.json")
        result = fixture("resultado_esperado.json")["data"]["observacoes"]
        raw_points = [(vi, ri, si, period, value) for vi, var in enumerate(raw) for ri, group in enumerate(var["resultados"]) for si, series in enumerate(group["series"]) for period, value in series["serie"].items()]
        expected = [(row["origem_indice"]["variavel"], row["origem_indice"]["resultado"], row["origem_indice"]["serie"], row["periodo_id"], row["valor_original"]) for row in result]
        self.assertEqual(raw_points, expected)
        self.assertEqual(len(result), 15)
        self.assertEqual({row["variavel_id"] for row in result}, {"000101", "102"})
        self.assertTrue(all(len(row["classificacoes"]) == 2 for row in result))

    def test_homonyms_leading_zeroes_and_null_level_have_explicit_identity(self):
        localities = fixture("localidades.json")
        self.assertEqual(len({row["nome"] for row in localities}), 1)
        self.assertEqual(len({row["id"] for row in localities}), 2)
        self.assertEqual(len(fixture("municipios_enriquecimento.json")), 1)
        raw = fixture("series.json")
        self.assertTrue(all(series["localidade"]["nivel"] is None for var in raw for group in var["resultados"] for series in group["series"]))
        result = fixture("resultado_esperado.json")["data"]["observacoes"]
        self.assertEqual({row["nivel_id"] for row in result}, {"N6"})
        self.assertEqual({row["localidade_id"] for row in result}, {"0000001", "0000002"})
        self.assertEqual({row["classificacoes"][1]["categoria_id"] for row in result}, {"00"})

    def test_markers_empty_null_and_unknown_are_not_zero(self):
        rows = fixture("resultado_esperado.json")["data"]["observacoes"]
        self.assertEqual({row["valor_status"] for row in rows}, {"numerico", "marcador", "vazio", "nulo", "nao_reconhecido"})
        for row in rows:
            if row["valor_status"] != "numerico":
                self.assertIsNone(row["valor_numerico"])
        self.assertTrue(any(row["valor_original"] == "-0.00" and row["valor_numerico"] == 0 for row in rows))

    def test_period_gap_is_not_an_invented_observation(self):
        periods = fixture("periodos.json")
        self.assertTrue(all(len(row["id"]) == 6 for row in periods))
        rows = fixture("resultado_esperado.json")["data"]["observacoes"]
        self.assertFalse(any(row["periodo_id"] == "202402" for row in rows))
        self.assertEqual(len(rows), 15)  # 16 estimadas, uma ausente; não preencher com zero.

    def test_all_territorial_groups_and_total_exception_are_retained(self):
        metadata = fixture("metadados_normalizados.json")
        self.assertEqual({row["grupo"] for row in metadata["niveis"]}, {"Administrativo", "Especial", "IBGE"})
        self.assertEqual(metadata["classificacoes"][0]["sumarizacao"]["excecao"], ["102"])
        self.assertFalse(metadata["classificacoes"][1]["sumarizacao"]["status"])

    def test_empty_result_and_unknown_pagination_are_supported(self):
        result = fixture("resultado_esperado.json")
        result["data"]["observacoes"] = fixture("series_vazias.json")
        validator("resultado").validate(result)
        validator("paginacao").validate({"page": 1, "page_size": 50, "total_count": None, "has_next": None})

    def test_truncated_success_is_forbidden(self):
        result = fixture("resultado_esperado.json")
        result["data"]["truncated"] = True
        self.assertFalse(validator("resultado").is_valid(result))

    def test_conflicting_fixture_keeps_both_occurrences(self):
        data = fixture("series_conflito.json")
        first = data[0]["resultados"][0]["series"][0]
        second = data[0]["resultados"][1]["series"][0]
        self.assertEqual(first["localidade"], second["localidade"])
        self.assertEqual(data[0]["resultados"][0]["classificacoes"], data[0]["resultados"][1]["classificacoes"])
        self.assertNotEqual(first["serie"]["202401"], second["serie"]["202401"])

    def test_official_captures_have_independent_manifest_and_valid_hashes(self):
        base = FIXTURES / "official"
        manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["kind"], "official_dataset")
        self.assertEqual(len(manifest["files"]), 8)
        for record in manifest["files"]:
            with self.subTest(path=record["path"]):
                self.assertEqual(record["status"], "captured")
                self.assertEqual(record["http_status"], 200)
                self.assertFalse(record["cache_hit"])
                self.assertTrue(record["source_url"].startswith("https://servicodados.ibge.gov.br/api/"))
                self.assertEqual(hashlib.sha256((base / record["path"]).read_bytes()).hexdigest(), record["sha256"])
        query = manifest["resolved_query"]
        self.assertEqual(hashlib.sha256((base / query["path"]).read_bytes()).hexdigest(), query["sha256"])

    def test_official_query_covers_every_classification_and_valid_total_rules(self):
        base = FIXTURES / "official"
        metadata = json.loads((base / "metadados_1712.json").read_text(encoding="utf-8"))
        query = json.loads((base / "consulta_1712.json").read_text(encoding="utf-8"))
        validator("consulta").validate(query)
        self.assertEqual({item["classificacao_id"] for item in query["classificacoes"]}, {str(item["id"]) for item in metadata["classificacoes"]})
        indexed = {str(item["id"]): item for item in metadata["classificacoes"]}
        for selected in query["classificacoes"]:
            classification = indexed[selected["classificacao_id"]]
            for category in selected["categoria_ids"]:
                if category == "0":
                    self.assertTrue(classification["sumarizacao"]["status"])
                    self.assertFalse(set(query["variavel_ids"]) & {str(id_) for id_ in classification["sumarizacao"]["excecao"]})
                else:
                    self.assertIn(category, {str(item["id"]) for item in classification["categorias"]})

    def test_official_series_is_period_map_and_has_four_values(self):
        raw = json.loads((FIXTURES / "official/series_1712.json").read_text(encoding="utf-8"))
        count = 0
        for variable in raw:
            for result in variable["resultados"]:
                self.assertEqual(len(result["classificacoes"]), 6)
                for series in result["series"]:
                    self.assertIsInstance(series["serie"], dict)
                    self.assertEqual(series["localidade"]["nivel"]["id"], "N1")
                    count += len(series["serie"])
        self.assertEqual(count, 4)

    def test_official_derived_example_is_labeled_and_validates(self):
        base = FIXTURES / "derived"
        manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(manifest["not_an_api_capture"])
        for record in manifest["files"]:
            self.assertEqual(hashlib.sha256((base / record["path"]).read_bytes()).hexdigest(), record["sha256"])
        result = json.loads((base / "resultado_1712_esperado.json").read_text(encoding="utf-8"))
        validator("resultado").validate(result)

    def test_official_unit_conflict_is_visible_and_not_replaced_silently(self):
        result = json.loads((FIXTURES / "derived/resultado_1712_esperado.json").read_text(encoding="utf-8"))
        rows = result["data"]["observacoes"]
        conflicts = [row for row in rows if row["unidade_status"] == "conflitante"]
        self.assertEqual(len(conflicts), 2)
        for row in conflicts:
            self.assertIsNone(row["unidade"])
            self.assertEqual(row["unidade_original"], "Mil frutos")
            self.assertEqual(row["classificacoes"][0]["categoria_unidade"], "Toneladas")
        self.assertEqual({warning["code"] for warning in result["data"]["warnings"]}, {"unit_metadata_conflict"})
