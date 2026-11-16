"""Acceptance gate for the downloaded first-round training and inference outputs."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
def load(p):return json.loads(p.read_text(encoding="utf8"))
def lines(p):return [json.loads(l) for l in p.read_text(encoding="utf8").splitlines()]
def main():
    import torch
    base_inputs={k:lines(HERE/f"{k}.jsonl") for k in ["confirm_original","confirm_wording","confirm_order"]}
    for k,f in [("old_original","pairs.jsonl"),("old_paraphrase","paraphrases.jsonl")]:
        base_inputs[k]=lines(ROOT/"paired_study"/f)
    for v,w in [("B",64),("D",16),("E",16)]:
        folder=HERE/"runs"/v
        stats=load(folder/"status.json")
        assert stats['status']=='complete' and stats['epoch']==3 and stats['frozen_probe_checks_passed']
        records=lines(folder/"training.jsonl")
        assert len(records)==432 and records[-1]["step"]==432
        vals=[load(folder/f"validation_epoch{i}.metrics.json") for i in (1,2,3)]
        assert all(m["n"]==339 for m in vals)
        sel=[tuple(m[k] for k in ['joint_success','data_accuracy','balanced_rule_score','self_consistency']) for m in vals]
        assert stats['best_epoch']==1+sel.index(max(sel))
        state=torch.load(folder/"best.pt",map_location='cpu',weights_only=True)
        assert len(state)==144 and sum(t.numel() for t in state.values())==stats["trainable_parameters"]==36*(2*2560*w+2560+w)
        assert all(t.dtype==torch.float32 and t.isfinite().all().item() for t in state.values())
    n=0
    for ds,golds in base_inputs.items():
        expected={r['id'] for r in golds}
        for cond in ("B","D","E") if ds.startswith("old") else ("Base","A","B","C","D","E"):
            base=HERE/"predictions"/ds/cond
            config=load(base.with_suffix(".config.json")); m=load(base.with_suffix(".metrics.json")); pred=lines(base.with_suffix(".jsonl"))
            assert config["condition"]==cond and config["dataset"]==ds and config["n"]==m["n"]==len(pred)==len(expected)
            assert {r["id"] for r in pred}==expected and all(isinstance(r["raw_output"],str) for r in pred)
            n+=len(pred)
    assert n==1440,n
    print(f"Recovered B/D/E best checkpoints, 9 validation metrics and {n} new raw predictions.")
if __name__=="__main__":main()
