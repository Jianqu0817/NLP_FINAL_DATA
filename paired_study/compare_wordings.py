"""Compare pair outcomes across wordings; preserve paired denominators, not 96 independent pairs."""
from pathlib import Path
from collections import Counter
import csv,json
HERE=Path(__file__).resolve().parent

def decisions(path):
    with (path/"pairs.jsonl").open(encoding="utf-8") as f:
        return {(r["condition"],r["family"],r["pair_id"]):r["both_suite_pass"]
                for r in map(json.loads,f) if r["mode"]=="strict"}

def compare():
    output=[]
    for metric,d1,d2 in (("project_profile","results","paraphrase_results"),("draft_behavior","semantic_results","paraphrase_semantic")):
        a,b=decisions(HERE/d1),decisions(HERE/d2)
        if a.keys()!=b.keys() or len(a)!=4*48: raise ValueError("incomplete four-condition paired comparison")
        for cond in sorted({k[0] for k in a}):
            for family in ["all"]+sorted({k[1] for k in a}):
                keys=[k for k in a if k[0]==cond and family in ("all", k[1])]
                counts=Counter((a[k],b[k]) for k in keys)
                output.append(dict(metric=metric, condition=cond, family=family, pairs=len(keys),
                    original=sum(a[k] for k in keys), paraphrase=sum(b[k] for k in keys),both=counts[1,1],
                    only_original=counts[1,0],only_paraphrase=counts[0,1],neither=counts[0,0]))
    with (HERE/"wording_comparison.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=output[0].keys()); w.writeheader();w.writerows(output)

def schema_nodes(obj):
    yield obj
    for value in obj.values():
        if isinstance(value,dict): yield from schema_nodes(value)
        elif isinstance(value,list):
            for item in value:
                if isinstance(item,dict):yield from schema_nodes(item)

def training():
    branches=Counter(); records=0; tr=0
    with (HERE.parent/'data/train.jsonl').open(encoding='utf8') as f:
        for row in map(json.loads,f):
            tr+=1
            nodes=[s for s in schema_nodes(row['reference_schema']) if 'if' in s]
            records+=bool(nodes)
            for s in nodes:branches[tuple(s.get('then',{}).get('required',[])),tuple(s.get('else',{}).get('required',[]))]+=1
    print(f"Train: {records}/{tr} rows use if; (then.required, else.required) counts: {dict(branches)}")

if __name__=="__main__":
    training()
    compare()
