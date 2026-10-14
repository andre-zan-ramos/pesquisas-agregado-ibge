"""Normalização v1 sem perda de ocorrências ou inferência de dimensões."""
import math
import re

from django.conf import settings
from agregados.errors import ServiceError
from .catalogo import array, obj, identifier, text
from .estatisticas import summarize, period_order


def inconsistent(details=None):
    raise ServiceError('upstream_inconsistent_data', 'As séries retornadas são incompatíveis com a consulta.', 502, details)


def value(raw):
    if raw is None:
        return None, 'nulo'
    if type(raw) not in (str, int, float):
        inconsistent()
    if raw == '':
        return None, 'vazio'
    if raw in ('X', 'x', '..', '...', '-'):
        return None, 'marcador'
    if type(raw) in (int, float) or re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)', raw):
        try:
            number = float(raw)
            if math.isfinite(number):
                return number, 'numerico'
        except (ValueError, OverflowError):
            pass
    return None, 'nao_reconhecido'


def identity(row, period=True):
    return (row['agregado_id'], row['variavel_id'], row['nivel_id'], row['localidade_id'],
            *((row['periodo_id'],) if period else ()),
            tuple(sorted((c['classificacao_id'], c['categoria_id']) for c in row['classificacoes'])))


def comparable(row):
    return {**{k: v for k, v in row.items() if k not in ('origem_indice', 'classificacoes')},
            'classificacoes': sorted(row['classificacoes'], key=lambda c: c['classificacao_id'])}


def unit_status(original, variable, classifications, metadata):
    expected = variable['unidade']
    if expected and expected.startswith('Vide categorias da classificação '):
        match = re.fullmatch(r"Vide categorias da classificação '(.+)'", expected)
        refs = [c for c in metadata['classificacoes'] if match and c['nome'] == match[1]]
        if len(refs) != 1:
            return None, 'nao_confirmada'
        chosen = [c for c in classifications if c['classificacao_id'] == refs[0]['id']]
        expected = chosen[0]['categoria_unidade'] if len(chosen) == 1 else None
    if not expected or not original:
        return None, 'nao_confirmada'
    return (original, 'coerente') if original == expected else (None, 'conflitante')


def normalize(raw, query, metadata):
    observations, warnings, seen = [], [], {}
    variables = {v['id']: v for v in metadata['variaveis']}
    classifications = {c['id']: c for c in metadata['classificacoes']}
    chosen = {c['classificacao_id']: c['categoria_ids'] for c in query['classificacoes']}

    def check_fields(item, required, optional=()):
        obj(item)
        if not set(required) <= item.keys():
            inconsistent()
        extra = set(item) - set(required) - set(optional)
        if extra:
            warnings.append({'code': 'unmapped_fields', 'message': 'Campos adicionais preservados no corpo original.', 'details': sorted(extra)})

    for vi, variable in enumerate(array(raw)):
        check_fields(variable, ('id', 'variavel', 'unidade', 'resultados'))
        vid = identifier(variable['id'], r'[0-9]+')
        if vid not in query['variavel_ids']:
            inconsistent({'variavel_id': vid})
        name, original_unit = text(variable['variavel']), text(variable['unidade'], True)
        for ri, result in enumerate(array(variable['resultados'])):
            check_fields(result, ('classificacoes', 'series'))
            cats, ids = [], set()
            for classification in array(result['classificacoes']):
                check_fields(classification, ('id', 'nome', 'categoria'))
                cid = identifier(classification['id'], r'[0-9]+')
                category = obj(classification['categoria'])
                if cid not in chosen or cid in ids or len(category) != 1:
                    inconsistent()
                ids.add(cid)
                cat_id, cat_name = next(iter(category.items()))
                cat_id = identifier(cat_id, r'[0-9]+')
                if cat_id not in chosen[cid]:
                    inconsistent()
                published = [c for c in classifications[cid]['categorias'] if c['id'] == cat_id]
                cats.append({'classificacao_id': cid, 'classificacao_nome': text(classification['nome']), 'categoria_id': cat_id, 'categoria_nome': text(cat_name), 'categoria_unidade': published[0]['unidade'] if published else None})
            if ids != set(chosen):
                inconsistent()
            unit, status = unit_status(original_unit, variables[vid], cats, metadata)
            if status != 'coerente':
                warnings.append({'code': 'unit_metadata_conflict' if status == 'conflitante' else 'unit_unconfirmed', 'message': 'Gráfico e estatísticas suspensos: unidade ' + status + '.', 'details': {'variavel': vi, 'resultado': ri}})
            for si, series in enumerate(array(result['series'])):
                check_fields(series, ('localidade', 'serie'))
                local = obj(series['localidade'])
                check_fields(local, ('id', 'nome', 'nivel'))
                if local['nivel'] is not None:
                    check_fields(local['nivel'], ('id',), ('nome',))
                lid = identifier(local['id'], r'[0-9]+')
                level = query['nivel_id'] if local['nivel'] is None else identifier(obj(local['nivel']).get('id'), r'N[0-9]+')
                if lid not in query['localidade_ids'] or level != query['nivel_id']:
                    inconsistent()
                for pid, literal in obj(series['serie']).items():
                    if pid not in query['periodo_ids']:
                        inconsistent({'periodo_id': pid})
                    numeric, value_status = value(literal)
                    row = {'agregado_id': query['agregado_id'], 'variavel_id': vid, 'variavel_nome': name, 'unidade': unit, 'unidade_original': original_unit, 'unidade_status': status, 'nivel_id': level, 'localidade_id': lid, 'localidade_nome': text(local['nome']), 'periodo_id': pid, 'classificacoes': cats, 'valor_original': literal, 'valor_numerico': numeric, 'valor_status': value_status, 'origem_indice': {'variavel': vi, 'resultado': ri, 'serie': si}}
                    key = identity(row)
                    if key in seen:
                        previous = seen[key]
                        # Only exact normalized duplicates may share analytic identity.
                        if comparable(row) != comparable(previous) or type(literal) != type(previous['valor_original']) or repr(literal) != repr(previous['valor_original']):
                            inconsistent({'indices': [previous['origem_indice'], row['origem_indice']]})
                        warnings.append({'code': 'duplicate_observation', 'message': 'Ocorrência idêntica preservada; análise conta a identidade uma vez.', 'details': [previous['origem_indice'], row['origem_indice']]})
                    else:
                        seen[key] = row
                    observations.append(row)
                    if len(observations) > settings.IBGE_MAX_OBSERVATIONS:
                        raise ServiceError('response_too_large', 'Reduza o recorte: quantidade real excedida.', 422)
    order, chronological = period_order(metadata, query)
    return {'consulta_aplicada': query, 'observacoes': observations, 'metadados': metadata, 'warnings': warnings, 'truncated': False, 'normalizer_version': 'v1', 'corpo_original': raw, 'periodos_apresentacao': order, 'ordem_cronologica': chronological, 'analises': summarize(list(seen.values()), order, chronological)}
