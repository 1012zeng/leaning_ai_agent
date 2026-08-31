# 阶段 03：RAG 检索增强生成

本阶段不是框架 API 清单。学习者要沿一条真实对象链完成读取、修改、故障定位、实验设计和工程交付：

`SourceDocument -> ParsedDocument -> Chunk -> EmbeddingRecord -> Candidate -> RankedHit -> ContextBundle -> Answer -> Citation`

## 学习入口

1. 先读 [课程入口](course/README.md)，完成诊断和环境检查。
2. 按 L01-L06 顺序学习 [必修主线](course/lessons/)。
3. 每章运行对应 [离线实验](labs/README.md)，不要只阅读答案。
4. 使用固定 [评测集](evals/README.md) 比较方案，禁止凭主观体验宣布优化有效。
5. 完成 [综合项目](course/capstone.md)、[出师试卷](course/exam.md) 和 [项目答辩](course/capstone.md#项目答辩量表)。

## 三层结构

| 层级 | 内容 | 是否阻塞结业 |
|---|---|---|
| 必修主线 | 可观测基线、解析与分块、Embedding/索引、混合检索与重排、引用与拒答、离线评测 | 是 |
| 工程扩展 | 配置与版本、追踪与隐私、评测门禁、失败恢复与回滚 | 是，完成 G4 才算工程交付 |
| 前沿选修 | GraphRAG、Agentic RAG、多模态 RAG、生产部署与成本深化 | 否 |

## 阶段闸门

| 闸门 | 核心证据 | 入口 |
|---|---|---|
| G1 跑通 | 离线 MVP 产出对象 ID 链、索引清单和 TraceEvent | [L01](course/lessons/L01_observable_naive_rag.md) |
| G2 优化 | 固定数据、索引和 profile 后，混合检索相对基线的 Recall@5 绝对提升至少 0.10 | [L04](course/lessons/L04_retrieval_and_reranking.md) |
| G3 评估 | 非 fixture 生成器完成质量评测，Faithfulness 不低于 0.80，并解释至少 3 个失败样例 | [L06](course/lessons/L06_evaluation_and_observability.md) |
| G4 工程化 | 配置可追溯、TraceEvent 完整、回归门禁和恢复演练通过 | [工程扩展](course/extensions/engineering.md) |

阈值只在数据集、索引、system profile、metric profile 和 judge 条件同时冻结时有效。未记录这些身份信息的分数不能用于过闸。

## 权威输入

- [可验收需求与对标基线](planning/01_requirements_and_benchmark.md)
- [课程、实验与仓库架构](planning/02_learning_and_repo_architecture.md)
- [代码与数据契约](planning/03_code_and_data_contracts.md)
- [官方资料核对表](course/references.md)

下一步：进入课程入口，先完成 20 分钟诊断，不要直接跳到向量数据库或框架章节。
