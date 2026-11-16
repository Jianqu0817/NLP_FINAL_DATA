"""Compile only completed held-out evaluations; never invent missing results."""
import csv
import json
from pathlib import Path
import statistics
import numpy as np
from evaluation import RATES

ROOT=Path(__file__).resolve().parents[1]

def main():
    output=ROOT/'results'
    output.mkdir(exist_ok=True)
    rows=[]
    for path in sorted((ROOT/'runs').glob('*/*.metrics.json')):
        if path.name not in {'test.metrics.json','challenge.metrics.json'} or 'smoke' in path.parent.name:
            continue
        data=json.loads(path.read_text())
        row={'run':path.parent.name,'split':path.name.split('.')[0],
             **{k:data.get(k) for k in ['n',*RATES,'field_accuracy','truncated_outputs','seconds',
                                      'output_tokens','tokens_per_second','generation_seconds',
                                      'generation_tokens_per_second','peak_allocated_gb']}}
        state=path.parent/'status.json'
        if state.exists():
            row.update({k:v for k,v in json.loads(state.read_text()).items() if k in
                        {'trainable_parameters','training_seconds','training_peak_allocated_gb','best_epoch'}})
        rows.append(row)
        for track,metrics in data.get('by_track',{}).items():
            rows.append({'run':path.parent.name,'split':path.name.split('.')[0],
                         'track':track,**{k:metrics.get(k) for k in ['n',*RATES]}})
        row['track']='all'
    (output/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    if rows:
        keys=list(dict.fromkeys(k for row in rows for k in row))
        with (output/'results.csv').open('w',newline='',encoding='utf-8-sig') as f:
            writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows(rows)
    summary={}
    for method in ['adapter','lora']:
        for split in ['test','challenge']:
            group=[r for r in rows if r['run'].startswith(method+'_lr') and r['split']==split and r.get('track')=='all']
            if group:
                summary[method+'_'+split]={'completed_runs':len(group),'joint_mean':statistics.mean(r['joint_success'] for r in group),
                    'joint_sd':statistics.stdev(r['joint_success'] for r in group) if len(group)>1 else None,
                    'note':'three-seed result only when completed_runs=3'}
    (output/'seed_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    paired={}
    selection_file=ROOT/'selected_configs.json'
    if selection_file.exists():
        selections=json.loads(selection_file.read_text())
        for split in ['test','challenge']:
            base=ROOT/'runs'/'base_zero'/f'{split}.jsonl'
            if not base.exists():
                continue
            baseline={r['id']:r for r in map(json.loads,base.read_text(encoding='utf-8').splitlines())}
            for method,configuration in selections.items():
                files=[ROOT/'runs'/f'{method}_lr{configuration["lr"]:g}_seed{seed}'/f'{split}.jsonl' for seed in [42,43,44]]
                if not all(p.exists() and p.with_suffix('.metrics.json').exists() for p in files):
                    continue
                runs=[{r['id']:r for r in map(json.loads,p.read_text(encoding='utf-8').splitlines())} for p in files]
                if not all(set(r)==set(baseline) for r in runs):
                    raise ValueError('paired evaluation IDs differ')
                for track in sorted({r.get('track','requirements') for r in baseline.values()}):
                    clusters={}
                    for uid,b in baseline.items():
                        if b.get('track','requirements')!=track:
                            continue
                        diff=statistics.mean(r[uid]['metrics']['joint_success'] for r in runs)-b['metrics']['joint_success']
                        clusters.setdefault(b.get('schema_cluster',b['family']),[]).append(diff)
                    sums=np.array([sum(v) for v in clusters.values()]);counts=np.array([len(v) for v in clusters.values()])
                    rng=np.random.default_rng(20261105)
                    draw=rng.integers(0,len(sums),size=(2000,len(sums)))
                    samples=sums[draw].sum(1)/counts[draw].sum(1)
                    paired[f'{method}-{split}-{track}']={'delta_joint':float(sums.sum()/counts.sum()),
                        'ci95':list(map(float,np.quantile(samples,[.025,.975]))),'clusters':len(clusters),
                        'note':'paired schema-cluster bootstrap, trained seeds averaged per item; seed variability reported separately'}
    (output/'paired_cluster_ci.json').write_text(json.dumps(paired,indent=2),encoding='utf-8')
    print(json.dumps({'completed_evaluations':len(rows),'seed_summary':summary}),flush=True)

if __name__=='__main__':
    main()
