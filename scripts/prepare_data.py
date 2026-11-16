"""Validate synthetic rows, enforce split separation, and freeze witness suites."""
import gzip
import json
from collections import Counter
from pathlib import Path
from evaluation import validator, witnesses, digest, dumps, score

ROOT = Path(__file__).resolve().parents[1]

def without_annotations(x):
    # Apply to schema nodes only: a data property named "title" is not annotation.
    out={}
    for k,v in x.items():
        if k in {'description','title','$schema'}:
            continue
        if k=='properties':
            out[k]={name:without_annotations(child) for name,child in v.items()}
        elif k in {'items','if','then','else'}:
            out[k]=without_annotations(v)
        elif k in {'oneOf','anyOf','allOf'}:
            out[k]=[without_annotations(child) for child in v]
        elif k=='required':
            out[k]=sorted(v)
        else:
            out[k]=v
    return out

def operator_signature(schema):
    found=set()
    def visit(s):
        if not isinstance(s,dict):
            return
        found.update(set(s)-{'$schema','type','properties','required','additionalProperties','title','description'})
        for c in s.get('properties',{}).values():
            visit(c)
        for k in ['items','if','then','else']:
            visit(s.get(k))
        for k in ['oneOf','anyOf','allOf']:
            for c in s.get(k,[]):
                visit(c)
    visit(schema)
    return ','.join(sorted(found))

def main():
    data_dir = ROOT/'data'
    manifest = {'generation':'GPT-6 Luna max, four workers; model-assisted synthetic templates',
                'human_test_available':False, 'splits':{}, 'excluded':[]}
    previous_families, previous_schemas, previous_inputs = set(), set(), set()
    train_signatures=set()
    for split in ['train','validation','test','challenge']:
        source = data_dir/(split+'_raw.jsonl')
        rows = [json.loads(l) for l in source.read_text(encoding='utf-8').splitlines() if l.strip()]
        for row in rows:
            row['track']='requirements'
        natural_file=data_dir/f'natural_{split}_raw.jsonl'
        if split in {'train','validation','test'}:
            natural_rows=[json.loads(l) for l in natural_file.read_text(encoding='utf-8').splitlines() if l.strip()]
            for row in natural_rows:
                row['track']='natural_meeting'
            rows.extend(natural_rows)
        retained, local_inputs, local_ids = [], set(), set()
        this_families, this_schemas = set(), set()
        for row in rows:
            for field in ['id','family','rule_tags','input','reference_schema','reference_data','provenance']:
                if field not in row:
                    raise ValueError(f'missing {field} in {source}')
            if not isinstance(row['input'],str) or not row['input'].strip():
                raise ValueError('empty input')
            validator(row['reference_schema']).validate(row['reference_data'])
            key = digest(without_annotations(row['reference_schema']))
            input_key = digest(''.join(row['input'].split()))
            reason = None
            if row['family'] in previous_families:
                reason = 'cross_split_family'
            elif key in previous_schemas and row['track']!='natural_meeting':
                reason = 'cross_split_exact_schema'
            elif input_key in previous_inputs or input_key in local_inputs:
                reason = 'duplicate_input'
            if reason:
                manifest['excluded'].append({'id':row['id'],'split':split,'reason':reason})
                continue
            if row['id'] in local_ids:
                raise ValueError('duplicate ID '+row['id'])
            row['split'] = split
            row['schema_cluster']=key
            row['operator_signature']=operator_signature(row['reference_schema'])
            row['unseen_operator_combination']=split!='train' and row['operator_signature'] not in train_signatures
            retained.append(row)
            local_inputs.add(input_key)
            local_ids.add(row['id'])
            this_families.add(row['family'])
            this_schemas.add(key)
        if len(retained) < max(20,len(rows)//2):
            raise ValueError(f'{split}: too many overlaps removed ({len(retained)}/{len(rows)})')
        target = data_dir/(split+'.jsonl')
        target.write_text(''.join(dumps(r)+'\n' for r in retained),encoding='utf-8')
        manifest['splits'][split] = {'n':len(retained),'raw_n':len(rows),'families':len(this_families),
            'unique_schemas':len(this_schemas),'sha256':digest(retained),
            'tracks':dict(Counter(r['track'] for r in retained)),
            'unseen_operator_combination_rows':sum(r['unseen_operator_combination'] for r in retained),
            'rules':dict(Counter(t for r in retained for t in r['rule_tags']))}
        if split != 'train':
            totals = Counter()
            with gzip.open(data_dir/(split+'_witnesses.jsonl.gz'),'wt',encoding='utf-8') as f:
                for row in retained:
                    suite = witnesses(row)
                    oracle = dumps({'schema':row['reference_schema'],'data':row['reference_data']})
                    if not score(row,oracle,suite)['joint_success']:
                        raise ValueError('oracle failed '+row['id'])
                    f.write(dumps({'id':row['id'],**suite})+'\n')
                    totals['positive'] += len(suite['positive'])
                    totals['negative'] += len(suite['negative'])
            manifest['splits'][split]['witness_counts'] = dict(totals)
        previous_families.update(this_families)
        previous_schemas.update(this_schemas)
        previous_inputs.update(local_inputs)
        if split=='train':
            train_signatures={r['operator_signature'] for r in retained}
        print(split,manifest['splits'][split],flush=True)
    (data_dir/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__ == '__main__':
    main()
