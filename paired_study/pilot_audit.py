"""Audit the three frozen pilot runs; print JSON without running inference."""
import gzip
import json
import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from evaluation import score, strict_loads

RUNS = {
    "Base": "base_zero",
    "Adapter": "adapter_lr0.0001_seed42",
    "LoRA": "lora_lr0.0001_seed42",
}
METRICS = ("format_success", "schema_rule_evaluable", "schema_suite_pass",
           "data_accuracy", "joint_success")
JSON_WS = " \t\r\n"


def rewrap(text):
    """Only add an envelope to exactly two complete, consecutive JSON objects."""
    text = text.strip(JSON_WS)
    try:
        _, end = json.JSONDecoder().raw_decode(text)
        first, second = text[:end], text[end:].strip(JSON_WS)
        if isinstance(strict_loads(first), dict) and isinstance(strict_loads(second), dict):
            return '{"schema":' + first + ',"data":' + second + '}'
    except ValueError:
        pass
    return None


def indexed(path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as f:
        records = {}
        for r in map(json.loads, f):
            if r["id"] in records:
                raise ValueError(f"duplicate ID {r['id']} in {path}")
            records[r["id"]] = r
        return records


def load_split(split):
    gold = indexed(ROOT / "data" / f"{split}.jsonl")
    suites = indexed(ROOT / "data" / f"{split}_witnesses.jsonl.gz")
    if gold.keys() != suites.keys():
        raise ValueError(f"witness IDs disagree with {split} inputs")
    runs = {}
    for name, dirname in RUNS.items():
        raw = indexed(ROOT / "runs" / dirname / f"{split}.jsonl")
        if gold.keys() != raw.keys():
            raise ValueError(f"{name} IDs disagree with {split} inputs")
        runs[name] = {}
        for k, r in raw.items():
            original = r["metrics"]
            wrapped = None if original["format_success"] else rewrap(r["raw_output"])
            adjusted = original if wrapped is None else score(gold[k], wrapped, suites[k])
            runs[name][k] = {"strict": original, "adjusted": adjusted,
                             "rewrapped": wrapped is not None}
    return gold, runs


def summarize(ids, run):
    return {
        "n": len(ids),
        "rewrapped": sum(run[k]["rewrapped"] for k in ids),
        **{mode: {m: sum(run[k][mode][m] for k in ids) for m in METRICS}
           for mode in ("strict", "adjusted")},
    }


def matched(ids, left, right, gates):
    counts = {"both": 0, "left_only": 0, "right_only": 0, "neither": 0}
    for k in ids:
        a, b = left[k]["adjusted"], right[k]["adjusted"]
        if all(a[g] and b[g] for g in gates):
            outcome = {(1, 1): "both", (1, 0): "left_only",
                       (0, 1): "right_only", (0, 0): "neither"}[
                           a["schema_suite_pass"], b["schema_suite_pass"]]
            counts[outcome] += 1
    return {"n": sum(counts.values()), **counts}


def main():
    report = {}
    for split in ("test", "challenge"):
        gold, runs = load_split(split)
        groups = {t: [k for k, r in gold.items() if r["track"] == t]
                  for t in sorted({r["track"] for r in gold.values()})}
        if split == "test":
            groups["overall"] = list(gold)
        report[split] = {
            t: {m: summarize(ids, run) for m, run in runs.items()}
            for t, ids in groups.items()
        }
        if split == "test":
            gates = {"both_parseable": ["format_success"],
                     "both_rule_evaluable": ["schema_rule_evaluable"],
                     "both_profile_valid_and_data_exact": ["schema_validity", "data_accuracy"]}
            report["matched_test_requirements"] = {
                f"{a} vs {b}": {
                    g: matched(groups["requirements"], runs[a], runs[b], needed)
                    for g, needed in gates.items()
                } for a, b in combinations(RUNS, 2)
            }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
