# Supplemental semantic probe diagnostic

Supplemental Draft 2020-12 behavior; project whitelist relaxed, no refs, no repairs beyond symmetric bare-object wrapping.

Strict headline scores remain in the original scorer. All rates retain every dataset item/pair.
Missing dialect is allowed here; explicit wrong dialect and local/external schema references are rejected.

Unknown keywords retain Draft validator behavior: they are ignored, not translated. In particular, `nullable` does not make a type nullable.

| Condition | Mode | N | Original item suite | Semantic item suite | Both-arm suite | Changed probes both correct | Rescued items |
|---|---|---:|---:|---:|---:|---:|---:|
| adapter | strict | 96 | 52.1% | 52.1% | 47.9% | 38.9% | 0 |
| adapter | diagnostic | 96 | 52.1% | 52.1% | 47.9% | 38.9% | 0 |
| base_demo | strict | 96 | 46.9% | 47.9% | 27.1% | 34.7% | 1 |
| base_demo | diagnostic | 96 | 46.9% | 47.9% | 27.1% | 34.7% | 1 |
| base_zero | strict | 96 | 51.0% | 53.1% | 29.2% | 44.4% | 2 |
| base_zero | diagnostic | 96 | 51.0% | 53.1% | 29.2% | 44.4% | 2 |
| lora | strict | 96 | 61.5% | 61.5% | 52.1% | 51.4% | 0 |
| lora | diagnostic | 96 | 61.5% | 61.5% | 52.1% | 51.4% | 0 |

## Observed original-profile failures

### adapter / strict

Failure reasons (item counts): `{"outside_project_keyword_whitelist": 2, "root_object_type_not_declared": 10}`
Outside-whitelist keywords (occurrences): `{"property": 2}`
Reference-bearing items: 0.

### adapter / diagnostic

Failure reasons (item counts): `{"outside_project_keyword_whitelist": 2, "root_object_type_not_declared": 10}`
Outside-whitelist keywords (occurrences): `{"property": 2}`
Reference-bearing items: 0.

### base_demo / strict

Failure reasons (item counts): `{"outside_project_keyword_whitelist": 23}`
Outside-whitelist keywords (occurrences): `{"maxProperties": 2, "minProperties": 2, "nullable": 21}`
Reference-bearing items: 0.

### base_demo / diagnostic

Failure reasons (item counts): `{"outside_project_keyword_whitelist": 23}`
Outside-whitelist keywords (occurrences): `{"maxProperties": 2, "minProperties": 2, "nullable": 21}`
Reference-bearing items: 0.

### base_zero / strict

Failure reasons (item counts): `{"outside_project_keyword_whitelist": 32, "wrong_dialect": 4}`
Outside-whitelist keywords (occurrences): `{"nullable": 32}`
Reference-bearing items: 0.

### base_zero / diagnostic

Failure reasons (item counts): `{"outside_project_keyword_whitelist": 32, "wrong_dialect": 4}`
Outside-whitelist keywords (occurrences): `{"nullable": 32}`
Reference-bearing items: 0.

### lora / strict

Failure reasons (item counts): `{}`
Outside-whitelist keywords (occurrences): `{}`
Reference-bearing items: 0.

### lora / diagnostic

Failure reasons (item counts): `{}`
Outside-whitelist keywords (occurrences): `{}`
Reference-bearing items: 0.

Per-case schema, original error, semantic error and full probe evidence: restriction_cases.jsonl.
Full item/pair records and by-family summaries are in items.jsonl, pairs.jsonl and summary.json.
A recovered finite probe pass does not establish schema equivalence. A flip without the correct direction receives no both-correct credit.
