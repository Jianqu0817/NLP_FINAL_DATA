# 期末报告改版方案（已实施 · 2026-11-16）

**状态：三轮修订全部实施并双语编译通过（EN 6 页 / ZH 5 页，零错误零引用警告）。**

**第三轮（结构精简 + 披露/局限性重写）：**
- 引言 4 段→3 段：删除全部实验数字（20.9%/580/挑战集/36.0%/48.1%/30/32/3/16→8/16）与三阶段流程史；发现预告改定性表述；贡献 (iii) 去掉重复的"两个分数一起报告"尾巴。数字迁移：pilot 数据移入 Design 导语，30/32 与 3/16→8/16 只存于摘要与 Results。
- 相关工作第一段重写为"自己立论"结构：压缩引用密度（6 引 5 句→4 引 3 句），新增立场句（"放置一直按每参数准确率挑选；放置对适配后所写内容的影响未被分离"），删 LoRA 定义句（引用移至 Conditions 处补挂）。
- 实验设计：删 `\subsection{Why paired executable evaluation}`，改为 `\paragraph{Goal and design rationale.}` 总目标导语（问题 + 三要素 + pilot 数字归位）+ `\paragraph{Hypotheses and conditions.}`（假设并入条件段）。
- AI 与数据披露：删"成对材料、分析代码和论文写作使用了AI辅助"；加"数据经过人工抽样检查以验证正确性"；"保存在项目中"→"archived on GitHub"（脚注 URL），按用户要求删去 checkpoints（体积原因）。
- 局限性整段重写：Adapter 方法局限与效果上限为主体（各轴代价 + 最好配置仍 8/7/10 对未过 + LoRA 上限对比），一句原因（低秩残差更新只能调制既有表征），保留有限探针/双口径并报一句，实验不足压缩为末句。原段全部事实信息保留。
- 注意事项：GitHub 仓库 Jianqu0817/NLP_FINAL_DATA 当前为空，用户将随后推送内容；仓库 README 需与论文"人工抽样检查"口径一致（原 README 写 not human-validated）。
**第一轮（场景化 + 文献加厚）：** 用户两条修改意见：① Related Work 加入插入位置的残差流机理视角（Elhage et al. 2021，作为设计假设而非机理断言）；② 闹钟背景保留但简化。实施结果：

- 引言四段：简化版闹钟场景（第 1 段仅保留"本地小模型 + 严格接口 + 20.9% + 挑战集全败于外壳 + 冻结骨干热插拔"）→ 记录与契约/沉默延迟失败 → 三阶段验证式路径 → 问题、发现与三条贡献。
- Related Work：放置脉络段（Houlsby→MAD-X→AdapterFusion→AdapterDrop→He 统一坐标→D–E 定位）+ 新增残差流机理视角段。
- 实验设计新增 "\subsection{Why paired executable evaluation / 为什么采用配对的可执行评估}"（含 20.9%→35.2% 包装证据）与 "\paragraph{Design viewed as hypotheses / 作为假设的设计}"（A–B/B–D/D–E 三个假设）。
- references.bib 新增 4 条已核实条目：pfeiffer2020、pfeiffer2021、ruckle2021、elhage2021。
- 摘要与标题未改动；编译结果 paper_en.pdf 6 页、paper_zh.pdf 5 页，无未定义引用、无错误、无 overfull。
- 旧引言第 2 段的 35.2% 包装证据移入新评估动机小节，未丢失。
- **文风校准（同日第二 pass，用户批准）**：删贡献列表尾部 "reported with single-seed caution"、假设段末 "not confirmatory tests" 整句、结果节 LoRA 参照句与 "little basis for a general claim" 防御句；结论新增一句前瞻（多种子与其他规则族检验位置效应的普适性）。中英文同步。校准后 single-seed 仅存摘要 1 处（范围声明），exploratory/confirmatory 移交局限性承担，零数字改动；重编译 EN 6 页 / ZH 5 页无错误。

**待办（用户确认终稿后）**：重新打包 `CISC7021_小组报告与汇报材料_*.zip`、同步 group_share 的先读我/讲稿口径。以下为原审阅稿，供对照。

---

---

## 1. 新引言（英文全文草稿）

四段结构：场景 → 记录与契约（沉默失败）→ 验证式研究路径 → 问题、发现与贡献。

```latex
\section{Introduction}
A privately deployed assistant is asked to set an alarm: ``Wake me at 6:30 on
workdays, tag it `workout'; the note can stay empty.'' The alarm application
accepts records only through a strict interface; a wrong field name, type, or
wrapper is rejected outright. A four-billion-parameter model running on the
user's own hardware keeps such schedules local, but it fails at precisely this
step: in our pilot the unadapted model reached strict joint success on only
20.9\% of 580 requests, and on the challenge split every baseline failure
began with an invalid wrapper. Parameter-efficient adaptation is the natural
remedy when a deployment cannot afford per-application copies of the backbone:
keep one frozen model and swap in a small trainable module---11.9M parameters
here---for each application.

The record, however, is only half of the deliverable. The same request states
rules for \emph{future} records: which fields are required, whether the note
may be empty, what a repeat-day list may contain. We ask the model to emit
these rules as an executable JSON Schema alongside the current instance, and
downstream validation runs against that contract, not against today's
example. A schema is thus a program for records nobody has submitted yet:
filling today's alarm correctly says nothing about whether a legitimate alarm
next month will be accepted. The most damaging failures are silent and
delayed---for instance a length bound attached to an array that nobody
constrained, rejecting valid records long after generation. Our experiments
use synthetic Chinese requirements whose rule families (count bounds,
optionality, nullability, conditional dependency) mirror such assistant-side
constraints; we do not evaluate on alarm data itself.

Which adapter should such a deployment choose? Adapter designs differ along
three axes: the activation inside the bottleneck, its width, and the point in
the transformer where the update is applied. We treated these axes as
hypotheses to test rather than defaults to inherit, in three stages. A pilot
trained one width-64 SiLU adapter and one LoRA on 2,300 requests and compared
them with the frozen base on 580 held-out requests: strict joint success rose
from 20.9\% to 36.0\% and 48.1\%, respectively. A frozen-checkpoint follow-up
then separated formatting from extraction and rule behavior and exposed a
rule-level failure invisible in the joint score: count bounds placed at the
object root, collapsing after paraphrase. The present study isolates the three
axes through pre-specified single-variable contrasts between adapter variants
trained under the original recipe.

When a requirement bounds one array and leaves another unrestricted, which
designs enforce the bound on the target array and leave the distractor free?
Across frozen paired tests that change one rule sentence while holding the
instance fixed, with wording and sentence-order variants, insertion site
produced the clearest separation: moving a width-16 affine module from the
completed block output to the post-attention residual left changed-rule
correctness unchanged (30/32) while complete count-suite success rose from
3/16 to 8/16 pairs on original wording. Item-level comparison locates the
difference: the post-block module attached an unjustified \texttt{maxItems}
to the unrestricted array. Removing SiLU repaired one placement error without
improving complete suites; narrowing the bottleneck preserved target bounds
while over-constraining the distractor. Our contributions: (i) an executable
paired evaluation that scores changed-rule correctness and invariant fidelity
separately; (ii) pre-specified activation, width, and site contrasts on a
modern decoder-only LLM, reported with single-seed caution; (iii) a traced
case in which equal changed-rule totals conceal divergent restriction
behavior, arguing that the two scores be reported together.
```

### 每段的数字溯源（均已核对）

| 断言 | 来源 |
|---|---|
| Base 580 题联合 20.9%（20.8621%）| WORK_STATE pilot 记录 / results |
| challenge 100 题基线全部因原始外壳格式失败（91+9）| WORK_STATE 2026-11-05 |
| Adapter 11,890,944 ≈ 11.9M | README 模型节 |
| 36.0% / 48.1%（36.0345 / 48.1034）| 同 pilot 记录 |
| 2300 训练请求 | data/manifest 冻结计数 |
| 改写后数量对崩溃（12/12→1/12）、根节点放置错误 | paired_study 结果（论文已引用）|
| 30/32、3/16→8/16、maxItems 泄漏 | mechanism_study/analysis/evidence.md |

## 2. Related Work：替换第一段（放置脉络），第二段不动

```latex
Bottleneck adapters freeze the pretrained network and add small modules that
map a hidden state into a lower-dimensional space and back, appended to the
trained computation \citep{houlsby2019}. Subsequent work made placement
itself a design variable: \citet{pfeiffer2020} obtained strong cross-lingual
transfer from a single adapter after the feed-forward sublayer, with modular
language and task adapters that can be swapped and reused;
\citet{pfeiffer2021} composed separately trained task adapters without
retraining any of them; \citet{ruckle2021} found that adapters in lower
layers can be removed at little cost, indicating that sites do not
contribute equally. \citet{he2022} unified these variants along two
separable axes---how the update is computed and where it is applied---and
identified attaching a bottleneck parallel to the feed-forward sublayer as a
particularly effective placement. LoRA \citep{hu2022} instead learns
low-rank updates to attention projections and serves here as a reference
method, not a site control. Our D--E contrast moves one trained form along
exactly the site axis, on a decoder-only LLM, and measures the effect on
generated rule behavior rather than task accuracy.
```

现有第二段（CheckList + Draft 2020-12）保持原文。

新增 `references.bib` 条目（三篇均已对照 ACL Anthology 核实，含页码）：

```bibtex
@inproceedings{pfeiffer2020,
 author={Jonas Pfeiffer and Ivan Vuli{\'c} and Iryna Gurevych and Sebastian Ruder},
 title={{MAD-X}: An Adapter-Based Framework for Multi-Task Cross-Lingual Transfer},
 booktitle={Proceedings of the 2020 Conference on Empirical Methods in Natural Language Processing (EMNLP)},
 pages={7654--7673}, year={2020}, publisher={Association for Computational Linguistics},
 url={https://aclanthology.org/2020.emnlp-main.617/}}
@inproceedings{pfeiffer2021,
 author={Jonas Pfeiffer and Aishwarya Kamath and Andreas R{\"u}ckl{\'e} and Kyunghyun Cho and Iryna Gurevych},
 title={AdapterFusion: Non-Destructive Task Composition for Transfer Learning},
 booktitle={Proceedings of the 16th Conference of the European Chapter of the Association for Computational Linguistics (EACL)},
 pages={487--503}, year={2021}, publisher={Association for Computational Linguistics},
 url={https://aclanthology.org/2021.eacl-main.39/}}
@inproceedings{ruckle2021,
 author={Andreas R{\"u}ckl{\'e} and Gregor Geigle and Max Glockner and Till Beck and Jonas Pfeiffer and Nils Reimers and Iryna Gurevych},
 title={AdapterDrop: On the Efficiency of Adapters in Transformers},
 booktitle={Proceedings of the 2021 Conference on Empirical Methods in Natural Language Processing (EMNLP)},
 pages={7930--7946}, year={2021}, publisher={Association for Computational Linguistics},
 url={https://aclanthology.org/2021.emnlp-main.626/}}
```

## 3. 配套修改（逐项，均待批准）

1. **摘要首句**（两个选项，其余摘要不动）：
   - 保留现状："Generating a correct JSON instance does not guarantee..."；
   - 场景化改写："A deployed assistant that emits both a record and its validation rules can fill the record correctly while writing rules that reject future legitimate records."（推荐，与引言呼应）
2. **Design 开头新增"假设视角"小段**（可选但推荐，落实"验证与探索"）：
   ```latex
   \paragraph{Design viewed as hypotheses.}
   The three contrasts test separable properties of the update. Activation:
   inside an already nonlinear decoder a nonlinear bottleneck may be
   redundant; A--B asks whether SiLU changes rule behavior at matched width.
   Width: the bottleneck bounds the rank of the update; B--D asks whether a
   narrower update preserves the target rule while narrowing what else
   changes. Site: an update written after attention enters the same block's
   MLP, whereas an update written after the completed block is read only by
   later layers; D--E asks whether this difference affects where generated
   constraints land. These are exploratory single-seed contrasts on selected
   checkpoints, not confirmatory tests.
   ```
3. **补一页内容以接近 6 页**（二选一或都做）：
   - A. 新增一张小图：D/E 两种插入位置的结构示意 + `confirm_count_04` 中 D 给 `gel_codes` 多写 `maxItems:2` 的 schema 片段对照（最能自解释核心发现，汇报时也可直接用）；
   - B. 在 Design 前加一小节 "From whole-task success to rule behavior"，把 pilot→paired→mechanism 的路径写成 4–6 句背景（内容全部来自已有报告，无新主张）。
4. **中文镜像**：`body_zh.tex` 同步以上全部改动（引言四段、文献段、假设段、图/小节）。
5. **重编译与发布**：XeLaTeX+BibTeX 双语重编译；数字一致性复核；重新打包 `CISC7021_小组报告与汇报材料_*.zip` 并同步 group_share 的先读我/讲稿口径。

## 4. 不改动的部分

标题、Experimental Design 的其余内容、Results、Conclusion、Limitations、AI and Data Disclosure、全部表格数字。Limitations 已含单种子与合成数据声明，与引言的 "we do not evaluate on alarm data itself" 一致。

## 5. 待确认

- 摘要首句用哪个选项；
- 第 3.3 项选 A、B 还是都做；
- 引言第四段贡献 (iii) 的措辞是否满意；
- 场景中的具体举例（6:30/工作日/workout 标签/可空备注）是否需要换成你想要的细节。
