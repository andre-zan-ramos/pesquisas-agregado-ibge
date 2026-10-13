"""Descoberta somente: composição do transporte existente sem séries."""
import re
from copy import deepcopy

from agregados.clients.ibge import IbgeClient
from agregados.errors import ServiceError


def invalid():
    raise ServiceError("upstream_inconsistent_data", "O IBGE retornou uma estrutura de catálogo incompatível.")


def identifier(value, pattern=None):
    if type(value) is int and value >= 0:
        value = str(value)
    if not isinstance(value, str) or not value or (pattern and not re.fullmatch(pattern, value)):
        invalid()
    return value


def text(value, nullable=False):
    if nullable and value is None:
        return value
    if not isinstance(value, str):
        invalid()
    return value


def array(value):
    if not isinstance(value, list):
        invalid()
    return value


def obj(value):
    if not isinstance(value, dict):
        invalid()
    return value


def item(value, numeric=False, label="nome"):
    value = obj(value)
    return {"id": identifier(value.get("id"), r"[0-9]+" if numeric else None), "nome": text(value.get(label))}


class CatalogService:
    def __init__(self, client=None):
        self.client = client or IbgeClient()
        self.sources = []

    def fetch(self, path, params=None):
        response = self.client.get_json(path, params)
        self.sources.append({k: response[k] for k in ("source_url", "fetched_at", "expires_at", "cache_hit")})
        return response["data"]

    def envelope(self, data):
        return {"data": data, "sources": self.sources}

    def domains(self):
        data = {}
        for key, acervo in (("assuntos", "A"), ("niveis", "N"), ("periodos", "P")):
            data[key] = [item(v, label="literal") for v in array(self.fetch("/api/v3/agregados", {"acervo": acervo}))]
            if key == "niveis":
                for level in data[key]:
                    identifier(level["id"], r"N[0-9]+")
        return data

    def researches(self, params):
        filters = {k: params[k] for k in ("assunto", "nivel", "periodo") if k in params}
        if filters:
            domains = self.domains()
            for key, domain in (("assunto", "assuntos"), ("nivel", "niveis"), ("periodo", "periodos")):
                if key in filters and filters[key] not in {v["id"] for v in domains[domain]}:
                    raise ServiceError("invalid_parameters", "Selecione filtros publicados no catálogo.", 400)
        result = []
        query = params.get("q", "").casefold()
        for raw in array(self.fetch("/api/v3/agregados", filters)):
            research = item(raw)
            aggregates = [item(v, numeric=True) for v in array(raw.get("agregados"))]
            if query and not any(query in research[k].casefold() for k in ("id", "nome")):
                aggregates = [v for v in aggregates if any(query in v[k].casefold() for k in ("id", "nome"))]
                if not aggregates:
                    continue
            result.append({**research, "agregados": aggregates})
        page, size = params.get("page", 1), params.get("page_size", 50)
        start = (page - 1) * size
        return {"items": result[start:start + size], "pagination": {"page": page, "page_size": size, "total_count": len(result), "has_next": start + size < len(result)}}

    def metadata(self, aggregate_id):
        raw = obj(self.fetch(f"/api/v3/agregados/{aggregate_id}/metadados"))
        data = item(raw, numeric=True)
        if data["id"] != aggregate_id:
            invalid()
        data.update(sidra_url=text(raw.get("URL")), pesquisa=text(raw.get("pesquisa")), assunto=text(raw.get("assunto")))
        periodicity = obj(raw.get("periodicidade"))
        data["periodicidade"] = {"frequencia": text(periodicity.get("frequencia")), **{k: identifier(periodicity.get(k), r"[0-9]+") for k in ("inicio", "fim")}}
        labels = {v["id"]: v["nome"] for v in [item(v, label="literal") for v in array(self.fetch("/api/v3/agregados", {"acervo": "N"}))]}
        data["niveis"] = []
        for group, levels in obj(raw.get("nivelTerritorial")).items():
            text(group)
            for level in array(levels):
                level = identifier(level, r"N[0-9]+")
                data["niveis"].append({"id": level, "nome": labels.get(level), "grupo": group})
        data["variaveis"] = []
        for variable in array(raw.get("variaveis")):
            data["variaveis"].append({**item(variable, numeric=True), "unidade": text(variable.get("unidade"), True), "sumarizacao": [text(v) for v in array(variable.get("sumarizacao"))]})
        data["classificacoes"] = []
        for classification in array(raw.get("classificacoes")):
            normalized = item(classification, numeric=True)
            summary = obj(classification.get("sumarizacao"))
            if type(summary.get("status")) is not bool:
                invalid()
            normalized["sumarizacao"] = {"status": summary["status"], "excecao": [identifier(v, r"[0-9]+") for v in array(summary.get("excecao"))]}
            normalized["categorias"] = []
            for category in array(classification.get("categorias")):
                converted = item(category, numeric=True)
                level = category.get("nivel")
                if level is not None and (type(level) is not int or level < 0):
                    invalid()
                converted.update(unidade=text(category.get("unidade"), True), nivel=level)
                normalized["categorias"].append(converted)
            data["classificacoes"].append(normalized)
        data["periodos"] = []
        for index, period in enumerate(array(self.fetch(f"/api/v3/agregados/{aggregate_id}/periodos"))):
            period = obj(period)
            data["periodos"].append({"id": identifier(period.get("id"), r"[0-9]+"), "literals": [text(v) for v in array(period.get("literals"))], "modificacao": text(period.get("modificacao"), True), "ordem": index})
        return deepcopy(data)
