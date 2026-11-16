"""Independent, deterministic evaluation of joint Schema + data generation."""
import copy
import hashlib
import json
import math
from datetime import datetime, timezone
from collections import Counter
from jsonschema import Draft202012Validator, FormatChecker

DIALECT = 'https://json-schema.org/draft/2020-12/schema'
CHECKER = FormatChecker()
KEYWORDS = {'$schema','type','properties','required','additionalProperties','items',
            'minItems','maxItems','enum','minimum','maximum','minLength','maxLength',
            'pattern','format','if','then','else','dependentRequired','oneOf','anyOf',
            'allOf','const','description','title'}

def dumps(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'))

def digest(x):
    return hashlib.sha256(dumps(x).encode()).hexdigest()

def profile(schema, root=True):
    if not isinstance(schema, dict):
        raise ValueError('schema must be an object')
    extra = set(schema) - KEYWORDS
    if extra:
        raise ValueError(f'unsupported keywords: {sorted(extra)}')
    if root and (schema.get('$schema') != DIALECT or schema.get('type') != 'object'):
        raise ValueError('root must declare Draft 2020-12 and object type')
    if 'additionalProperties' in schema and not isinstance(schema['additionalProperties'], bool):
        raise ValueError('additionalProperties must be boolean in this profile')
    for child in schema.get('properties', {}).values():
        profile(child, False)
    for key in ['items','if','then','else']:
        if key in schema:
            profile(schema[key], False)
    for key in ['oneOf','anyOf','allOf']:
        for child in schema.get(key, []):
            profile(child, False)

def validator(schema):
    Draft202012Validator.check_schema(schema)
    profile(schema)
    return Draft202012Validator(schema, format_checker=CHECKER)

def strict_loads(text):
    def pairs(ps):
        out = {}
        for k, v in ps:
            if k in out:
                raise ValueError('duplicate key')
            out[k] = v
        return out
    def constant(s):
        raise ValueError(f'non-JSON constant {s}')
    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)

def pair(text):
    obj = strict_loads(text)
    if not isinstance(obj, dict) or set(obj) != {'schema','data'}:
        raise ValueError('expected exactly schema and data')
    if not all(isinstance(obj[k], dict) for k in obj):
        raise ValueError('schema and data must be objects')
    return obj['schema'], obj['data']

def paths(obj, path=()):
    yield path, obj
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from paths(v, path+(k,))
    elif isinstance(obj, list):
        for k, v in enumerate(obj):
            yield from paths(v, path+(k,))

def replace(obj, path, value, delete=False):
    if not path:
        return copy.deepcopy(value)
    out = copy.deepcopy(obj)
    cur = out
    for k in path[:-1]:
        cur = cur[k]
    if delete:
        del cur[path[-1]]
    else:
        cur[path[-1]] = copy.deepcopy(value)
    return out

def schema_values(schema):
    """Values at and around each declared boundary, including conditional branches."""
    values = []
    if isinstance(schema, dict):
        values += schema.get('enum', [])
        if 'const' in schema:
            values.append(schema['const'])
        for k in ['minimum','maximum']:
            if k in schema:
                v = schema[k]
                values.extend([v-1, v, v+1])
        for v in schema.values():
            values.extend(schema_values(v))
    elif isinstance(schema, list):
        for v in schema:
            values.extend(schema_values(v))
    return values

def simple_value(schema):
    if 'const' in schema:
        return schema['const']
    if 'enum' in schema:
        return schema['enum'][0]
    kind=schema.get('type','string')
    if isinstance(kind,list):
        kind=next((t for t in kind if t!='null'),'null')
    if kind=='object':
        return {k:simple_value(v) for k,v in schema.get('properties',{}).items()}
    if kind=='array':
        return [simple_value(schema.get('items',{})) for _ in range(schema.get('minItems',1))]
    if kind in ('integer','number'):
        return schema.get('minimum',min(1,schema.get('maximum',1)))
    if kind=='boolean':
        return False
    if kind=='null':
        return None
    fmt=schema.get('format')
    formats={'email':'alternate@example.org','date':'2026-12-20',
             'date-time':'2026-12-20T08:00:00+08:00','time':'08:00:00'}
    return formats.get(fmt,'A'*max(schema.get('minLength',1),1))

def schema_at(schema,path):
    for k in path:
        schema=schema.get('items',{}) if isinstance(k,int) else schema.get('properties',{}).get(k,{})
    return schema

def witnesses(row):
    """Build witnesses BEFORE inference, from reference requirements only.

    This finite mutation suite is not a logical equivalence proof.
    Every mutation is reclassified by the reference validator.
    """
    data, schema = row['reference_data'], row['reference_schema']
    val = validator(schema)
    val.validate(data)
    positive, negative = [], []
    seen = set()
    boundaries = schema_values(schema)
    candidates = [(data, 'reference')]
    for path, value in paths(data):
        label = '/'.join(map(str, path)) or '$'
        options = [None, True, False, 0, 1, -1, '', '替换文本', '007', [], {}]
        if isinstance(value, str):
            options += [value+'甲', '另一值', '2026-12-20', '2026-12-20T08:00:00+08:00',
                        '09:15:00', 'other@example.org', '00012', '2026-02-30']
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            options += [value-1, value+1, value+0.5]
        elif isinstance(value, list):
            options += [value[:max(0,len(value)-1)], value+[copy.deepcopy(value[0])] if value else [None]]
        elif isinstance(value, dict):
            extra = copy.deepcopy(value)
            extra['unexpected_field'] = 'extra'
            options.append(extra)
            local_schema=schema_at(schema,path)
            props=local_schema.get('properties',{})
            filled={k:copy.deepcopy(value[k]) if k in value else simple_value(s) for k,s in props.items()}
            variants=[filled]
            for k,s in props.items():
                for alternative in s.get('enum',[]):
                    v=copy.deepcopy(filled);v[k]=alternative;variants.append(v)
            for variant in variants:
                options.append(variant)
                for k in props:
                    if k not in local_schema.get('required',[]):
                        v=copy.deepcopy(variant);v.pop(k,None);options.append(v)
        options += [v for v in boundaries if not isinstance(v, (dict,list))]
        for option in options:
            candidates.append((replace(data,path,option), label+':replace'))
        if path:
            candidates.append((replace(data,path,None,True),label+':delete'))
    # Multiple-field alternatives help expose schemas overfitted to one instance.
    for instance, label in candidates:
        key = dumps(instance)
        if key in seen:
            continue
        seen.add(key)
        destination = positive if val.is_valid(instance) else negative
        destination.append({'instance': instance, 'mutation': label})
    # Keep all finite witnesses: no candidate-conditioned selection or silent cap.
    if not positive or not negative:
        raise ValueError(f'empty witness class for {row["id"]}')
    return {'positive': positive, 'negative': negative}

def leaves(obj):
    return {p: v for p, v in paths(obj) if not isinstance(v,(dict,list)) or not v}

def normalize_data(value,schema):
    if isinstance(value,dict):
        return {k:normalize_data(v,schema.get('properties',{}).get(k,{})) for k,v in value.items()}
    if isinstance(value,list):
        return [normalize_data(v,schema.get('items',{})) for v in value]
    if isinstance(value,float) and value.is_integer():
        return int(value)
    if isinstance(value,str) and schema.get('format')=='date-time':
        try:
            dt=datetime.fromisoformat(value.replace('Z','+00:00'))
            if dt.tzinfo is not None:
                return dt.astimezone(timezone.utc).isoformat()
        except ValueError:
            pass
    return value

def score(row, text, suite):
    result = dict(format_success=0, schema_meta_validity=0, schema_validity=0, schema_rule_evaluable=0, positive_acceptance=0.,
                  negative_rejection=0., balanced_rule_score=0., schema_suite_pass=0,
                  data_accuracy=0, reference_compliance=0, self_consistency=0,
                  joint_success=0, field_correct=0, field_total=len(leaves(row['reference_data'])),
                  extra_fields=0, error=None)
    try:
        schema, data = pair(text)
        result['format_success'] = 1
    except Exception as exc:
        result['error'] = 'format: '+str(exc)
        return result
    reference = validator(row['reference_schema'])
    normalized_prediction=normalize_data(data,row['reference_schema'])
    normalized_reference=normalize_data(row['reference_data'],row['reference_schema'])
    result['data_accuracy'] = int(dumps(normalized_prediction) == dumps(normalized_reference))
    result['reference_compliance'] = int(reference.is_valid(data))
    gold, predicted = leaves(normalized_reference), leaves(normalized_prediction)
    result['field_correct'] = sum(p in predicted and dumps(predicted[p]) == dumps(v) for p,v in gold.items())
    result['extra_fields'] = len(set(predicted)-set(gold))
    try:
        Draft202012Validator.check_schema(schema)
        result['schema_meta_validity'] = 1
        try:
            profile(schema)
            result['schema_validity'] = 1
        except ValueError as exc:
            result['error']='profile: '+str(exc)
        # Rule meaning is measured separately from a missing dialect declaration.
        profile(schema,root=False)
        if '$schema' in schema and schema['$schema'] != DIALECT:
            raise ValueError('unsupported declared dialect')
        val=Draft202012Validator(schema,format_checker=CHECKER)
        result['schema_rule_evaluable'] = 1
        pos = [val.is_valid(w['instance']) for w in suite['positive']]
        neg = [not val.is_valid(w['instance']) for w in suite['negative']]
        result['positive_acceptance'] = sum(pos)/len(pos)
        result['negative_rejection'] = sum(neg)/len(neg)
        result['balanced_rule_score'] = (result['positive_acceptance']+result['negative_rejection'])/2
        result['schema_suite_pass'] = int(all(pos) and all(neg))
        result['self_consistency'] = int(val.is_valid(data))
    except Exception as exc:
        result['error'] = 'schema: '+str(exc)
    result['joint_success'] = int(all(result[k] for k in
        ['format_success','schema_validity','schema_suite_pass','data_accuracy','reference_compliance','self_consistency']))
    return result

RATES = ['format_success','schema_meta_validity','schema_validity','schema_rule_evaluable','positive_acceptance','negative_rejection',
         'balanced_rule_score','schema_suite_pass','data_accuracy','reference_compliance',
         'self_consistency','joint_success']

def aggregate(records):
    n = len(records)
    metrics = {'n': n}
    metrics.update({k: sum(r['metrics'][k] for r in records)/n if n else None for k in RATES})
    denominator = sum(r['metrics']['field_total'] for r in records)
    metrics['field_accuracy'] = sum(r['metrics']['field_correct'] for r in records)/denominator if denominator else None
    metrics['extra_fields'] = sum(r['metrics']['extra_fields'] for r in records)
    metrics['truncated_outputs'] = sum(r.get('truncated',False) for r in records)
    for group in ['rule_tags','family','track']:
        buckets = {}
        for record in records:
            values = record.get(group,[]) if group == 'rule_tags' else [record.get(group,'unknown')]
            for v in values:
                buckets.setdefault(v,[]).append(record)
        metrics['by_'+group] = {v: {'n':len(rs), **{k:sum(r['metrics'][k] for r in rs)/len(rs) for k in RATES}}
                                for v,rs in buckets.items()}
    return metrics
