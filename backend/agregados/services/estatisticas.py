"""Estatísticas descritivas por identidade, nunca totais ou preenchimentos."""
import math
import re
import statistics


def period_order(metadata, query):
    ids = [p['id'] for p in metadata['periodos'] if p['id'] in query['periodo_ids']]
    frequency = metadata['periodicidade']['frequencia'].casefold()
    chronological = (frequency == 'anual' and all(re.fullmatch(r'[0-9]{4}', p) and p[:4] != '0000' for p in ids)) or (frequency == 'mensal' and all(re.fullmatch(r'[0-9]{6}', p) and p[:4] != '0000' and 1 <= int(p[4:]) <= 12 for p in ids))
    return (sorted(ids) if chronological else ids), bool(chronological)


def summarize(rows, order, chronological):
    from .normalizacao import identity
    groups = {}
    for row in rows:
        groups.setdefault(identity(row, False), []).append(row)
    result = []
    for observations in groups.values():
        first = observations[0]
        by_period = {r['periodo_id']: r for r in observations}
        numbers = [r['valor_numerico'] for r in observations if r['valor_numerico'] is not None]
        suspended = any(r['unidade_status'] != 'coerente' for r in observations) or len({r['unidade'] for r in observations}) != 1
        n = len(numbers)
        mean = statistics.mean(numbers) if n and not suspended else None
        arithmetic_warning = []
        try:
            deviation = statistics.stdev(numbers) if n >= 2 and not suspended else None
        except OverflowError:
            deviation = None
            arithmetic_warning.append('Desvio e CV indisponíveis: cálculo excede a representação numérica finita.')
        cv = deviation / mean * 100 if deviation is not None and mean > 0 else None
        low, high = (min(numbers), max(numbers)) if n and not suspended else (None, None)
        # Arithmetic can exceed float range even with finite observations.
        finite = lambda v: v if v is None or math.isfinite(v) else None
        analysis = {
            'variavel_id': first['variavel_id'], 'variavel_nome': first['variavel_nome'],
            'nivel_id': first['nivel_id'], 'localidade_id': first['localidade_id'],
            'localidade_nome': first['localidade_nome'], 'classificacoes': first['classificacoes'],
            'unidade': None if suspended else first['unidade'], 'suspensa': suspended,
            'n': n, 'sem_numero': len(observations) - n,
            'media': finite(mean), 'desvio': finite(deviation), 'cv': finite(cv),
            'minimo': low, 'maximo': high,
            'periodos_min': [p for p in order if p in by_period and by_period[p]['valor_numerico'] == low] if low is not None else [],
            'periodos_max': [p for p in order if p in by_period and by_period[p]['valor_numerico'] == high] if high is not None else [],
            'grafico_linhas': chronological and not suspended,
            'pontos': [{
                'periodo_id': p,
                'valor': by_period[p]['valor_numerico'] if p in by_period and not suspended else None,
                'lacuna': p not in by_period,
            } for p in order],
            'avisos': ['Gráfico e estatísticas suspensos: unidade conflitante ou não confirmada.'] if suspended else [
                *(['Cronologia não confirmada; gráfico de linhas suspenso.'] if not chronological else []),
                'Resumo descritivo do recorte; a adequação da escala ao CV não foi certificada.',
                *(['CV indisponível: exige duas observações e média positiva e cálculo finito.'] if finite(cv) is None else []),
                *arithmetic_warning,
            ],
        }
        result.append(analysis)
    return result
