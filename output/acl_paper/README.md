# 瓶颈 Adapter 如何影响规则生成？ / How Do Bottleneck Adapters Shape Rule Generation?

中英文稿根据同一组已完成的 CISC7021 实验撰写。入口为 paper_en.tex 和 paper_zh.tex；body_en.tex、body_zh.tex 为正文。共用 tables.tex、appendix.tex（双语标题与正文）和 references.bib，以保持结果一致。

排版使用 ACL 官方仓库 acl-org/acl-style-files 的 acl.sty 与 acl_natbib.bst（版本 d5adc823ff0f80f98c80405ca0ab66c68e684409，https://github.com/acl-org/acl-style-files）。采用 preprint 模式：双栏、作者—年份引文、页码，无审稿行号。署名栏目前显示课程项目；提交课程作业时可将两个入口里的 PaperAuthor 改为自己的姓名与院系。

## 编译

使用 XeLaTeX + BibTeX（MiKTeX 或 TeX Live）。英文正文使用 Times New Roman；中文稿另用 xeCJK，优先使用 Windows 宋体/黑体/楷体，否则使用 Fandol。无 Times New Roman 的系统可将两个入口里的字体名改为 TeX Gyre Termes。

在本目录运行（中文把 paper_en 改为 paper_zh）：

    xelatex paper_en
    bibtex paper_en
    xelatex paper_en
    xelatex paper_en

## 证据

原始实验说明位于项目的 mechanism_study/report/mechanism_report.md；数值表与逐题对照位于 mechanism_study/analysis/。较早的实验见 paired_study/report/course_report.md。本次只重写论文、编排图表；未增加模型运行。
