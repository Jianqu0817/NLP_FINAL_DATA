# Generating JSON Schema and Data from Chinese Requirements

CISC7021 | Course project report | 13 November 2026

## Abstract

This project studies whether parameter-efficient adaptation improves a language model's ability to generate both a reusable JSON Schema and an accurate JSON instance from Chinese requirements. A frozen Qwen3-4B-Instruct-2507 model is compared with a post-block bottleneck Adapter and attention-projection LoRA under closely matched trainable-parameter budgets. The original single-seed pilot reported strict joint success of 20.9%, 36.0%, and 48.1% for Base, Adapter, and LoRA on 580 requests. An output-wrapper audit raises Base to 35.2% without changing its schemas or data, showing why format, extraction, and rule behavior need separate evaluation. A frozen follow-up holds instance facts constant across 48 requirement pairs and adds an untuned Base condition with one unrelated worked example. On the original paired wording, Adapter and LoRA pass complete strict suites on 36 and 32 pairs, versus 14 and 12 for the untuned conditions. A second wording reverses the adapted models' complete-rule ranking. Both preserve a nullability advantage, while neither solves conditional reversal. The evidence supports specific rule gains alongside format gains, with substantial wording sensitivity.

## 1. The task and the evaluation problem

A request contains two kinds of information: general validation requirements and facts for one record. The model must return exactly one JSON object with the keys `schema` and `data`. The schema must express the requirements for future records; the data must faithfully encode the supplied facts. These objectives can diverge. An extracted object may be correct even when its schema permits missing required fields, rejects valid alternatives, or turns a sample identifier into an unjustified fixed rule.

The main research question is therefore: **Does adaptation improve rule-sensitive schema generation beyond teaching the output wrapper and the instance format?** A second practical question asks whether a single simple demonstration can recover an appreciable part of the apparent fine-tuning benefit without changing model weights.

The study combines an existing broad pilot with a smaller behavioral follow-up. The pilot measures delivery across held-out scenario/schema families and a known-schema meeting track. The follow-up changes one requirement at a time while leaving the correct instance unchanged. This removes the need to infer rule changes from improvements in extracted data.

## 2. Related work and design choice

Houlsby et al. [1] introduced small trainable adapter modules while keeping the original pretrained network fixed. This project uses the same bottleneck principle but implements one residual module after each Qwen decoder block, rather than reproducing their BERT architecture. Hu et al. [2] introduced LoRA, which freezes pretrained weights and learns low-rank updates. Here LoRA modifies the attention query, key, value, and output projections. The two methods are compared as alternative adaptation mechanisms at approximately 11.8 million trainable parameters, not as an architectural novelty.

The base checkpoint is Qwen3-4B-Instruct-2507 [3]. Schema behavior is evaluated using the Draft 2020-12 validation vocabulary [4] and a deliberately bounded keyword profile. Schema acceptance on carefully chosen instances supplies concrete evidence about an output's rules, while avoiding comparison based only on schema text or key order.

\pagebreak

## 3. Experimental setup

### 3.1 Model and adaptation

The base revision is `cdbee75f17c01a7cc42f958dc650907174af0554`; backbone weights are frozen in BF16. Both training runs use learning rate 0.0001, seed 42, and three epochs. Validation selects Adapter epoch 1 and LoRA epoch 2 by joint success, with data accuracy, balanced rule score, and self-consistency as tie-breakers. The paired results do not select checkpoints.

| Condition | Trainable mechanism | Parameters | Inference prompt |
|---|---|---:|---|
| Base zero | No weight updates | 0 | Shared instructions only |
| Base + example | No weight updates | 0 | Shared instructions + one simple worked example |
| Adapter | 36 post-block 2560-to-64-to-2560 bottlenecks; SiLU; residual output | 11,890,944 | Shared instructions only |
| LoRA | Rank 16; alpha 32; attention q/k/v/o; no bias or dropout | 11,796,480 | Shared instructions only |

Adapter uses a random down projection, zero-initialized up projection, FP32 trainable weights and optimizer states, and BF16 outputs. Both methods share training data, AdamW, weight decay 0.01, cosine scheduling, and 5% warmup. Training uses one NVIDIA L40S, microbatch size 1 with gradient accumulation 16, and a 4,096-token sequence limit. The parameter budgets are approximately matched.

### 3.2 Data and inference

The pilot uses 2,300 training requests (2,000 explicit requirements; 300 meetings), 339 validation requests, 580 main-test requests, and 100 challenge requests. The main test has 500 requirements from 20 held-out templates with 25 substitutions each, plus 80 colloquial meetings. Meetings use a system-supplied field convention and measure expression generalization with known schemas; they are reported separately.

All examples are synthetic: GPT-6 Luna-assisted original generators and model-assisted paired templates are expanded deterministically. There is no independent human test set. The follow-up uses seed 20261113 and four recurring rule-template structures, each instantiated in 12 scenarios.

All follow-up conditions share requests, system instructions, greedy decoding, batch size 16, and a 2,048-token output limit. The Base example demonstrates a single string field, `label`, with its schema and instance. It has no count, optionality, nullability, or conditional rule from the paired test; only prompting changes.

### 3.3 Strict delivery and diagnostic scoring

Strict scoring uses the raw reply. It rejects malformed JSON, duplicate keys, extra surrounding text, or an incorrect wrapper. A valid task-profile schema must declare Draft 2020-12 and root object type, and use only the supported keywords. Instance accuracy ignores object-key order, preserves array order, normalizes equivalent date-time instants and integral numeric values, and preserves identifier strings.

Joint success requires correct format, task-profile-valid schema, every reference probe correct, exact instance data, reference-schema compliance, and predicted schema/data self-consistency. Diagnostic scoring additionally wraps a reply containing exactly two bare sequential objects, schema first and data second. It neither edits those objects nor removes code fences. Strict and diagnostic results are reported separately.

\pagebreak

## 4. What the original pilot actually established

### 4.1 A large wrapper effect

| Main test (580 requests) | Base zero | Base + example | Adapter | LoRA |
|---|---:|---:|---:|---:|
| Strict joint success | 121 / 580 (20.9%) | 126 / 580 (21.7%) | 209 / 580 (36.0%) | 279 / 580 (48.1%) |
| Wrapper-diagnostic joint success | 204 / 580 (35.2%) | 126 / 580 (21.7%) | 209 / 580 (36.0%) | 279 / 580 (48.1%) |

The Base-example column is the later frozen-checkpoint control on the same requests. The original Base often produced two adjacent JSON objects instead of the required outer object. Mechanical wrapping increases its success by 83 requests. Consequently, the apparent Adapter-minus-Base net gap shrinks from 88 requests to 5; the LoRA gap shrinks from 158 to 75. These are differences in totals, not claims that the models fail on the same requests.

### 4.2 Separate rules from extracted data

The table below applies the same wrapper diagnostic to every method. Each cell gives the count passing **all reference probes / exact data / joint delivery**, with the full track as denominator. The Base-example column is the later control; the other three columns reuse saved pilot predictions.

| Track | N | Base zero | Base + example | Adapter | LoRA |
|---|---:|---:|---:|---:|---:|
| Explicit requirements | 500 | 162 / 286 / 140 | 118 / 205 / 86 | 133 / 378 / 133 | 208 / 381 / 203 |
| Known-schema meetings | 80 | 80 / 64 / 64 | 50 / 60 / 40 | 80 / 76 / 76 | 80 / 76 / 76 |
| Challenge requests | 100 | 36 / 45 / 19 | 13 / 41 / 3 | 31 / 52 / 17 | 30 / 55 / 13 |

Adapter produces more correct instances than Base on the requirement track, yet fewer schemas pass the complete probe suite. LoRA improves both on that track. On the challenge set, both adapted methods extract more correct data while passing fewer complete schema suites than diagnostic Base. Thus, improved extraction and format compliance can coexist with weaker coverage of reference rules.

On the shared subset of 264 requirement requests where both Base and Adapter schemas are executable, Base alone passes 61 complete suites and Adapter alone passes 19. For Base and LoRA, the shared executable subset has 266 requests: Base alone passes 11 and LoRA alone passes 18. These conditional subsets differ across comparisons and should not replace the full-denominator table.

### 4.3 Reference-label mismatches

A family-level audit found two witness-active mismatches. In `test_customer_quote`, the reference imposes a `^C[0-9]{5}$` pattern on `customer_id` although the request only establishes a string field. In `test_monthly_forecast`, the request requires the first day of a month, but the reference and frozen positive probes allow a mid-month date. Each shared template has 25 rows: 50 requests carry witnesses capable of penalizing faithful instructions, not 50 demonstrated model misgradings.

Two further families require 15 alphanumeric tax-ID characters but the reference narrows letters to uppercase; their witnesses contain no discriminating lowercase example. Offset-specific date-time wording also exceeds the reference constraints in two families, without a distinguishing frozen witness. The audit covered all 20 requirement templates. Original scores retain the frozen labels and mean "passing reference witnesses"; the new pairs explicitly specify their constraints.

\pagebreak

## 5. Frozen paired follow-up

### 5.1 Hold facts constant; change the requirement

Each of 48 pairs contains two Chinese requests with identical field names, facts, and correct `data`. One requirement clause changes. Both reference schemas accept that shared data. Arm direction is balanced within each family, and deterministic shuffling prevents A/B or presentation order from encoding a strictness shortcut.

| Rule family | Pairs | Changed requirement | Discriminating counterexample |
|---|---:|---|---|
| Count bounds | 12 | Overlapping, non-nested array-length intervals | One length accepted only on each side |
| Required / optional | 12 | One string field may or may not be omitted | Delete that field |
| Nullable / non-null | 12 | One required field allows string-or-null or string only | Replace its value with null |
| Conditional dependency | 12 | Swap which of two discriminator values makes another field required | Omit the dependent field under each value |

For example, a library bundle may contain the same three book names under either an allowed length interval of two to three or three to four. The data need not change, but a two-book candidate and a four-book candidate must exchange acceptance labels. For an optionality pair, deleting the target field distinguishes the schemas. For a nullability pair, the target remains required in both arms, so omission is a common negative control rather than a valid substitute for null.

Each pair shares exactly the same named probe instances across its arms. Labels come from the reference validators before inference. Common positive controls include legal alternative strings and the reference instance. Common negative controls cover wrong types, missing invariant required fields, extra fields, and, where relevant, invalid enum values or lengths outside both intervals. The count and conditional families include flips in both directions; optionality and nullability are naturally nested rule changes.

### 5.2 Metrics answer different questions

- **Format / task profile / data:** whether each of the 96 replies satisfies the interface, schema declarations and supported keywords, or exact instance target.
- **Both-arm suite pass:** the percentage of 48 pairs for which every probe is correctly classified on both arms. This guards against answering only the changed requirement while breaking invariant rules.
- **Changed-probe both-correct:** among discriminating probes, the percentage with the correct decision on both arms. A flip in the wrong direction receives no credit.
- **Joint pair success:** both replies meet the complete strict joint criterion.

All denominators retain missing, malformed, or unevaluable outputs as failures. A finite probe suite characterizes behavior on those instances; it cannot establish full logical equivalence between two arbitrary schemas. The four-family design supports descriptive mechanism-level diagnosis, with limited lexical and structural coverage.

\pagebreak

## 6. Paired results: nullability improves, conditionals fail

### 6.1 Strict delivery and rule behavior

| Condition | Format / 96 | Profile / 96 | Exact data / 96 |
|---|---:|---:|---:|
| Base zero | 96 | 59 | 96 |
| Base + example | 83 | 47 | 83 |
| Adapter | 94 | 94 | 94 |
| LoRA | 94 | 92 | 94 |

| Condition | Strict suite pairs / 48 | Draft behavior pairs / 48 | Changed probes both correct | Strict joint pairs / 48 |
|---|---:|---:|---:|---:|
| Base zero | 14 (29.2%) | 18 (37.5%) | 38.9% | 14 |
| Base + example | 12 (25.0%) | 25 (52.1%) | 33.3% | 12 |
| Adapter | 36 (75.0%) | 36 (75.0%) | 66.7% | 36 |
| LoRA | 32 (66.7%) | 32 (66.7%) | 62.5% | 32 |

Changed-probe rates above use the strict project scorer. Mechanical wrapping changes none of these paired results; all predictions are present and none are truncated. The adapted models outperform both untuned conditions on complete pair suites, while Base zero extracts every reference instance exactly. The paired advantage therefore includes rule behavior beyond instance extraction.

Supplemental **Draft behavior** retains valid wrappers and rejects wrong dialects and schema references, but relaxes the keyword whitelist and permits an omitted dialect declaration. Unknown keywords are ignored, not repaired: `nullable` does not add null to `type: string`. Base frequently emits this annotation. Ignoring `nullable: false` can expose correct non-null behavior obscured by a profile failure. Supplemental results describe probe behavior and do not replace strict scores.

### 6.2 Family-level explanation

This table uses the supplemental Draft-behavior criterion: every listed probe must be correct on both arms. Each family contains 12 pairs.

| Family | Base zero | Base + example | Adapter | LoRA |
|---|---:|---:|---:|---:|
| Count bounds | 10 / 12 | 12 / 12 | 12 / 12 | 10 / 12 |
| Required / optional | 5 / 12 | 12 / 12 | 12 / 12 | 10 / 12 |
| Nullable / non-null | 0 / 12 | 0 / 12 | 12 / 12 | 12 / 12 |
| Conditional dependency | 3 / 12 | 1 / 12 | 0 / 12 | 0 / 12 |

Both adapted models track the nullability change on all 12 scenarios, whereas neither untuned condition passes one complete nullability pair. The simple example helps Base with count and optionality behavior, but not nullability, and it reduces strict format success. Neither adaptation solves conditional reversal: both fail all 12 conditional pairs. Adapter's higher overall count is specific to this suite and these checkpoints.


\pagebreak

## 7. Wording sensitivity changes the ranking

A secondary check paraphrases the same 48 pairs: it presents the facts first and rewrites the requirement clauses in Chinese while preserving IDs, schemas, instances, probes, arm directions, and all numerical boundaries. The same checkpoints, system prompt, example, and decoding settings are reused. This is a second wording of the original test, not 48 new independent pairs. The AI-authored paraphrases have no independent human equivalence annotation.

### 7.1 Complete rule-suite success declines

All pair counts use the 48-pair denominator. Supplemental Draft-behavior and project-profile suite counts happen to coincide on the paraphrased version; they differ on the original wording, as shown in Section 6.

| Condition | Original Draft-behavior pairs | Paraphrased Draft-behavior pairs | Paraphrased strict joint pairs |
|---|---:|---:|---:|
| Base zero | 18 / 48 | 14 / 48 | 14 / 48 |
| Base + example | 25 / 48 | 13 / 48 | 13 / 48 |
| Adapter | 36 / 48 | 23 / 48 | 23 / 48 |
| LoRA | 32 / 48 | 25 / 48 | 22 / 48 |

Adapter loses 13 complete rule pairs and LoRA loses seven on the rewritten requests. The adapted-model ordering reverses for complete rule-suite success, although Adapter still has one more strict joint pair. LoRA's three-pair gap between complete rule behavior and joint delivery reflects the additional data and interface requirements in the joint metric. One Adapter paraphrase output is truncated; no other paraphrase output is truncated.

### 7.2 Which findings survive the wording change?

Each cell shows original-to-paraphrased Draft-behavior passing pairs, out of 12 for that family.

| Family | Base zero | Base + example | Adapter | LoRA |
|---|---:|---:|---:|---:|
| Count bounds | 10 -> 12 | 12 -> 11 | 12 -> 1 | 10 -> 6 |
| Required / optional | 5 -> 2 | 12 -> 2 | 12 -> 12 | 10 -> 9 |
| Nullable / non-null | 0 -> 0 | 0 -> 0 | 12 -> 10 | 12 -> 10 |
| Conditional dependency | 3 -> 0 | 1 -> 0 | 0 -> 0 | 0 -> 0 |

The nullability separation remains: both adapted models pass 10 pairs under the second wording while both untuned models pass none. Conditional reversal remains unsolved by both adapted models. The original Adapter advantage on length bounds is highly wording-specific: it drops from 12 pairs to one.

In `count_bounds_01_a` and `_01_b`, paraphrased instructions still assign the two length intervals to `books`. Adapter outputs the correct numerical `minItems` and `maxItems` at the root object instead of inside the array property's schema. Those keywords do not constrain the `books` array there. The instance is correct, but the schema accepts out-of-range lists. This failure is structural placement, not a wrong extracted boundary number.

Across both wordings, nullability improves and conditional reversal fails; the overall rule-suite ranking is wording-sensitive.

\pagebreak

## 8. Prompting control on the original tasks

The one-example Base is also evaluated on the original main and challenge requests, preserving the pilot's input IDs, scorer, and decoding settings. This comparison connects the narrow paired test to the original deliverable and asks whether demonstration helps on the broader tasks.

### 8.1 A format gain is not a comparable joint gain

All entries below are strict passing counts on the 580 original main-test requests.

| Condition | Format | Exact data | All reference probes | Joint |
|---|---:|---:|---:|---:|
| Base zero | 372 | 260 | 143 | 121 |
| Base + example | 468 | 265 | 168 | 126 |
| Adapter | 550 | 454 | 213 | 209 |
| LoRA | 541 | 457 | 288 | 279 |

Adding one unrelated example produces 96 more correctly wrapped outputs, but only five more exact instances and five more joint successes overall. Format improves substantially without a comparable improvement in downstream delivery. Three Base-example replies and two LoRA replies reach the output limit; none of the original Base or Adapter replies does.

### 8.2 The aggregate hides opposite track effects

Strict joint counts are shown with every request in its track retained. The wrapper-diagnostic rule/data/joint decomposition for all four methods appears in Section 4.2.

| Track | N | Base zero | Base + example | Adapter | LoRA |
|---|---:|---:|---:|---:|---:|
| Explicit requirements | 500 | 121 | 86 | 133 | 203 |
| Known-schema meetings | 80 | 0 | 40 | 76 | 76 |
| Challenge requests | 100 | 0 | 3 | 17 | 13 |

The demonstration improves meeting delivery from zero to 40 requests, but requirement-track joint success falls from 121 to 86. On the challenge set, its format count rises from zero to 86 while joint success reaches only three. The original Base's wrapper-diagnostic challenge score is 19, so the demo's three strict successes should not be mistaken for recovered latent rule ability across the whole set.

The single example is therefore a useful format control rather than a uniformly stronger baseline. Its effect depends on the track and metric: it helps count and optionality behavior in the paired diagnostic, leaves paired nullability unsolved, and harms strict requirement-track delivery. A demonstration cannot be assumed to substitute for adaptation merely because it illustrates the desired wrapper.

\pagebreak

## 9. Error analysis and implications

Two original examples show why the evaluation decomposition matters. In `test_sales_contract_order_001`, both Base and LoRA delivered correct data and valid wrappers. Adding an unexpected field to the buyer object was accepted by Base's schema and rejected by LoRA's. This is a concrete rule-level improvement. In `test_warehouse_pick_pack_011`, wrapping Base's two objects reveals a schema and instance that pass the reference suite. Adapter extracts the three packages correctly but omits `required` inside the array-item schema, allowing an empty package object. That is a schema failure despite successful extraction.

A paired conditional error is equally concrete. In `conditional_dependency_09_b`, `inspection_note` is required only when `purchase_channel` is the local option (English translation); it is optional for the other channel. Adapter puts the note in both the `then` and `else` required lists. Its schema therefore rejects a valid non-local record lacking the note. The reference instance already contains the note and cannot expose this error by itself; the alternate-branch omission probe does.

Across the 24 conditional outputs per method, 21 of 22 parseable Adapter replies and 16 of 22 parseable LoRA replies literally require the target field in both branches. A training-schema inventory provides a plausible source of this branch error. All 200 training schemas containing `if` use `then.required = [phone]` and `else.required = [email]`; none uses the test's same-field, one-sided optional pattern. The observed over-requirement is consistent with transfer of a two-required-branch template. The inventory and one output support this mechanism as a hypothesis, not an isolated causal effect.

The practical selection criterion is the downstream requirement. For an application that only consumes the extracted instance, exact data accuracy is directly relevant. For an application that deploys the generated schema as a validator for future data, accepting all positive alternatives and rejecting invalid cases is essential. A high joint score is useful for delivery, but it should be accompanied by this decomposition before choosing an adaptation method.

## 10. Limitations and conclusion

Both adapted models were trained once at one learning rate and seed. The new test reuses those checkpoints and therefore measures these configurations rather than training stability. Synthetic templates induce repeated language and rule structures; the paired study has four recurring rule-template structures and only two controlled wordings. The original pilot also contains the documented reference-rule mismatches. These conditions bound the generalization of the results and motivate reporting request counts, family breakdowns, and actual counterexamples alongside aggregate rates.

The answer is selective: these adapted checkpoints learn some reusable constraints beyond the wrapper and instance format. The strongest evidence is the nullability contrast: both adapted models pass all 12 pairs while both untuned conditions fail all 12, even with the same correct instance facts. Yet both adapted models fail every conditional-reversal pair, and their branch over-requirement resembles the repeated training pattern. LoRA has higher broad-pilot delivery. Adapter leads complete-suite success on the original paired wording, but LoRA leads that metric on the paraphrase. The nullability separation persists across both wordings, while neither adaptation solves conditional reversal. The defensible takeaway is to evaluate adaptation by the rules it preserves and changes, separately from format and extraction, before deploying a generated validator.

\pagebreak

## 11. Reproducibility and AI assistance

The follow-up adds 1,448 generations using existing pilot checkpoints and frozen evaluation data, covering the original-wording pairs, their paraphrases, and the one-example control on the original tasks. No follow-up training is performed. The base model ID, revision, prompt, decoding configuration, checkpoint paths, raw outputs, and scoring code are retained in the project. The model is loaded without the gold schema in its inference prompt; the one-example condition receives only the unrelated single-field demonstration.

The original pilot data were generated using GPT-6 Luna-authored scripts and deterministic slot substitution. The paired set, analysis code, and this report were prepared with AI assistance. Reference schemas and behavioral probes are programmatically validated; there is no independent human annotation claim. Measured outcomes come from retained outputs and deterministic scoring. The label audit uses the actual prompts, shared reference schemas, and frozen witnesses; it was not a blinded independent human review.

### Reproduction map

| Artifact or entry point | Purpose |
|---|---|
| `paired_study/pilot_audit.py` | CPU-only reanalysis of original saved predictions |
| `paired_study/build_pairs.py` | Validate or deterministically reproduce the frozen 48 pairs |
| `paired_study/run_inference.py` | Run a specified frozen-checkpoint condition and split |
| `paired_study/score_pairs.py` | Strict and diagnostic paired behavior scoring |
| `paired_study/semantic_probe.py` | Supplemental Draft-behavior diagnostic |
| `paired_study/build_paraphrase.py` | Second wording with all non-input fields preserved |

The editable source is `paired_study/report/course_report.md`; `render_report.py` builds the PDF with ReportLab. Detailed results are retained in `paired_study/results/`, `semantic_results/`, `paraphrase_results/`, `paraphrase_semantic/`, `wording_comparison.csv`, and `original_control/comparison.csv`. The source audits are `pilot_audit.md` and `label_audit.md`, under `paired_study/`. Commands run from the project root in the appropriate environment. The builder refuses to silently overwrite an existing paired set that differs from its deterministic output. This preserves the distinction between the pre-inference frozen test and any future corrected version. Original test scores are not silently rewritten when interpreting the audited label issue.

## References

[1] N. Houlsby et al., "Parameter-Efficient Transfer Learning for NLP," Proceedings of ICML, PMLR 97, pp. 2790-2799, 2019. [Official paper](https://proceedings.mlr.press/v97/houlsby19a.html).

[2] E. J. Hu et al., "LoRA: Low-Rank Adaptation of Large Language Models," arXiv:2106.09685, 2021. [Paper](https://arxiv.org/abs/2106.09685).

[3] Qwen Team, "Qwen3-4B-Instruct-2507," model card. [Official model repository](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507).

[4] A. Wright, H. Andrews, and B. Hutton, "JSON Schema Validation: A Vocabulary for Structural Validation of JSON," Draft 2020-12 validation specification, 2022. [Specification](https://json-schema.org/draft/2020-12/json-schema-validation).
