# Natural meeting data generation notes

## Scope

This supplemental track uses colloquial Chinese meeting requests and the shared meeting convention supplied by the system prompt: `start_time`, `location`, and `participants` with `name` and `phone`. Every field is required, extra fields are disallowed, and the attendee count stated in the request fixes the participant array length. Inputs do not name those English keys or spell out schema-language rules. Each includes an explicit reference date and the Asia/Shanghai timezone. The requests cover tomorrow, the day after tomorrow, and explicit calendar dates.

The output schema is Draft 2020-12. `start_time` is a `date-time` string with a `+08:00` offset; `location`, `name`, and `phone` are strings. Participant arrays have matching `minItems` and `maxItems` values equal to the stated count. The schema has only `start_time`, `location`, and `participants`; it does not add a meeting title.

This tests expression generalization over a familiar schema, not schema-held-out generalization. Sentence-template families are disjoint across splits; the fixed field convention is shared.

## Generated files and counts

Run `python scripts/generate_natural.py` to regenerate the three raw JSONL files. The seed is `20261105`.

| Split | Rows | Distinct phrasing families | Rows per family | Participant count coverage |
|---|---:|---:|---:|---|
| train | 300 | 15 | 20 | 1–6 participants, 50 rows per count |
| validation | 40 | 4 | 10 | 1–6 participants; counts 1–4 have 7 rows each and 5–6 have 6 each |
| test | 80 | 8 | 10 | 1–6 participants; counts 1–2 have 14 rows each and 3–6 have 13 each |

Date-expression coverage is balanced by construction:

| Split | 明天 | 后天 | Absolute date |
|---|---:|---:|---:|
| train | 100 | 100 | 100 |
| validation | 14 | 13 | 13 |
| test | 27 | 27 | 26 |

Family names are prefixed with their split (`natural_train_`, `natural_validation_`, or `natural_test_`), and the generator checks that family sets do not overlap. The sentence patterns vary the order of time, place, participant lists, and output requests. Name and phone renderings also vary while keeping each participant's name and phone paired.

## Provenance and validation

All examples are synthetic. GPT-6 Luna max authored the templates; Python deterministically fills the date, time, location, count, fictional name, and synthetic phone slots. This is template-assisted generation, not independent row-by-row model generation, human authorship, or human validation. Row-level provenance records the model label, method, seed, reference date, timezone, and validation status. Phone values are strings and include zeros.

The generator checks each reference schema with `Draft202012Validator.check_schema`, then validates each reference data object using `Draft202012Validator` with `FormatChecker`. It also checks row/family totals, disjoint family membership, explicit timezone anchors, and that input text contains no English field keys or detailed schema keywords. The three files are:

- `data/natural_train_raw.jsonl`
- `data/natural_validation_raw.jsonl`
- `data/natural_test_raw.jsonl`
