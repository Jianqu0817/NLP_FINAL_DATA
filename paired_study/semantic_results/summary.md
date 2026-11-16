# Supplemental semantic probe diagnostic

Supplemental Draft 2020-12 behavior; project whitelist relaxed, no refs, no repairs beyond symmetric bare-object wrapping.

Strict headline scores remain in the original scorer. All rates retain every dataset item/pair.
Missing dialect is allowed here; explicit wrong dialect and local/external schema references are rejected.

Unknown keywords retain Draft validator behavior: they are ignored, not translated. In particular, `nullable` does not make a type nullable.

| Condition | Mode | N | Original item suite | Semantic item suite | Both-arm suite | Changed probes both correct | Rescued items |
|---|---|---:|---:|---:|---:|---:|---:|
| adapter | strict | 96 | 75.0% | 75.0% | 75.0% | 66.7% | 0 |
| adapter | diagnostic | 96 | 75.0% | 75.0% | 75.0% | 66.7% | 0 |
| base_demo | strict | 96 | 49.0% | 66.7% | 52.1% | 58.3% | 17 |
| base_demo | diagnostic | 96 | 49.0% | 66.7% | 52.1% | 58.3% | 17 |
| base_zero | strict | 96 | 40.6% | 54.2% | 37.5% | 56.9% | 13 |
| base_zero | diagnostic | 96 | 40.6% | 54.2% | 37.5% | 56.9% | 13 |
| lora | strict | 96 | 69.8% | 69.8% | 66.7% | 62.5% | 0 |
| lora | diagnostic | 96 | 69.8% | 69.8% | 66.7% | 62.5% | 0 |

## Observed original-profile failures

### adapter / strict

Failure reasons (item counts): `{}`
Outside-whitelist keywords (occurrences): `{}`
Reference-bearing items: 0.

### adapter / diagnostic

Failure reasons (item counts): `{}`
Outside-whitelist keywords (occurrences): `{}`
Reference-bearing items: 0.

### base_demo / strict

Failure reasons (item counts): `{"outside_project_keyword_whitelist": 36}`
Outside-whitelist keywords (occurrences): `{"nullable": 36}`
Reference-bearing items: 0.

### base_demo / diagnostic

Failure reasons (item counts): `{"outside_project_keyword_whitelist": 36}`
Outside-whitelist keywords (occurrences): `{"nullable": 36}`
Reference-bearing items: 0.

### base_zero / strict

Failure reasons (item counts): `{"outside_project_keyword_whitelist": 30, "wrong_dialect": 9}`
Outside-whitelist keywords (occurrences): `{"nullable": 38}`
Reference-bearing items: 0.

### base_zero / diagnostic

Failure reasons (item counts): `{"outside_project_keyword_whitelist": 30, "wrong_dialect": 9}`
Outside-whitelist keywords (occurrences): `{"nullable": 38}`
Reference-bearing items: 0.

### lora / strict

Failure reasons (item counts): `{"outside_project_keyword_whitelist": 2}`
Outside-whitelist keywords (occurrences): `{"nullable": 2}`
Reference-bearing items: 0.

### lora / diagnostic

Failure reasons (item counts): `{"outside_project_keyword_whitelist": 2}`
Outside-whitelist keywords (occurrences): `{"nullable": 2}`
Reference-bearing items: 0.

Per-case schema, original error, semantic error and full probe evidence: restriction_cases.jsonl.
Full item/pair records and by-family summaries are in items.jsonl, pairs.jsonl and summary.json.
A recovered finite probe pass does not establish schema equivalence. A flip without the correct direction receives no both-correct credit.
