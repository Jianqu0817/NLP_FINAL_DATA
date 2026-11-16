# Paired counterfactual rule results

All rates use all dataset items/pairs; missing, malformed, or unevaluable outputs receive zero rule credit.
Strict preserves the original wrapper. Diagnostic additionally wraps exactly two bare sequential objects, schema first.
Probe agreement measures this finite test suite, not schema equivalence. Flip rate alone ignores direction; both-correct is primary.

| Condition | Mode | N | Format | Profile | Data | Balanced rule | Both-arm suite | Changed probes both correct | Joint pair | Truncated | Missing |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| adapter | strict | 96 | 97.9% | 85.4% | 89.6% | 85.1% | 47.9% | 38.9% | 47.9% | 1 | 0 |
| adapter | diagnostic | 96 | 97.9% | 85.4% | 89.6% | 85.1% | 47.9% | 38.9% | 47.9% | 1 | 0 |
| base_demo | strict | 96 | 88.5% | 64.6% | 83.3% | 62.9% | 27.1% | 34.7% | 27.1% | 0 | 0 |
| base_demo | diagnostic | 96 | 88.5% | 64.6% | 83.3% | 62.9% | 27.1% | 34.7% | 27.1% | 0 | 0 |
| base_zero | strict | 96 | 100.0% | 63.5% | 89.6% | 62.3% | 29.2% | 36.1% | 29.2% | 0 | 0 |
| base_zero | diagnostic | 96 | 100.0% | 63.5% | 89.6% | 62.3% | 29.2% | 36.1% | 29.2% | 0 | 0 |
| lora | strict | 96 | 99.0% | 99.0% | 85.4% | 93.5% | 52.1% | 51.4% | 45.8% | 0 | 0 |
| lora | diagnostic | 96 | 99.0% | 99.0% | 85.4% | 93.5% | 52.1% | 51.4% | 45.8% | 0 | 0 |

## Family breakdown

| Condition | Mode | Family | Pairs | Both-arm suite | Changed probes both correct |
|---|---|---|---:|---:|---:|
| adapter | strict | conditional_dependency | 12 | 0.0% | 4.2% |
| adapter | strict | count_bounds | 12 | 8.3% | 16.7% |
| adapter | strict | nullable | 12 | 83.3% | 91.7% |
| adapter | strict | required_optional | 12 | 100.0% | 100.0% |
| adapter | diagnostic | conditional_dependency | 12 | 0.0% | 4.2% |
| adapter | diagnostic | count_bounds | 12 | 8.3% | 16.7% |
| adapter | diagnostic | nullable | 12 | 83.3% | 91.7% |
| adapter | diagnostic | required_optional | 12 | 100.0% | 100.0% |
| base_demo | strict | conditional_dependency | 12 | 0.0% | 4.2% |
| base_demo | strict | count_bounds | 12 | 91.7% | 91.7% |
| base_demo | strict | nullable | 12 | 0.0% | 0.0% |
| base_demo | strict | required_optional | 12 | 16.7% | 16.7% |
| base_demo | diagnostic | conditional_dependency | 12 | 0.0% | 4.2% |
| base_demo | diagnostic | count_bounds | 12 | 91.7% | 91.7% |
| base_demo | diagnostic | nullable | 12 | 0.0% | 0.0% |
| base_demo | diagnostic | required_optional | 12 | 16.7% | 16.7% |
| base_zero | strict | conditional_dependency | 12 | 0.0% | 0.0% |
| base_zero | strict | count_bounds | 12 | 100.0% | 100.0% |
| base_zero | strict | nullable | 12 | 0.0% | 0.0% |
| base_zero | strict | required_optional | 12 | 16.7% | 16.7% |
| base_zero | diagnostic | conditional_dependency | 12 | 0.0% | 0.0% |
| base_zero | diagnostic | count_bounds | 12 | 100.0% | 100.0% |
| base_zero | diagnostic | nullable | 12 | 0.0% | 0.0% |
| base_zero | diagnostic | required_optional | 12 | 16.7% | 16.7% |
| lora | strict | conditional_dependency | 12 | 0.0% | 0.0% |
| lora | strict | count_bounds | 12 | 50.0% | 62.5% |
| lora | strict | nullable | 12 | 83.3% | 83.3% |
| lora | strict | required_optional | 12 | 75.0% | 100.0% |
| lora | diagnostic | conditional_dependency | 12 | 0.0% | 0.0% |
| lora | diagnostic | count_bounds | 12 | 50.0% | 62.5% |
| lora | diagnostic | nullable | 12 | 83.3% | 83.3% |
| lora | diagnostic | required_optional | 12 | 75.0% | 100.0% |

## Metric meanings

- Profile: valid Draft 2020-12 schema, supported original keywords, correct dialect declaration, and root object type.
- Rule evaluability allows missing dialect or root type, as in the original scorer; an explicitly wrong dialect or unsupported keyword remains unevaluable.
- Balanced rule: mean positive acceptance and negative rejection per item, then macro-average over all items.
- Both-arm suite: every probe correct on both arms of a pair. Changed-probe both-correct requires the correct acceptance direction on both arms.
- Data accuracy uses original numeric/date-time normalization; field accuracy, extra fields, reference compliance and self-consistency remain separately available in summary.json.
- Truncation comes only from explicit truncated=true or finish_reason=length/max_tokens metadata, not guessed from malformed text.
- items.jsonl preserves raw outputs, generated objects, failures, and every probe result. pairs.jsonl aligns expected and predicted decisions across arms.
- conditions_comparison.jsonl aligns every condition pair on the same pair ID and mode; deltas are descriptive, not significance tests.
