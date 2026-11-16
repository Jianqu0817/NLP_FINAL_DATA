# Where Adapter Changes Help - and Where They Do Not

CISC7021 | Mechanism results supplement | 13 November 2026

## Main finding

Adapter width and insertion site change different parts of schema behavior. Narrowing an affine post-block adapter preserves the old count-rule behavior across wording, but introduces frequent restrictions on a new unrestricted distractor array. Moving that narrow adapter to the post-attention residual reduces these extra restrictions and improves complete-suite success, without improving its already strong response to the changed count interval.

The new confirmation set separates a correct response to the changed rule from correct behavior on all unchanged rules. For original wording, D and E each score 30/32 changed-probe comparisons; complete-suite success rises from D's 3/16 pairs to E's 8/16. Thus this site contrast mainly improves broader constraint fidelity in the measured examples, rather than sensitivity to the manipulated interval itself.

Removing SiLU also changes the outcome: on reordered confirmation inputs, A places the correct interval only at the object root in 5/32 items, while B has zero such cases. Yet B remains below A on complete-suite success in all three confirmation versions. An improvement in one error type is not an overall win.

## Six conditions, three controlled contrasts

| Condition | Module and site | Trainable parameters | Best epoch |
|---|---|---:|---:|
| Base | Frozen backbone | 0 | - |
| A | SiLU, width 64, post-block | 11,890,944 | 1 |
| B | Affine, width 64, post-block | 11,890,944 | 3 |
| C | Attention q/k/v/o LoRA, rank 16 | 11,796,480 | 2 |
| D | Affine, width 16, post-block | 3,041,856 | 3 |
| E | Affine, width 16, post-attention residual | 3,041,856 | 2 |

The pre-specified architecture comparisons are A to B (activation), B to D (width), and D to E (site). A to C is a reference comparison between adaptation configurations. All results below use the validation-selected checkpoints, strict wrapper scoring, and full Draft 2020-12 executable schema probes unless stated otherwise.

\pagebreak

## 1. Matched training and the exact intervention

The frozen backbone is Qwen/Qwen3-4B-Instruct-2507, revision `cdbee75f17c01a7cc42f958dc650907174af0554`. Historical A/C and new B/D/E records report NVIDIA L40S and PyTorch 2.7.1+cu128. The backbone uses BF16 and SDPA; trainable adapter parameters and computations use FP32 with outputs cast back to the incoming activation dtype.

A applies `h + U SiLU(Dh + b_D) + b_U`. B/D/E apply `h + U(Dh + b_D) + b_U`. Both projections retain their biases. The linear part of the factorized affine update has rank at most the bottleneck width. It is still trained as two factors inside a nonlinear decoder.

New runs call the unchanged original training loop. All runs share seed 42, 2300 training examples, three epochs, AdamW, LR 1e-4, weight decay 0.01, microbatch size 1, accumulation 16, norm clipping at 1.0, cosine decay, and ceiling-rounded 5% warmup. Each epoch uses `random.Random(42 + epoch)` for its sample order. Incomplete accumulation groups use their actual size. Training targets over 4096 tokens raise an error; only assistant target tokens contribute to loss.

All 339 validation examples are decoded after every epoch. Checkpoint selection maximizes the tuple `(joint_success, data_accuracy, balanced_rule_score, self_consistency)`; an exact tie retains the earlier checkpoint. A/C select epochs 1/2 and B/D/E select 3/3/2. These different selected epochs follow the shared policy, rather than a fixed-epoch comparison. Paired tests never select weights. All five training statuses report completed three-epoch runs and passed frozen-weight probes.

The down projection starts with normal weights of standard deviation 0.02; its bias and the up projection are zero. Constructor order and seed match initial tensors for A/B and for D/E. B/D have different shapes and are not elementwise initialization matches. All residual modules initially act as the identity.

Greedy decoding uses the original system prompt and chat template, batch size 16, a 2048-token cap, repetition penalty 1.0, and no demonstration. Strict scoring requires one wrapper object containing schema and data. All 30 dataset-condition sources are complete. The symmetric two-bare-object wrapper diagnostic changes no complete-suite counts in this mechanism study. No confirmation output is truncated.

### E modifies both residual and MLP input

If r is the sum of the incoming block residual and attention output, E computes `z = T_linear(r)` and then `output = z + MLP(post_attention_layernorm(z))`. D instead applies its adapter after the complete block. E updates the tensor shared by the carried residual and the normalization input, cloning the adapter input before that update for safe backward. Returning a new normalization input alone would miss the carried residual.

Local structural tests match E to these explicit equations exactly for outputs, input gradients, and every adapter gradient in FP32/BF16, with/without non-reentrant checkpointing. These small-module implementation checks supplement the actual-model smoke and completed training records; they are not task-performance measurements.

\pagebreak

## 2. Confirmation data and primary outcomes

Each confirmation version has the same 24 pairs: 16 count-bound pairs and 8 nullable controls. Each pair changes exactly one rule sentence while keeping material facts and reference data fixed. Count tasks include a named focus array and an unrestricted distractor array. Intervals compare [2,4] with [1,3], or [3,5] with [2,4], with balanced direction and field order. Reference lengths satisfy both arms. Probes test focus lengths 0-6 and distractor lengths 0 and 6, alongside requiredness, type, extra-field and material-value controls.

Wording rewrites semantic blocks in place. Order permutes the exact original sentences. They are separate manipulations. The protocol, labels and analysis plan were frozen before prediction inspection. New tasks/keys/IDs differ from the old set; materials are model-authored synthetic examples.

**Co-primary outcomes:** changed-probe correctness requires both arms to make the right decision, over all 32 discriminating comparisons. Complete-suite success requires both arms to pass every positive and negative probe, over all 16 count pairs. Conditional changed correctness retains only comparisons with both arms full-Draft-evaluable; its actual denominator is shown. Missing, malformed and truncated outputs remain failures in unconditional denominators.

| Version | Model | Suite pairs | Changed / all | Changed / evaluable |
| --- | --- | --- | --- | --- |
| Original | Base | 2/16 | 14/32 | 14/16 |
| Original | A | 9/16 | 29/32 | 29/32 |
| Original | B | 8/16 | 29/32 | 29/30 |
| Original | C | 11/16 | 29/32 | 29/32 |
| Original | D | 3/16 | 30/32 | 30/32 |
| Original | E | 8/16 | 30/32 | 30/32 |
| Wording | Base | 12/16 | 26/32 | 26/26 |
| Wording | A | 13/16 | 31/32 | 31/32 |
| Wording | B | 8/16 | 30/32 | 30/30 |
| Wording | C | 13/16 | 28/32 | 28/32 |
| Wording | D | 8/16 | 29/32 | 29/32 |
| Wording | E | 9/16 | 29/32 | 29/32 |
| Order | Base | 1/16 | 25/32 | 25/26 |
| Order | A | 6/16 | 19/32 | 19/28 |
| Order | B | 5/16 | 30/32 | 30/32 |
| Order | C | 8/16 | 29/32 | 29/32 |
| Order | D | 3/16 | 28/32 | 28/30 |
| Order | E | 6/16 | 28/32 | 28/32 |

\pagebreak

## 3. A changed rule can be right while the schema is wrong

!COUNT_FIGURE!

**Figure 1.** The same frozen confirmation pairs produce two different views of competence. D/E have identical changed-probe totals in each version, but E passes more complete suites. Counts are shown directly; the two rows have different denominators. Repeated wording/order versions are not independent observations to pool.

### Nullable sensitivity remains a useful positive control

Cells show complete suites; changed correctness/all; changed correctness/evaluable, respectively.

| Model | Original | Wording | Order |
| --- | --- | --- | --- |
| Base | 0/8; 0/8; 0/7 | 0/8; 0/8; 0/8 | 0/8; 0/8; 0/6 |
| A | 6/8; 6/8; 6/8 | 3/8; 3/8; 3/8 | 8/8; 8/8; 8/8 |
| B | 5/8; 5/8; 5/7 | 2/8; 2/8; 2/8 | 7/8; 7/8; 7/7 |
| C | 8/8; 8/8; 8/8 | 6/8; 7/8; 7/8 | 7/8; 7/8; 7/7 |
| D | 8/8; 8/8; 8/8 | 5/8; 6/8; 6/8 | 8/8; 8/8; 8/8 |
| E | 8/8; 8/8; 8/8 | 6/8; 6/8; 6/8 | 8/8; 8/8; 8/8 |

Base passes no nullable pair. D/E preserve the original and reordered nullability behavior while wording still changes their success. The eight nullable pairs test required string-versus-null rules; they do not estimate general schema competence.

\pagebreak

## 4. What the controlled contrasts show

The table reports count-suite transitions on the same 16 pairs. Loss is divided by left-condition passes; gain is divided by left-condition failures. Conditional loss/gain repeats the comparison only on pairs where both models produce evaluable schemas in both arms. Zero eligible denominators are shown as unavailable, not zero percent.

| Version | Contrast | Loss / pass | Gain / fail | Conditional loss; gain |
| --- | --- | --- | --- | --- |
| Original | A to B | 2/9 | 1/7 | 2/9; 1/6 |
| Original | B to D | 5/8 | 0/8 | 5/8; 0/7 |
| Original | D to E | 0/3 | 5/13 | 0/3; 5/13 |
| Wording | A to B | 5/13 | 0/3 | 4/12; 0/3 |
| Wording | B to D | 2/8 | 2/8 | 2/8; 1/7 |
| Wording | D to E | 0/8 | 1/8 | 0/8; 1/8 |
| Order | A to B | 1/6 | 0/10 | 1/6; 0/8 |
| Order | B to D | 2/5 | 0/11 | 2/5; 0/10 |
| Order | D to E | 0/3 | 3/13 | 0/3; 3/12 |

**Activation, A to B.** Original and rewritten changed-probe totals are similar (29 to 29 and 31 to 30, each /32); reordered totals improve from 19 to 30. On the reordered inputs, A has five root-only exact-bound items while B has none. However, complete count suites fall from 9/13/6 to 8/8/5 across original/wording/order. Removing the activation reduces this particular placement failure but does not improve full-schema behavior consistently.

**Width, B to D.** Narrowing the affine module changes complete count suites from 8/8/5 to 3/8/3. Target bounds remain exactly placed in all 32 items of each confirmation version for both models. D's distractor receives a bound more often: 22/14/23 items, versus B's 14/14/22. Nullable suites improve from 5/2/7 to 8/5/8. Thus width reduction is not a uniform loss of rule sensitivity or target attachment; it changes which unchanged rules are violated.

**Site, D to E.** Complete count suites improve from 3/8/3 to 8/9/6. E retains every D count-suite pass in each confirmation version and adds 5, 1, and 3. Both have changed-probe totals 30/29/28 out of 32. Distractor-bound counts fall from 22/14/23 to 14/11/16. This contrast links the site intervention to fewer unintended constraints and better full-suite fidelity in these trained models.

**Reference LoRA, C.** Count suites are 11/13/8, and nullable suites 8/6/7. C passes 8/16 count pairs across all three versions, compared with A 6, B 4, D 2 and E 5. This configuration comparison changes targets, parameterization, scaling and biases together; it does not isolate an activation or site effect.

\pagebreak

## 5. Placement and a concrete invariant failure

| Model | Target orig. | Target word. | Target order | Distractor O / W / R (each /32) |
| --- | --- | --- | --- | --- |
| Base | 32/32 | 32/32 | 31/32 | 22 / 9 / 29 |
| A | 31/32 | 32/32 | 27/32 | 12 / 6 / 10 |
| B | 32/32 | 32/32 | 32/32 | 14 / 14 / 22 |
| C | 31/32 | 31/32 | 32/32 | 6 / 2 / 13 |
| D | 32/32 | 32/32 | 32/32 | 22 / 14 / 23 |
| E | 32/32 | 32/32 | 32/32 | 14 / 11 / 16 |

Target columns count direct exact minItems/maxItems on the focus array. Distractor columns count any bound on the explicitly unrestricted array. These are item-level structural diagnostics, not replacements for executed probe behavior. A semantically equivalent composition may pass without direct placement. A keyword at the object root does not enforce an array-length rule.

### Example: confirm_count_04, original wording

Both arms name `beam_presets` as the focus array, with intervals a=[2,4] and b=[3,5]. D and E both express these intervals correctly. Relative to E, D adds only `properties.gel_codes.maxItems: 2` in each arm, even though gel_codes is unrestricted. Their schemas otherwise agree.

The unchanged probe `distractor_n_6` contains six gel_codes and should be accepted under both arms. D rejects it in both arms; E accepts it. It is D's only failing probe in each arm, and E passes the complete suites. This case explains why the two models can tie on the manipulated interval while differing in complete-schema success. B's schemas also match E's in this pair.

The example supports the distractor-constraint interpretation for this pair. Across the dataset, the fall in distractor-bound items accompanies the site improvement; other failure types remain visible in the complete per-item records.

\pagebreak

## 6. Robustness: old success does not transfer unchanged

The old set has 48 pairs in two aligned wordings, including 12 count pairs. It provides continuity with the earlier report. Base/A/C predictions are reused, and B/D/E are newly evaluated on the same frozen inputs.

| Model | Old original | Old rewrite | Old both / Base-stable | New all three /16 |
| --- | --- | --- | --- | --- |
| Base | 10/12 | 12/12 | 10/10 | 1/16 |
| A | 12/12 | 1/12 | 0/10 | 6/16 |
| B | 11/12 | 6/12 | 3/10 | 4/16 |
| C | 10/12 | 6/12 | 4/10 | 8/16 |
| D | 12/12 | 12/12 | 10/10 | 2/16 |
| E | 12/12 | 11/12 | 9/10 | 5/16 |

On the ten old count pairs passed by Base in both wordings, A retains none across both versions; D retains all ten and E nine. D therefore removes the observed old-set wording loss under this definition. Its perfect 12/12 old count result in each wording does not transfer to the new distractor-array tasks: it passes only 2/16 confirmation count pairs across all three versions.

The confirmation Base is unstable: count suites are 2/16 in original wording, 12/16 in rewritten wording, and 1/16 after reordering. Only one pair, confirm_count_07, passes Base in all three versions; no adapted condition retains that pair across all versions. This 0/1 result has a very small denominator. The all-pair cross-version counts are the more informative companion view for these inputs, and Base-damaged cases are not evidence of adaptation destroying a demonstrated stable ability.

Old all-family complete suites are Base 18/14, A 36/23, B 29/23, C 32/25, D 36/31 and E 35/33 across original/paraphrase (each /48). Old paraphrase strict joint success is lower than schema-suite success for B (18 versus 23), C (22 versus 25), D (30 versus 31) and E (31 versus 33), separating rule behavior from instance delivery. Truncation affects one old-paraphrase A pair and one old-original E pair; both remain in their denominators.

\pagebreak

## 7. Attribution and conclusion

The cleanest local finding is the D-to-E site contrast. It holds architecture width, affine module, parameter budget, initial tensors and training policy fixed. On the confirmation set, E improves all three complete-suite totals, retains every D pass, and produces fewer distractor bounds, while the manipulated-rule correctness totals remain equal. The measured benefit is therefore broader schema fidelity under this site intervention, with a directly verified extra-constraint example.

The A-to-B contrast supports an activation-dependent error profile: removing SiLU reduces root-only bounds after instruction reordering, but does not improve complete-suite totals. B-to-D shows that narrower affine adaptation can preserve old wording behavior and nullable sensitivity while worsening new count suites. These results reject a single explanation in which either nonlinearity or bottleneck width uniformly determines rule generation.

Each architecture is represented by one seed and a validation-selected checkpoint. The observed differences include the architecture's optimization trajectory and the shared selection policy; different best epochs are part of that comparison. They do not establish a distribution of causal effects over random restarts, identify an internal neural representation, or make C an isolated architectural ablation. Finite synthetic probes establish the tested decisions and constraints, not logical equivalence for every possible JSON instance.

**Practical conclusion:** assess changed-rule sensitivity together with invariant constraints and aligned wording/order variants. The strongest discriminating-probe score can coexist with frequent harmful restrictions elsewhere in the generated schema. In this study, moving the narrow affine module improves that tradeoff, while the old simple-task ranking alone would conceal it.

## Reproduction and evidence

The prior course report remains unchanged. This is a standalone supplement with editable prose and a rendering script in `mechanism_study/report/`. Detailed methods and a source-level comparability record are retained alongside it.

- `scripts/experiment.py`: unchanged training loop, prompt, decoder and original scoring.
- `mechanism_study/train_variant.py`: B/D/E construction and checked checkpoint loading; `runs/B`, `runs/D`, `runs/E`: completed status, validation and configuration records.
- `mechanism_study/CONFIRM_PROTOCOL.md` and `analysis_plan.md`: pre-prediction design, endpoints and comparisons.
- `mechanism_study/analysis/summary.json` and `evidence.md`: complete numerical results; `items.jsonl`, `pairs.jsonl`, `contrasts.jsonl`, `cross_variants.jsonl`: schemas, executable decisions, conditional denominators, IDs and transition cells.
- `mechanism_study/predictions/`: raw new replies and generation configs. Historical old-set controls remain in `paired_study/`.

Training statuses report successful frozen-weight checks. Analysis reports complete inputs with no missing prediction IDs. The supplement reads the accepted analysis rather than rescoring outputs or rerunning experiments. All data are synthetic; there is no independent human-annotated test set.
