"""CPU-only paired rule evaluation; original evaluation contract is unchanged.

Usage: python paired_study/score_pairs.py --pairs PATH --predictions A.jsonl B.jsonl --output-dir DIR
Condition names are prediction file stems. Missing IDs remain in every denominator.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import evaluation as original


def read_jsonl(path):
    with Path(path).open(encoding='utf-8-sig') as handle:
        return [original.strict_loads(line) for line in handle if line.strip()]


def diagnostic_wrapper(text):
    """Only wrap two bare sequential JSON objects, schema first, data second.

    strict_loads rechecks duplicate keys and non-JSON constants. raw_decode is
    used only to locate value boundaries, never to repair malformed JSON.
    """
    try:
        original.pair(text)
        return text, False
    except (ValueError, TypeError):
        pass
    decoder = json.JSONDecoder()
    first_start = len(text) - len(text.lstrip())
    _, first_end = decoder.raw_decode(text, first_start)
    second_start = first_end + len(text[first_end:]) - len(text[first_end:].lstrip())
    _, second_end = decoder.raw_decode(text, second_start)
    if text[second_end:].strip():
        raise ValueError('content after second object')
    schema = original.strict_loads(text[first_start:first_end])
    data = original.strict_loads(text[second_start:second_end])
    if not isinstance(schema, dict) or not isinstance(data, dict):
        raise ValueError('two bare values must both be objects')
    return original.dumps({'schema': schema, 'data': data}), True


def validate_rows(rows):
    """Reject malformed experiment inputs before scoring any prediction."""
    ids, groups = set(), defaultdict(list)
    for row in rows:
        for key in ('id', 'pair_id', 'family', 'arm', 'input', 'reference_data', 'reference_schema', 'probes'):
            if key not in row:
                raise ValueError(f'missing {key} in dataset row')
        if row['id'] in ids:
            raise ValueError(f'duplicate dataset ID: {row["id"]}')
        ids.add(row['id'])
        if not isinstance(row['reference_data'], dict):
            raise ValueError(f'reference data is not an object: {row["id"]}')
        val = original.validator(row['reference_schema'])
        val.validate(row['reference_data'])
        probes = row['probes']
        if not probes or len({p['id'] for p in probes}) != len(probes):
            raise ValueError(f'empty or duplicated probe IDs: {row["id"]}')
        if not all(isinstance(p['accept'], bool) for p in probes):
            raise ValueError(f'probe accept must be boolean: {row["id"]}')
        if not {p['accept'] for p in probes} == {True, False}:
            raise ValueError(f'need positive and negative probes: {row["id"]}')
        for probe in probes:
            if val.is_valid(probe['instance']) != probe['accept']:
                raise ValueError(f'reference disagrees with probe: {row["id"]}/{probe["id"]}')
        groups[row['pair_id']].append(row)
    if not rows:
        raise ValueError('empty dataset')
    for pair_id, pair in groups.items():
        if len(pair) != 2 or len({r['arm'] for r in pair}) != 2 or len({r['family'] for r in pair}) != 1:
            raise ValueError(f'pair needs two distinct arms in one family: {pair_id}')
        left, right = ({p['id']: p for p in r['probes']} for r in pair)
        if set(left) != set(right):
            raise ValueError(f'probe IDs not matched: {pair_id}')
        for probe_id in left:
            if original.dumps(left[probe_id]['instance']) != original.dumps(right[probe_id]['instance']):
                raise ValueError(f'probe instances not matched: {pair_id}/{probe_id}')
        if not any(left[k]['accept'] != right[k]['accept'] for k in left):
            raise ValueError(f'pair has no discriminating probe: {pair_id}')
    return groups


def score_item(row, prediction, mode):
    raw = prediction.get('raw_output', '') if prediction is not None else ''
    if not isinstance(raw, str):
        raise ValueError(f'raw_output must be a string for {row["id"]}')
    text, rewrapped = raw, False
    if mode == 'diagnostic':
        try:
            text, rewrapped = diagnostic_wrapper(raw)
        except (ValueError, TypeError):
            pass  # Original format failure is retained, not silently repaired.
    suite = {name: [{'instance': p['instance']} for p in row['probes'] if p['accept'] == accept]
             for name, accept in [('positive', True), ('negative', False)]}
    metrics = original.score(row, text, suite)
    metrics.update(dialect_declared=0, root_object_declared=0, profile_keywords_compliant=0,
                   probe_accuracy=0., probe_correct=0, probe_total=len(row['probes']),
                   rewrapped=int(rewrapped))
    schema, data, val = None, None, None
    if metrics['format_success']:
        schema, data = original.pair(text)
        metrics['dialect_declared'] = int(schema.get('$schema') == original.DIALECT)
        metrics['root_object_declared'] = int(schema.get('type') == 'object')
        try:
            original.profile(schema, root=False)
            metrics['profile_keywords_compliant'] = 1
        except (ValueError, TypeError, AttributeError):
            pass
        if metrics['schema_rule_evaluable']:
            val = original.Draft202012Validator(schema, format_checker=original.CHECKER)
    probes = []
    for probe in row['probes']:
        accepted = val.is_valid(probe['instance']) if val is not None else None
        probes.append({'id': probe['id'], 'instance': probe['instance'], 'expected_accept': probe['accept'],
                       'predicted_accept': accepted, 'correct': accepted == probe['accept']})
    metrics['probe_correct'] = sum(p['correct'] for p in probes)
    metrics['probe_accuracy'] = metrics['probe_correct'] / len(probes)
    truncated = bool(prediction and (prediction.get('truncated') or prediction.get('finish_reason') in ('length', 'max_tokens')))
    return {'id': row['id'], 'pair_id': row['pair_id'], 'family': row['family'], 'arm': row['arm'],
            'mode': mode, 'missing_prediction': prediction is None, 'truncated': truncated,
            'finish_reason': prediction.get('finish_reason') if prediction else None,
            'metrics': metrics, 'probes': probes, 'generated_schema': schema, 'generated_data': data,
            'raw_output': raw}


def pair_result(records):
    left, right = records
    lp, rp = ({p['id']: p for p in r['probes']} for r in records)
    evidence = []
    for probe_id in lp:
        a, b = lp[probe_id], rp[probe_id]
        discriminating = a['expected_accept'] != b['expected_accept']
        both_evaluable = a['predicted_accept'] is not None and b['predicted_accept'] is not None
        evidence.append({'id': probe_id, 'discriminating': discriminating,
                         'expected_accept': [a['expected_accept'], b['expected_accept']],
                         'predicted_accept': [a['predicted_accept'], b['predicted_accept']],
                         'both_correct': a['correct'] and b['correct'],
                         'predicted_flip': bool(both_evaluable and a['predicted_accept'] != b['predicted_accept'])})
    changed = [p for p in evidence if p['discriminating']]
    unchanged = [p for p in evidence if not p['discriminating']]
    return {'pair_id': left['pair_id'], 'family': left['family'], 'mode': left['mode'],
            'ids': [left['id'], right['id']], 'arms': [left['arm'], right['arm']],
            'both_rule_evaluable': int(all(r['metrics']['schema_rule_evaluable'] for r in records)),
            'both_suite_pass': int(all(r['metrics']['schema_suite_pass'] for r in records)),
            'both_joint_success': int(all(r['metrics']['joint_success'] for r in records)),
            'discriminating_probe_total': len(changed),
            'discriminating_both_correct': sum(p['both_correct'] for p in changed),
            'discriminating_predicted_flip': sum(p['predicted_flip'] for p in changed),
            'discriminating_all_correct': int(all(p['both_correct'] for p in changed)),
            'invariant_probe_total': len(unchanged),
            'invariant_both_correct': sum(p['both_correct'] for p in unchanged),
            'probes': evidence}


EXTRA_RATES = ['dialect_declared', 'root_object_declared', 'profile_keywords_compliant', 'probe_accuracy', 'rewrapped']


def aggregate_items(records):
    result = original.aggregate(records)
    n = len(records)
    result.update({key: sum(r['metrics'][key] for r in records)/n if n else None for key in EXTRA_RATES})
    result['missing_predictions'] = sum(r['missing_prediction'] for r in records)
    result['probe_total'] = sum(r['metrics']['probe_total'] for r in records)
    result['probe_correct'] = sum(r['metrics']['probe_correct'] for r in records)
    result['probe_micro_accuracy'] = result['probe_correct']/result['probe_total'] if result['probe_total'] else None
    return result


def aggregate_pairs(records):
    n = len(records)
    result = {'n_pairs': n}
    for key in ['both_rule_evaluable', 'both_suite_pass', 'both_joint_success', 'discriminating_all_correct']:
        result[key] = sum(r[key] for r in records)/n if n else None
    for prefix, numerators in [('discriminating', ['both_correct', 'predicted_flip']), ('invariant', ['both_correct'])]:
        total = sum(r[prefix+'_probe_total'] for r in records)
        result[prefix+'_probe_total'] = total
        for numerator in numerators:
            count = sum(r[prefix+'_'+numerator] for r in records)
            result[prefix+'_'+numerator+'_count'] = count
            result[prefix+'_'+numerator+'_rate'] = count/total if total else None
    return result


def summarize(items, pairs):
    result = {'items': aggregate_items(items), 'pairs': aggregate_pairs(pairs), 'by_family': {}}
    for family in sorted({r['family'] for r in items}):
        result['by_family'][family] = {
            'items': aggregate_items([r for r in items if r['family'] == family]),
            'pairs': aggregate_pairs([r for r in pairs if r['family'] == family])}
    return result


def write_jsonl(path, rows):
    path.write_text(''.join(json.dumps(r, ensure_ascii=False, allow_nan=False)+'\n' for r in rows), encoding='utf-8')


def render_markdown(summary):
    lines = ['# Paired counterfactual rule results', '',
             'All rates use all dataset items/pairs; missing, malformed, or unevaluable outputs receive zero rule credit.',
             'Strict preserves the original wrapper. Diagnostic additionally wraps exactly two bare sequential objects, schema first.',
             'Probe agreement measures this finite test suite, not schema equivalence. Flip rate alone ignores direction; both-correct is primary.', '',
             '| Condition | Mode | N | Format | Profile | Data | Balanced rule | Both-arm suite | Changed probes both correct | Joint pair | Truncated | Missing |',
             '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    def pct(value):
        return '—' if value is None else f'{100*value:.1f}%'
    for condition, modes in summary['conditions'].items():
        for mode, result in modes.items():
            i, p = result['items'], result['pairs']
            lines.append(f'| {condition} | {mode} | {i["n"]} | {pct(i["format_success"])} | {pct(i["schema_validity"])} | {pct(i["data_accuracy"])} | {pct(i["balanced_rule_score"])} | {pct(p["both_suite_pass"])} | {pct(p["discriminating_both_correct_rate"])} | {pct(p["both_joint_success"])} | {i["truncated_outputs"]} | {i["missing_predictions"]} |')
    lines += ['', '## Family breakdown', '', '| Condition | Mode | Family | Pairs | Both-arm suite | Changed probes both correct |', '|---|---|---|---:|---:|---:|']
    for condition, modes in summary['conditions'].items():
        for mode, result in modes.items():
            for family, values in result['by_family'].items():
                p = values['pairs']
                lines.append(f'| {condition} | {mode} | {family} | {p["n_pairs"]} | {pct(p["both_suite_pass"])} | {pct(p["discriminating_both_correct_rate"])} |')
    lines += ['', '## Metric meanings', '',
              '- Profile: valid Draft 2020-12 schema, supported original keywords, correct dialect declaration, and root object type.',
              '- Rule evaluability allows missing dialect or root type, as in the original scorer; an explicitly wrong dialect or unsupported keyword remains unevaluable.',
              '- Balanced rule: mean positive acceptance and negative rejection per item, then macro-average over all items.',
              '- Both-arm suite: every probe correct on both arms of a pair. Changed-probe both-correct requires the correct acceptance direction on both arms.',
              '- Data accuracy uses original numeric/date-time normalization; field accuracy, extra fields, reference compliance and self-consistency remain separately available in summary.json.',
              '- Truncation comes only from explicit truncated=true or finish_reason=length/max_tokens metadata, not guessed from malformed text.',
              '- items.jsonl preserves raw outputs, generated objects, failures, and every probe result. pairs.jsonl aligns expected and predicted decisions across arms.',
              '- conditions_comparison.jsonl aligns every condition pair on the same pair ID and mode; deltas are descriptive, not significance tests.', '']
    return '\n'.join(lines)


def run(pairs_path, prediction_paths, output_dir):
    rows = read_jsonl(pairs_path)
    groups = validate_rows(rows)
    ids = {r['id'] for r in rows}
    summary = {'dataset': str(Path(pairs_path).resolve()), 'n_items': len(rows), 'n_pairs': len(groups), 'conditions': {}}
    all_items, all_pairs, conditions = [], [], set()
    for path in prediction_paths:
        condition = Path(path).stem
        if condition in conditions:
            raise ValueError(f'condition filename stems must be unique: {condition}')
        conditions.add(condition)
        predictions = {}
        for prediction in read_jsonl(path):
            item_id = prediction['id']
            if item_id in predictions or item_id not in ids:
                raise ValueError(f'duplicate or unknown prediction ID in {path}: {item_id}')
            if 'raw_output' not in prediction:
                raise ValueError(f'missing raw_output in {path}: {item_id}')
            predictions[item_id] = prediction
        summary['conditions'][condition] = {}
        for mode in ('strict', 'diagnostic'):
            items = [dict(condition=condition, **score_item(row, predictions.get(row['id']), mode)) for row in rows]
            indexed = {r['id']: r for r in items}
            pairs = [dict(condition=condition, **pair_result([indexed[r['id']] for r in pair])) for pair in groups.values()]
            summary['conditions'][condition][mode] = summarize(items, pairs)
            all_items.extend(items)
            all_pairs.extend(pairs)
    comparisons = []
    condition_order = list(summary['conditions'])
    pair_index = {(r['condition'], r['mode'], r['pair_id']): r for r in all_pairs}
    for i, left in enumerate(condition_order):
        for right in condition_order[i+1:]:
            for mode in ('strict', 'diagnostic'):
                for pair_id in groups:
                    a, b = (pair_index[c, mode, pair_id] for c in (left, right))
                    comparisons.append({'condition_a': left, 'condition_b': right, 'mode': mode,
                                        'pair_id': pair_id, 'family': a['family'],
                                        'both_suite_pass_a': a['both_suite_pass'], 'both_suite_pass_b': b['both_suite_pass'],
                                        'both_suite_pass_delta_b_minus_a': b['both_suite_pass']-a['both_suite_pass'],
                                        'changed_both_correct_a': a['discriminating_both_correct'],
                                        'changed_both_correct_b': b['discriminating_both_correct'],
                                        'changed_probe_total': a['discriminating_probe_total']})
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    (output/'summary.md').write_text(render_markdown(summary), encoding='utf-8')
    write_jsonl(output/'items.jsonl', all_items)
    write_jsonl(output/'pairs.jsonl', all_pairs)
    write_jsonl(output/'conditions_comparison.jsonl', comparisons)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pairs', type=Path, required=True)
    parser.add_argument('--predictions', type=Path, nargs='+', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.pairs, args.predictions, args.output_dir)
    print(f'Scored {result["n_items"]} items / {result["n_pairs"]} pairs; results: {args.output_dir.resolve()}')
