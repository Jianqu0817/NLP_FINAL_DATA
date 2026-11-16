"""Greedy evaluation, same prompt/runner/decoder as the pilot. No test input selects weights."""
import argparse
import json
import random
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0,str(ROOT/"scripts"))
import experiment as exp
import numpy as np
import torch

DATA = {"old_original": ROOT/"paired_study/pairs.jsonl", "old_paraphrase": ROOT/"paired_study/paraphrases.jsonl",
        **{f"confirm_{w}": HERE/f"confirm_{w}.jsonl" for w in ("original","wording","order")}}

def run(condition, datasets):
    random.seed(42); np.random.seed(42); torch.manual_seed(42); torch.cuda.manual_seed_all(42)
    torch.set_num_threads(8)
    if condition in ("Base","A","C"):
        method = {"Base":"base","A":"adapter","C":"lora"}[condition]
        ckpt = ROOT/"runs"/(method+"_lr0.0001_seed42")/"best.pt" if condition!="Base" else None
        model, tok, manifest = exp.build(SimpleNamespace(method=method,width=64,checkpoint=ckpt))
    else:
        from train_variant import build_for_eval
        ckpt = HERE/"runs"/condition/"best.pt"
        model,tok,manifest = build_for_eval(condition,ckpt)
    for dataset in datasets:
        if condition in ("Base","A","C") and dataset.startswith("old_"):
            raise ValueError("Use existing pilot predictions for old controls.")
        source = DATA[dataset]
        rows=list(map(json.loads,source.read_text(encoding="utf-8").splitlines()))
        assert len(rows)==len({r["id"] for r in rows})==(96 if dataset.startswith("old_") else 48)
        for r in rows: r["rule_tags"]=[r["family"]]
        suites={r["id"]:{k:[{"instance":p["instance"]} for p in r["probes"] if p["accept"]==v]
                          for k,v in (("positive",True),("negative",False))} for r in rows}
        args=SimpleNamespace(eval_batch=16,max_new_tokens=2048)
        out=HERE/"predictions"/dataset/(condition+".jsonl")
        out.parent.mkdir(parents=True,exist_ok=True)
        if out.exists(): raise FileExistsError(out)
        conf=dict(condition=condition,dataset=dataset,n=len(rows),model=manifest,system=exp.SYSTEM,
                  checkpoint=str(ckpt) if ckpt else None,eval_batch=16,max_new_tokens=2048,decoding="greedy",
                  seed=42,gpu=torch.cuda.get_device_name(),torch=torch.__version__)
        out.with_suffix(".config.json").write_text(json.dumps(conf,ensure_ascii=False,indent=2),encoding="utf8")
        m=exp.evaluate(model,tok,rows,suites,args,out)
        print("EVAL_COMPLETE",condition,dataset,len(rows),m["truncated_outputs"],round(m["seconds"],2),flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("condition",choices=["Base","A","B","C","D","E"])
    p.add_argument("datasets",choices=list(DATA),nargs="+")
    args=p.parse_args();run(args.condition,args.datasets)
