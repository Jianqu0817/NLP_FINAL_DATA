# 冻结检查点对照：格式、数据与规则

本目录包含 2026-11-13 的推理实验，使用原 pilot 的 Qwen3-4B-Instruct-2507、最佳 Adapter 和最佳 LoRA，不重新训练。四个条件是 Base 零样本、Base 加一个简单的完整输出示例、Adapter、LoRA。示例只有一个字符串字段；不演示四类目标规则，但确实展示了整套外层结构、方言声明、必填和禁止额外字段的写法。

## 读结果

- [英文课程报告（可编辑）](report/course_report.md) · [排版 PDF](../output/pdf/cisc7021_schema_adaptation_report.pdf)
- [主测试设计](PROTOCOL.md) · [严格评分](results/summary.md) · [按 Draft 实际执行的补充评分](semantic_results/summary.md)
- [同义改写设计](PARAPHRASE.md) · [同一批题的措辞敏感性](wording_comparison.csv)
- [原 580+100 题的四条件对照](original_control/comparison.csv) · [机械补壳复核](pilot_audit.md) · [原参考标签核查](label_audit.md)
- 原始预测分别位于 predictions/、paraphrase_predictions/ 和 original_control/。每个条件另有配置及耗时。先按 ID 对齐，不把两种措辞当成 96 对独立题。

## 如何解释一次通过

测试题要求同时生成规则（schema）和本条记录（data）。配对主指标要求两端各自接受所有正例、拒绝所有反例；相同记录可以符合两端规则，单看抽取的 data 无法过关。正式评分沿用原任务支持的关键字范围。补充评分检查实际 Draft 2020-12 行为：无效外壳、错误显式方言和引用仍不接受；未知关键字不翻译，尤其不能把 nullable 当作允许 null。两种评分均保留所有题在分母中。

## 在 CPU 上复算

以下 PowerShell 命令从项目根目录运行，不需要 GPU。环境依赖见根目录 requirements.txt。生成器核对已冻结的数据；不覆盖不同的内容。

~~~powershell
python paired_study/build_pairs.py
python paired_study/build_paraphrase.py
foreach ($v in @(
    @('pairs.jsonl','predictions','results','semantic_results'),
    @('paraphrases.jsonl','paraphrase_predictions','paraphrase_results','paraphrase_semantic')
)) {
    $inputs = (Get-ChildItem "paired_study/$($v[1])/*.jsonl").FullName
    python paired_study/score_pairs.py --pairs "paired_study/$($v[0])" --predictions $inputs --output-dir "paired_study/$($v[2])"
    python paired_study/semantic_probe.py --pairs "paired_study/$($v[0])" --predictions $inputs --output-dir "paired_study/$($v[3])"
}
python paired_study/compare_wordings.py
python paired_study/compare_control.py
~~~

原始冻结权重和环境已具备时，可在服务器的项目 Python 环境用 run_inference.py 单独复现一个条件，例如 paired:base_demo、paraphrase:adapter 或 test:base_demo。模型加载、system prompt、批量生成与原指标均复用 scripts/experiment.py。已存在的原始输出禁止覆盖；复现请使用单独的项目副本或输出目录。
