"""Check that the local archive contains complete, distinct predictions before stopping the rented GPU."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent

def read(p):
    with p.open(encoding="utf8") as f: return list(map(json.loads,f))

def validate():
    total=0
    for dataset,folder,names,n in [
        (HERE/"pairs.jsonl","predictions",("base_zero","base_demo","adapter","lora"),96),
        (HERE/"paraphrases.jsonl","paraphrase_predictions",("base_zero","base_demo","adapter","lora"),96),
        (HERE.parent/"data/test.jsonl","original_control",("test_base_demo",),580),
        (HERE.parent/"data/challenge.jsonl","original_control",("challenge_base_demo",),100)]:
        expected={r["id"] for r in read(dataset)}
        assert len(expected)==n
        for name in names:
            d=HERE/folder
            rs=read(d/(name+".jsonl"))
            metrics=json.loads((d/(name+".metrics.json")).read_text(encoding="utf8"))
            cfg=json.loads((d/(name+".config.json")).read_text(encoding="utf8"))
            assert len(rs)==metrics["n"]==cfg["n"]==n and {r["id"] for r in rs}==expected, name
            assert all(isinstance(r["raw_output"],str) and r["output_tokens"]>0 for r in rs), name
            total+=n
    print(f"All 10 runs archived: {total} complete prediction records with expected IDs.")
if __name__=="__main__": validate()
