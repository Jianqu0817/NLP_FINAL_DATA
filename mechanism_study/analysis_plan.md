# Frozen local analysis plan

Recorded 2026-11-13 before mechanism predictions were inspected. Scoring implementation and synthetic tests are committed as local files (this workspace has no Git repository).

## Inputs and exclusions

Five datasets: old_original (`paired_study/pairs.jsonl`), old_paraphrase (`paired_study/paraphrases.jsonl`), and confirm_original/confirm_wording/confirm_order. Conditions Base, A, B, C, D, E. Original old Base/A/C predictions are read directly from paired_study base_zero/adapter/lora files; they are never regenerated here. Other files are `mechanism_study/predictions/<dataset>/<condition>.jsonl`. No weights or remote access.

## Fixed endpoints

- Co-primary: discriminating probes both-correct in the required direction, and both arms pass **every** positive and negative probe under executable Draft 2020-12 semantics. For each NEW variant, count denominators are 32 discriminating probe pairs and 16 complete-suite pairs; nullable denominators are 8 and 8. Retain all pairs in unconditional denominators, including missing, malformed, or truncated predictions. Also show conditional both-correct numerator/denominator restricted to both-arm Draft-evaluable pairs. Require positive/invariant controls as well as changed-probe direction. Reuse semantic_probe's no-reference domain and explicit wrong-dialect rejection.
- Secondary: both-arm project-profile suite pass (project schema validity AND all probes), original strict joint success, both-arm format/data accuracy, changed-probe both-correct and all invariant probes correct. Do not substitute a flip for a correct decision.
- Strict wrapper and symmetric two-bare-object diagnostic are scored separately. Strict wrapper is the main view; diagnostic identifies wrapper-mediated changes.
- Structural count-bounds evidence: exact minItems/maxItems at declared target array; exact numbers only at root; wrong/missing otherwise. Also retain root/target/distractor values independently. These literal labels do not replace executed probes or credit semantically equivalent compositions as direct placement.
- Report exact-target placement over all count items and over Draft-evaluable count items separately; root/distractor any-bound and target-missing-bound counts remain explicit. Pair-level contrast and cross-variant output includes common evaluability intersections.
- Truncation uses only explicit metadata. Report item and pair counts; do not remove truncated cases.

## Matched comparisons

Report pair-level retained pass, lost pass, gained pass, and retained failure with their IDs; loss denominator is left-condition passes, gain denominator left-condition failures. Main ablations A:B, B:D, D:E; include A:C (LoRA), Base:A and Base:C. Show family strata. Base failure is a damaged baseline, not evidence of lost Base ability.

Across aligned wording/order variants, use the same pair IDs and the common Base-stable subset: Base passes all compared variants. Count condition pass loss on that subset and its all-variant intersection; separately show gains on Base-damaged pairs. No denominator formed by pooling variants as independent samples. Show all-pair cross-variant condition stability as well. Keep IDs and complete per-pair rows in machine-readable outputs; short examples in summary.

## Validation and finalization

Synthetic fixtures cover correct array bounds, correct numbers at wrong root, wrong numbers, wrapper-only rescue, unsupported project keywords with valid Draft meaning, missing/truncated outputs, transition denominators and common-subset wording stability. Validate reference schemas/probes before predictions. Reject unknown or duplicate prediction IDs. In-progress output explicitly lists unavailable files; final `--require-complete` requires all 30 files and all dataset IDs. Output is numerical evidence, not a prose interpretation of intervention causality.
