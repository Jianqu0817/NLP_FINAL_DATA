# Training data generation notes

- Rows: 2,000 synthetic examples, all assigned to the `train` split.
- Named scenarios: 80 semantic task families; 25 deterministic slot substitutions per family.
- Representative schema variants: 80 distinct schemas across the 80 scenario families.
- Structural/constraint combinations: 80 distinct representative schemas after normalizing away family-specific record-ID patterns and schema title/description annotations.
- Exact row-level schema signatures: 160 after excluding schema title/description annotations.
- Seed: `20261105`. Running `python scripts/generate_train.py` rewrites the same JSONL deterministically.
- Provenance on every row: `gpt-6-luna max`; `template-assisted synthetic generation`.
- No external APIs were called. No independent human validation is claimed.

## Family counts by domain

- 会议 (`meeting`): 250 rows, 10 families.
- 提醒事项 (`reminder`): 250 rows, 10 families.
- 课程 (`course`): 250 rows, 10 families.
- 报名登记 (`registration`): 250 rows, 10 families.
- 库存与物资 (`inventory`): 250 rows, 10 families.
- 订单与售后 (`order`): 250 rows, 10 families.
- 图书 (`book`): 250 rows, 10 families.
- 实验室任务 (`lab_task`): 250 rows, 10 families.

## Rule coverage

- `allOf`: 200 rows
- `anyOf`: 200 rows
- `array`: 1200 rows
- `conditional`: 200 rows
- `const`: 400 rows
- `dependentRequired`: 200 rows
- `enum`: 1550 rows
- `exact_array_length`: 1000 rows
- `format_date`: 1000 rows
- `format_email`: 600 rows
- `if_then_else`: 200 rows
- `maxLength`: 950 rows
- `nested_object`: 1800 rows
- `nullable`: 200 rows
- `numeric_bounds`: 1800 rows
- `oneOf`: 200 rows
- `optional_property`: 600 rows
- `pattern`: 1850 rows

The scenarios cover meetings, reminders, courses, registration, inventory, orders, books, and lab tasks. Each family has a domain-specific structure (such as meeting schedules, reminder recurrence, course assessments, registration seats, stock locations, order line items, book catalog data, or lab measurements) alongside one of ten shared extraction patterns. Prompts provide English field keys with Chinese explanations, all rules, every concrete reference value, and array order. Optional and conditional/dependency branches are spelled out per example.

The schemas use Draft 2020-12 and the contract's supported keywords: scalar types, nested objects, arrays with exact lengths, enums, numeric bounds, string patterns and lengths, date/email formats, nullable values, `if`/`then`/`else`, `dependentRequired`, `oneOf`, `anyOf`, and `allOf`. Every schema and data instance was checked locally using `jsonschema` Draft202012Validator with `FormatChecker`.
