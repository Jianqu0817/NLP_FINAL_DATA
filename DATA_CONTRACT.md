# Joint Schema + JSON experiment data contract

Model: Qwen/Qwen3-4B-Instruct-2507. All generated examples are synthetic; never label model-written examples as human-written.

Each JSONL row: `id`, `split`, `family`, `rule_tags` (list), `input` (Chinese string), `reference_schema` (object), `reference_data` (object), `provenance` (object).

Target assistant output is one JSON object with exactly `schema` and `data`, both objects. Schema dialect is Draft 2020-12 with `$schema` set to `https://json-schema.org/draft/2020-12/schema`.

Every task specifies both rules and concrete instance facts in Chinese. Field names must be explicitly supplied in the request (Chinese explanation plus English key), so there is no hidden field-name oracle. Do not include a literal JSON Schema in the input. Use ordinary Chinese instructions, including field names as necessary. All constraints in the reference schema must follow the request or the global defaults below.

Global defaults, also included in the system prompt: object fields are required unless explicitly called optional; extra object fields are forbidden; names/text/phone/identifiers are strings; phone strings preserve leading zeros; ordered lists retain input order. No invented values or constraints. A specifically stated exact participant/item count is a schema array-length constraint. Supplied individual names, dates, and phone values are instance facts, not `const` constraints. If null is requested for missing information, declare the field nullable. Relative dates require explicit reference date and Asia/Shanghai timezone in the input.

Supported schema keywords: `$schema`, `type`, `properties`, `required`, `additionalProperties` (boolean), `items` (schema), `minItems`, `maxItems`, `enum`, `minimum`, `maximum`, `minLength`, `maxLength`, `pattern` (simple anchored digit/identifier patterns), `format` (date/date-time/time/email), `if`, `then`, `else`, `dependentRequired`, `oneOf`, `anyOf`, `allOf`, `const` (only when requirements explicitly fix values or in conditional discriminators). No refs or recursive schemas. Avoid unevaluatedProperties and advanced dialect interactions.

Conditional schemas: discriminator must be required in the `if` predicate when testing its value; declare all possible properties at the root before `additionalProperties:false`; only unconditional required fields go in root required. Optional branch fields must not accidentally become required in the other branch.

Generate a mix of scalar, nested, array, numeric bounds, enums, conditional and dependency requirements. All reference data must pass reference schema validation with FormatChecker.

Family is the semantic task/constraint/template source, not a row ID. Paraphrases and slot substitutions remain in the same family. Each agent owns a separate generator and output file. Fixed random seeds required. Report family counts, rule coverage and provenance; do not fabricate independent human validation.

Agents generate templates and generator code themselves, then execute to create examples. This is template-based model-assisted synthetic generation, and must be described accurately. Keep all work in the specified owned files.

Supplemental natural-meeting track: colloquial meeting requests need not name English fields. The system prompt supplies the agreed start_time/location/participants{name,phone} convention, exact attendee count, required fields, no extra fields, and no invented meeting title. This track uses disjoint expression families across splits but intentionally shares known schemas. Its results must be reported separately from the schema-held-out requirements track.
