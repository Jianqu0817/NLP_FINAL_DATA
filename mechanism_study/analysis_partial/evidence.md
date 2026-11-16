# Mechanism numerical evidence

Complete inputs: False.

| Dataset | Condition | Family | Draft full suite | Changed both-correct | Conditional changed | Profile suite | Strict joint | Format | Data | Truncated pairs |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| old_original | Base | all | 18/48 | 41/72 | 41/62 | 14/48 | 14/48 | 48/48 | 48/48 | 0 |
| old_original | Base | count_bounds | 10/12 | 20/24 | 20/20 | 10/12 | 10/12 | 12/12 | 12/12 | 0 |
| old_original | Base | nullable | 0/12 | 0/12 | 0/10 | 0/12 | 0/12 | 12/12 | 12/12 | 0 |
| old_original | A | all | 36/48 | 48/72 | 48/68 | 36/48 | 36/48 | 46/48 | 46/48 | 0 |
| old_original | A | count_bounds | 12/12 | 24/24 | 24/24 | 12/12 | 12/12 | 12/12 | 12/12 | 0 |
| old_original | A | nullable | 12/12 | 12/12 | 12/12 | 12/12 | 12/12 | 12/12 | 12/12 | 0 |
| old_original | C | all | 32/48 | 45/72 | 45/68 | 32/48 | 32/48 | 46/48 | 46/48 | 0 |
| old_original | C | count_bounds | 10/12 | 21/24 | 21/24 | 10/12 | 10/12 | 12/12 | 12/12 | 0 |
| old_original | C | nullable | 12/12 | 12/12 | 12/12 | 12/12 | 12/12 | 12/12 | 12/12 | 0 |
| old_paraphrase | Base | all | 14/48 | 32/72 | 32/68 | 14/48 | 14/48 | 48/48 | 38/48 | 0 |
| old_paraphrase | Base | count_bounds | 12/12 | 24/24 | 24/24 | 12/12 | 12/12 | 12/12 | 12/12 | 0 |
| old_paraphrase | Base | nullable | 0/12 | 0/12 | 0/11 | 0/12 | 0/12 | 12/12 | 12/12 | 0 |
| old_paraphrase | A | all | 23/48 | 28/72 | 28/68 | 23/48 | 23/48 | 46/48 | 39/48 | 1 |
| old_paraphrase | A | count_bounds | 1/12 | 4/24 | 4/24 | 1/12 | 1/12 | 12/12 | 11/12 | 0 |
| old_paraphrase | A | nullable | 10/12 | 11/12 | 11/12 | 10/12 | 10/12 | 12/12 | 12/12 | 0 |
| old_paraphrase | C | all | 25/48 | 37/72 | 37/70 | 25/48 | 22/48 | 47/48 | 35/48 | 0 |
| old_paraphrase | C | count_bounds | 6/12 | 15/24 | 15/24 | 6/12 | 6/12 | 12/12 | 12/12 | 0 |
| old_paraphrase | C | nullable | 10/12 | 10/12 | 10/12 | 10/12 | 10/12 | 12/12 | 12/12 | 0 |

## Paired strict Draft full-suite contrasts

| Dataset | Contrast | Family | Left pass | Right pass | Loss / left pass | Gain / left fail | Lost IDs (up to 4) | Gained IDs (up to 4) |
|---|---|---|---:|---:|---:|---:|---|---|
| old_original | A:C | all | 36 | 32 | 4/36 | 0/12 | count_bounds_04, count_bounds_10, required_optional_04, required_optional_02 |  |
| old_original | A:C | count_bounds | 12 | 10 | 2/12 | 0/0 | count_bounds_04, count_bounds_10 |  |
| old_original | A:C | nullable | 12 | 12 | 0/12 | 0/0 |  |  |
| old_original | Base:A | all | 18 | 36 | 3/18 | 21/30 | conditional_dependency_09, conditional_dependency_01, conditional_dependency_11 | count_bounds_02, nullable_01, required_optional_03, count_bounds_12 |
| old_original | Base:A | count_bounds | 10 | 12 | 0/10 | 2/2 |  | count_bounds_02, count_bounds_12 |
| old_original | Base:A | nullable | 0 | 12 | 0/0 | 12/12 |  | nullable_01, nullable_10, nullable_05, nullable_12 |
| old_original | Base:C | all | 18 | 32 | 6/18 | 20/30 | count_bounds_04, conditional_dependency_09, conditional_dependency_01, count_bounds_10 | count_bounds_02, nullable_01, required_optional_03, count_bounds_12 |
| old_original | Base:C | count_bounds | 10 | 10 | 2/10 | 2/2 | count_bounds_04, count_bounds_10 | count_bounds_02, count_bounds_12 |
| old_original | Base:C | nullable | 0 | 12 | 0/0 | 12/12 |  | nullable_01, nullable_10, nullable_05, nullable_12 |
| old_paraphrase | A:C | all | 23 | 25 | 5/23 | 7/25 | nullable_12, required_optional_10, required_optional_12, nullable_11 | count_bounds_02, count_bounds_09, count_bounds_06, count_bounds_11 |
| old_paraphrase | A:C | count_bounds | 1 | 6 | 0/1 | 5/11 |  | count_bounds_02, count_bounds_09, count_bounds_06, count_bounds_11 |
| old_paraphrase | A:C | nullable | 10 | 10 | 2/10 | 2/2 | nullable_12, nullable_11 | nullable_05, nullable_04 |
| old_paraphrase | Base:A | all | 14 | 23 | 11/14 | 20/34 | count_bounds_02, count_bounds_08, count_bounds_04, count_bounds_09 | nullable_01, required_optional_03, required_optional_11, nullable_10 |
| old_paraphrase | Base:A | count_bounds | 12 | 1 | 11/12 | 0/0 | count_bounds_02, count_bounds_08, count_bounds_04, count_bounds_09 |  |
| old_paraphrase | Base:A | nullable | 0 | 10 | 0/0 | 10/12 |  | nullable_01, nullable_10, nullable_12, nullable_06 |
| old_paraphrase | Base:C | all | 14 | 25 | 6/14 | 17/34 | count_bounds_08, count_bounds_04, count_bounds_03, count_bounds_10 | nullable_01, required_optional_03, required_optional_11, nullable_10 |
| old_paraphrase | Base:C | count_bounds | 12 | 6 | 6/12 | 0/0 | count_bounds_08, count_bounds_04, count_bounds_03, count_bounds_10 |  |
| old_paraphrase | Base:C | nullable | 0 | 10 | 0/0 | 10/12 |  | nullable_01, nullable_10, nullable_05, nullable_06 |

## Strict count-bound placement (items)

| Dataset | Condition | Exact target / all | Exact target / evaluable | Root-only exact numbers | Root any bound | Distractor any bound | Target missing bound |
|---|---|---:|---:|---:|---:|---:|---:|
| old_original | Base | 24/24 | 22/22 | 0 | 0 | 0 | 0 |
| old_original | A | 24/24 | 24/24 | 0 | 0 | 0 | 0 |
| old_original | C | 21/24 | 21/24 | 3 | 3 | 0 | 3 |
| old_paraphrase | Base | 24/24 | 24/24 | 0 | 0 | 0 | 0 |
| old_paraphrase | A | 2/24 | 2/24 | 22 | 22 | 0 | 22 |
| old_paraphrase | C | 15/24 | 15/24 | 9 | 12 | 0 | 9 |

## Strict cross-variant Draft full-suite stability

| Variants | Condition | Family | Common pairs | Base-stable pairs | All-variant pass / Base-stable | All-variant pass / all | Losses on Base-stable by variant |
|---|---|---|---:|---:|---:|---:|---|
| old_original, old_paraphrase | Base | all | 48 | 12 | 12/12 | 12/48 | old_original: 0/12; old_paraphrase: 0/12 |
| old_original, old_paraphrase | A | all | 48 | 12 | 2/12 | 23/48 | old_original: 0/12; old_paraphrase: 10/12 |
| old_original, old_paraphrase | C | all | 48 | 12 | 6/12 | 24/48 | old_original: 2/12; old_paraphrase: 6/12 |
| old_original, old_paraphrase | Base | count_bounds | 12 | 10 | 10/10 | 10/12 | old_original: 0/10; old_paraphrase: 0/10 |
| old_original, old_paraphrase | A | count_bounds | 12 | 10 | 0/10 | 1/12 | old_original: 0/10; old_paraphrase: 10/10 |
| old_original, old_paraphrase | C | count_bounds | 12 | 10 | 4/10 | 6/12 | old_original: 2/10; old_paraphrase: 6/10 |
| old_original, old_paraphrase | Base | nullable | 12 | 0 | 0/0 | 0/12 | old_original: 0/0; old_paraphrase: 0/0 |
| old_original, old_paraphrase | A | nullable | 12 | 0 | 0/0 | 10/12 | old_original: 0/0; old_paraphrase: 0/0 |
| old_original, old_paraphrase | C | nullable | 12 | 0 | 0/0 | 10/12 | old_original: 0/0; old_paraphrase: 0/0 |

## Unavailable inputs

- D:\DS_workspace\NLP_FINAL\mechanism_study\predictions\old_original\B.jsonl
- D:\DS_workspace\NLP_FINAL\mechanism_study\predictions\old_original\D.jsonl
- D:\DS_workspace\NLP_FINAL\mechanism_study\predictions\old_original\E.jsonl
- D:\DS_workspace\NLP_FINAL\mechanism_study\predictions\old_paraphrase\B.jsonl
- D:\DS_workspace\NLP_FINAL\mechanism_study\predictions\old_paraphrase\D.jsonl
- D:\DS_workspace\NLP_FINAL\mechanism_study\predictions\old_paraphrase\E.jsonl
- D:\DS_workspace\NLP_FINAL\mechanism_study\predictions\confirm_original\Base.jsonl
- D:\DS_workspace\NLP_FINAL\mechanism_study\predictions\confirm_original\A.jsonl
- D:\DS_workspace\NLP_FINAL\mechanism_study\predictions\confirm_original\B.jsonl
- D:\DS_workspace\NLP_FINAL\mechanism_study\predictions\confirm_original\C.jsonl
- D:\DS_workspace\NLP_FINAL\mechanism_study\predictions\confirm_original\D.jsonl
- D:\DS_workspace\NLP_FINAL\mechanism_study\predictions\confirm_original\E.jsonl
- D:\DS_workspace\NLP_FINAL\mechanism_study\predictions\confirm_wording\Base.jsonl
- D:\DS_workspace\NLP_FINAL\mechanism_study\predictions\confirm_wording\A.jsonl
- D:\DS_workspace\NLP_FINAL\mechanism_study\predictions\confirm_wording\B.jsonl
- D:\DS_workspace\NLP_FINAL\mechanism_study\predictions\confirm_wording\C.jsonl
- D:\DS_workspace\NLP_FINAL\mechanism_study\predictions\confirm_wording\D.jsonl
- D:\DS_workspace\NLP_FINAL\mechanism_study\predictions\confirm_wording\E.jsonl
- D:\DS_workspace\NLP_FINAL\mechanism_study\predictions\confirm_order\Base.jsonl
- D:\DS_workspace\NLP_FINAL\mechanism_study\predictions\confirm_order\A.jsonl
- D:\DS_workspace\NLP_FINAL\mechanism_study\predictions\confirm_order\B.jsonl
- D:\DS_workspace\NLP_FINAL\mechanism_study\predictions\confirm_order\C.jsonl
- D:\DS_workspace\NLP_FINAL\mechanism_study\predictions\confirm_order\D.jsonl
- D:\DS_workspace\NLP_FINAL\mechanism_study\predictions\confirm_order\E.jsonl

Diagnostic-wrapper results, all family strata, all IDs and conditional evaluability intersections: summary.json, pairs.jsonl, contrasts.jsonl, cross_variants.jsonl.
