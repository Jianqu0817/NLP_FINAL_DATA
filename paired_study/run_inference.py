"""Inference-only follow-up. Reuse the frozen pilot model, prompts, decoding and evaluator."""
import argparse
import json
import random
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "scripts"))
import experiment as exp

# No counts, optional/null fields, or conditional rules from the diagnostic.
DEMO = {"input": "把一条标签记录转成规定的输出。字段 label 是字符串，这条记录的标签是青瓷。",
        "reference_schema": {"$schema": "https://json-schema.org/draft/2020-12/schema",
                             "type": "object", "properties": {"label": {"type": "string"}},
                             "required": ["label"], "additionalProperties": False},
        "reference_data": {"label": "青瓷"}}

def run(task):
    split, condition = task.split(":")
    if split not in ("test", "challenge", "paired", "paraphrase") or condition not in ("base_zero", "base_demo", "adapter", "lora"):
        raise ValueError(task)
    paired = split in ("paired","paraphrase")
    outdir = HERE / ("paraphrase_predictions" if split=="paraphrase" else ("predictions" if paired else "original_control"))
    outdir.mkdir(exist_ok=True)
    out = outdir / ((condition if paired else split+"_"+condition)+".jsonl")
    if out.exists() or out.with_suffix(".metrics.json").exists():
        raise FileExistsError(out)
    if paired:
        rows = [json.loads(line) for line in (HERE/("paraphrases.jsonl" if split=="paraphrase" else "pairs.jsonl")).read_text(encoding="utf8").splitlines()]
        if len(rows)!=96 or len({r["pair_id"] for r in rows})!=48:
            raise ValueError("expected frozen 48-pair study")
        suites = {r["id"]: {kind:[{"instance":p["instance"]} for p in r["probes"] if p["accept"] == accepted]
                            for kind,accepted in (("positive",True),("negative",False))} for r in rows}
        for r in rows: r["rule_tags"]=[r["family"]]
    else:
        rows, suites = exp.read_rows(split), exp.read_suites(split)
    method = condition if condition in ("adapter","lora") else "base"
    ckpt = ROOT/"runs"/(method+"_lr0.0001_seed42")/"best.pt" if method!="base" else None
    args=SimpleNamespace(method=method, width=64, checkpoint=ckpt, eval_batch=16, max_new_tokens=2048)
    random.seed(42); np.random.seed(42); torch.manual_seed(42); torch.cuda.manual_seed_all(42)
    torch.set_num_threads(8)
    model, tokenizer, manifest = exp.build(args)
    examples = [DEMO] if condition=="base_demo" else None
    out.with_suffix(".config.json").write_text(json.dumps(dict(condition=condition, split=split, checkpoint=str(ckpt) if ckpt else None,
        model=manifest, gpu=torch.cuda.get_device_name(), seed=42, eval_batch=16, max_new_tokens=2048,
        decoding="greedy", demo=examples, system=exp.SYSTEM, n=len(rows)),ensure_ascii=False,indent=2),encoding="utf-8")
    m=exp.evaluate(model,tokenizer,rows,suites,args,out,examples)
    print("COMPLETE",task,len(rows),m["truncated_outputs"],round(m["seconds"],2),flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("task");run(p.parse_args().task)
