# L04：稀疏/稠密/混合检索、查询变换、Rerank 与上下文组装

## 本章目标与活动

本章把“检索优化”拆成四个不同问题：召回哪些候选、业务过滤允许哪些候选、如何融合/重排、哪些证据最终进入有限上下文。每一步都有独立对象和指标。

| 活动 | 任务 | 证据 |
|---|---|---|
| 读代码 | 追踪 query -> channel candidates -> ranked hits -> context | 每步数量、分数语义、丢弃原因 |
| 改代码 | 新增过滤字段、query rewrite 或 rerank profile | schema/profile、测试、回归 |
| 设计实验 | sparse/dense/hybrid/rerank 消融 | Recall@5、MRR、nDCG、p95、上下文 token |
| 解释结果 | 诊断过滤误杀、改写漂移或 rerank 退化 | 首个异常对象和恢复策略 |

## 概念闭环 1：`Candidate` 保留每个检索通道的原始证据

### 1. 一句话定义与具体问题

`Candidate` 是某个检索通道对某个 chunk 的一次原始命中，保留 channel、raw score、score kind/semantics 和通道内排名，解决稀疏/稠密分数不可比却被错误相加的问题。

稀疏检索擅长精确词、编号、名称和罕见 token；稠密检索擅长同义表达与语义近邻。混合检索不是“两个数组拼起来”，而是保留两路证据后由明确的融合 profile 决策。

### 2. 运行时对象 shape/type/字段

CandidateSet 是一个 query/index 对应的 `Candidate[]`。Candidate 关键字段：candidate/query/chunk/source version/index IDs、retrieval channel、raw score、score semantics、score kind、channel rank，以及经过明确校准才可存在的 normalized score。

同一 chunk 被 dense、bm25 两路命中时保留两条 Candidate；同通道同块只有一条。raw score 必须有限；`l2_distance` 的 lower-better 与 cosine/BM25 的 higher-better 不可混用。

### 3. 最小可运行代码与阅读点

运行 `python -m rag_lab demo --stdout` 观察 hybrid 通道的 `CandidateSet`（BM25 + dense 两路）。阅读 query adapter、各通道 retriever、hit -> Candidate 映射，以及确定性 tie-break。确认 retrieval 阶段没有偷偷执行 RRF。

### 4. 调用链和中间状态

```text
RetrievalQuery(original + normalized + filters + index_id)
 -> validate filter against IndexManifest
 -> sparse channel -> Candidate[]
 -> dense channel  -> Candidate[]
 -> aggregate CandidateSet without cross-channel score arithmetic
 -> RerankPort consumes candidate IDs
```

看最终 hit 前，先按 channel 分组检查候选：相关 chunk 是从未被召回，还是被召回后在融合/精排中丢失，两者修复完全不同。

### 5. 可复现失败：distance 当 similarity

让一个 adapter 返回 L2 distance，却按降序排序。shape 和类型都合法，但最远结果排在最前。正确映射必须写 `score_kind=l2_distance`、`score_semantics=lower_better` 并按语义排序；修复后用相关 chunk 的 channel rank 与 Recall@k 验证。

另一个失败是把 BM25 raw score 与 cosine raw score直接相加。两者标度和分布不同，结果依数据批次漂移；应使用 rank-based RRF 或经过版本化校准的融合方法。

### 6. 指标与冻结条件

每通道记录 hit count、Recall@k、MRR、score/rank 分布、空命中率和 latency；混合结果记录增量召回、重复率和按 query 类型切片。固定 query set、index ID、filter、top_k、channel profile 和 labels。

### 7. 参数/方案取舍

| 方案 | 擅长 | 代价/失败边界 |
|---|---|---|
| BM25/稀疏 | 编号、专名、精确词、可解释词项 | 同义表达弱；分词/语言配置敏感 |
| dense | 语义改写、相似描述 | 可能漏精确 ID，受模型领域和 prompt 影响 |
| hybrid + RRF | 两路互补，分数标度不一致时稳健 | 两路成本更高；RRF 参数与候选深度需评测 |
| calibrated weighted score | 可表达业务权重 | 校准维护复杂，跨版本不可直接比较 |

### 8. 学员任务、验收与参考答案

任务：从评测集中挑出精确编号、同义问法、模糊问法三类 query，比较 sparse/dense/hybrid 的候选和指标。验收运行 `pytest tests/test_index_retrieval_rerank.py -k "retrieval or candidate"`，报告保留每路 Candidate，不只列最终文本。

参考答案要点：精确编号通常让 sparse 受益，同义问法可能让 dense 受益，但结论必须由当前语料证明。hybrid 若未提升，先检查候选深度、分词、重复去重和标签，而不是立即调 RRF 常数。

## 概念闭环 2：元数据过滤与查询变换改变的不是同一件事

### 1. 一句话定义与具体问题

元数据过滤用调用者声明的结构化事实缩小合法搜索空间；查询变换生成一个更适合检索的派生表达。前者控制“允许搜什么”，后者影响“如何找相关”，必须保留原问题和变换轨迹。

### 2. 运行时对象 shape/type/字段

`RetrievalQuery` 同时保存 `original_text`、`normalized_text`、locale、结构化 `filters`、top_k、retrieval profile、index ID 和 `rewrite_steps[]`。filter 使用显式递归 AST：and/or/not 或 field/operator/value；field 必须在 IndexManifest 的 filterable fields 白名单。

业务过滤是调用者事实，不应由 LLM 自行发明。rewrite step 是派生数据，必须保存 kind、输入哈希、输出文本和 profile，不能覆盖 original text。

### 3. 最小可运行代码与阅读点

用 `python -m rag_lab demo` 配合不同 `query.filters` 观察 category filter 行为；阅读 `retrieval.py` 的 filter schema 校验逻辑，确认过滤在检索层完成、供应商表达式不穿过 port。

### 4. 调用链和中间状态

```text
caller query + authorized filters
 -> normalize without overwriting original
 -> optional rewrite/decompose, append rewrite_steps
 -> validate filter field/operator/type against manifest
 -> adapter translates FilterExpr to backend expression
 -> retrieve each query/channel
 -> preserve child-query provenance in candidates/trace
```

多查询扩展或 HyDE 只能作为可回退 profile。多跳问题可分解，但子查询结果必须能追到原 query ID。

### 5. 可复现失败：过滤误杀与改写漂移

过滤误杀：把 `category=汤品` 错映射为全文匹配或不存在字段，相关文档在检索前被排除。正确结果是 schema 错时 `INVALID_FILTER`，合法但无数据时 success 空 candidates。

改写漂移：原问题问“2026 规则”，rewrite 删除年份，召回旧版本。修复要求 original text 保留、rewrite profile 更新、时效字段进入合法 filter 或排序策略，并用时效冲突题例验证。

### 6. 指标

记录 filter reject/empty rate、pre/post filter candidate count、rewrite rate、rewrite fallback、原 query 与改写 query Recall@k、时效/多跳/模糊 query 切片，以及额外 latency/cost。

### 7. 方案取舍

| 方案 | 适用 | 回退条件 |
|---|---|---|
| 规则规范化 | 大小写、空白、稳定别名 | 一般总是启用，但必须可测试 |
| 多查询扩展 | 用户表达不稳定、希望提高召回 | 候选噪声/成本过高时关闭或限深度 |
| HyDE | 短问题难与文档表述对齐 | 生成假设漂移或敏感领域时谨慎 |
| 查询分解 | 多跳、多个约束 | 子问题不可独立或延迟预算不足时拒绝 |
| 元数据过滤 | 权限、租户、类别、时间等硬约束 | 不可用相似度替代；字段不合法直接拒绝 |

### 8. 学员任务与参考答案

任务：为“指定类别且只使用当前版本”的 query 增加 filter schema 和测试，再设计一个 rewrite 会删除关键约束的失败用例。验收 `pytest tests/test_index_retrieval_rerank.py -k "filter"`，预期非法字段在检索前失败，合法无匹配返回空结果，漂移用例可回退原 query。

参考答案要点：权限/租户 filter 不能降级为无过滤搜索；普通质量 filter 可以按产品策略提示用户修正。回退必须出现在 trace 中并标记 degraded，不能把改写失败隐藏成正常结果。

## 概念闭环 3：`RankedHit` 把融合/精排决策与原始召回分开

### 1. 一句话定义与具体问题

`RankedHit` 是 RRF 融合和可选 cross-encoder 精排后的全局有序命中，保存贡献它的 Candidate IDs、分数组成、rerank profile 和上下文准入决策，解决“最终排序从哪里来”的审计问题。

### 2. 运行时对象 shape/type/字段

关键字段：ranked hit/query/chunk/source IDs、candidate IDs、全局 rank、final score、score components、rerank profile、eligible flag 和 decision codes。同 query 的 rank 从 1 连续唯一；并列按 chunk ID 稳定打破；不合格 hit 不得进入 ContextBundle。

RRF 参数、cross-encoder model revision、阈值、fallback 策略都属于 rerank profile，不属于 retrieval profile。

### 3. 最小可运行代码与阅读点

用 `python -m rag_lab failures --scenario rerank_degradation` 触发 timeout fallback；阅读 `rerank.py` 的 candidate grouping、RRF rank 公式、阈值和 fallback。确认 RankedHit 不修改 Candidate 或 Chunk。

### 4. 调用链和中间状态

CandidateSet -> group by chunk while preserving candidate IDs -> RRF components -> optional cross-encoder score -> deterministic final order -> threshold decision -> RankedHitSet(confidence) -> ContextAssembly。

bi-encoder 适合大范围便宜召回，cross-encoder 同时读取 query 与候选文本做昂贵精排。因此 rerank 的输入深度是延迟/质量关键参数。

### 5. 可复现失败：Rerank 超时或退化

注入 reranker timeout。若 profile 允许，回退到 RRF 排名并标记 `status=degraded`/fallback event；否则返回 retryable `UPSTREAM_TIMEOUT`。错误实现会返回空 hits、沿用半批结果，或把 fallback 冒充正常精排。

退化也可能无异常：Rerank 后 MRR 下降。检查 query/document 输入顺序、模型领域、截断、candidate depth 和 score tie，不应只增加超时。

### 6. 指标

记录 Recall@candidate_k、MRR/nDCG before/after、top-k swap、eligible rate、rerank p50/p95、timeout/fallback count、每 query 候选数和 batch size。G2 的质量门槛用固定评测集，不能用某个成功案例。

### 7. 取舍

RRF 无需跨通道校准、快且可解释；cross-encoder 可能提升前排质量，但有模型、截断和延迟成本。小候选集或 latency 严格场景可只用 RRF；高价值复杂问答可用精排；是否启用必须看增量 MRR/nDCG 与 p95。

### 8. 学员任务与参考答案

任务：比较 candidate depth 10/30/100 与 rerank limit 5/10 的矩阵。验收报告包含 Recall@candidate_k、MRR@5、p95 和 fallback；只改 rerank profile。

参考答案要点：候选太浅时 reranker 无法找回未召回证据；候选太深会增加成本与噪声。最优点是满足质量门槛下成本最低的组合，不是最大参数。

## 概念闭环 4：`ContextBundle` 是有限预算下的证据发布物

### 1. 一句话定义与具体问题

`ContextBundle` 把可准入 RankedHit 按版本化 assembly profile 放进固定 token budget，并为每段建立可引用锚点，解决“top-k 文本直接拼接”造成的重复、超预算和引用断裂。

### 2. 运行时对象 shape/type/字段

关键字段：context/query IDs、assembly profile、token budget/count、selected hits、render order、rendered text hash、rendered context、warnings。总 token 不超 budget；selected hit 必须 eligible；每个 `[S1]` 锚点可无歧义映射 hit；不得静默截断原 Chunk。

### 3. 最小可运行代码与阅读点

用 `python -m rag_lab failures --scenario context_overflow` 观察 context budget 超预算 warning；阅读 `context.py` 的 token 计算、单块超预算 warning 与 deterministic order。

### 4. 调用链和中间状态

RankedHitSet -> filter eligible -> resolve immutable chunks -> dedupe/conflict policy -> estimate tokens -> add whole chunks in deterministic order -> emit skipped reasons/warnings -> render anchors -> hash bundle。

### 5. 可复现失败：超预算静默截断

让一个 chunk 大于剩余预算。正确默认是跳过并记录 `CHUNK_EXCEEDS_REMAINING_BUDGET`；只有明确压缩 profile 生成新的可追溯 span 时才能压缩。字符串切片后仍沿用原 chunk ID 会让 Citation span 失真。

### 6. 指标

token utilization、selected/dropped hit count、duplicate ratio、eligible rate、warning count、context precision、citation coverage 和 generation latency/cost。预算提升可能增加召回覆盖，也可能降低 faithfulness，需端到端验证。

### 7. 取舍

按 rank 贪心简单稳定，但可能漏掉互补证据；多样性/覆盖优化可减少重复，但决策复杂。压缩能省 token，却引入新的派生内容与潜在事实丢失。默认先用完整 chunk + 显式跳过，指标证明需要后再引入压缩。

### 8. 学员任务与参考答案

任务：设计 600/1200/1800 三组预算，比较 token utilization、证据覆盖、faithfulness、延迟和成本；增加单块超预算回归测试。

参考答案要点：更大 budget 不是单调更好。正确报告应指出哪类题受益、哪类因噪声退化，并选择满足引用/faithfulness 门槛的最低预算。任何 silent truncation 都是阻断错误。

## 概念闭环 5：2026 主流 RAG 变体与取舍

> 主线（L01–L04）建立的是"检索→重排→上下文→生成"的可观测基线。2026 工程实践在此基线上叠加了多种变体。本节只做**对比与取舍**，不替代主线；每种变体都应按 G2 方式在固定评测集上做消融。

### 1. 一句话定义与问题

当朴素 RAG 在相关切片上出现"检索命中但答案漏关键信息"或"检索不到但模型其实知道"两类失败时，2026 主流变体从两个方向切入：**让检索自我纠错**（corrective / self-RAG）和**让检索变成多步决策**（agentic retrieval / plan-and-execute）。

### 2. 变体对比

| 变体 | 核心机制 | 解决什么 | 新增风险 / 成本 | 何时采用 |
|---|---|---|---|---|
| Corrective RAG（CRAG） | 检索后用轻量评估器给每个 chunk 打分（relevant / irrelevant / ambiguous），对负面结果触发补充检索或改写。 | 检索噪声多、前排混入不相关 chunk。 | 增加一次评估调用和分支逻辑；评估器本身可能误判。 | 检索结果质量波动大、irrelevant chunk 频繁进入 context。 |
| Self-RAG | 生成过程中让模型自判是否需要检索、检索后自判 chunk 是否有用、生成后自判回答是否 grounded，按需触发多轮。 | 减少不必要的检索、提升引用忠实度。 | 多轮推理成本和延迟显著；自判 token 需版本化并计入 judge profile。 | 查询分布差异大、很多题无需检索或需多轮检索。 |
| Agentic retrieval / ReAct | 把检索作为 Agent 的一个工具，Agent 根据中间结果决定下一步（再查、改写、澄清、终止）。 | 多跳、需分解或动态选择工具的复杂查询。 | 步骤数、工具调用错误累积、成本；需终止条件和预算。 | 确定性 query decomposition 无法覆盖、需多步查询规划。 |
| Long-context RAG | 把更长文档或更多 chunk 直接放进上下文，配合长上下文模型或上下文压缩。 | 小块分块导致跨块信息断裂。 | 成本随上下文增长；长上下文模型仍可能丢中间信息（lost-in-the-middle）。 | 文档总量不大或跨块事实密集，且已证明短上下文确实丢失关键信息。 |
| Reranker-as-judge | 用 LLM 替代 cross-encoder 做重排，输出分级相关度。 | 需要更细粒度相关性判断。 | LLM 调用成本高、延迟大；judge profile 必须固定。 | cross-encoder 精度不足且延迟预算宽松。 |

### 3. 取舍原则

1. **先证明基线失败模式**：用 L06 的切片报告定位是 retrieval / context / generation 哪一步失败，再选对应变体。不要在朴素 RAG 还没跑通时引入 Self-RAG。
2. **每种变体都是新的 profile / 新的 port**：CRAG 的评估器、Self-RAG 的自判 token、Agentic 的工具 schema 都必须版本化，进 G3/G4 评测。
3. **成本与延迟是硬约束**：多轮检索和 Agent 步骤数直接放大 p95 和单位 query 成本；报告必须包含成本对比。
4. **fixture 不能验证变体效果**：变体涉及真实检索判断和生成自判，必须用非 fixture 的真实模型 + 固定评测集。

### 4. 与本课程主线的关系

- L01–L04 的 Candidate / RankedHit / ContextBundle 对象链是**所有变体的公共基础**：CRAG 在 Candidate 层加评估，Self-RAG 在 generation 层加自判，Agentic 把整条链包进 Agent 工具。
- 变体的观测都依赖 L06 的 TraceEvent 和指标契约；没有可观测基线，变体优化就是黑盒。

### 5. 学员任务与参考答案

任务：选一种变体（CRAG 或 Self-RAG），在固定评测集上与 L04 的 hybrid baseline 做消融，报告 Recall@5、MRR、faithfulness、p95、单位 query 成本和失败切片变化。

参考答案要点：变体不是银弹。正确结论应指出哪类切片受益、哪类退化，并给出"在什么条件下采用、什么条件下回退基线"的明确判据。若成本增长超过质量改善，应拒绝采用。

## G2 优化闸门

用固定 `dataset_id@version`、index ID、metric profile 和代码版本比较 Naive dense baseline 与 hybrid + rerank。通过要求：Recall@5 绝对提升至少 0.10，同时报告 MRR、p95 和成本；若未达标，可以提交严谨的失败分析，但不能宣称过闸。

报告必须包含：实验假设、唯一变量、profile diff、总体与失败类型切片、至少两个 case 的 Candidate/RankedHit 追踪、局限和回退策略。

## 章末小结

- retrieval 负责保留通道候选，rerank 负责融合/精排与准入，context 负责预算；不要合成一个黑盒函数。
- filter 是业务约束，rewrite 是派生表达；都必须可校验、可追踪、可回退。
- 优化应先看相关证据在哪一步丢失，再改对应 profile。
- Recall 提升若伴随 p95、成本或 faithfulness 不可接受退化，不是生产可用优化。

下一步：进入 [L05](L05_grounded_generation.md)，把上下文锚点变成可验证 Citation，并让证据不足成为明确拒答而不是幻觉。
