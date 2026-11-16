# Single-seed preliminary comparison

User requested one Adapter and one LoRA training run, three epochs each.
Both use learning rate 1e-4 and seed 42. No learning-rate search,
additional seeds, or width ablations were run in this reduced queue.
These are synthetic-data, single-seed results, not a stability claim.

| Method | Split | Track | N | Joint success | Data accuracy | Rule score |
|---|---|---|---:|---:|---:|---:|
| base_zero | test | requirements | 500 | 24.20% | 52.00% | 48.59% |
| base_zero | test | natural_meeting | 80 | 0.00% | 0.00% | 0.00% |
| base_zero | challenge | requirements | 100 | 0.00% | 0.00% | 0.00% |
| adapter_lr0.0001_seed42 | test | requirements | 500 | 26.60% | 75.60% | 79.18% |
| adapter_lr0.0001_seed42 | test | natural_meeting | 80 | 95.00% | 95.00% | 100.00% |
| adapter_lr0.0001_seed42 | challenge | requirements | 100 | 17.00% | 52.00% | 72.12% |
| lora_lr0.0001_seed42 | test | requirements | 500 | 40.60% | 76.20% | 82.51% |
| lora_lr0.0001_seed42 | test | natural_meeting | 80 | 95.00% | 95.00% | 100.00% |
| lora_lr0.0001_seed42 | challenge | requirements | 100 | 13.00% | 55.00% | 77.11% |
