"""Synthetic acceptance cases; no model inference."""
import copy
import json
import unittest
import score_mechanism as scoring

def fixture():
    rows=scoring.paired.read_jsonl(scoring.ROOT/'paired_study/pairs.jsonl')
    groups=scoring.paired.validate_rows(rows)
    return copy.deepcopy(next(pair for pair in groups.values() if pair[0]['family']=='count_bounds'))

def prediction(row,schema=None, bare=False, **metadata):
    schema=copy.deepcopy(row['reference_schema'] if schema is None else schema)
    text=json.dumps({'schema':schema,'data':row['reference_data']})
    if bare:text=json.dumps(schema)+'\n'+json.dumps(row['reference_data'])
    return {'id':row['id'],'raw_output':text,**metadata}

class ScoringTests(unittest.TestCase):
    def test_correct_and_wrong_attachment(self):
        rows=fixture()
        correct=[scoring.item_score(r,prediction(r),'strict') for r in rows]
        self.assertEqual(scoring.pair_score(correct)['draft_suite'],1)
        self.assertEqual(correct[0]['placement']['label'],'correct_at_array')
        for row in rows:
            schema=copy.deepcopy(row['reference_schema'])
            field=next(k for k,v in schema['properties'].items() if 'minItems' in v)
            for key in ('minItems','maxItems'):schema[key]=schema['properties'][field].pop(key)
            item=scoring.item_score(row,prediction(row,schema),'strict')
            self.assertEqual(item['placement']['label'],'correct_numbers_root_only')
            self.assertEqual(item['metrics']['schema_suite_pass'],0)
            schema['minItems']+=20
            self.assertEqual(scoring.item_score(row,prediction(row,schema),'strict')['placement']['label'],'wrong_or_missing')

    def test_wrapping_missing_and_truncation(self):
        row=fixture()[0]
        self.assertEqual(scoring.item_score(row,prediction(row,bare=True),'strict')['metrics']['schema_suite_pass'],0)
        self.assertEqual(scoring.item_score(row,prediction(row,bare=True),'diagnostic')['metrics']['schema_suite_pass'],1)
        missing=scoring.item_score(row,None,'strict')
        self.assertTrue(missing['missing_prediction'])
        self.assertEqual(missing['metrics']['schema_suite_pass'],0)
        truncated=scoring.item_score(row,prediction(row,finish_reason='length'),'strict')
        self.assertTrue(truncated['truncated'])
        self.assertEqual(truncated['metrics']['schema_suite_pass'],1)

    def test_full_draft_not_profile(self):
        row=fixture()[0]
        schema=copy.deepcopy(row['reference_schema']);schema['$comment']='valid annotation, outside project whitelist'
        item=scoring.item_score(row,prediction(row,schema),'strict')
        self.assertEqual(item['metrics']['schema_suite_pass'],1)
        self.assertEqual(item['original_metrics']['schema_validity'],0)
        pair=scoring.pair_score([item,item])
        self.assertEqual(pair['draft_suite'],1)
        self.assertEqual(pair['profile_suite'],0)

    def test_transitions_and_zero_denominator(self):
        left={str(k):{'draft_suite':v} for k,v in enumerate([1,1,0,0])}
        right={str(k):{'draft_suite':v} for k,v in enumerate([1,0,1,0])}
        result=scoring.transitions(left,right,'draft_suite')
        self.assertEqual(result['loss'],{'count':1,'denominator':2,'rate':.5})
        self.assertEqual(result['gain'],{'count':1,'denominator':2,'rate':.5})
        self.assertIsNone(scoring.transitions({}, {}, 'draft_suite')['loss']['rate'])

    def test_common_base_stable_cross_variants(self):
        index={}
        for dataset,base,condition in [('v1',[1,1,0],[1,0,1]),('v2',[1,0,0],[0,1,1])]:
            for c,values in [('Base',base),('A',condition)]:
                index[dataset,c,'strict']={str(k):dict(family='count_bounds',**{m:v for m in scoring.PAIR_METRICS}) for k,v in enumerate(values)}
        rows=scoring.cross_variants(index,['v1','v2'],'strict')
        result=next(r for r in rows if r['condition']=='A' and r['metric']=='draft_suite')
        self.assertEqual(result['base_stable_ids'],['0'])
        self.assertEqual(result['condition_pass_on_base_stable_all_variants']['count'],0)
        self.assertEqual(result['per_variant']['v1']['base_stable_loss']['count'],0)
        self.assertEqual(result['per_variant']['v2']['base_stable_loss']['count'],1)
        self.assertEqual(result['per_variant']['v2']['base_failure_gain']['denominator'],2)
        self.assertEqual(result['condition_original_to_variant_transitions']['v2']['base_stable']['lost_pass']['ids'],['0'])
        self.assertEqual(result['condition_original_to_variant_transitions']['v2']['all']['gained_pass']['ids'],['1'])

if __name__=='__main__':unittest.main()
