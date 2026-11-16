# 中文改述敏感性测试

这是主测试的独立措辞敏感性检查，不替换冻结的 pairs.jsonl 或其主结果。

## 改了什么

- 每个冻结条目仅替换 input，共 96 行、48 对，每族 12 对。行顺序、ID、arm、family、参考数据、参考 Schema 和全部探针逐项保留。
- 先交代具体材料，再说明字段、类型和规则。四族分别改写数量范围、能否省略、能否为 null、条件必填的中文表达，不添加 Schema 关键字提示。
- 同一对两臂仍只替换一条规则句：材料、字段说明和通用要求完全相同。原来的方向、条件取值及数字均来自冻结参考规则，不重新抽样。
- 保留 Draft 2020-12、$schema 声明、schema/data 单对象输出、禁止额外字段、默认必填、禁止额外约束，以及材料值不能成为固定值限制。

## 来源与检查

build_paraphrase.py 只读取 pairs.jsonl 和 build_pairs.py 的场景元数据，不读取任何预测文件或结果行，也不调用推理服务。改述模板由 Agent 编写，未经过独立人工等义标注；它用于检测另一套措辞下的敏感性，不代表自然语言表达分布。

运行 `python paired_study/build_paraphrase.py`。已有产物若不同会拒绝覆盖。内置检查验证非 input 字段逐项不变、96 行及分族数量、每对相同材料与控制、单条规则句变化，并复用原数据验证，检查探针标签和两臂判别方向。

分族行数：`{"conditional_dependency": 24, "count_bounds": 24, "nullable": 24, "required_optional": 24}`。

## 每族一对示例

### count_bounds

**两臂相同的材料与字段说明：**

收到的材料如下：包名是“周末共读”，书名列表按先后次序列为“山海记”、“河岸笔记”。请据此整理社区读书会的借阅包。这份记录使用两个字段：bundle_name 存放包名，类型为字符串；books 存放书名列表，使用字符串组成的数组，顺序与材料保持一致。

**仅改变的规则句：**

- `count_bounds_01_a`：清单 books 至少要有 2 项，最多只能有 3 项；这两个数量本身也允许。
- `count_bounds_01_b`：清单 books 至少要有 1 项，最多只能有 2 项；这两个数量本身也允许。

### required_optional

**两臂相同的材料与字段说明：**

手头已有这些信息：住客姓名为“林晓”；到店说明并非未知，内容是“晚间抵达”。现在请整理民宿预订记录。住客姓名写入 guest_name，这是必须提供的字符串字段；到店说明对应字段 arrival_note，用来存放文本。

**仅改变的规则句：**

- `required_optional_01_a`：提交记录时可以不带 arrival_note，漏掉这一项也符合要求。只要填写了 arrival_note，它就必须是字符串，不能填 null。
- `required_optional_01_b`：提交记录时一定要带上 arrival_note，不能把它漏掉。只要填写了 arrival_note，它就必须是字符串，不能填 null。

### nullable

**两臂相同的材料与字段说明：**

手头已有这些信息：动物名字为“豆豆”；健康说明并非未知，内容是“已完成检查”。现在请录入宠物领养记录。动物名字写入 pet_name，这是必须提供的字符串字段；健康说明对应字段 health_note，用来存放文本。

**仅改变的规则句：**

- `nullable_01_a`：health_note 这一项无论如何都不能省略；它的值必须写字符串，不接受 null。
- `nullable_01_b`：health_note 这一项无论如何都不能省略；它的值可以写字符串，也可以写 null。

### conditional_dependency

**两臂相同的材料与字段说明：**

这次收到的内容是：报名类型选择了“个人”，另外已给出联络说明“邮件联系”。请把这份材料用于整理工作坊报名。报名类型使用字段 enrollment_type：它必须出现，类型是字符串，可选值只有“个人”和“团体”。联络说明使用字段 contact_note；一旦填写，内容必须是字符串而不能是 null。

**仅改变的规则句：**

- `conditional_dependency_01_a`：是否必须填写 contact_note，要看 enrollment_type 的选择：选“团体”就不能缺少 contact_note；选“个人”则不要求提供 contact_note，可以直接省略。
- `conditional_dependency_01_b`：是否必须填写 contact_note，要看 enrollment_type 的选择：选“个人”就不能缺少 contact_note；选“团体”则不要求提供 contact_note，可以直接省略。

### 各族、各臂共用的结尾

每个对象只能使用已列出的字段，不接受额外字段。没有明确说可以省略、也不是仅在指定情况下才要求出现的字段，都必须提供。不要自行增加取值、长度或数量方面的约束；材料给出的具体内容只用于这条数据，不能据此把字段限定成固定值。结果需要同时包含整理好的数据与相应的 JSON Schema：采用 Draft 2020-12，并写出 $schema 声明。回复只能是一个 JSON 对象，恰好使用 schema 和 data 两个键。

## 使用

推理时把数据入口改为 paraphrases.jsonl，其他系统提示、few-shot、生成设置、checkpoint 和评分规则保持原条件。与主测试按相同 ID 配对比较；此文件的生成不运行推理。
