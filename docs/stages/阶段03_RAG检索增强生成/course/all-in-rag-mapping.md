# all-in-rag 路线对照表

> 对标仓库：[datawhalechina/all-in-rag](https://github.com/datawhalechina/all-in-rag)（本地 `all-in-rag/`，28 个中文章节 + C1–C9 代码）。
> 本表把参考仓库的章节递进映射到本课程 L01–L06 + 工程扩展（E01–E04）+ 前沿选修（A01–A04），并标注**吸收点**与**改进点**。
> 核对日期：2026-08-31。一手资料见 [官方资料核对表](references.md)。

## 映射总览

| all-in-rag 章节 | 主题 | 本课程对应 | 吸收 | 改进 |
|---|---|---|---|---|
| Ch1 RAG 简介 / 准备工作 / 四步构建 | RAG 概念、环境、最小可用系统 | **L01** 可观测朴素 RAG | 四步流程（加载→切块→检索→生成）作为入门直觉 | 本课程把"最小可用"替换为"可观测基线"：每步产出强类型对象、StageResult、TraceEvent，拒绝黑盒 demo |
| Ch2 数据加载 / 文本分块 | 文档加载器、分块策略 | **L02** 解析与分块 | 多格式加载、递归/固定/语义分块思路 | 本课程用 SourceDocument→ParsedDocument→Chunk 三层确定性派生，chunk ID 由内容+profile 哈希，拒绝随机 UUID 和无版本 chunk |
| Ch3 向量嵌入 / 向量数据库 / Milvus / 索引优化 | 嵌入模型、向量库、索引选型 | **L03** Embedding 与索引 | 嵌入选型、FAISS/Milvus/Qdrant、IVF/HNSW 对比 | 本课程把嵌入/索引参数冻结为 EmbeddingProfile/IndexProfile，IndexManifest 含 checksum 和 coverage，索引写失败显式 partial 状态 |
| Ch3 多模态嵌入 | 图像/音频嵌入 | **A03** 多模态选修 | 多模态编码思路 | 主线不深入；放入选修并要求与文本-only 建立同层评测标签 |
| Ch4 混合检索 / 查询构建 / 查询重构 / 检索进阶 | 混合检索、查询改写、高级检索 | **L04** 检索、重排与上下文 | BM25+稠密双路、RRF、查询改写、rerank | 本课程把检索/重排/上下文分成三个独立 port，Candidate 不比较跨通道原始分数；filter 字段须进 manifest 白名单；rerank 超时显式 degraded fallback |
| Ch4 文本到SQL | NL2SQL | 范围外（标注） | Text2SQL 思路 | 本课程范围外；确定性计算走数据库，不挤占必修主线 |
| Ch5 格式化生成 | 提示工程、格式化输出 | **L05** 引用、拒答与生成 | 提示模板、输出格式化 | 本课程用 extractive grounded generation 替代 LLM 自由生成，Citation 必须过 span/quote hash/source version 校验；增加拒答与澄清语义 |
| Ch6 评估介绍 / 常用工具 | 评测概念、Ragas/LlamaIndex 评估 | **L06** 离线评测与可观测性 | 评测指标概念、工具选型 | 本课程建立分层指标契约（retrieval/context/generation/runtime），失败归因只记最早阶段；fixture 只用于契约回归，不充当质量证据 |
| Ch7 基于知识图谱的 RAG | GraphRAG | **A01** GraphRAG 选修 | 图 schema、实体/关系、图检索 | 主线不深入；选修要求与 hybrid baseline 同切片对照 |
| Ch8 综合项目（模块化 RAG 系统） | 完整模块化系统 | **综合项目** capstone | 模块化拆分（data/indexing/generation） | 本课程综合项目额外要求：配置可追溯、TraceEvent 完整、回归门禁、恢复演练、引用可校验 |
| Ch9 图 RAG 系统架构 / 图数据建模 / Neo4j / 智能查询路由 | 图 RAG 深入 | **A01** GraphRAG 选修 | Neo4j 集成、查询路由 | 主线不深入；选修要求构图成本、查询 p95、更新复杂度有证据 |

## 工程扩展与前沿选修的对照

| 本课程模块 | all-in-rag 对应 | 吸收 | 改进 |
|---|---|---|---|
| **E01** 配置、profile、版本 | Ch8 config.py + 各章硬编码参数 | 配置驱动思路 | 本课程引入 ProfileRef（profile_id, version, config_hash）不可变身份；任何语义参数变化产生新 hash；配置与密钥分离 |
| **E02** 追踪与隐私 | 各章 print/logging | 可观测思路 | 本课程用 W3C TraceContext + 自研 TraceEvent，字段低基数、不泄漏正文/密钥 |
| **E03** 评测门禁 | Ch6 评估示例 | 指标门禁思路 | 本课程把门禁嵌入 G1–G4，阈值只在 dataset/index/metric/judge 身份冻结时有效 |
| **E04** 失败恢复与回滚 | 各章异常处理 | 异常处理思路 | 本课程要求 partial_success / quarantine / degraded 显式状态，恢复演练作为 G4 必需输入 |
| **A02** Agentic RAG | 无直接对应（all-in-rag 不含 Agent） | — | 本课程新增：tool schema、状态、终止、预算、权限、人工确认、失败恢复 |
| **A04** 部署与成本深化 | 无直接对应 | — | 本课程新增：SSE、背压、cache invalidation、容量模型、SLO、灰度回滚 |

## 关键差异（本课程对 all-in-rag 的改进总结）

1. **对象链可观察**：all-in-rag 用 `Document.metadata` 和临时 chunk ID；本课程用强类型冻结 dataclass + 内容派生 ID + 版本化 profile。
2. **检索/重排/上下文分离**：all-in-rag 常在同一个函数内完成检索+重排；本课程分成三个独立 port，中间对象（Candidate / RankedHit / ContextBundle）可独立检查。
3. **失败语义显式化**：all-in-rag 用 print/简单异常；本课程用 StageResult + ProblemDetails + failure attribution，区分 success / partial_success / failed / degraded。
4. **评测契约化**：all-in-rag 评估示例偏演示；本课程建立 metric_contract.json + 校验脚本 + 切片报告 + judge profile 固定。
5. **工程护栏**：all-in-rag 缺少配置版本化、trace 规范、恢复演练；本课程用 E01–E04 补齐。
6. **前沿扩展**：all-in-rag 不含 Agentic RAG / 部署成本深化；本课程用 A02 / A04 补齐。

下一步：进入 [术语表](glossary.md) 按小节查阅每个名词的定义与边界。
