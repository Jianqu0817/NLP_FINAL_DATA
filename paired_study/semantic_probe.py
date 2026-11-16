"""Supplemental Draft 2020-12 probe behavior, independent of project whitelist.

Usage mirrors score_pairs.py. This diagnostic never replaces strict headline
results. Missing dialect is allowed; an explicit other dialect and all schema
references are rejected. No schema is repaired or dereferenced.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

import score_pairs as paired

original = paired.original


def restrictions(schema):
    """Record actual original-profile failures and every reference occurrence."""
    references, outside = [], []
    # Walk schema-bearing keywords, not instance data inside const/enum/default.
    mappings = {'properties', 'patternProperties', '$defs', 'definitions', 'dependentSchemas'}
    singles = {'items', 'additionalItems', 'additionalProperties', 'unevaluatedProperties',
               'unevaluatedItems', 'contains', 'propertyNames', 'if', 'then', 'else', 'not',
               'contentSchema'}
    lists = {'allOf', 'anyOf', 'oneOf', 'prefixItems'}

    def visit(node, path='$'):
        if not isinstance(node, dict):
            return
        for key, value in node.items():
            location = path+'/'+key
            if key in {'$ref', '$dynamicRef', '$recursiveRef'}:
                references.append({'path': location, 'target': value})
            if key not in original.KEYWORDS:
                outside.append({'path': location, 'keyword': key})
            if key in mappings and isinstance(value, dict):
                for name, child in value.items():
                    visit(child, location+'/'+name)
            elif key in singles:
                # Draft-04 tuple items are invalid 2020-12, still audit them.
                if isinstance(value, list):
                    for index, child in enumerate(value):
                        visit(child, location+'/'+str(index))
                else:
                    visit(value, location)
            elif key in lists and isinstance(value, list):
                for index, child in enumerate(value):
                    visit(child, location+'/'+str(index))
            elif key == 'dependencies' and isinstance(value, dict):
                for name, child in value.items():
                    if isinstance(child, dict):
                        visit(child, location+'/'+name)
    visit(schema)
    try:
        original.profile(schema)
        profile_error = None
    except Exception as exc:
        profile_error = str(exc)
    reasons = []
    if schema.get('$schema') != original.DIALECT:
        reasons.append('missing_dialect' if '$schema' not in schema else 'wrong_dialect')
    if schema.get('type') != 'object':
        reasons.append('root_object_type_not_declared')
    if outside:
        reasons.append('outside_project_keyword_whitelist')
    if profile_error and not reasons:
        reasons.append('other_profile_restriction')
    return {'original_profile_error': profile_error, 'profile_reasons': reasons,
            'outside_project_keywords': outside, 'references': references}


def score(row, prediction, mode):
    baseline = paired.score_item(row, prediction, mode)
    audit = {'original_profile_error': None, 'profile_reasons': [],
             'outside_project_keywords': [], 'references': []}
    schema = baseline['generated_schema']
    validator, error = None, None
    meta_valid = False
    if schema is not None:
        audit = restrictions(schema)
        try:
            original.Draft202012Validator.check_schema(schema)
            meta_valid = True
            if '$schema' in schema and schema['$schema'] != original.DIALECT:
                raise ValueError('explicit dialect is not Draft 2020-12')
            if audit['references']:
                raise ValueError('schema reference outside no-ref task domain')
            validator = original.Draft202012Validator(schema, format_checker=original.CHECKER)
        except Exception as exc:
            error = str(exc)
    else:
        error = baseline['metrics']['error']
    probes = []
    for probe in row['probes']:
        accepted = validator.is_valid(probe['instance']) if validator is not None else None
        probes.append({'id': probe['id'], 'instance': probe['instance'],
                       'expected_accept': probe['accept'], 'predicted_accept': accepted,
                       'correct': accepted == probe['accept']})
    positive = [p['correct'] for p in probes if p['expected_accept']]
    negative = [p['correct'] for p in probes if not p['expected_accept']]
    metrics = {'schema_meta_validity': int(meta_valid), 'schema_rule_evaluable': int(validator is not None),
               'schema_suite_pass': int(all(p['correct'] for p in probes)),
               'probe_correct': sum(p['correct'] for p in probes), 'probe_total': len(probes),
               'balanced_rule_score': (sum(positive)/len(positive)+sum(negative)/len(negative))/2,
               'self_consistency': int(validator.is_valid(baseline['generated_data'])) if validator is not None else 0}
    return {**{k: baseline[k] for k in ('id', 'pair_id', 'family', 'arm', 'mode', 'missing_prediction',
                                      'truncated', 'raw_output', 'generated_schema', 'generated_data')},
            'original_metrics': baseline['metrics'], 'metrics': metrics, 'probes': probes,
            'audit': audit, 'semantic_error': error}


def pair_score(records):
    # Reuse matched-probe logic without presenting a new joint headline metric.
    adapted = [{**r, 'metrics': {**r['metrics'], 'joint_success': 0}} for r in records]
    result = paired.pair_result(adapted)
    del result['both_joint_success']
    return result


def summarize(items, pairs):
    n = len(items)
    reasons = Counter(reason for item in items for reason in item['audit']['profile_reasons'])
    keywords = Counter(k['keyword'] for item in items for k in item['audit']['outside_project_keywords'])
    return {'n_items': n, 'missing_predictions': sum(r['missing_prediction'] for r in items),
            'format_success': sum(r['original_metrics']['format_success'] for r in items)/n,
            'original_schema_suite_pass': sum(r['original_metrics']['schema_suite_pass'] for r in items)/n,
            'semantic_schema_suite_pass': sum(r['metrics']['schema_suite_pass'] for r in items)/n,
            'semantic_rule_evaluable': sum(r['metrics']['schema_rule_evaluable'] for r in items)/n,
            'semantic_balanced_rule_score': sum(r['metrics']['balanced_rule_score'] for r in items)/n,
            'rescued_suite_pass_count': sum(r['metrics']['schema_suite_pass'] and not r['original_metrics']['schema_suite_pass'] for r in items),
            'reference_present_count': sum(bool(r['audit']['references']) for r in items),
            'profile_failure_reasons': dict(sorted(reasons.items())),
            'outside_project_keyword_occurrences': dict(sorted(keywords.items())),
            'pairs': paired.aggregate_pairs([{**r, 'both_joint_success': 0} for r in pairs])}


def run(pairs_path, prediction_paths, output_dir):
    rows = paired.read_jsonl(pairs_path)
    groups = paired.validate_rows(rows)
    ids = {r['id'] for r in rows}
    summary = {'diagnostic': 'Supplemental Draft 2020-12 behavior; project whitelist relaxed, no refs, no repairs beyond symmetric bare-object wrapping.',
               'dataset': str(Path(pairs_path).resolve()), 'conditions': {}}
    all_items, all_pairs, restriction_cases = [], [], []
    for path in prediction_paths:
        condition = Path(path).stem
        if condition in summary['conditions']:
            raise ValueError(f'duplicate condition stem: {condition}')
        predictions = {}
        for prediction in paired.read_jsonl(path):
            item_id = prediction['id']
            if item_id not in ids or item_id in predictions:
                raise ValueError(f'unknown or duplicate prediction ID: {item_id}')
            if 'raw_output' not in prediction:
                raise ValueError(f'missing raw_output: {item_id}')
            predictions[item_id] = prediction
        summary['conditions'][condition] = {}
        for mode in ('strict', 'diagnostic'):
            items = [dict(condition=condition, **score(r, predictions.get(r['id']), mode)) for r in rows]
            indexed = {r['id']: r for r in items}
            pairs = [dict(condition=condition, **pair_score([indexed[r['id']] for r in pair])) for pair in groups.values()]
            aggregate = summarize(items, pairs)
            # Pair aggregate helper has a joint metric; remove this irrelevant placeholder.
            del aggregate['pairs']['both_joint_success']
            aggregate['by_family'] = {}
            for family in sorted({r['family'] for r in rows}):
                family_summary = summarize([r for r in items if r['family'] == family], [r for r in pairs if r['family'] == family])
                del family_summary['pairs']['both_joint_success']
                aggregate['by_family'][family] = family_summary
            summary['conditions'][condition][mode] = aggregate
            all_items.extend(items)
            all_pairs.extend(pairs)
            restriction_cases.extend(r for r in items if r['audit']['original_profile_error'] or r['audit']['references'])
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    paired.write_jsonl(output/'items.jsonl', all_items)
    paired.write_jsonl(output/'pairs.jsonl', all_pairs)
    paired.write_jsonl(output/'restriction_cases.jsonl', restriction_cases)
    lines = ['# Supplemental semantic probe diagnostic', '', summary['diagnostic'], '',
             'Strict headline scores remain in the original scorer. All rates retain every dataset item/pair.',
             'Missing dialect is allowed here; explicit wrong dialect and local/external schema references are rejected.', '',
             'Unknown keywords retain Draft validator behavior: they are ignored, not translated. In particular, `nullable` does not make a type nullable.', '',
             '| Condition | Mode | N | Original item suite | Semantic item suite | Both-arm suite | Changed probes both correct | Rescued items |',
             '|---|---|---:|---:|---:|---:|---:|---:|']
    for condition, modes in summary['conditions'].items():
        for mode, result in modes.items():
            p = result['pairs']
            lines.append(f'| {condition} | {mode} | {result["n_items"]} | {result["original_schema_suite_pass"]:.1%} | {result["semantic_schema_suite_pass"]:.1%} | {p["both_suite_pass"]:.1%} | {p["discriminating_both_correct_rate"]:.1%} | {result["rescued_suite_pass_count"]} |')
    lines += ['', '## Observed original-profile failures', '']
    for condition, modes in summary['conditions'].items():
        for mode, result in modes.items():
            lines += [f'### {condition} / {mode}', '',
                      f'Failure reasons (item counts): `{json.dumps(result["profile_failure_reasons"], ensure_ascii=False)}`',
                      f'Outside-whitelist keywords (occurrences): `{json.dumps(result["outside_project_keyword_occurrences"], ensure_ascii=False)}`',
                      f'Reference-bearing items: {result["reference_present_count"]}.', '']
    lines += ['Per-case schema, original error, semantic error and full probe evidence: restriction_cases.jsonl.',
              'Full item/pair records and by-family summaries are in items.jsonl, pairs.jsonl and summary.json.',
              'A recovered finite probe pass does not establish schema equivalence. A flip without the correct direction receives no both-correct credit.', '']
    (output/'summary.md').write_text('\n'.join(lines), encoding='utf-8')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pairs', type=Path, required=True)
    parser.add_argument('--predictions', type=Path, nargs='+', required=True)
    parser.add_argument('--output-dir', type=Path, default=Path(__file__).parent/'semantic_results')
    args = parser.parse_args()
    run(args.pairs, args.predictions, args.output_dir)
    print(f'Supplemental diagnostic written to {args.output_dir.resolve()}')
