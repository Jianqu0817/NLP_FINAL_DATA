"""CPU-only pre-inference audit; never loads predictions."""
import copy
import json
from pathlib import Path
import sys
import unittest
from collections import Counter
from jsonschema import Draft202012Validator

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'paired_study'))
from score_pairs import validate_rows
from build_confirmation import build

class ConfirmationAudit(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.data={v:[json.loads(l) for l in (HERE/f'confirm_{v}.jsonl').read_text(encoding='utf-8').splitlines()] for v in ['original','wording','order']}
 def test_frozen_reproducible_and_contract(self):
  self.assertEqual(self.data,build())
  for v,rows in self.data.items():
   self.assertEqual(len(rows),48)
   self.assertEqual(Counter(r['family'] for r in rows),{'count_bounds':32,'nullable':16})
   groups=validate_rows(rows)
   self.assertEqual(len(groups),24)
   for pair in groups.values():
    a,b=pair
    self.assertEqual(a['reference_data'],b['reference_data'])
    self.assertEqual([i for i,(x,y) in enumerate(zip(a['input_sentences'],b['input_sentences'])) if x!=y],[2])
    sa,sb=copy.deepcopy(a['reference_schema']),copy.deepcopy(b['reference_schema'])
    sa['properties'].pop(a['focus_field']);sb['properties'].pop(b['focus_field'])
    self.assertEqual(sa,sb)
    changed=[p['id'] for p,q in zip(a['probes'],b['probes']) if p['accept']!=q['accept']]
    self.assertEqual(len(changed),2 if a['family']=='count_bounds' else 1)
    if a['family']=='count_bounds':
     self.assertTrue(all(x.startswith('focus_n_') for x in changed))
     self.assertEqual({p['accept'] for p,q in zip(a['probes'],b['probes']) if p['accept']!=q['accept']},{True,False})
    else:self.assertEqual(changed,['target_null'])
 def test_variants_only_requested_manipulation(self):
  for o,w,s in zip(*(self.data[v] for v in ['original','wording','order'])):
   self.assertEqual(o['id'],w['id']);self.assertEqual(o['id'],s['id'])
   for key in ['reference_data','reference_schema','probes','focus_field','distractor_field','expected_min','expected_max','expected_nullable']:
    self.assertEqual(o[key],w[key]);self.assertEqual(o[key],s[key])
   self.assertEqual(s['input_sentences'],[o['input_sentences'][i] for i in [0,3,2,1,4,5,6]])
   self.assertEqual(Counter(o['input_sentences']),Counter(s['input_sentences']))
   for key in o['reference_data']:
    self.assertEqual(o['input'].count(key),w['input'].count(key))
   self.assertEqual(o['input_sentences'][0],w['input_sentences'][0])
   self.assertEqual(len(o['input_sentences']),len(w['input_sentences']))
 def test_full_draft_labels_and_placement(self):
  for row in self.data['original']:
   rs=row['reference_schema'];Draft202012Validator.check_schema(rs)
   v=Draft202012Validator(rs);v.validate(row['reference_data'])
   for p in row['probes']:self.assertEqual(v.is_valid(p['instance']),p['accept'])
   f,d=row['focus_field'],row['distractor_field']
   if row['family']=='count_bounds':
    self.assertEqual(rs['properties'][f]['minItems'],row['expected_min'])
    self.assertEqual(rs['properties'][f]['maxItems'],row['expected_max'])
    self.assertNotIn('minItems',rs['properties'][d]);self.assertNotIn('maxItems',rs['properties'][d])
    for p in row['probes']:
     if p['id'].startswith('distractor_n_'):self.assertTrue(p['accept'])
    # Bounds swapped onto the distractor must be behaviorally exposed.
    bad=copy.deepcopy(rs)
    for k in ['minItems','maxItems']:bad['properties'][d][k]=bad['properties'][f].pop(k)
    bv=Draft202012Validator(bad)
    self.assertTrue(any(bv.is_valid(p['instance'])!=p['accept'] for p in row['probes']))
 def test_novelty_and_counterbalance(self):
  old=[json.loads(l) for l in (HERE.parent/'paired_study'/'pairs.jsonl').read_text(encoding='utf-8-sig').splitlines()]
  oldkeys={k for r in old for k in r['reference_data']}
  new=self.data['original']
  self.assertFalse(oldkeys & {k for r in new for k in r['reference_data']})
  self.assertFalse({r['id'] for r in old}&{r['id'] for r in new})
  oldtasks={r['input'].split('。')[0] for r in old}
  self.assertFalse(oldtasks & {r['input_sentences'][0][:-1] for r in new})
  aa=[r for r in new if r['arm']=='a']
  self.assertEqual(sum(r['expected_nullable'] for r in aa if r['family']=='nullable'),4)
  self.assertEqual(sum(r['reference_schema']['required'].index(r['focus_field'])==1 for r in aa if r['family']=='count_bounds'),8)

if __name__=='__main__':unittest.main()
