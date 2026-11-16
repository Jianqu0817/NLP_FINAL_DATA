"""Build one alternate Chinese wording for every frozen paired-study item.

Reads only the frozen dataset and the original scenario metadata, never
predictions. Writes paraphrases.jsonl and PARAPHRASE.md beside this script.
"""
from __future__ import annotations

import copy
from collections import Counter, defaultdict
import json
from pathlib import Path

import build_pairs as primary

HERE = Path(__file__).resolve().parent
SUFFIX = ('每个对象只能使用已列出的字段，不接受额外字段。没有明确说可以省略、'
          '也不是仅在指定情况下才要求出现的字段，都必须提供。不要自行增加取值、'
          '长度或数量方面的约束；材料给出的具体内容只用于这条数据，不能据此把字段限定成固定值。'
          '结果需要同时包含整理好的数据与相应的 JSON Schema：采用 Draft 2020-12，'
          '并写出 $schema 声明。回复只能是一个 JSON 对象，恰好使用 schema 和 data 两个键。')


def pieces(row):
    family = row['family']
    index = int(row['pair_id'].rsplit('_', 1)[1])-1
    schema, data = row['reference_schema'], row['reference_data']
    if family == 'count_bounds':
        scene, label, key, _, list_label, list_key, _ = primary.COUNTS[index]
        material = f'收到的材料如下：{label}是“{data[key]}”，{list_label}按先后次序列为'
        material += '、'.join(f'“{item}”' for item in data[list_key])+'。'
        common = (f'请据此{scene}。这份记录使用两个字段：{key} 存放{label}，类型为字符串；'
                  f'{list_key} 存放{list_label}，使用字符串组成的数组，顺序与材料保持一致。')
        lo, hi = (schema['properties'][list_key][k] for k in ('minItems', 'maxItems'))
        clause = f'清单 {list_key} 至少要有 {lo} 项，最多只能有 {hi} 项；这两个数量本身也允许。'
    elif family in ('required_optional', 'nullable'):
        table = primary.OPTIONALS if family == 'required_optional' else primary.NULLABLES
        scene, label, key, _, target_label, target, _ = table[index]
        material = f'手头已有这些信息：{label}为“{data[key]}”；{target_label}并非未知，内容是“{data[target]}”。'
        common = (f'现在请{scene}。{label}写入 {key}，这是必须提供的字符串字段；'
                  f'{target_label}对应字段 {target}，用来存放文本。')
        if family == 'required_optional':
            presence = (f'提交记录时一定要带上 {target}，不能把它漏掉。' if target in schema['required'] else
                        f'提交记录时可以不带 {target}，漏掉这一项也符合要求。')
            clause = presence+f'只要填写了 {target}，它就必须是字符串，不能填 null。'
        else:
            nullable = 'null' in schema['properties'][target]['type'] if isinstance(schema['properties'][target]['type'], list) else False
            value_rule = '可以写字符串，也可以写 null' if nullable else '必须写字符串，不接受 null'
            clause = f'{target} 这一项无论如何都不能省略；它的值{value_rule}。'
    elif family == 'conditional_dependency':
        scene, label, key, states, target_label, target, _ = primary.CONDITIONALS[index]
        material = f'这次收到的内容是：{label}选择了“{data[key]}”，另外已给出{target_label}“{data[target]}”。'
        common = (f'请把这份材料用于{scene}。{label}使用字段 {key}：它必须出现，'
                  f'类型是字符串，可选值只有“{states[0]}”和“{states[1]}”。'
                  f'{target_label}使用字段 {target}；一旦填写，内容必须是字符串而不能是 null。')
        required_state = schema['if']['properties'][key]['const']
        optional_state = next(state for state in states if state != required_state)
        clause = (f'是否必须填写 {target}，要看 {key} 的选择：选“{required_state}”就不能缺少 {target}；'
                  f'选“{optional_state}”则不要求提供 {target}，可以直接省略。')
    else:
        raise ValueError(f'unknown family: {family}')
    return material+common, clause, SUFFIX


def build(rows):
    primary.validate(rows)
    output, groups = [], defaultdict(list)
    for row in rows:
        common, clause, suffix = pieces(row)
        result = copy.deepcopy(row)
        result['input'] = common+clause+suffix
        if result['input'] == row['input']:
            raise ValueError(f'wording unchanged: {row["id"]}')
        if {k: v for k, v in result.items() if k != 'input'} != {k: v for k, v in row.items() if k != 'input'}:
            raise ValueError(f'non-input content changed: {row["id"]}')
        groups[row['pair_id']].append((common, clause, suffix))
        output.append(result)
    for pair_id, pair in groups.items():
        a, b = pair
        if a[0] != b[0] or a[2] != b[2] or a[1] == b[1]:
            raise ValueError(f'not a single-clause paired change: {pair_id}')
    primary.validate(output)
    return output


def documentation(rows):
    counts = Counter(r['family'] for r in rows)
    lines = ['# 中文改述敏感性测试', '',
             '这是主测试的独立措辞敏感性检查，不替换冻结的 pairs.jsonl 或其主结果。', '',
             '## 改了什么', '',
             '- 每个冻结条目仅替换 input，共 96 行、48 对，每族 12 对。行顺序、ID、arm、family、参考数据、参考 Schema 和全部探针逐项保留。',
             '- 先交代具体材料，再说明字段、类型和规则。四族分别改写数量范围、能否省略、能否为 null、条件必填的中文表达，不添加 Schema 关键字提示。',
             '- 同一对两臂仍只替换一条规则句：材料、字段说明和通用要求完全相同。原来的方向、条件取值及数字均来自冻结参考规则，不重新抽样。',
             '- 保留 Draft 2020-12、$schema 声明、schema/data 单对象输出、禁止额外字段、默认必填、禁止额外约束，以及材料值不能成为固定值限制。', '',
             '## 来源与检查', '',
             'build_paraphrase.py 只读取 pairs.jsonl 和 build_pairs.py 的场景元数据，不读取任何预测文件或结果行，也不调用推理服务。'
             '改述模板由 Agent 编写，未经过独立人工等义标注；它用于检测另一套措辞下的敏感性，不代表自然语言表达分布。', '',
             '运行 `python paired_study/build_paraphrase.py`。已有产物若不同会拒绝覆盖。'
             '内置检查验证非 input 字段逐项不变、96 行及分族数量、每对相同材料与控制、单条规则句变化，'
             '并复用原数据验证，检查探针标签和两臂判别方向。', '',
             f'分族行数：`{json.dumps(dict(sorted(counts.items())), ensure_ascii=False)}`。', '',
             '## 每族一对示例', '']
    for family in ('count_bounds', 'required_optional', 'nullable', 'conditional_dependency'):
        sample = sorted((r for r in rows if r['pair_id'] == family+'_01'), key=lambda r: r['arm'])
        common, _, suffix = pieces(sample[0])
        lines += [f'### {family}', '', '**两臂相同的材料与字段说明：**', '', common, '', '**仅改变的规则句：**', '']
        for row in sample:
            lines += [f'- `{row["id"]}`：{pieces(row)[1]}']
        lines += ['']
    lines += ['### 各族、各臂共用的结尾', '', SUFFIX, '',
              '## 使用', '',
              '推理时把数据入口改为 paraphrases.jsonl，其他系统提示、few-shot、生成设置、checkpoint 和评分规则保持原条件。'
              '与主测试按相同 ID 配对比较；此文件的生成不运行推理。', '']
    return '\n'.join(lines)


def write_frozen(path, content):
    if path.exists():
        if path.read_text(encoding='utf-8') != content:
            raise ValueError(f'existing frozen paraphrase artifact differs; not overwritten: {path}')
    else:
        path.write_text(content, encoding='utf-8', newline='\n')


if __name__ == '__main__':
    source = [json.loads(line) for line in (HERE/'pairs.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    output = build(source)
    write_frozen(HERE/'paraphrases.jsonl', ''.join(json.dumps(r, ensure_ascii=False, separators=(',', ':'))+'\n' for r in output))
    write_frozen(HERE/'PARAPHRASE.md', documentation(output))
    print('Paraphrases ready: 96 rows / 48 pairs; only input changed, one rule clause differs within each pair.')
