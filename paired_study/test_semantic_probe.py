import copy
import json
from pathlib import Path
import tempfile
import unittest

import semantic_probe as semantic
from test_score_pairs import fixtures, prediction


class SemanticTests(unittest.TestCase):
    def test_annotation_rescued_but_wrong_rule_not_rescued(self):
        row = fixtures()[1]
        response = json.loads(prediction(row)['raw_output'])
        response['schema']['$comment'] = 'Harmless annotation outside project whitelist'
        result = semantic.score(row, {'raw_output': json.dumps(response)}, 'strict')
        self.assertEqual(result['original_metrics']['schema_rule_evaluable'], 0)
        self.assertEqual(result['metrics']['schema_suite_pass'], 1)
        self.assertEqual(result['audit']['outside_project_keywords'][0]['keyword'], '$comment')
        response['schema']['properties']['x']['minimum'] = 0
        result = semantic.score(row, {'raw_output': json.dumps(response)}, 'strict')
        self.assertEqual(result['metrics']['schema_suite_pass'], 0)
        self.assertEqual(result['metrics']['schema_rule_evaluable'], 1)

    def test_dialect_and_reference_domain(self):
        row = fixtures()[0]
        response = json.loads(prediction(row)['raw_output'])
        del response['schema']['$schema']
        self.assertEqual(semantic.score(row, {'raw_output': json.dumps(response)}, 'strict')['metrics']['schema_suite_pass'], 1)
        response['schema']['$schema'] = 'https://json-schema.org/draft-07/schema'
        self.assertEqual(semantic.score(row, {'raw_output': json.dumps(response)}, 'strict')['metrics']['schema_rule_evaluable'], 0)
        del response['schema']['$schema']
        for reference in ['#/$defs/local', 'https://example.com/schema.json']:
            response['schema']['properties']['x']['$ref'] = reference
            result = semantic.score(row, {'raw_output': json.dumps(response)}, 'strict')
            self.assertEqual(result['metrics']['schema_rule_evaluable'], 0)
            self.assertEqual(len(result['audit']['references']), 1)

    def test_pair_and_output(self):
        rows = fixtures()
        predictions = []
        for row in rows:
            changed = copy.deepcopy(row)
            changed['reference_schema']['$comment'] = 'annotation'
            predictions.append(prediction(changed, bare=True))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            semantic.paired.write_jsonl(root/'pairs.jsonl', rows)
            semantic.paired.write_jsonl(root/'annotation.jsonl', predictions)
            result = semantic.run(root/'pairs.jsonl', [root/'annotation.jsonl'], root/'out')
            self.assertEqual(result['conditions']['annotation']['strict']['semantic_schema_suite_pass'], 0)
            diagnostic = result['conditions']['annotation']['diagnostic']
            self.assertEqual(diagnostic['pairs']['both_suite_pass'], 1)
            self.assertEqual(diagnostic['pairs']['discriminating_both_correct_rate'], 1)
            self.assertEqual(diagnostic['rescued_suite_pass_count'], 2)
            self.assertTrue((root/'out'/'restriction_cases.jsonl').exists())


if __name__ == '__main__':
    unittest.main()
