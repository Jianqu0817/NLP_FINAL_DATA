# Evaluation generation notes

## Provenance and method

These records are synthetic and authored for this task by GPT-6 Luna max. The generator uses hand-written Chinese task-family templates with fixed-seed deterministic slot substitution; the rows are not individually sampled from a language-model API and are not human-validated.
The seed is `20261105`. Each row carries the same model/method disclosure, seed, and family template ID in `provenance`.

## Split and family counts

Validation: 300 rows across 12 semantic task families (12 rows per family). Test: 500 rows across 20 separate business task families (20 rows per family).
Validation covers college processes; test covers business operations. Family names identify distinct tasks and constraint patterns, not paraphrase IDs.

### Validation families

- `val_campus_identity`: 25
- `val_club_event`: 25
- `val_course_registration`: 25
- `val_dining_order`: 25
- `val_dorm_repair`: 25
- `val_exam_roster`: 25
- `val_experiment_log`: 25
- `val_internship_offer`: 25
- `val_library_return`: 25
- `val_peer_tutoring`: 25
- `val_scholarship_application`: 25
- `val_student_trip`: 25

### Test families

- `test_b2b_lead_intake`: 25
- `test_business_travel_claim`: 25
- `test_campaign_brief`: 25
- `test_customer_quote`: 25
- `test_employee_onboarding`: 25
- `test_equipment_maintenance`: 25
- `test_hotel_group_booking`: 25
- `test_meeting_minutes`: 25
- `test_monthly_forecast`: 25
- `test_product_catalog`: 25
- `test_project_milestone`: 25
- `test_recruiting_candidate`: 25
- `test_refund_claim`: 25
- `test_sales_contract_order`: 25
- `test_subscription_change`: 25
- `test_supplier_qualification`: 25
- `test_support_case`: 25
- `test_training_signin`: 25
- `test_vendor_invoice_payment`: 25
- `test_warehouse_pick_pack`: 25

## Rule coverage

Tags are descriptive; rows may carry several tags. Test split is explicitly separated into ordinary and combination examples:
- Test ordinary: 75
- Test combination: 425

Combined tag counts across both splits:
- `all_of`: 25
- `any_of`: 25
- `array`: 25
- `array_count`: 425
- `array_range`: 25
- `business`: 500
- `college`: 300
- `combination`: 600
- `conditional`: 125
- `dependent_required`: 75
- `enum`: 575
- `format`: 600
- `nested`: 450
- `nullable`: 100
- `one_of`: 75
- `optional`: 75
- `ordinary`: 200
- `pattern`: 650
- `range`: 550

The set includes scalar and nested objects, exact array counts and bounded array lengths, integer and numeric ranges, enums, simple anchored patterns, date/time/date-time formats, `if`/`then`/`else`, `dependentRequired`, `oneOf`, `allOf`, optional fields, and explicit nullable values. Nullable fields always state the null policy in the input. Conditional and dependency examples state which branch fields are required or omitted.

## Validation

The generator checks each schema with `Draft202012Validator.check_schema` and validates every `reference_data` object with `Draft202012Validator` plus `FormatChecker` before writing JSONL. The output is deterministic for the fixed seed.

## Limits

The data are synthetic, template-based, and use bounded slot vocabularies; repeated phrasing and structural regularity may make them easier than naturally authored requests. They do not provide independent human validation, and the provenance reports model-assisted template authorship rather than per-row model generation.
