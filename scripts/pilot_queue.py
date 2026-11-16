"""User-requested reduced queue: preserve current Adapter, run one LoRA, evaluate, stop."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback

from pipeline import ROOT, STATUS, train, evaluate


def identity(pid):
    try:
        command = Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0', b' ').decode()
        # Read state after cmdline: an exiting process can clear cmdline between
        # reads while an earlier stat snapshot still described it as running.
        stat = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        return {'state': stat[0], 'ppid': int(stat[1]), 'start': stat[19], 'command': command}
    except FileNotFoundError:
        return None


def retire_scheduler(record):
    current = identity(record['old_scheduler_pid'])
    if current is None or current['start'] != record['old_scheduler_start']:
        return
    if 'scripts/pipeline.py --stage core' not in current['command'] or current['state'] not in {'T','t'}:
        raise RuntimeError('old scheduler identity/state changed; refusing to signal it')
    os.kill(record['old_scheduler_pid'], signal.SIGKILL)
    print('Retired old stopped scheduler; existing training process has exited.', flush=True)


def wait_for_adapter(record):
    pid = record['training_pid']
    scheduler = identity(record['old_scheduler_pid'])
    if scheduler and scheduler['start'] == record['old_scheduler_start'] and scheduler['state'] not in {'T','t'}:
        raise RuntimeError('old scheduler is not stopped')
    while True:
        current = identity(pid)
        if current is None or current['start'] != record['training_start'] or current['state'] == 'Z':
            break
        if not current['command']:
            # Transient exit state, not evidence of a different live command.
            time.sleep(0.1)
            continue
        if 'adapter_lr0.0001_seed42' not in current['command'] or '--mode train' not in current['command']:
            raise RuntimeError('training process identity changed')
        STATUS.write_text(json.dumps({'status':'running','scope':'pilot_only',
            'current':record['training_run'],'phase':'preserving_existing_training',
            'training_pid':pid,'updated_unix':time.time()},indent=2))
        time.sleep(15)
    # Clean up the stopped scheduler on both success and failure; never signal a
    # process group or close its tmux session while the training child is alive.
    retire_scheduler(record)
    state_path = ROOT/'runs'/record['training_run']/'status.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    if state.get('status') != 'complete' or state.get('epoch') != 3:
        raise RuntimeError('existing Adapter training exited before completing three epochs')


def report():
    subprocess.run([sys.executable,'scripts/summarize.py'],cwd=ROOT,check=True)
    records=[]
    lines=['# Single-seed preliminary comparison', '',
           'User requested one Adapter and one LoRA training run, three epochs each.',
           'Both use learning rate 1e-4 and seed 42. No learning-rate search,',
           'additional seeds, or width ablations were run in this reduced queue.',
           'These are synthetic-data, single-seed results, not a stability claim.', '',
           '| Method | Split | Track | N | Joint success | Data accuracy | Rule score |',
           '|---|---|---|---:|---:|---:|---:|']
    for name in ['base_zero','adapter_lr0.0001_seed42','lora_lr0.0001_seed42']:
        for split in ['test','challenge']:
            metrics=json.loads((ROOT/'runs'/name/f'{split}.metrics.json').read_text())
            for track,m in metrics['by_track'].items():
                row={'method':name,'split':split,'track':track,**m}
                records.append(row)
                lines.append(f'| {name} | {split} | {track} | {m["n"]} | '
                    f'{m["joint_success"]:.2%} | {m["data_accuracy"]:.2%} | {m["balanced_rule_score"]:.2%} |')
    (ROOT/'results'/'pilot_summary.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'results'/'pilot_summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def main():
    policy=json.loads((ROOT/'experiment_scope.json').read_text())
    if policy.get('mode') != 'pilot_only':
        raise RuntimeError('pilot-only policy required')
    transition=ROOT/'queue_transition.json'
    if transition.exists():
        wait_for_adapter(json.loads(transition.read_text()))
    else:
        train('adapter_lr0.0001_seed42','adapter',1e-4,42,['--epochs','3'])
    train('lora_lr0.0001_seed42','lora',1e-4,42,['--epochs','3'])
    for method in ['adapter','lora']:
        name=f'{method}_lr0.0001_seed42'
        evaluate(name,method,ROOT/'runs'/name/'best.pt')
    evaluate('base_zero','base')
    report()
    STATUS.write_text(json.dumps({'status':'pilot_complete','scope':'pilot_only',
        'remaining_experiments':'deferred_pending_user_decision','updated_unix':time.time()},indent=2))
    print('Pilot complete. No further experiments will start.',flush=True)


if __name__=='__main__':
    try:
        main()
    except Exception as exc:
        current=json.loads(STATUS.read_text()) if STATUS.exists() else {}
        current.update(status='failed',scope='pilot_only',error=str(exc),updated_unix=time.time())
        STATUS.write_text(json.dumps(current,indent=2))
        traceback.print_exc()
        raise SystemExit(1)
