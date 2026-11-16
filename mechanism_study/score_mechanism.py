"""CPU-only pre-specified mechanism analysis; reuse the existing scoring contracts."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'paired_study'))
import score_pairs as paired
import semantic_probe as semantic

CONDITIONS = ('Base', 'A', 'B', 'C', 'D', 'E')
DATASETS = {'old_original': ROOT/'paired_study/pairs.jsonl',
            'old_paraphrase': ROOT/'paired_study/paraphrases.jsonl',
            **{n: HERE/(n+'.jsonl') for n in ('confirm_original', 'confirm_wording', 'confirm_order')}}
CONTRASTS = [('A','B'), ('B','D'), ('D','E'), ('A','C'), ('Base','A'), ('Base','C')]
PAIR_METRICS = ('draft_suite', 'profile_suite', 'strict_joint', 'format', 'data',
                'changed_all_correct', 'invariant_all_correct')

def ratio(n, d):
    return {'count': n, 'denominator': d, 'rate': n/d if d else None}

def placement(row, schema):
    if row['family'] != 'count_bounds':
        return None
    ref = row['reference_schema']['properties']
    field = row.get('focus_field') or next(k for k,v in ref.items() if 'minItems' in v)
    expected = [row.get('expected_min', ref[field]['minItems']), row.get('expected_max', ref[field]['maxItems'])]
    schema = schema or {}
    properties = schema.get('properties', {})
    properties = properties if isinstance(properties,dict) else {}
    target = properties.get(field, {})
    def bounds(node):
        return [node.get('minItems'), node.get('maxItems')] if isinstance(node,dict) else [None,None]
    target_values, root_values = bounds(target), bounds(schema)
    def numeric(values):
        return all(isinstance(v,(int,float)) and not isinstance(v,bool) for v in values)
    correct_target = numeric(target_values) and target_values == expected and isinstance(target,dict) and target.get('type') == 'array'
    label = 'correct_at_array' if correct_target else ('correct_numbers_root_only' if root_values == expected else 'wrong_or_missing')
    distractor_values=bounds(properties.get(row.get('distractor_field'), {}))
    return {'label': label, 'focus_field': field, 'expected': expected,
            'target': target_values, 'root': root_values,
            'root_has_any_bound':any(k in schema for k in ('minItems','maxItems')),
            'target_missing_bound':any(v is None for v in target_values),
            'distractor': distractor_values,'distractor_has_any_bound':any(v is not None for v in distractor_values)}

def item_score(row, prediction, mode):
    item = semantic.score(row, prediction, mode)
    item['placement'] = placement(row, item['generated_schema'])
    return item

def pair_score(items):
    base = semantic.pair_score(items)
    return {'pair_id': base['pair_id'], 'family': base['family'], 'ids': base['ids'],
            'draft_suite': base['both_suite_pass'],
            'both_evaluable': base['both_rule_evaluable'],
            'profile_suite': int(all(i['original_metrics']['schema_validity'] and i['original_metrics']['schema_suite_pass'] for i in items)),
            'strict_joint': int(all(i['original_metrics']['joint_success'] for i in items)),
            'format': int(all(i['original_metrics']['format_success'] for i in items)),
            'data': int(all(i['original_metrics']['data_accuracy'] for i in items)),
            'changed_all_correct': base['discriminating_all_correct'],
            'changed_both_correct': base['discriminating_both_correct'],
            'changed_total': base['discriminating_probe_total'],
            'invariant_all_correct': int(base['invariant_both_correct'] == base['invariant_probe_total']),
            'invariant_both_correct': base['invariant_both_correct'],
            'invariant_total': base['invariant_probe_total'],
            'missing': int(any(i['missing_prediction'] for i in items)),
            'truncated': int(any(i['truncated'] for i in items)),
            'placement': [i['placement']['label'] if i['placement'] else None for i in items]}

def summarize(items, pairs):
    result = {'n_items':len(items), 'n_pairs':len(pairs),
              'pairs': {m:ratio(sum(p[m] for p in pairs), len(pairs)) for m in PAIR_METRICS},
              'items': {m:ratio(sum(i['original_metrics'][m] for i in items),len(items)) for m in ('format_success','schema_validity','data_accuracy','joint_success')},
              'missing_items':sum(i['missing_prediction'] for i in items),
              'truncated_items':sum(i['truncated'] for i in items),
              'missing_pairs':sum(p['missing'] for p in pairs), 'truncated_pairs':sum(p['truncated'] for p in pairs),
              'placement_items':dict(Counter(i['placement']['label'] for i in items if i['placement'])),
              'placement_pairs':dict(Counter('|'.join(p['placement']) for p in pairs if all(p['placement'])))}
    result['pairs']['both_evaluable']=ratio(sum(p['both_evaluable'] for p in pairs),len(pairs))
    result['pairs']['changed_both_correct_conditional']=ratio(
        sum(p['changed_both_correct'] for p in pairs if p['both_evaluable']),
        sum(p['changed_total'] for p in pairs if p['both_evaluable']))
    count_items=[i for i in items if i['placement']]
    evaluable_count=[i for i in count_items if i['metrics']['schema_rule_evaluable']]
    result['placement_exact_target']=ratio(sum(i['placement']['label']=='correct_at_array' for i in count_items),len(count_items))
    result['placement_exact_target_conditional']=ratio(sum(i['placement']['label']=='correct_at_array' for i in evaluable_count),len(evaluable_count))
    result['placement_root_any']=sum(i['placement']['root_has_any_bound'] for i in count_items)
    result['placement_distractor_any']=sum(i['placement']['distractor_has_any_bound'] for i in count_items)
    result['placement_target_missing_bound']=sum(i['placement']['target_missing_bound'] for i in count_items)
    for prefix in ('changed','invariant'):
        result['pairs'][prefix+'_both_correct'] = ratio(sum(p[prefix+'_both_correct'] for p in pairs),sum(p[prefix+'_total'] for p in pairs))
    return result

def transitions(left, right, metric):
    if left.keys() != right.keys():
        raise ValueError('comparison pair IDs differ')
    cells = {name:[] for name in ('retained_pass','lost_pass','gained_pass','retained_failure')}
    for pid in left:
        a,b = bool(left[pid][metric]),bool(right[pid][metric])
        cells[{(True,True):'retained_pass',(True,False):'lost_pass',(False,True):'gained_pass',(False,False):'retained_failure'}[a,b]].append(pid)
    passing = len(cells['retained_pass'])+len(cells['lost_pass'])
    failing = len(cells['retained_failure'])+len(cells['gained_pass'])
    return {'n_pairs':len(left), 'left_passes':passing, 'left_failures':failing,
            'loss':ratio(len(cells['lost_pass']),passing), 'gain':ratio(len(cells['gained_pass']),failing),
            **{name:{'count':len(ids),'ids':ids} for name,ids in cells.items()}}

def cross_variants(index, datasets, mode, family='all'):
    available = [d for d in datasets if (d,'Base',mode) in index]
    if len(available) != len(datasets):
        return []
    common = set.intersection(*(set(index[d,'Base',mode]) for d in datasets))
    if family != 'all':
        common = {p for p in common if index[datasets[0],'Base',mode][p]['family']==family}
    results=[]
    for condition in CONDITIONS:
        if not all((d,condition,mode) in index for d in datasets):
            continue
        for metric in PAIR_METRICS:
            evaluable=sorted(p for p in common if all(index[d,condition,mode][p].get('both_evaluable',1) for d in datasets))
            stable = sorted(p for p in common if all(index[d,'Base',mode][p][metric] for d in datasets))
            damaged = sorted(common-set(stable))
            per_variant={}
            for d in datasets:
                losses=[p for p in stable if not index[d,condition,mode][p][metric]]
                gains=[p for p in damaged if not index[d,'Base',mode][p][metric] and index[d,condition,mode][p][metric]]
                base_fail=[p for p in damaged if not index[d,'Base',mode][p][metric]]
                per_variant[d]={'base_stable_loss':ratio(len(losses),len(stable)), 'loss_ids':losses,
                                'base_failure_gain':ratio(len(gains),len(base_fail)), 'gain_ids':gains}
            allpass=[p for p in common if all(index[d,condition,mode][p][metric] for d in datasets)]
            stable_allpass=sorted(set(allpass)&set(stable))
            variant_transitions={}
            first=datasets[0]
            for d in datasets[1:]:
                subsets={'all':sorted(common),'base_stable':stable,'common_evaluable':evaluable}
                variant_transitions[d]={name:transitions({p:index[first,condition,mode][p] for p in subset},
                                                         {p:index[d,condition,mode][p] for p in subset},metric)
                                        for name,subset in subsets.items()}
            results.append({'datasets':datasets,'condition':condition,'mode':mode,'family':family,'metric':metric,
                            'common_pairs':len(common),'base_stable_pairs':len(stable),'base_stable_ids':stable,
                            'common_evaluable_pairs':len(evaluable),'common_evaluable_ids':evaluable,
                            'condition_all_variant_pass':ratio(len(allpass),len(common)),
                            'condition_pass_on_base_stable_all_variants':ratio(len(stable_allpass),len(stable)),
                            'base_stable_all_variant_pass_ids':stable_allpass,'per_variant':per_variant,
                            'condition_original_to_variant_transitions':variant_transitions})
    return results

def prediction_path(dataset, condition):
    if dataset.startswith('old_') and condition in ('Base','A','C'):
        folder='predictions' if dataset=='old_original' else 'paraphrase_predictions'
        return ROOT/'paired_study'/folder/({'Base':'base_zero','A':'adapter','C':'lora'}[condition]+'.jsonl')
    return HERE/'predictions'/dataset/(condition+'.jsonl')

def render_evidence(summary,comparisons,cross):
    def frac(value):return str(value['count'])+'/'+str(value['denominator'])
    lines=['# Mechanism numerical evidence','',f'Complete inputs: {summary["complete"]}.', '',
           '| Dataset | Condition | Family | Draft full suite | Changed both-correct | Conditional changed | Profile suite | Strict joint | Format | Data | Truncated pairs |',
           '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for dataset,conditions in summary['datasets'].items():
        for condition,modes in conditions.items():
            stats=modes['strict']
            for family,s in [('all',stats)]+[(f,s) for f,s in stats['by_family'].items() if f in ('count_bounds','nullable')]:
                p=s['pairs']
                values=[frac(p[m]) for m in ('draft_suite','changed_both_correct','changed_both_correct_conditional','profile_suite','strict_joint','format','data')]
                lines.append('| '+' | '.join([dataset,condition,family]+values+[str(s['truncated_pairs'])])+' |')
    lines+=['','## Paired strict Draft full-suite contrasts','',
            '| Dataset | Contrast | Family | Left pass | Right pass | Loss / left pass | Gain / left fail | Lost IDs (up to 4) | Gained IDs (up to 4) |',
            '|---|---|---|---:|---:|---:|---:|---|---|']
    for r in comparisons:
        if r['mode']!='strict' or r['metric']!='draft_suite' or r['family'] not in ('all','count_bounds','nullable'):continue
        right=r['retained_pass']['count']+r['gained_pass']['count']
        lines.append('| '+' | '.join([r['dataset'],r['condition_a']+':'+r['condition_b'],r['family'],str(r['left_passes']),str(right),frac(r['loss']),frac(r['gain']),', '.join(r['lost_pass']['ids'][:4]),', '.join(r['gained_pass']['ids'][:4])])+' |')
    lines+=['','## Strict count-bound placement (items)','',
            '| Dataset | Condition | Exact target / all | Exact target / evaluable | Root-only exact numbers | Root any bound | Distractor any bound | Target missing bound |',
            '|---|---|---:|---:|---:|---:|---:|---:|']
    for dataset,conditions in summary['datasets'].items():
        for condition,modes in conditions.items():
            s=modes['strict']
            lines.append('| '+' | '.join([dataset,condition,frac(s['placement_exact_target']),frac(s['placement_exact_target_conditional']),str(s['placement_items'].get('correct_numbers_root_only',0)),str(s['placement_root_any']),str(s['placement_distractor_any']),str(s['placement_target_missing_bound'])])+' |')
    lines+=['','## Strict cross-variant Draft full-suite stability','',
            '| Variants | Condition | Family | Common pairs | Base-stable pairs | All-variant pass / Base-stable | All-variant pass / all | Losses on Base-stable by variant |',
            '|---|---|---|---:|---:|---:|---:|---|']
    for r in cross:
        if r['mode']!='strict' or r['metric']!='draft_suite' or r['family'] not in ('all','count_bounds','nullable'):continue
        losses='; '.join(d+': '+frac(v['base_stable_loss']) for d,v in r['per_variant'].items())
        lines.append('| '+' | '.join([', '.join(r['datasets']),r['condition'],r['family'],str(r['common_pairs']),str(r['base_stable_pairs']),frac(r['condition_pass_on_base_stable_all_variants']),frac(r['condition_all_variant_pass']),losses])+' |')
    if summary['unavailable']:lines+=['','## Unavailable inputs','']+['- '+s for s in summary['unavailable']]
    lines+=['','Diagnostic-wrapper results, all family strata, all IDs and conditional evaluability intersections: summary.json, pairs.jsonl, contrasts.jsonl, cross_variants.jsonl.','']
    return '\n'.join(lines)

def run(output, require_complete=False):
    output=Path(output)
    summary={'datasets':{},'unavailable':[], 'sources':{}, 'complete':True}
    all_items,all_pairs,comparisons=[],[],[]
    index={}
    for dataset,path in DATASETS.items():
        if not path.exists():
            summary['unavailable'].append(str(path));continue
        rows=paired.read_jsonl(path); groups=paired.validate_rows(rows); ids={r['id'] for r in rows}
        summary['datasets'][dataset]={}
        for condition in CONDITIONS:
            source=prediction_path(dataset,condition)
            summary['sources'][dataset+'/'+condition]=str(source.resolve())
            if not source.exists():
                summary['unavailable'].append(str(source));continue
            predictions={}
            for pred in paired.read_jsonl(source):
                if pred['id'] not in ids or pred['id'] in predictions or 'raw_output' not in pred:
                    raise ValueError(f'invalid/duplicate prediction ID or absent raw_output: {source}: {pred.get("id")}')
                predictions[pred['id']]=pred
            if set(predictions)!=ids:
                summary['unavailable'].append(f'{source}: missing {len(ids-set(predictions))} IDs')
            summary['datasets'][dataset][condition]={}
            for mode in ('strict','diagnostic'):
                items=[dict(dataset=dataset,condition=condition,**item_score(r,predictions.get(r['id']),mode)) for r in rows]
                byid={i['id']:i for i in items}
                pairs=[dict(dataset=dataset,condition=condition,mode=mode,**pair_score([byid[r['id']] for r in pair])) for pair in groups.values()]
                index[dataset,condition,mode]={p['pair_id']:p for p in pairs}
                stats=summarize(items,pairs)
                stats['by_family']={f:summarize([i for i in items if i['family']==f],[p for p in pairs if p['family']==f]) for f in sorted({r['family'] for r in rows})}
                summary['datasets'][dataset][condition][mode]=stats
                all_items.extend(items);all_pairs.extend(pairs)
        for mode in ('strict','diagnostic'):
            for a,b in CONTRASTS:
                if (dataset,a,mode) not in index or (dataset,b,mode) not in index:continue
                left,right=index[dataset,a,mode],index[dataset,b,mode]
                for family in ['all']+sorted({p['family'] for p in left.values()}):
                    l={k:v for k,v in left.items() if family in ('all',v['family'])}
                    r={k:right[k] for k in l}
                    for metric in PAIR_METRICS:
                        eligible={k:v for k,v in l.items() if v['both_evaluable'] and r[k]['both_evaluable']}
                        comparisons.append(dict(dataset=dataset,condition_a=a,condition_b=b,mode=mode,family=family,metric=metric,
                                                conditional_on_both_evaluable=transitions(eligible,{k:r[k] for k in eligible},metric),**transitions(l,r,metric)))
    cross=[]
    for datasets in (['old_original','old_paraphrase'],['confirm_original','confirm_wording'],['confirm_original','confirm_order'],['confirm_original','confirm_wording','confirm_order']):
        for mode in ('strict','diagnostic'):
            families=sorted({p['family'] for p in all_pairs if p['dataset']==datasets[0]})
            for family in ['all']+families:
                cross.extend(cross_variants(index,datasets,mode,family))
    summary['complete']=not summary['unavailable']
    if require_complete and not summary['complete']:
        raise ValueError('incomplete inputs: '+'; '.join(summary['unavailable']))
    output.mkdir(parents=True,exist_ok=True)
    (output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (output/'evidence.md').write_text(render_evidence(summary,comparisons,cross),encoding='utf-8')
    for name,records in [('items',all_items),('pairs',all_pairs),('contrasts',comparisons),('cross_variants',cross)]:
        paired.write_jsonl(output/(name+'.jsonl'),records)
    table=[]
    for dataset,conditions in summary['datasets'].items():
        for condition,modes in conditions.items():
            for mode,stats in modes.items():
                for family,s in [('all',stats)]+list(stats['by_family'].items()):
                    table.append(dict(dataset=dataset,condition=condition,mode=mode,family=family,n_pairs=s['n_pairs'],
                                      **{m:s['pairs'][m]['count'] for m in PAIR_METRICS},truncated_pairs=s['truncated_pairs'],missing_pairs=s['missing_pairs']))
    if table:
        with (output/'pair_counts.csv').open('w',encoding='utf-8',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=list(table[0]));writer.writeheader();writer.writerows(table)
    return summary

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=HERE/'analysis')
    parser.add_argument('--require-complete',action='store_true')
    args=parser.parse_args()
    result=run(args.output_dir,args.require_complete)
    print(json.dumps({'complete':result['complete'],'unavailable':result['unavailable'],'output':str(args.output_dir.resolve())},ensure_ascii=False))
