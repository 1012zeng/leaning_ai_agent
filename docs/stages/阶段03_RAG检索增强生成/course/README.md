# RAG 必修课程：从对象与调用链做工程决策

> 课程版本：1.0.0 | 状态：Stage 2 实现版 | 契约：`MUJI-19-RAG-CONTRACTS 1.0.0` | 官方资料核对日期：2026-08-31

## 你最终要证明什么

完成本阶段后，你不只要“会搭 RAG”，还要能提供五类证据：

| 能力 | 可观察证据 |
|---|---|
| 读代码 | 从入口追踪一条对象链，指出每次 shape/type/字段变化和模块所有者 |
| 改代码 | 只改变一个 profile 参数，保留版本与配置哈希，测试没有破坏不变量 |
| 诊断 | 从症状提出假设，用 trace 和中间对象定位失败阶段，而不是盲目换模型 |
| 做实验 | 固定数据、代码、索引和指标口径，报告对照组、变量、结果和不确定性 |
| 做交付 | 干净环境可启动，正常/边界/错误/恢复测试通过，引用可追溯且无硬编码密钥 |

## 入门诊断

先用 20 分钟独立完成，不查参考答案。把结果记录到自己的学习档案。

1. 写一个函数读取 UTF-8 文本，空文件返回明确异常；说明为什么不能用裸 `except`。
2. 给定 `list[dict[str, object]]`，按 `source_document_id` 分组并保留最新 `state_effective_at`。
3. 用自己的语言解释 HTTP 422、503 和“可重试”为什么不是一回事。
4. 读懂 `list[float]` 的 shape，说明两个 512 维向量为什么不能写进 768 维索引。
5. 说明 Git 分支、commit SHA、测试通过三者分别证明什么。

判定：完成 4-5 项可直接进入 L01；完成 2-3 项先补 Python 类型、异常、文件处理和 pytest；完成 0-1 项先回到阶段 0。诊断只决定补强内容，不降低本阶段闸门。

## 统一概念闭环卡

每个关键概念都按以下八项展开。遇到缺项时，先把缺项补齐再做实验。

1. 一句话定义与具体问题。
2. 运行时对象的实际 shape/type/字段及不变量。
3. 仓库内最小可运行入口和关键代码阅读点。
4. 从入口到输出的调用链及中间状态。
5. 至少一个可复现故障和预期错误语义。
6. 判断修复有效的指标与冻结条件。
7. 参数/方案取舍和适用边界。
8. 学员修改任务、验收命令、预期结果和参考答案。

完整实验源码唯一归属于 `../labs/`，评测真值唯一归属于 `../evals/`。讲义只给阅读路径、最小调用方式和修改任务，不复制第二套实现。

## 必修主线

| 顺序 | 章节 | 主要对象 | 配套实验 | 通过证据 |
|---:|---|---|---|---|
| 1 | [L01 可观测朴素 RAG](lessons/L01_observable_naive_rag.md) | 全链对象、`StageResult` | lab01 | 对象 ID 链、索引清单、trace、失败定位单 |
| 2 | [L02 解析与分块](lessons/L02_parsing_and_chunking.md) | `SourceDocument`、`ParsedDocument`、`Chunk` | lab02 | 分块消融、span 校验、空文档/乱码恢复 |
| 3 | [L03 Embedding 与索引](lessons/L03_embedding_and_index.md) | `EmbeddingRecord`、`IndexManifest` | lab03 | 维度/metric 校验、Flat/IVF/HNSW 对比 |
| 4 | [L04 检索、重排与上下文](lessons/L04_retrieval_and_reranking.md) | `RetrievalQuery`、`Candidate`、`RankedHit`、`ContextBundle` | lab04 | 稀疏/稠密/混合对照、过滤、查询变换、Rerank 消融 |
| 5 | [L05 引用、拒答与生成](lessons/L05_grounded_generation.md) | `Answer`、`Claim`、`Citation` | lab05 | span 校验、引用覆盖、拒答和 prompt injection 防护 |
| 6 | [L06 离线评测与可观测性](lessons/L06_evaluation_and_observability.md) | `EvalCase`、`EvaluationReport`、`TraceEvent` | lab06 | 检索/生成分层指标、失败切片、成本/延迟报告 |

每章都包含“读代码、改代码、设计实验、解释结果”四类活动，至少完成三类才算完成章节。

## 工程扩展与选修

- [E01-E04 工程扩展](extensions/engineering.md)：配置与版本、追踪与隐私、评测门禁、重试/降级/回滚。
- [A01-A04 前沿选修](extensions/advanced.md)：GraphRAG、Agentic RAG、多模态 RAG、部署与成本深化。选修不能替代 G1-G4。

## 统一运行和验收约定

环境前提：Python 3.11+；默认路径不需要付费 API、远程模型或 GPU。fixture 只验证契约与恢复行为，不能充当 G3 质量证据。

先按 [实验 README](../labs/README.md) 的锁定依赖步骤安装；课程不在第二处复制安装命令，避免依赖入口漂移。安装后执行统一质量检查：

```powershell
cd docs/stages/阶段03_RAG检索增强生成/labs
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m ruff check .
```

上述命令应产生零退出码；具体 lab 命令以 [实验 README](../labs/README.md) 为权威源。报告必须固定：`dataset_id@version`、`index_id`、profile identity、config hash、commit SHA、随机种子和运行模式。

## 阶段产物

- [综合项目与项目答辩量表](capstone.md)
- [出师试卷、参考答案与评分标准](exam.md)
- [20 道面试题、追问与评分点](interview.md)
- [官方资料核对表](references.md)

下一步：完成诊断并打开 L01；先画出对象链，再运行 baseline。
