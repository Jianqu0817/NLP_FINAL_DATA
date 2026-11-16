# NEW confirmation protocol — frozen before inference

Freeze date: 2026-11-13. Scope: new Chinese input requirements, reference labels and finite probe suites only. No checkpoint/service access and no NEW prediction inspection during construction. Dataset identity is the file names plus row IDs and deterministic generator; the generator aborts on any existing content difference.

## Question and design

Does the generated schema attach a changed count interval to the named array, rather than ignore it, impose it on another array, or rely on input phrasing/order? Nullable sensitivity is the positive control.

`confirm_original.jsonl`, `confirm_wording.jsonl`, `confirm_order.jsonl` each contain the same 24 pairs / 48 items: 16 `count_bounds` and 8 `nullable`. IDs are `confirm_count_01_a/b` through `confirm_count_16_a/b` and `confirm_nullable_01_a/b` through `confirm_nullable_08_a/b`. They differ from previous paired-study IDs. Named tasks and field keys are new; the 24 scenarios were checked against previous paired inputs, not against predictions.

- Both arms contain identical material facts and reference data. Exactly one rule sentence changes. All other instructions are identical across arms. A/B direction is balanced; it does not label strictness.
- Count pairs contain an anchor string, a focus string array and an unrestricted distractor string array. Focus appears first in half the field declarations and second in half. Eight pairs compare [2,4] with [1,3], eight compare [3,5] with [2,4], with direction counterbalanced. Reference length is respectively 2 or 3, inside both intervals. Probe lengths 0–6 test both boundaries, including two opposing-direction discriminating lengths. Distractor length 0 and 6 probes expose misplaced restrictions. Item types, requiredness, extras and non-fixed material values are controlled.
- Nullable pairs contain an anchor and two text fields. The focus changes between string-only and string-or-null while remaining required. The distractor has a fixed nullable rule, allowed in four pairs and disallowed in four. Missing focus is always invalid. Focus null is the sole discriminating probe.
- `wording` rewrites each semantic block while retaining its position, field keys, facts, intervals, output contract and total number of blocks. It adds no condition-specific instruction. `order` uses the exact original sentences, with permutation [0,3,2,1,4,5,6]: task, facts, target rule, field definitions, common requirements, no-extra-restrictions clause, output clause. Fields are explicit wherever rules occur; no pronouns require the original order. These are separate manipulations, not a combined paraphrase-and-reorder treatment.

Each row includes `focus_field`, `distractor_field`, `expected_min`, `expected_max`, `expected_nullable`, and `input_sentences` for machine audits. Count bounds are numeric. Nullable expected bounds are JSON null. Metadata is not appended to the model input. Labels are produced and checked with full `Draft202012Validator`, not inferred from a generated schema or restricted keyword coverage. Reference schemas also satisfy the prior scorer's profile.

## Frozen outcomes and denominators

Score all three variants independently with the original paired scorer and a full-Draft semantic pass. Preserve original wrapper scoring as strict and report diagnostic wrapping separately. Never silently mix wrapper-repaired and strict results. A syntactically parsed valid full-Draft schema is rule-evaluable for the full-Draft pass; wrapper failure, invalid schema and missing prediction are explicit failures. The restricted-profile rate remains a separate compatibility outcome.

Primary count-rule outcome: discriminating probes **both-correct** in the required direction, aggregated per model and variant. The unconditional denominator is all 32 count discriminating probe pairs (16 pairs × 2); missing/unevaluable arms receive zero. Report both-arm complete-suite success over all 16 pairs as a co-primary completeness outcome. Also report the conditional both-correct fraction only among discriminating probe pairs with both arms full-Draft-evaluable, always with numerator and actual denominator; it cannot replace the unconditional result. Nullable positive control uses all 8 discriminating probe pairs, with the corresponding conditional denominator and all 8 complete-suite pairs. A predicted flip alone is secondary because it can be in the wrong direction.

Placement diagnostic for count rows: whether both exact expected minItems/maxItems are directly attached to `properties[focus_field]`, and whether either bound is spuriously attached to `properties[distractor_field]`. Report exact-target rate over all 32 count items and separately over full-Draft-evaluable count items; failures receive zero in the unconditional rate. These are structural diagnostics: equivalent allOf/ref formulations can be semantically correct without direct placement, so full-Draft probe behavior is primary. Report missing, misplaced, wrong-valued and correctly placed bounds separately when possible.

Wording/order robustness: same-ID changes relative to original on the same frozen pairs. Use all 16 count / 8 nullable pairs for unconditional differences, and explicitly report intersections of evaluable pairs for conditional differences. Report sample counts and raw paired successes; treat this small synthetic set descriptively, not as a broad generalization estimate. Full probes, generated schemas and raw outputs remain retrievable. No test wording, reference label or probe may change after NEW outputs are inspected; corrections require a separately named version and reason.

## Reproduction and pre-inference acceptance

From the repository root:

```powershell
python mechanism_study/build_confirmation.py
python -m unittest discover -s mechanism_study -p test_confirmation.py -v
```

Tests establish the shared paired input contract, full-Draft labels, identical material data and probe instances across arms, single-sentence/single-field rule changes, exact order-only permutation, aligned semantics across variants, novel keys/tasks/IDs, balanced directions/field positions, and behavioral exposure of swapped-array bounds. Chinese scenarios and the paraphrase blocks are model-authored synthetic material; automated checks do not substitute for independent human annotation.
