"""Captura manual limitada da fase 0. Não é executada por setup ou testes.

Requer --execute; não consulta municípios inteiros nem séries all.
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()
from django.test import override_settings
from agregados.clients.ibge import IbgeClient, build_url
from agregados.errors import ServiceError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Executa somente o lote limitado descrito neste script.")
    args = parser.parse_args()
    if not args.execute:
        parser.print_help()
        return
    destination = ROOT / "backend/agregados/tests/fixtures/official"
    destination.mkdir(exist_ok=True)
    if (destination / "manifest.json").exists():
        raise SystemExit("Captura já existe. Preserve a evidência; não sobrescrever automaticamente.")
    records = []
    results = {}

    def capture(name, path, params=None):
        try:
            result = IbgeClient().get_json(path, params)
        except ServiceError as exc:
            records.append({"path": name, "status": "failed", "code": exc.error_code, "source_url": build_url(path, params), "http_status": None, "internal_status": exc.status_code, "recorded_at": datetime.now(timezone.utc).isoformat()})
            print(name, exc.error_code, flush=True)
            return None
        body = (json.dumps(result["data"], ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        (destination / name).write_bytes(body)
        records.append({"path": name, "status": "captured", "kind": "official_dataset", "body_representation": "complete_json_reserialized", "source_url": result["source_url"], "fetched_at": result["fetched_at"], "expires_at": result["expires_at"], "cache_hit": result["cache_hit"], "http_status": 200, "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)})
        print(name, "captured", len(body), flush=True)
        results[name] = result["data"]
        return result["data"]

    def identifier(value):
        if isinstance(value, bool) or not isinstance(value, (int, str)) or not str(value).isdigit():
            raise ValueError("ID incompatível na captura")
        return str(value)

    try:
        with override_settings(IBGE_MAX_ATTEMPTS=1):
            for acervo in ["A", "N", "P"]:
                capture(f"acervo_{acervo}.json", "/api/v3/agregados", {"acervo": acervo})
            metadata = capture("metadados_1712.json", "/api/v3/agregados/1712/metadados")
            periods = capture("periodos_1712.json", "/api/v3/agregados/1712/periodos")
            localities = capture("localidades_1712_N1.json", "/api/v3/agregados/1712/localidades/N1")
            if not metadata or not periods or not localities:
                print("Recorte de séries não executado: falta referência válida.", flush=True)
                return
            period = identifier(periods[0]["id"])
            capture("catalogo_226_N1.json", "/api/v3/agregados", {"classificacao": "226", "nivel": "N1", "periodo": period})
            variable_ids = [identifier(var["id"]) for var in metadata["variaveis"] if identifier(var["id"]) in ["214", "1982"]]
            if len(variable_ids) != 2 or not any(identifier(locality["id"]) == "1" for locality in localities):
                print("Recorte de séries não executado: variáveis/território não confirmados.", flush=True)
                return
            selections = []
            for classification in metadata["classificacoes"]:
                class_id = identifier(classification["id"])
                category_ids = {identifier(cat["id"]) for cat in classification["categorias"]}
                wanted = {"226": ["4844", "96608"], "218": ["4780"]}.get(class_id)
                if wanted and all(id_ in category_ids for id_ in wanted):
                    selected = wanted
                else:
                    summary = classification.get("sumarizacao", {})
                    exceptions = {identifier(id_) for id_ in summary.get("excecao", [])}
                    if summary.get("status") is True and not exceptions.intersection(variable_ids):
                        selected = ["0"]
                    else:
                        print("Recorte não resolvido para classificação", class_id, flush=True)
                        return
                selections.append({"classificacao_id": class_id, "categoria_ids": selected})
            # No máximo quatro combinações de variável/categoria × uma localidade × um período.
            combinations = 1
            for selected in selections:
                combinations *= len(selected["categoria_ids"])
            if len(variable_ids) * combinations > 4:
                raise ValueError("Recorte excede quatro observações estimadas")
            query = {"agregado_id": "1712", "nivel_id": "N1", "localidade_ids": ["1"], "variavel_ids": variable_ids, "periodo_ids": [period], "classificacoes": selections}
            (destination / "consulta_1712.json").write_text(json.dumps(query, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            classification_query = "|".join(item["classificacao_id"] + "[" + ",".join(item["categoria_ids"]) + "]" for item in selections)
            capture("series_1712.json", f"/api/v3/agregados/1712/periodos/{period}/variaveis/{'|'.join(variable_ids)}", {"classificacao": classification_query, "localidades": "BR"})
    finally:
        manifest = {"kind": "official_dataset", "authorization_scope": "Execução da fase 0 solicitada em 13/10/2026; lote manual limitado de referência.", "maximum_requests": 8, "maximum_estimated_series_observations": 4, "files": records}
        query_path = destination / "consulta_1712.json"
        if query_path.exists():
            manifest["resolved_query"] = {"path": query_path.name, "kind": "resolved_query", "sha256": hashlib.sha256(query_path.read_bytes()).hexdigest()}
        (destination / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
