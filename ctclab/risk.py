"""Exact candidate edit-risk audit for a bounded supplied CTC frame law.

Decisions are restricted to the supplied candidates. Token edit count is not
length-normalized WER, and model-expected loss is not measured recognition error.
"""
from copy import deepcopy
from fractions import Fraction
from itertools import product
from .prefix_input import validate


def edit_distance(left, right):
    """Unit-cost token insertion, deletion and substitution distance."""
    previous = list(range(len(right) + 1))
    for i, a in enumerate(left, 1):
        current = [i]
        for j, b in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[j] + 1,
                               previous[j - 1] + (a != b)))
        previous = current
    return previous[-1]


def audit_risk(request):
    if type(request) is not dict or set(request) != {'symbols', 'blank', 'frames', 'candidates'}:
        raise ValueError('Exactly symbols, blank, frames and candidates required')
    rows = validate({k: request[k] for k in ('symbols', 'blank', 'frames')} | {'beam_width': 1})
    candidates = request['candidates']
    if type(candidates) is not list or not 1 <= len(candidates) <= 32:
        raise ValueError('One to 32 supplied candidates required')
    blank = request['blank']
    for candidate in candidates:
        if (type(candidate) is not list or len(candidate) > 6 or
                any(type(k) is not int or not 0 <= k < len(request['symbols']) or k == blank
                    for k in candidate)):
            raise ValueError('Candidates need at most six nonblank integer token indices')
    if len({tuple(x) for x in candidates}) != len(candidates):
        raise ValueError('Candidates must be distinct')
    law = {}
    for path in product(range(len(request['symbols'])), repeat=len(rows)):
        mass = Fraction(1)
        transcript = []
        for t, token in enumerate(path):
            mass *= rows[t][token]
            if token != blank and (t == 0 or token != path[t - 1]):
                transcript.append(token)
        if mass:
            key = tuple(transcript)
            law[key] = law.get(key, Fraction(0)) + mass
    support = sorted(law)
    records = []
    risks = []
    for candidate in candidates:
        distances = [edit_distance(candidate, transcript) for transcript in support]
        histogram = [sum((law[t] for t, d in zip(support, distances) if d == loss), Fraction(0))
                     for loss in range(7)]
        risk = sum((loss * mass for loss, mass in enumerate(histogram)), Fraction(0))
        risks.append(risk)
        probability = law.get(tuple(candidate), Fraction(0))
        records.append({'tokens': list(candidate), 'posterior_mass': str(probability),
                        'sentence_error_risk': str(1 - probability),
                        'distances_to_support': distances,
                        'edit_loss_mass': [str(x) for x in histogram], 'edit_risk': str(risk)})
    maximum = max(law.values())
    return {'schema': 'ctclab-candidate-edit-risk-v1', 'request': deepcopy(request),
            'support': [{'tokens': list(t), 'mass': str(law[t])} for t in support],
            'total_mass': str(sum(law.values())), 'candidates': records,
            'map_transcripts': [list(t) for t in support if law[t] == maximum],
            'minimum_candidate_edit_risk': str(min(risks)),
            'minimum_candidate_indices': [i for i, risk in enumerate(risks) if risk == min(risks)],
            'scope': 'Exact expected unit token edit count under the supplied independent-frame CTC law. '
                     'Only the supplied candidates compete; zero-posterior candidates are allowed. '
                     'Not unrestricted minimum-risk decoding, length-normalized WER, measured '
                     'recognition error, calibrated confidence or a scalable decoder.'}
