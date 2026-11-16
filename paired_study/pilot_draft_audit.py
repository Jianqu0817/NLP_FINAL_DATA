"""Compare original pilot witnesses under the project profile and Draft 2020-12."""
from collections import Counter
from itertools import combinations
import json
from pathlib import Path

import pilot_audit as pilot
from semantic_probe import restrictions, original

HERE = Path(__file__).resolve().parent


def score(row, prediction, suite):
    metrics = prediction["metrics"]
    text = prediction["raw_output"]
    if not metrics["format_success"]:
        text = pilot.rewrap(text)
        if text is not None:
            metrics = original.score(row, text, suite)
    prior = metrics["schema_suite_pass"]
    before = metrics["schema_rule_evaluable"]
    if before or text is None:
        return dict(profile=prior, draft=prior, profile_evaluable=before,
                    draft_evaluable=before, keywords=[], status="reused" if before else "format")
    schema, _ = original.pair(text)
    restrictions_ = restrictions(schema)
    keywords = sorted({r["keyword"] for r in restrictions_["outside_project_keywords"]})
    result = dict(profile=prior, draft=0, profile_evaluable=0, draft_evaluable=0,
                  keywords=keywords)
    if "$schema" in schema and schema["$schema"] != original.DIALECT:
        return dict(result, status="wrong_dialect")
    if restrictions_["references"]:
        return dict(result, status="reference")
    if not metrics["schema_meta_validity"]:
        return dict(result, status="meta_invalid")
    validator = original.Draft202012Validator(schema, format_checker=original.CHECKER)
    passes = all(validator.is_valid(w["instance"]) for w in suite["positive"]) and all(
        not validator.is_valid(w["instance"]) for w in suite["negative"])
    return dict(result, draft=int(passes), draft_evaluable=1, status="newly_evaluable")


def summarize(ids, run):
    rescued = [k for k in ids if run[k]["draft"] and not run[k]["profile"]]
    return {**{m: sum(run[k][m] for k in ids)
               for m in ("profile", "draft", "profile_evaluable", "draft_evaluable")},
            "status": dict(Counter(run[k]["status"] for k in ids)),
            "rescued_keyword_sets": dict(Counter(", ".join(run[k]["keywords"]) or "(none)"
                                                for k in rescued)),
            "rescued_ids": rescued}


def paired(ids, left, right):
    outcomes = {(1, 1): "both", (0, 1): "right_only", (1, 0): "left_only", (0, 0): "neither"}
    counts = dict.fromkeys(outcomes.values(), 0)
    for k in ids:
        counts[outcomes[left[k]["draft"], right[k]["draft"]]] += 1
    return {"n": len(ids), **counts}


def run():
    report = {}
    for split in ("test", "challenge"):
        gold = pilot.indexed(pilot.ROOT / "data" / f"{split}.jsonl")
        suites = pilot.indexed(pilot.ROOT / "data" / f"{split}_witnesses.jsonl.gz")
        paths = {m: pilot.ROOT / "runs" / path / f"{split}.jsonl"
                 for m, path in pilot.RUNS.items()}
        demo = HERE / "original_control" / f"{split}_base_demo.jsonl"
        if demo.is_file():
            paths["Base + example"] = demo
        runs = {}
        for condition, path in paths.items():
            raw = pilot.indexed(path)
            if raw.keys() != gold.keys() or suites.keys() != gold.keys():
                raise ValueError(f"inputs, predictions and witnesses must match: {path}")
            runs[condition] = {k: score(r, raw[k], suites[k]) for k, r in gold.items()}
        for track in sorted({r["track"] for r in gold.values()}):
            ids = [k for k, r in gold.items() if r["track"] == track]
            paired_results = {}
            for a, b in combinations(runs, 2):
                common = [k for k in ids if runs[a][k]["draft_evaluable"]
                          and runs[b][k]["draft_evaluable"]]
                paired_results[f"{a} vs {b}"] = {
                    "all": paired(ids, runs[a], runs[b]),
                    "both_draft_evaluable": paired(common, runs[a], runs[b]),
                }
            report[f"{split}/{track}"] = {"n": len(ids),
                                          "counts": {m: summarize(ids, r) for m, r in runs.items()},
                                          "paired_draft": paired_results}
    return report


if __name__ == "__main__":
    (HERE / "pilot_draft_audit.json").write_text(
        json.dumps(run(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
