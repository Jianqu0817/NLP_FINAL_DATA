"""Sequential, bounded GPU experiment queue; failures stop the queue."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
STATUS=ROOT/'pipeline_status.json'

def run(name,args):
    command=[sys.executable,'-u','scripts/experiment.py',*args,'--name',name]
    state={'status':'running','current':name,'command':command,'updated_unix':time.time()}
    STATUS.write_text(json.dumps(state,indent=2))
    print(json.dumps(state),flush=True)
    log=ROOT/'logs'/f'{name}_{args[args.index("--mode")+1]}_{args[args.index("--split")+1] if "--split" in args else "train"}.log'
    with log.open('w') as f:
        result=subprocess.run(command,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    if result.returncode:
        state.update(status='failed',exit_code=result.returncode,log=str(log),updated_unix=time.time())
        STATUS.write_text(json.dumps(state,indent=2))
        raise RuntimeError(f'{name} failed; inspect {log}')

def train(name,method,lr,seed,extra=None):
    path=ROOT/'runs'/name/'status.json'
    if path.exists() and json.loads(path.read_text()).get('status')=='complete':
        return
    run(name,['--mode','train','--method',method,'--lr',str(lr),'--seed',str(seed),*(extra or [])])

def evaluate(name,method,checkpoint=None,extra=None):
    for split in ['test','challenge']:
        if (ROOT/'runs'/name/f'{split}.metrics.json').exists():
            continue
        args=['--mode','eval','--method',method,'--split',split]
        if checkpoint:
            args += ['--checkpoint',str(checkpoint)]
        run(name,args+(extra or []))

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--stage',choices=['smoke','core','ablation'],default='core')
    p.add_argument('--smoke-prefix',default='')
    args=p.parse_args()
    policy_file=ROOT/'experiment_scope.json'
    if args.stage in {'core','ablation'} and policy_file.exists():
        if json.loads(policy_file.read_text()).get('mode')=='pilot_only':
            raise RuntimeError('Extended experiments deferred by the user; run scripts/pilot_queue.py instead.')
    (ROOT/'logs').mkdir(exist_ok=True)
    if args.stage=='smoke':
        prefix=args.smoke_prefix
        run(prefix+'base_smoke',['--mode','eval','--method','base','--split','validation','--eval-limit','12','--eval-batch','2'])
        train(prefix+'adapter_smoke','adapter',3e-4,42,['--limit','16','--epochs','2','--accum','4','--eval-limit','4','--eval-batch','2'])
        train(prefix+'lora_smoke','lora',3e-4,42,['--limit','16','--epochs','1','--accum','4','--eval-limit','4','--eval-batch','2'])
        for method in ['adapter','lora']:
            run(prefix+method+'_smoke_reload',['--mode','eval','--method',method,'--split','validation',
                '--checkpoint',str(ROOT/'runs'/f'{prefix}{method}_smoke'/'best.pt'),'--eval-limit','4','--eval-batch','2'])
            state=json.loads((ROOT/'runs'/f'{prefix}{method}_smoke'/'status.json').read_text())
            before=ROOT/'runs'/f'{prefix}{method}_smoke'/f'validation_epoch{state["best_epoch"]}.jsonl'
            after=ROOT/'runs'/f'{prefix}{method}_smoke_reload'/'validation.jsonl'
            a=[json.loads(l)['raw_output'] for l in before.read_text().splitlines()]
            b=[json.loads(l)['raw_output'] for l in after.read_text().splitlines()]
            if a!=b:
                raise RuntimeError(f'{method}: save/load outputs differ')
        STATUS.write_text(json.dumps({'status':'smoke_complete','updated_unix':time.time()},indent=2))
        return
    selections={}
    selection_file=ROOT/'selected_configs.json'
    if args.stage=='core':
        for method in ['adapter','lora']:
            candidates=[]
            for lr in [1e-4,3e-4]:
                name=f'{method}_lr{lr:g}_seed42'
                train(name,method,lr,42)
                state=json.loads((ROOT/'runs'/name/'status.json').read_text())
                candidates.append((state['best_selection_key'],lr,name))
            # Stable tiebreak selects the first learning rate (1e-4).
            selected=max(candidates,key=lambda item:item[0])
            selections[method]={'lr':selected[1],'seed42_run':selected[2],'selection_key':selected[0]}
            selection_file.write_text(json.dumps(selections,indent=2))
            for seed in [43,44]:
                train(f'{method}_lr{selected[1]:g}_seed{seed}',method,selected[1],seed)
        # Test inference starts only after model selection is finished.
        evaluate('base_zero','base')
        evaluate('base_few','base',extra=['--few-shot'])
        for method,selection in selections.items():
            for seed in [42,43,44]:
                name=f'{method}_lr{selection["lr"]:g}_seed{seed}'
                evaluate(name,method,ROOT/'runs'/name/'best.pt')
    else:
        selections=json.loads(selection_file.read_text())
        for width in [32,128]:
            name=f'adapter_width{width}_seed42'
            train(name,'adapter',selections['adapter']['lr'],42,['--width',str(width)])
            evaluate(name,'adapter',ROOT/'runs'/name/'best.pt',['--width',str(width)])
    STATUS.write_text(json.dumps({'status':args.stage+'_complete','updated_unix':time.time()},indent=2))
    print(args.stage,'complete',flush=True)

if __name__=='__main__':
    main()
