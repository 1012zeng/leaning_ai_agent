# RAG 评测基线

本目录是课程和最终项目共享的固定评测事实源，只包含语料、标注协议、指标契约和数据校验，不实现检索或生成业务逻辑。

## 资产

| 路径 | 作用 |
|---|---|
| `datasets/rag_course_cooking/1.0.0/` | 16 份中文源文档、40 个冻结 chunk、48 条题例、真值、91 条分级标签和 manifest |
| `schemas/dataset_records.schema.json` | SourceDocument、Chunk、EvalCase、GroundTruth、RetrievalLabel 与 manifest 的 JSON Schema |
| `schemas/evaluation_run.schema.json` | 评测运行、per-case 指标、聚合分母、失败归因、延迟和成本结果契约 |
| `metrics/metric_contract.json` | Hit/Recall/MRR/nDCG、上下文、引用、忠实度、相关性、延迟与成本的机器口径 |
| `metrics/baseline_expectations.json` | 关键词、稠密、混合+rerank 的可证伪序位假设，不含伪造分数 |
| `ANNOTATION_GUIDE.md` | 来源优先的标注、相关性等级、响应模式、split 和质量规则 |
| `VERSIONING.md` | 不可变 SemVer 发布与变更流程 |

语料专门覆盖结构化 Markdown、表格、重复通知、跨段/跨文档答案、2024/2026 冲突政策、近名城市干扰、无答案、模糊问题与文档 Prompt Injection。事实为合成课程语料，便于逐字审查，不包含个人信息或外部版权文本。

## 校验

从本目录运行，Python 3.11+，不需要第三方包、网络、GPU 或付费 API：

```powershell
python validate_dataset.py
python -m unittest discover -s tests -v
```

校验覆盖 UTF-8/JSONL、确定性 ID、source bytes/hash、chunk span、manifest count/checksum、case-ground-truth 一一对应、claim-label-citation 闭合、filter 字段、split/category/difficulty/诊断阶段分布、拒答/澄清不变量、旧版本与注入困难负例。

只有在创建新数据集版本时才运行写入命令：

```powershell
python tools/compile_dataset.py --write
python tools/compile_dataset.py --check
```

`authoring/cases.jsonl` 是人工审查入口；编译器把可读 chunk key 解析为契约 ID 并生成发布 JSONL。不要直接编辑生成的 `corpus.jsonl`、`chunks.jsonl`、`eval_cases.jsonl`、`ground_truth.jsonl`、`retrieval_labels.jsonl` 或 `manifest.json`。

## 使用纪律

- train/dev 可用于讲解和调参；test 只能在 system profile 冻结后运行。
- 运行结果必须携带 dataset manifest、system/metric/judge/pricing profiles 和 commit SHA。
- model judge、答案、trace、延迟与成本都是派生/观测数据，不得回写 ground truth。
- fixture 可验证 schema 和失败恢复，但不能充当 faithfulness 或 answer relevance 的质量证据。
