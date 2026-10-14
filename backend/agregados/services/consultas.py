"""Dimensões e validação; nunca executa séries."""
import re
import unicodedata
from math import prod

from django.conf import settings
from agregados.clients.ibge import build_url
from agregados.errors import ServiceError
from .catalogo import CatalogService, array, obj, identifier, text, invalid


def selection_error(field):
    raise ServiceError("invalid_selection", "Selecione dimensões publicadas e compatíveis.", 400, {"field": field})


def normalize_search(value):
    return ''.join(c for c in unicodedata.normalize('NFD', value.casefold()) if not unicodedata.combining(c))


def validate_input(data):
    fields = {'agregado_id', 'nivel_id', 'variavel_ids', 'localidade_ids', 'periodo_ids', 'classificacoes'}
    if not isinstance(data, dict) or set(data) != fields:
        selection_error('consulta')
    for field, pattern in (('agregado_id', r'[0-9]+'), ('nivel_id', r'N[0-9]+')):
        if type(data[field]) is not str or not re.fullmatch(pattern, data[field]):
            selection_error(field)
    def ids(values, field):
        if not isinstance(values, list) or not values or any(type(v) is not str or not re.fullmatch(r'[0-9]+', v) for v in values) or len(set(values)) != len(values):
            selection_error(field)
    for field in ('variavel_ids', 'localidade_ids', 'periodo_ids'):
        ids(data[field], field)
    if not isinstance(data['classificacoes'], list):
        selection_error('classificacoes')
    seen = set()
    for item in data['classificacoes']:
        if not isinstance(item, dict) or set(item) != {'classificacao_id', 'categoria_ids'}:
            selection_error('classificacoes')
        ids([item['classificacao_id']], 'classificacao_id')
        ids(item['categoria_ids'], 'categoria_ids')
        if item['classificacao_id'] in seen:
            selection_error('classificacoes')
        seen.add(item['classificacao_id'])
    return data


class QueryService(CatalogService):
    def periods(self, aggregate_id):
        result = []
        for index, raw in enumerate(array(self.fetch(f'/api/v3/agregados/{aggregate_id}/periodos'))):
            raw = obj(raw)
            result.append({'id': identifier(raw.get('id'), r'[0-9]+'), 'literals': [text(v) for v in array(raw.get('literals'))], 'modificacao': text(raw.get('modificacao'), True), 'ordem': index})
        return {'items': result}

    def locations(self, aggregate_id, params, metadata=None):
        metadata = metadata or self.metadata(aggregate_id)
        level = params['nivel']
        if level not in {v['id'] for v in metadata['niveis']}:
            selection_error('nivel_id')
        result = []
        for raw in array(self.fetch(f'/api/v3/agregados/{aggregate_id}/localidades/{level}')):
            raw = obj(raw)
            published_level = raw.get('nivel')
            if published_level is not None and identifier(obj(published_level).get('id'), r'N[0-9]+') != level:
                invalid()
            result.append({'id': identifier(raw.get('id'), r'[0-9]+'), 'nome': text(raw.get('nome')), 'nivel_id': level, 'uf_sigla': None})
        query = normalize_search(params.get('q', ''))
        result = [v for v in result if query in normalize_search(v['id'] + ' ' + v['nome'])]
        if params.get('_all'):
            return result
        page, size = params.get('page', 1), params.get('page_size', 50)
        start = (page - 1) * size
        return {'items': result[start:start + size], 'pagination': {'page': page, 'page_size': size, 'total_count': len(result), 'has_next': start + size < len(result)}}

    def validate(self, data):
        data = validate_input(data)
        limits = {'max_variables': settings.IBGE_MAX_VARIABLES, 'max_localities': settings.IBGE_MAX_LOCALITIES, 'max_observations': settings.IBGE_MAX_OBSERVATIONS, 'max_response_bytes': settings.IBGE_MAX_RESPONSE_BYTES}
        if len(data['variavel_ids']) > limits['max_variables'] or len(data['localidade_ids']) > limits['max_localities']:
            raise ServiceError('query_too_large', 'Reduza as variáveis ou localidades selecionadas.', 422)
        metadata = self.metadata(data['agregado_id'])
        for field, published in (('variavel_ids', metadata['variaveis']), ('periodo_ids', metadata['periodos'])):
            if not set(data[field]) <= {v['id'] for v in published}:
                selection_error(field)
        locations = self.locations(data['agregado_id'], {'nivel': data['nivel_id'], '_all': True}, metadata)
        if not set(data['localidade_ids']) <= {v['id'] for v in locations}:
            selection_error('localidade_ids')
        chosen = {v['classificacao_id']: v['categoria_ids'] for v in data['classificacoes']}
        if set(chosen) != {v['id'] for v in metadata['classificacoes']}:
            selection_error('classificacoes')
        for classification in metadata['classificacoes']:
            categories = chosen[classification['id']]
            allowed = {v['id'] for v in classification['categorias']} - {'0'}
            summary = classification['sumarizacao']
            if summary['status'] and not set(data['variavel_ids']) & set(summary['excecao']):
                allowed.add('0')
            if not set(categories) <= allowed:
                selection_error('categoria_ids')
        estimate = len(data['variavel_ids']) * len(data['localidade_ids']) * len(data['periodo_ids']) * prod(len(v) for v in chosen.values())
        if estimate > limits['max_observations']:
            raise ServiceError('query_too_large', 'Reduza o recorte: orçamento de observações excedido.', 422, {'estimated_observations': estimate})
        locality = 'BR' if data['nivel_id'] == 'N1' and data['localidade_ids'] == ['1'] else f"{data['nivel_id']}[{','.join(data['localidade_ids'])}]"
        params = {'localidades': locality}
        if chosen:
            params['classificacao'] = '|'.join(f"{key}[{','.join(values)}]" for key, values in chosen.items())
        try:
            url = build_url(f"/api/v3/agregados/{data['agregado_id']}/periodos/{'|'.join(data['periodo_ids'])}/variaveis/{'|'.join(data['variavel_ids'])}", params)
        except ServiceError as error:
            if error.error_code == 'invalid_parameters':
                raise ServiceError('query_too_large', 'Reduza o recorte: expressão de URL excedida.', 422) from error
            raise
        return {'consulta_resolvida': data, 'source_url': url, 'estimated_observations': estimate, 'limites': limits, 'warnings': []}
