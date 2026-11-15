"""References use complete edit alignments and the separate prefix recurrence."""
import copy
from fractions import Fraction as F
import itertools
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from ctclab.prefix import audit_prefix
from ctclab.risk import audit_risk, edit_distance


def alignment_costs(a, b):
    if not a:
        yield len(b)
    elif not b:
        yield len(a)
    else:
        for tail in alignment_costs(a[1:], b):
            yield 1 + tail
        for tail in alignment_costs(a, b[1:]):
            yield 1 + tail
        for tail in alignment_costs(a[1:], b[1:]):
            yield (a[0] != b[0]) + tail


def control():
    return {'symbols': ['_', 'A', 'B'], 'blank': 0,
            'frames': [['1/7', '3/7', '3/7'], ['1/16', '3/8', '9/16'], ['9/20', '1/10', '9/20']],
            'candidates': [[2], [1, 2]]}


class Risk(unittest.TestCase):
    def test_all_small_edit_alignments(self):
        strings = [t for n in range(5) for t in itertools.product([1, 2], repeat=n)]
        count = 0
        for a in strings:
            for b in strings:
                self.assertEqual(edit_distance(a, b), min(alignment_costs(a, b)))
                count += 1
        self.assertEqual(count, 961)

    def test_selected_map_edit_disagreement(self):
        request = control()
        saved = copy.deepcopy(request)
        report = audit_risk(request)
        self.assertEqual(report['map_transcripts'], [[1, 2]])
        self.assertEqual(report['minimum_candidate_indices'], [0])
        self.assertEqual(report['minimum_candidate_edit_risk'], '127/160')
        self.assertEqual([r['edit_risk'] for r in report['candidates']], ['127/160', '449/560'])
        self.assertEqual([r['sentence_error_risk'] for r in report['candidates']], ['389/560', '1511/2240'])
        self.assertEqual(request, saved)
        report['request']['candidates'][0].append(1)
        self.assertEqual(request, saved)

    def test_seeded_laws_against_prefix_and_alignments(self):
        rng = random.Random(819)
        for i in range(80):
            c = 2 + i % 3
            blank = i % c
            tokens = [k for k in range(c) if k != blank]
            weights = [[rng.randint(0, 9) for _ in range(c)] for _ in range(i % 5)]
            for row in weights:
                if not sum(row):
                    row[blank] = 1
            request = {'symbols': [str(k) for k in range(c)], 'blank': blank,
                       'frames': [[str(F(v, sum(row))) for v in row] for row in weights],
                       'candidates': [[], [tokens[0]], [tokens[-1]] * 2]}
            report = audit_risk(request)
            prefix = audit_prefix({k: request[k] for k in ('symbols', 'blank', 'frames')} | {'beam_width': 64})
            law = {tuple(t['prefix']): F(t['full_mass']) for t in prefix['transcripts']}
            self.assertEqual({tuple(t['tokens']): F(t['mass']) for t in report['support']}, law)
            references = []
            for candidate in report['candidates']:
                distances = [min(alignment_costs(candidate['tokens'], transcript)) for transcript in sorted(law)]
                self.assertEqual(candidate['distances_to_support'], distances)
                expected_bins = [sum((law[t] for t, distance in zip(sorted(law), distances) if distance == k), F(0)) for k in range(7)]
                self.assertEqual(list(map(F, candidate['edit_loss_mass'])), expected_bins)
                reference = sum((mass * min(alignment_costs(candidate['tokens'], transcript))
                                 for transcript, mass in law.items()), F(0))
                self.assertEqual(F(candidate['edit_risk']), reference)
                references.append(reference)
                self.assertEqual(sum(map(F, candidate['edit_loss_mass'])), 1)
                self.assertEqual(F(candidate['edit_loss_mass'][0]), F(candidate['posterior_mass']))
            self.assertEqual(F(report['minimum_candidate_edit_risk']), min(references))
            self.assertEqual(report['minimum_candidate_indices'], [j for j, risk in enumerate(references) if risk == min(references)])
            self.assertEqual(report['total_mass'], '1')

    def test_boundaries_ties_and_zero_posterior_candidates(self):
        request = {'symbols': ['_', 'A'], 'blank': 0, 'frames': [['1/2', '1/2']],
                   'candidates': [[], [1], [1, 1]]}
        report = audit_risk(request)
        self.assertEqual(report['minimum_candidate_indices'], [0, 1])
        self.assertEqual(report['candidates'][2]['posterior_mass'], '0')
        request['frames'] = []
        report = audit_risk(request)
        self.assertEqual([c['edit_risk'] for c in report['candidates']], ['0', '1', '2'])
        request = {'symbols': ['_', 'A', 'B', 'C'], 'blank': 0,
                   'frames': [['1/4'] * 4] * 6,
                   'candidates': [list(t) for t in itertools.islice(itertools.product([1, 2, 3], repeat=6), 32)]}
        self.assertEqual(audit_risk(request)['total_mass'], '1')
        for bad in [dict(request, candidates=[]), dict(request, candidates=[[True]]),
                    dict(request, candidates=[[0]]), dict(request, candidates=[[4]]),
                    dict(request, candidates=[[1] * 7]), dict(request, candidates=[[1], [1]]),
                    dict(request, candidates=request['candidates'] + [[2]]), dict(request, extra=1)]:
            with self.assertRaises(ValueError):
                audit_risk(bad)

    def test_cli_roundtrip_strict_errors_and_atomic_output(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d) / 'input.json'
            output = Path(d) / 'output.json'
            source.write_text(json.dumps(control()))
            command = [sys.executable, '-m', 'ctclab.risk_cli', '--input', str(source), '--output', str(output)]
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(json.loads(output.read_text()), audit_risk(control()))
            preserved = output.read_bytes()
            for text in ['{"symbols":[],"symbols":[]}', '{"frames":NaN}', '{"frames":1.0}', 'x' * 65537]:
                source.write_text(text)
                result = subprocess.run(command, capture_output=True)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, b'')
                self.assertEqual(output.read_bytes(), preserved)
            source.write_text(json.dumps(control()))
            result = subprocess.run(command[:-1] + [str(source)], capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(source.read_text()), control())
            self.assertFalse(list(Path(d).glob('.ctc-risk-*')))


if __name__ == '__main__':
    unittest.main()
