"""Small CPU fixtures for wrapper, denominator and counterfactual semantics."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import score_pairs as scorer


def fixtures():
    rows = []
    for arm, minimum in [('a', 0), ('b', 2)]:
        schema = {'$schema': scorer.original.DIALECT, 'type': 'object',
                  'properties': {'x': {'type': 'integer', 'minimum': minimum}},
                  'required': ['x'], 'additionalProperties': False}
        rows.append({'id': arm, 'pair_id': 'p1', 'family': 'minimum', 'arm': arm,
                     'input': f'minimum {minimum}', 'reference_schema': schema, 'reference_data': {'x': 3},
                     'probes': [{'id': str(x), 'instance': {'x': x}, 'accept': x >= minimum} for x in [-1, 0, 2, 3]]})
    return rows


def prediction(row, bare=False):
    schema, data = row['reference_schema'], row['reference_data']
    raw = json.dumps(schema)+'\n'+json.dumps(data) if bare else json.dumps({'schema': schema, 'data': data})
    return {'id': row['id'], 'raw_output': raw}


class ScorerTests(unittest.TestCase):
    def test_correct_and_pair_blind_schema(self):
        rows = fixtures()
        scorer.validate_rows(rows)
        records = [scorer.score_item(r, prediction(r), 'strict') for r in rows]
        self.assertEqual(scorer.pair_result(records)['both_joint_success'], 1)
        blind = prediction(rows[0])
        records[1] = scorer.score_item(rows[1], blind, 'strict')
        paired = scorer.pair_result(records)
        self.assertEqual(paired['discriminating_both_correct'], 0)
        self.assertEqual(paired['discriminating_predicted_flip'], 0)
        self.assertEqual(paired['both_suite_pass'], 0)
        self.assertEqual(records[1]['metrics']['data_accuracy'], 1)

    def test_only_two_bare_objects_are_rewrapped(self):
        row = fixtures()[0]
        bare = prediction(row, bare=True)
        self.assertEqual(scorer.score_item(row, bare, 'strict')['metrics']['format_success'], 0)
        diagnostic = scorer.score_item(row, bare, 'diagnostic')
        self.assertEqual(diagnostic['metrics']['joint_success'], 1)
        self.assertEqual(diagnostic['metrics']['rewrapped'], 1)
        invalids = [f'```json\n{bare["raw_output"]}\n```', bare['raw_output']+' {}',
                    '{"x": 1, "x": 2}\n{}', '{}\n{"x": NaN}', '[]\n{}',
                    'prefix '+bare['raw_output'], bare['raw_output'][:-1]]
        for text in invalids:
            with self.subTest(text=text):
                self.assertEqual(scorer.score_item(row, {'raw_output': text}, 'diagnostic')['metrics']['format_success'], 0)

    def test_profile_and_rule_are_separate(self):
        row = fixtures()[0]
        pred = json.loads(prediction(row)['raw_output'])
        del pred['schema']['$schema']
        result = scorer.score_item(row, {'raw_output': json.dumps(pred)}, 'strict')['metrics']
        self.assertEqual(result['schema_validity'], 0)
        self.assertEqual(result['dialect_declared'], 0)
        self.assertEqual(result['schema_suite_pass'], 1)
        pred['schema']['$schema'] = 'https://json-schema.org/draft-07/schema'
        result = scorer.score_item(row, {'raw_output': json.dumps(pred)}, 'strict')['metrics']
        self.assertEqual(result['schema_rule_evaluable'], 0)
        self.assertEqual(result['probe_correct'], 0)

    def test_full_denominator_artifacts_and_truncation(self):
        rows = fixtures()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scorer.write_jsonl(root/'fixture.jsonl', rows)
            first = prediction(rows[0])
            first['finish_reason'] = 'length'
            scorer.write_jsonl(root/'partial.jsonl', [first])
            scorer.write_jsonl(root/'bare.jsonl', [prediction(r, bare=True) for r in rows])
            result = scorer.run(root/'fixture.jsonl', [root/'partial.jsonl', root/'bare.jsonl'], root/'out')
            partial = result['conditions']['partial']['strict']['items']
            self.assertEqual(partial['n'], 2)
            self.assertEqual(partial['schema_suite_pass'], .5)
            self.assertEqual(partial['missing_predictions'], 1)
            self.assertEqual(partial['truncated_outputs'], 1)
            self.assertEqual(partial['probe_micro_accuracy'], .5)
            self.assertEqual(result['conditions']['bare']['diagnostic']['pairs']['both_suite_pass'], 1)
            self.assertEqual(len(scorer.read_jsonl(root/'out'/'conditions_comparison.jsonl')), 2)
            self.assertTrue((root/'out'/'summary.md').read_text(encoding='utf-8').startswith('# Paired'))

    def test_reject_bad_reference_and_unknown_prediction(self):
        rows = fixtures()
        bad = copy.deepcopy(rows)
        bad[1]['probes'][1]['accept'] = True
        with self.assertRaisesRegex(ValueError, 'reference disagrees'):
            scorer.validate_rows(bad)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scorer.write_jsonl(root/'fixture.jsonl', rows)
            scorer.write_jsonl(root/'unknown.jsonl', [{'id': 'unknown', 'raw_output': '{}'}])
            with self.assertRaisesRegex(ValueError, 'unknown prediction ID'):
                scorer.run(root/'fixture.jsonl', [root/'unknown.jsonl'], root/'out')


if __name__ == '__main__':
    unittest.main()
