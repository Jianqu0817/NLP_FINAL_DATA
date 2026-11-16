import copy
import unittest
from evaluation import DIALECT, dumps, witnesses, score, normalize_data

class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.row = {'id':'test','reference_schema':{
            '$schema':DIALECT,'type':'object','properties':{
                'name':{'type':'string'}, 'count':{'type':'integer','minimum':1,'maximum':5},
                'date':{'type':'string','format':'date'}},
            'required':['name','count','date'],'additionalProperties':False},
            'reference_data':{'name':'会议','count':4,'date':'2026-11-06'}}
        self.suite = witnesses(self.row)

    def candidate(self,schema=None,data=None):
        return dumps({'schema':schema if schema is not None else self.row['reference_schema'],
                      'data':data if data is not None else self.row['reference_data']})

    def test_oracle(self):
        self.assertEqual(score(self.row,self.candidate(),self.suite)['joint_success'],1)

    def test_permissive(self):
        s={'$schema':DIALECT,'type':'object'}
        m=score(self.row,self.candidate(schema=s),self.suite)
        self.assertEqual(m['self_consistency'],1)
        self.assertEqual(m['schema_suite_pass'],0)

    def test_missing_declaration_not_semantic_failure(self):
        s=copy.deepcopy(self.row['reference_schema'])
        del s['$schema']
        m=score(self.row,self.candidate(schema=s),self.suite)
        self.assertEqual(m['schema_meta_validity'],1)
        self.assertEqual(m['schema_validity'],0)
        self.assertEqual(m['schema_suite_pass'],1)
        self.assertEqual(m['joint_success'],0)

    def test_overrestrictive(self):
        s=copy.deepcopy(self.row['reference_schema'])
        s['const']=self.row['reference_data']
        m=score(self.row,self.candidate(schema=s),self.suite)
        self.assertLess(m['positive_acceptance'],1)

    def test_wrong_content_and_date(self):
        d=dict(self.row['reference_data'],date='2026-11-07')
        m=score(self.row,self.candidate(data=d),self.suite)
        self.assertEqual(m['self_consistency'],1)
        self.assertEqual(m['data_accuracy'],0)
        d['date']='2026-02-30'
        self.assertEqual(score(self.row,self.candidate(data=d),self.suite)['reference_compliance'],0)

    def test_raw_format(self):
        for text in ['```json\n'+self.candidate()+'\n```',self.candidate()+' explanation',
                     '{"schema":{},"data":{},"data":{}}','{"schema":{},"data":{"a":NaN}}']:
            self.assertEqual(score(self.row,text,self.suite)['format_success'],0)

    def test_missing_and_extra(self):
        d={'name':'会议','date':'2026-11-06','extra':1}
        m=score(self.row,self.candidate(data=d),self.suite)
        self.assertEqual(m['reference_compliance'],0)
        self.assertEqual(m['data_accuracy'],0)

    def test_time_normalization(self):
        schema={'type':'string','format':'date-time'}
        self.assertEqual(normalize_data('2026-11-06T15:30:00+08:00',schema),
                         normalize_data('2026-11-06T07:30:00Z',schema))
        self.assertNotEqual(normalize_data('00123',{'type':'string'}),'123')

if __name__ == '__main__':
    unittest.main()
