# Qwen3 joint JSON Schema + data adaptation experiment

This repository implements the authorized course experiment: Chinese requirements and concrete facts -> one object containing `schema` and `data`.

**Training is complete.** The November 5 pilot trained Adapter and LoRA once each (three epochs, learning rate 1e-4, seed 42). The November 13 [follow-up](paired_study/README.md) uses the same frozen checkpoints to separate output formatting, instance extraction, and rule following. The original metrics and limited training queue remain intact.

The later [mechanism ablation](mechanism_study/README.md) adds three single-seed training runs to distinguish activation, width and residual-stream position. See the [paired results](mechanism_study/analysis/evidence.md) for all conditions.

## Model and methods

- Base: `Qwen/Qwen3-4B-Instruct-2507`, exact revision recorded in `model_manifest.json` on the server.
- Frozen BF16 base. 36 separate post-decoder-block bottleneck adapters, 2560 -> 64 -> 2560, SiLU, random down projection and zero up projection. Trainable parameters: 11,890,944. Trainable adapters and optimizer states use FP32; outputs are cast back to backbone BF16. PEFT similarly promotes LoRA trainable weights to FP32.
- Comparison: LoRA rank 16, alpha 32, q/k/v/o projections, no bias/dropout. Trainable parameters: 11,796,480.
- Baselines: original zero-shot Base and, in the follow-up, Base with one unrelated worked example. The original proposed three-training-example baseline was not run.
- The extended design (two learning rates, seeds 42/43/44, and ablations) was deferred.
- Selection order: validation joint success, data accuracy, balanced rule score, self-consistency; first checkpoint wins complete ties. Test answers never select a configuration.

## Data provenance and scope

The user explicitly requested 1-5 GPT-6 Luna workers at max reasoning. Four such workers author generator scripts for training, evaluation, challenge, and supplemental natural-meeting data. Templates plus deterministic slot substitutions produce synthetic examples. This is **not human-authored or human-validated data**, and the challenge split is not called a human test set.

Raw generator outputs are retained. `prepare_data.py` checks reference validity, excludes exact schema/input overlaps across splits, records counts/hashes, and builds independent positive/negative witness suites before predictions. Named scenario count and distinct schema count are reported separately. A combination tag alone is not proof that a combination was unseen: actual operator-signature novelty is separately measured. Independent generators can introduce style/domain differences; this is part of the scope of held-out evaluation, not a perfectly isolated causal manipulation.

Frozen data counts: training2300, validation339, test580, challenge100. One duplicate validation request was excluded. Training contains2000 requirements examples and300 natural-meeting examples; test contains500 requirements examples and80 natural meetings. All3319 reference pairs validate. The validation/test/challenge witness suites contain268014 total positive and negative instances. See `data/manifest.json` and `data/final_audit.json` for counts, split hashes, actual operator-combination novelty, and exclusions.

The main requirements track explicitly names fields and requirements. The supplemental natural-meeting track uses colloquial Chinese and the user's agreed meeting field convention, supplied in the global system prompt. It measures expression generalization with known schemas, while the requirements track holds out schema families. Report these tracks separately. Global conventions are in `DATA_CONTRACT.md` and the fixed system prompt.

## Evaluation

All headline rates use every request as denominator. Evaluate raw replies, no repair. Reject duplicate keys, trailing explanations, NaN, and incorrect wrapper types. Pin Draft 2020-12, an explicit supported-keyword profile, and FormatChecker.

Report format success, schema validity, positive acceptance, negative rejection, balanced rule score, schema witness-suite pass, data exact accuracy, reference-schema compliance, predicted schema/data self-consistency, and joint success. Joint success requires all syntax/schema/witness/data/compliance gates. Finite witness-suite success is **not a proof of full schema equivalence**. Witnesses include valid alternate values and invalid single-rule mutations, plus candidate alternate branch/property combinations reclassified using the reference validator.

Data comparisons ignore object-key order and preserve list order per the task contract. Date-time strings are normalized to UTC instants, and integral floating-point numbers are normalized to integers. Identifier/phone strings preserve leading zeros. Alternate field names or free-form paraphrases are not automatically accepted. Field-level accuracy is diagnostic; extra fields cause whole-object accuracy to fail. Meta-schema legality, strict task-profile compliance, and rule behavior are separately reported, so omitting only the dialect declaration does not erase the diagnostic semantic score.

No gold schema is supplied during main-task inference. Supplying it for constrained decoding would leak the prediction target. No claim of method novelty or beneficial results is made before measurements.

## Commands

```bash
python scripts/generate_train.py
python scripts/generate_eval.py
python scripts/generate_challenge.py
python scripts/generate_natural.py
python scripts/test_evaluation.py
python scripts/prepare_data.py
python scripts/pilot_queue.py
python scripts/summarize.py
```

The smoke stage has completed, checking finite nonzero gradients and frozen weight probes, expected trainable counts, and saved/reloaded predictions. Its results are excluded from final results. The pilot ran sequentially on one GPU. Existing complete runs are skipped; incomplete runs are not silently overwritten. The originally planned extended configuration above is retained as future design context, not the currently executing scope. A completed pilot writes `results/pilot_summary.md` and `results/pilot_summary.json`, plus the standard CSV tables; its final state is `pilot_complete`.

## Cloud workspace

Remote project: `/root/gpufree-data/nlp_final`; persistent model cache: `/root/gpufree-data/hf_cache`. Hardware observed: NVIDIA L40S 46068 MiB, 120 GiB cgroup RAM limit, 24 vCPUs. Python3.11, PyTorch2.7.1+cu128. Dependencies pinned in `requirements.txt`, full environment frozen remotely. The server's system Python is not the experiment environment; use `.venv/bin/python` from the remote project.

`pipeline_status.json`, `logs/`, and each run's `status.json` expose actual progress. Checkpoints, raw predictions, row-level metrics and manifests are retained. The original SSH helper targets the November 5 instance endpoint. For future access use the address and authentication provided for the current instance.
