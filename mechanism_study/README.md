# Adapter mechanism ablation — first round

Seed 42 only. Comparisons: A:B removes SiLU at width 64 after the block; B:D narrows the linear bottleneck (also changes parameter budget); D:E moves the same width-16 module from block output to the post-attention residual before the MLP. C is the existing Q/K/V/O LoRA comparator, not a single-variable location contrast. Base is the frozen checkpoint.

The original pilot's train/validation splits, optimizer, learning rate, 3 epochs, batch/accumulation, greedy evaluation and checkpoint ranking are reused. Holdout inputs never select weights. Only B/D/E train. The original experiment's scheduler remains disabled for its extended jobs.

- [Module and training implementation](train_variant.py); [position and gradient tests](test_variant_structure.py)
- [Frozen 24-pair confirmation design](CONFIRM_PROTOCOL.md); [pre-specified scoring plan](analysis_plan.md)
- [Inference](run_eval.py); [scorer](score_mechanism.py); [local download checks](verify_downloads.py)
- Old pairs and old paraphrases use archived Base/A/C predictions from paired_study. New predictions: 3 new checkpoints × 2 old datasets × 96 items, plus 6 conditions × 3 confirmation wordings × 48 items = 1,440 generations. The 3 wordings are repeated measures of **the same 24 pairs**, not 72 independent pairs.

## First-round finding (seed 42)

On the 16 new two-array range pairs, moving the same width-16 module from the block output to the post-attention residual (D→E) left correct target-bound changes unchanged in all three input variants (30, 29, 28 out of 32 probes), but improved complete rule pairs from 3→8, 8→9 and 3→6. Both modules wrote the exact bounds on the target array on all 32 arms of each variant; E less often imposed unrequested bounds on the second array. Removing SiLU from the width-64 block-end module eliminated five target bounds written only at the root on the order-only variant, yet did not improve complete-pair accuracy in any of the three versions. Width and placement comparisons concern these selected, single-seed checkpoints; LoRA is a practical comparator rather than an isolated site intervention.

[English report supplement](../output/pdf/cisc7021_adapter_mechanism.pdf) · [Complete numerical evidence](analysis/evidence.md) · [Local recovery archive](outputs.tar) (all three trained checkpoints and raw results)

## Reproduce in a separate workspace

Use the original frozen Qwen model manifest, pilot scripts and dataset, historical best adapter/LoRA weights, and the experiment Python environment. From the project root:

~~~bash
for v in B D E; do
    python mechanism_study/train_variant.py "$v" --smoke && python mechanism_study/train_variant.py "$v" || exit 1
done
for v in Base A C; do python mechanism_study/run_eval.py "$v" confirm_original confirm_wording confirm_order || exit 1; done
for v in B D E; do python mechanism_study/run_eval.py "$v" confirm_original confirm_wording confirm_order old_original old_paraphrase || exit 1; done
python mechanism_study/verify_downloads.py
python mechanism_study/score_mechanism.py --require-complete
~~~

Training refuses a nonempty output directory; inference refuses to overwrite existing raw predictions.
