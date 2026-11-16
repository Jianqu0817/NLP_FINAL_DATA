# Training comparability record

Prepared from the local training, inference, and scoring sources on 2026-11-13. This is the implementation-level record for the supplement; it does not replace the measured runtime records.

## Matched by direct code reuse

- B/D/E call the original `experiment.train` without modifying it. Optimizer, scheduler, accumulation normalization, clipping, training-row shuffle, label masking, full validation and checkpoint ordering are inherited rather than reimplemented.
- B/D/E arguments match historical A/C configuration fields: seed 42; LR 1e-4; three epochs; accumulation 16; no training or validation limits; evaluation batch 16; maximum train length 4096; maximum generation length 2048.
- The backbone loader, manifest, BF16 dtype and SDPA choice are the original loader. New bottleneck parameters are FP32, with both biases retained. The expected architecture remains 36 layers and hidden size 2560.
- A/B initialization has matching tensors at equal width; D/E initialization matches at equal width. The local initialization test extracts the original Bottleneck class rather than reproducing its constructor in the test.
- The original trainable-parameter budget check and frozen probes remain active. They are not weakened for E because E has the same bottleneck parameterization as D.
- New inference calls the original evaluator with its original system prompt, template, greedy decoder, EOS handling and output scoring. Historical old-set Base/A/C predictions are read directly, not regenerated.

## Deliberate differences and interpretation

- A/B changes only the module activation in its architecture. The nonlinear model and affine model can follow different optimization paths after their matched identity initialization; that path is part of the intervention.
- B/D changes width and parameter budget. Their differently shaped projections are not elementwise initialization matches.
- D/E changes the site. E changes both carried residual and MLP input. Post-block D changes the value only after the complete decoder block.
- Historical A/C are selected earlier runs; B/D/E are new runs. Runtime versions, GPU model, selected epochs and actual successful completion must be taken from their emitted configuration/status records before finalizing findings. Matching code is not evidence that all runs completed.
- C differs in adaptation targets, parameterization, scale and bias policy. Its comparison is descriptive between configurations, not an isolated nonlinearity test.
- Same seed and row order do not constitute multi-seed evidence or prove bitwise GPU reproducibility across software/hardware changes.

## Checks already available

`python mechanism_study/test_variant_structure.py` passed locally. Its nonzero-weight E test matches an explicit decoder implementation exactly in FP32 and BF16, with/without non-reentrant checkpointing, including input and trainable gradients. Frozen parameters have no gradients and inference-mode execution agrees. Zero-up identity and A/B initialization matching also pass. Real-model GPU smoke and completed training status are required runtime inputs for the result supplement.

## Completed runtime evidence

1. B/D/E local training status records report three completed epochs and selected epochs 3/3/2. All report passed frozen-weight probes. Configuration records match the historical L40S / PyTorch 2.7.1+cu128 runtime.
2. The analysis owner supplied complete results in `mechanism_study/analysis/`, including summary, per-item/pair records, contrasts, cross-variant transitions and the selected invariant-failure example. All 30 source files are present.
3. Confirmation-protocol conditional full-Draft-evaluable denominators. The scorer now exposes `changed_both_correct_conditional`, evaluability intersections, conditional placement and transition counts; final result tables must retain their actual denominators.
4. The final report retains one truncated A old-paraphrase pair and one truncated E old-original pair; confirmation outputs have no truncations. No prediction IDs are missing.

Final prose uses the pre-specified confirmation co-primary endpoints: count discriminating-probe correctness /32 and complete-suite pair success /16, with analogous nullable /8 endpoints. The analysis plan's suite emphasis does not erase the confirmation protocol's discriminating-probe endpoint.

The old report is unchanged. Accepted findings are in `mechanism_report.md`; the final eight-page PDF is `output/pdf/cisc7021_adapter_mechanism.pdf`. The renderer reads accepted analysis fields and does not rescore predictions or run experiments.
