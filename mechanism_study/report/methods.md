# Adapter Mechanism Ablations for Chinese JSON Schema Generation

## Study question

This supplement examines whether a model's response to a changed schema rule depends on adapter nonlinearity, bottleneck width, or insertion site. The task is to generate a JSON object containing a JSON Schema and concrete data from Chinese requirements. A correct rule change must alter the schema's behavior in the requested direction while preserving the unchanged requirements and the material data.

The study combines controlled architectural ablations with paired behavioral probes. Each probe pair keeps the task and data fixed and changes one rule sentence. The original paired set provides continuity with the preceding report; a separately constructed confirmation set tests count-bound placement and sensitivity to wording and instruction order.

## Architectural interventions

Let h be a decoder hidden state, D the down projection, U the up projection, and b_D and b_U their biases. The historical adapter A applies

`T_A(h) = h + U SiLU(Dh + b_D) + b_U`.

The new variants use the affine residual transformation

`T_linear(h) = h + U(Dh + b_D) + b_U`.

Adapter computations and parameters use FP32; the resulting hidden state is cast back to the incoming activation dtype. These equations describe the module before that final cast. The factorized affine update has rank at most its bottleneck width in its linear component. Its factorization, optimization path, biases, and insertion site remain part of the intervention.

| Condition | Adaptation | Width | Insertion site |
|---|---|---:|---|
| Base | Frozen original model | - | - |
| A | SiLU bottleneck residual | 64 | After every complete decoder block |
| B | Affine bottleneck residual | 64 | After every complete decoder block |
| C | LoRA, rank 16, alpha 32 | - | Attention q/k/v/o projections |
| D | Affine bottleneck residual | 16 | After every complete decoder block |
| E | Affine bottleneck residual | 16 | After attention residual addition, before the MLP |

A, B, D, and E retain both projection biases and install one module in each of 36 decoder blocks. For hidden size H and bottleneck width w, their trainable parameter count is `36(2Hw + H + w)`, with H = 2560. C uses the historical attention-projection LoRA configuration, with no trainable projection biases and zero LoRA dropout. C is a reference adaptation method; A versus C changes several architectural properties together.

### The insertion-site contrast changes both paths

For E, let r denote the sum of a block's incoming residual and attention output. The second half of the block computes

`z = T_linear(r)`

`output = z + MLP(post_attention_layernorm(z))`.

Thus the intervention enters both the carried residual and the MLP input. The implementation updates the tensor shared by those two paths before the post-attention layer normalization. It clones the adapter input before the in-place update so that backward can use the unmodified saved input. This differs from a hook that merely returns a replacement layer-normalization input, which leaves the carried residual unchanged.

The structural test compares this hook with the explicit equations above at nonzero adapter weights. Forward outputs, input gradients, and every adapter-parameter gradient agree exactly in FP32 and BF16, with and without non-reentrant gradient checkpointing. These are implementation checks on a small decoder stand-in with the verified Qwen3 residual ordering; actual-model smoke records are separate runtime evidence.

## Matched training and checkpoint selection

The backbone is Qwen/Qwen3-4B-Instruct-2507 at revision `cdbee75f17c01a7cc42f958dc650907174af0554`. Training uses the original local snapshot, a frozen BF16 backbone, SDPA attention, and FP32 trainable modules. New training calls the unchanged `scripts/experiment.py:train` function. Historical A and C checkpoints are retained rather than retrained for this supplement.

The shared training specification is seed 42, three epochs, learning rate 1e-4, AdamW with weight decay 0.01, one example per forward pass, and gradient accumulation over 16 examples. Each epoch shuffles the same training indices with `random.Random(42 + epoch)`. The final incomplete accumulation group is normalized by its actual size. Gradients are clipped at norm 1.0. The cosine schedule uses warmup for the ceiling of 5% of all optimizer steps. The maximum training length is 4096 tokens; the encoder raises an error for an overlong example instead of truncating its target. Only assistant target tokens contribute to the loss.

The training split contains 2300 examples. All 339 validation examples are decoded after each epoch. The selected checkpoint maximizes the lexicographic tuple `(joint_success, data_accuracy, balanced_rule_score, self_consistency)`. An exact tie retains the earlier selected epoch. Final inference loads `best.pt`, not automatically the last epoch. No confirmation or old paired input participates in checkpoint selection.

Initialization follows the historical constructor sequence: down weights are drawn from a zero-mean normal distribution with standard deviation 0.02; down bias, up weights, and up bias are zero. A and B have identical initial parameter tensors under the same seed; D and E likewise match. B and D have different tensor shapes, so their width contrast does not provide elementwise-matched initialization. All residual modules initially act as the identity. The training loop rejects an unexpected trainable parameter count, nonfinite loss, and invalid or zero aggregate trainable gradients, and checks frozen-weight probes after every epoch.

## Paired data and confirmation design

The old original and paraphrased sets each contain 48 aligned pairs, or 96 items. Existing Base, A, and C predictions are reused for these sets. New B, D, and E predictions use the same inputs and generation procedure.

The confirmation set contains 24 pairs, or 48 items, in each of three aligned versions: original wording, rewritten wording, and reordered instructions. Sixteen pairs test count bounds; eight test nullable sensitivity as a positive control. Tasks, field keys, and pair IDs are new relative to the old paired set. The confirmation protocol, reference labels, probe suites, and analysis plan were recorded before inspecting its model predictions.

In count pairs, an anchor string, a named focus array, and an unrestricted distractor array appear in both arms. Only the focus array's interval changes. Eight pairs compare [2,4] with [1,3]; eight compare [3,5] with [2,4]. Direction is counterbalanced, and the focus array appears first in half the field declarations and second in half. Reference data have a length accepted under both arms. Probes of lengths 0 through 6 test the interval boundaries, including two lengths with opposite required directions of change. Distractor lengths 0 and 6 expose restrictions applied to the wrong array. Other probes control item type, requiredness, additional fields, and unwanted constraints on material values.

In nullable pairs, the required focus field changes between string-only and string-or-null. The distractor has a fixed nullable rule, allowed in four pairs and disallowed in four. A missing focus field remains invalid in both arms. Focus-null acceptance is the discriminating probe.

The wording version rewrites semantic blocks without changing their positions, facts, field keys, intervals, or output contract. The order version uses the exact original sentences with permutation [0,3,2,1,4,5,6]. Wording and order therefore form separate manipulations. Probe labels are checked with a full Draft 2020-12 validator. The Chinese scenarios and rewrites are model-authored synthetic materials.

## Generation and behavioral scoring

All new predictions use the original system prompt, chat template, evaluator, and greedy decoder: evaluation batch size 16, a 2048-token output cap, repetition penalty 1.0, and no demonstrations. Strict scoring requires the requested single wrapper object with `schema` and `data`. A separate diagnostic admits two bare objects when they can be wrapped symmetrically; diagnostic results remain distinct from the strict primary view.

The confirmation count endpoints are the number of discriminating probe pairs for which both arms are correct, over all 32 such comparisons, and the number of complete-schema probe-suite successes in both arms, over all 16 count pairs. Nullable endpoints use the corresponding denominators of 8 discriminating comparisons and 8 complete-suite pairs. A changed prediction is correct only if it changes in the required direction. Complete-suite success also requires the invariant positive and negative probes to pass. Missing, malformed, or truncated outputs remain in the unconditional denominators and receive no credit for an unevaluable schema.

The conditional discriminating-probe rate is reported with its numerator and actual denominator among comparisons with both arms full-Draft-evaluable. This separates rule decisions from inability to produce an evaluable schema while retaining the unconditional result. The original restricted-project schema validity and suite rates remain compatibility outcomes alongside full-Draft executable behavior. Format success, data accuracy, and strict joint success are reported separately.

Count-bound placement is a structural diagnostic. It records direct `minItems` and `maxItems` values at the focus array, at the root, and at the distractor array. Exact target placement is reported over all 32 count items and over evaluable count items. Equivalent schema compositions can pass the executable probes without directly placing the two keywords at the focus node, so direct placement and semantic success answer different questions.

## Pre-specified contrasts and interpretation

| Contrast | Changed factor | Interpretation within this experiment |
|---|---|---|
| A to B | SiLU removed; same width and post-block site | Effect of the adapter nonlinearity under matched parameter budget and initialization |
| B to D | Width 64 to 16; affine post-block modules | Effect of narrowing the affine bottleneck under the shared training recipe |
| D to E | Post-block to post-attention residual site; affine width 16 | Effect of the insertion site, with matched parameter tensors at initialization |
| A to C | Bottleneck adapter to attention LoRA | Reference comparison between adaptation configurations |
| Base to A; Base to C | Frozen model to historical adaptation | Retention, loss, and acquisition relative to the original model |

Each contrast records retained passes, lost passes, gained passes, and retained failures on the same pair IDs. The loss denominator is the left condition's passing pairs; the gain denominator is its failing pairs. Family-level results distinguish count-bound behavior from nullable sensitivity and the other old-set families.

For wording and order, the Base-stable subset contains only pair IDs that Base passes in every compared version. Adapted-model losses on this common subset measure loss of an observed stable baseline behavior. Gains on Base-failing cases are presented separately. All-pair cross-version success also shows condition stability without conditioning on Base. The aligned versions are repeated measurements of the same pairs, not independent samples to be pooled into a larger denominator.

The contrasts characterize this single-seed, synthetic-task configuration. Shared optimization and paired inputs sharpen comparisons between these trained models; independent seeds would be needed to estimate variation in an architectural effect across training runs.

## Reproducible source record

The frozen training and evaluation behavior is defined in `scripts/experiment.py`. Variant construction and runtime entry points are in `mechanism_study/train_variant.py`; the local structural test is `mechanism_study/test_variant_structure.py`. Input construction is recorded in `mechanism_study/CONFIRM_PROTOCOL.md` and `build_confirmation.py`. The pre-prediction scoring plan is `mechanism_study/analysis_plan.md`, and scoring is implemented in `mechanism_study/score_mechanism.py` with the original paired and full-Draft semantic scorers. Raw predictions, pair IDs, transitions, truncation flags, and generated schemas remain the retrievable evidence for the eventual result tables.
