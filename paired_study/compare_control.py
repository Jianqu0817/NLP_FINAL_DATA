"""Summarize the same requests for four conditions, separately by track and format handling."""
import json, csv, sys
from pathlib import Path
import pilot_audit as audit
HERE=Path(__file__).resolve().parent
RUNS={**audit.RUNS, "Base + example":None}
KEYS=("format_success","schema_validity","schema_rule_evaluable","schema_suite_pass","data_accuracy","joint_success")
def main():
    out=[]
    for split in ("test","challenge"):
        gold=audit.indexed(audit.ROOT/"data"/f"{split}.jsonl")
        suites=audit.indexed(audit.ROOT/"data"/f"{split}_witnesses.jsonl.gz")
        for condition, path in RUNS.items():
            loc=(audit.ROOT/"runs"/path/f"{split}.jsonl") if path else (HERE/"original_control"/f"{split}_base_demo.jsonl")
            raw=audit.indexed(loc)
            if gold.keys()!=raw.keys(): raise ValueError(f"Incomplete result: {loc}")
            adj={}
            for k,r in raw.items():
                wrapped=None if r["metrics"]["format_success"] else audit.rewrap(r["raw_output"])
                adj[k]=audit.score(gold[k],wrapped,suites[k]) if wrapped is not None else r["metrics"]
            for track in ["all"]+(["requirements","natural_meeting"] if split=="test" else []):
                ids=[k for k in gold if track=="all" or gold[k]["track"]==track]
                for mode in ("strict","rewrapped"):
                    scores=[raw[k]["metrics"] if mode=="strict" else adj[k] for k in ids]
                    out.append(dict(split=split,track=track,condition=condition,mode=mode,n=len(ids),
                        **{m:sum(r[m] for r in scores) for m in KEYS},
                        truncated=sum(raw[k]["truncated"] for k in ids)))
    with (HERE/"original_control"/"comparison.csv").open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=out[0].keys()); writer.writeheader();writer.writerows(out)
if __name__=="__main__": main()
