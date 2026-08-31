# L01：建立可观测的朴素 RAG 基线

## 本章目标与活动

你要把“加载、切块、检索、拼 Prompt、生成”从一句流程图变成可检查的对象链。完成本章后，应能判断失败发生在检索前、检索中、上下文组装还是生成阶段。

| 活动 | 本章任务 | 证据 |
|---|---|---|
| 读代码 | 从 `rag_lab/cli.py` 的 `main()` 追到每个 port | 调用链标注，至少写出 7 个函数/类和 I/O 类型 |
| 改代码 | 改 `top_k` 或上下文阈值，不改领域对象字段 | 新 profile identity、测试结果和差异报告 |
| 设计实验 | 比较“仅关键词”和“确定性向量”基线 | 固定数据与指标的对照表 |
| 解释结果 | 对一个错误答案定位首个异常中间状态 | 假设、证据、结论和排除项 |

## 概念闭环 1：RAG 不是向量数据库

### 1. 一句话定义与问题

RAG 是“先从一个可追溯知识源取得证据，再让生成器基于证据回答”的系统模式，解决模型参数知识不够新、不含私有数据和回答缺少出处的问题。向量数据库只可能是 retrieval 的一个 adapter；没有向量库也能用 BM25 做 RAG，有向量库但没有证据约束也不等于可靠 RAG。

什么时候不要用 RAG：答案来自确定性数据库计算时优先 SQL/业务代码；知识需要改变模型行为风格而不是提供事实时再评估微调；数据很小且可完整放入上下文时先比较长上下文方案。选择必须由质量、延迟、成本、权限和更新频率共同决定。

### 2. 运行时对象

| 阶段 | 输入 -> 输出 | 必须观察的字段 | 核心不变量 |
|---|---|---|---|
| ingestion | bytes -> `SourceDocument`/`ParsedDocument`/`Chunk` | source/version/chunk ID、span、profile | 同输入和 profile 可重建同一派生 ID |
| indexing | `Chunk` -> `EmbeddingRecord`/`IndexManifest` | dimension、metric、coverage、state | 向量维度与 manifest 一致；只有 ready 索引可发布 |
| retrieval | `RetrievalQuery` -> `Candidate[]` | channel、source document/version ID、raw score、score semantics、rank | 不同 score kind 的原始分数不可直接比较；Candidate 直接携带来源链 |
| rerank/context | `Candidate[]` -> `RankedHit[]` -> `ContextBundle` | candidate IDs、final score、eligible、token budget | 不合格 hit 不进上下文；不得静默截断 chunk |
| generation | `ContextBundle` -> `Answer`/`Citation[]` | outcome、claim span、citation IDs、finish reason | 事实性 claim 必须有可校验引用 |
| observability | stage event -> `TraceEvent` | trace/span、stage、status、refs、metrics | 只记录 ID/计数/哈希，不复制正文和密钥 |

字段级权威定义见 [代码与数据契约 §3](../../planning/03_code_and_data_contracts.md#3-核心领域对象)。

### 3. 最小可运行代码与阅读点

运行离线 baseline：`python -m rag_lab demo --config configs/offline.json --stdout`。先找 CLI 入口（`rag_lab/cli.py`），再按 port 顺序阅读，不从 adapter 反向猜领域语义。

关键阅读点：

1. CLI 如何加载固定 dataset manifest 和 system profile。
2. 每个 stage 如何返回 `StageResult[T]`，空结果与失败是否区分。
3. 对象 ID 如何被下一个 stage 引用，而不是传可变供应商对象。
4. TraceEvent 在哪里创建，是否包含输入/输出 ID 和 duration。
5. fixture generator 为什么只用于确定性契约回归。

预期最小输出不是一段自然语言，而是：一个 ready `IndexManifest`、完整对象 ID 链、一个 `Answer` 或明确拒答、以及从 ingestion 到 generation 的 trace。

### 4. 调用链与中间状态

```text
CLI
 -> IngestionPort.ingest(command)
    -> SourceDocument -> ParsedDocument -> Chunk[]
 -> IndexingPort.build(command)
    -> EmbeddingRecord[] -> IndexManifest(state=ready)
 -> RetrievalPort.retrieve(query)
    -> CandidateSet
 -> RerankPort.rerank(command)
    -> RankedHitSet
 -> ContextAssemblyPort.assemble(command)
    -> ContextBundle
 -> GenerationPort.generate(command)
    -> Answer + Citation[]
```

调试时按顺序停下，不要直接看最终答案：先确认 ingestion item count，再看 manifest coverage，再看 relevant chunk 是否进入 candidates/hits/context，最后才看 claims/citations。

### 5. 可复现失败：检索无命中

用 `python -m rag_lab demo --query-text "🙂"` 提交一个无命中问题，或把元数据过滤条件改成不存在的分类（修改 `configs/offline.json` 的 `query.filters`）。

正确语义：retrieval 返回 success + `candidates=[]`；context 返回空 bundle 和 `NO_ELIGIBLE_HITS` warning；generation 返回 `outcome=insufficient_evidence`。错误实现会返回 500、编造答案，或在 trace 中丢掉空结果阶段。

诊断顺序：先验证 filter 是否有效，再验证索引是否 ready，再区分“合法无命中”和“后端失败”。`NO_HITS` 不是 `INDEX_NOT_READY`。

### 6. 指标与冻结条件

baseline 至少记录：ingestion 创建/隔离数量、index coverage、Recall@5、MRR、空检索率、拒答率、引用覆盖、各 stage latency 和生成 token/cost 占位。

比较两个系统前必须冻结 dataset version、index ID、profile identity、metric profile、commit SHA 和运行模式。只说“10 问答对 8 个”没有题例版本、证据标注和失败分层，不能作为工程结论。

### 7. 方案取舍与边界

| 选择 | 适用 | 代价/风险 |
|---|---|---|
| 手写最小实现 | 建立对象与调用链直觉、做确定性测试 | 功能少，不代表生产吞吐和模型效果 |
| LangChain/LlamaIndex adapter | 快速接入加载器、模型和存储 | 框架对象不能穿过 port；升级只改 adapter |
| fixture embedding/generator | CI 无网络回归 | 不证明语义质量，不能过 G3 |
| 本地真实模型 | 无 API Key 的质量实验 | 受硬件影响，结果需固定 model revision/profile |
| 云端模型 | 质量和能力上限对比 | 有成本、限流、隐私和网络失败边界 |

### 8. 学员任务、验收与参考答案

任务：把 `top_k` 从基线值改为两组参数，其他条件不变。记录 Candidate、RankedHit、ContextBundle 和 Answer 的变化，并解释 Recall@5、上下文 token 数和延迟之间的关系。

验收：运行 `python -m rag_lab demo` 和 `pytest`；预期测试通过，每组结果具有不同 profile/config hash；对象链不断裂；报告没有把 raw distance 当 relevance score。

参考答案要点：增大 `top_k` 只保证候选更多，不保证最终答案更好；召回可能上升，但 rerank/上下文成本通常上升，噪声也可能增加。合理结论应基于固定评测集的曲线或表格，而不是选一个“看起来不错”的问题。若分数没有变化，先检查参数是否真正进入 profile 和检索调用。

## 概念闭环 2：`StageResult` 把失败变成接口语义

### 1. 一句话定义与问题

`StageResult[T]` 是每个阶段统一返回的结构化结果，用来区分成功、部分成功、失败、隔离和合法空结果，避免调用方从日志字符串猜测下一步。

### 2. 运行时对象

顶层包含 `request_id`、`status`、可选 `data`、`item_results`、`warnings` 和可选 `problem`。逐项结果包含 `item_key`、`status`、`output_refs` 和可选 `problem`。`partial_success` 必须同时有成功项和失败/隔离项。

### 3. 最小可运行代码与阅读点

在 `tests/test_pipeline.py` 中找一个正常用例和一个空文档用例（`test_no_hits_propagate_to_abstention`），对比 `StageResult`，确认错误由稳定 `problem.code` 表达，`detail` 只用于阅读。

### 4. 调用链和中间状态

adapter 异常先映射为 `ProblemDetails`，stage 再决定整批失败、逐项失败、隔离或降级；orchestrator 只根据稳定状态和 `retryable` 分支，不解析异常文本。

### 5. 可复现失败

把一个空文件和一个正常文件放进同一 ingestion batch。正确结果是 `partial_success`：正常项 created，空项 quarantined 且 code 为 `EMPTY_DOCUMENT`。整批抛异常或悄悄丢文件都错误。

### 6. 指标

观察 `created_count`、`quarantined_count{code}`、`failed_count{code}`、batch status 和 retry count。修复有效要求正常项仍成功、空项行为符合契约，不能只让异常消失。

### 7. 取舍

逐项结果增加 schema 和调用方复杂度，但能支持批处理部分失败、精确重试和审计。小脚本也应保留此边界，因为后续项目会复用。

### 8. 学员任务与参考答案

任务：阅读空文档测试，增加“同一批次两个空文件 + 一个正常文件”用例。预期仍是 partial success，两个隔离项都有独立 item key，正常项只写一次。参考答案的核心不是断言异常消息，而是断言 status、problem code、output refs 和副作用数量。

## 章末小结与检查

- RAG 是证据获取与 grounded generation 的系统，不是某个向量库或框架。
- 最终答案只是末端产物；诊断必须从最早异常中间对象开始。
- 合法无命中、低置信度和拒答属于业务结果，不应伪装成系统错误。
- fixture 证明确定性工程回归，真实模型或人工双审才证明质量。

自测：为什么“检索有结果”仍可能必须拒答？参考答案：Candidate 可能来自不适用版本、不同通道原始分数不可比、Rerank 后全部低于准入阈值，或上下文/引用校验失败；有数组元素不等于有足够证据。

下一步：进入 [L02](L02_parsing_and_chunking.md)，把原始 bytes 到 Chunk 的每次变换和不变量画清楚。
