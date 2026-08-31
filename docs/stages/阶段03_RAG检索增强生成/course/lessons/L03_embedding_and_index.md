# L03：Embedding、距离语义与不可变索引

## 本章目标与活动

本章不要求背模型榜单。你要能解释一条文本如何变成固定 shape 的向量，索引如何冻结模型与 metric 语义，以及模型或维度变化时为什么必须新建索引。

| 活动 | 任务 | 证据 |
|---|---|---|
| 读代码 | 追踪 chunk -> embedding -> staging index -> manifest -> alias | shape/字段/状态变化图 |
| 改代码 | 增加一个 embedding 或 index profile | profile、schema 校验、兼容性测试 |
| 设计实验 | 对比 exact Flat、IVF、HNSW 或可用等价后端 | Recall@k、p50/p95、内存、构建时间 |
| 解释结果 | 诊断维度不匹配或 similarity/distance 方向错误 | 最早异常对象和修复证据 |

## 概念闭环 1：Embedding 是带 profile 的派生对象

### 1. 一句话定义与具体问题

Embedding 把 query 或 document 编码为固定维度的数值向量，使系统能按语义邻近召回；`EmbeddingRecord` 则把向量与精确 chunk、模型 revision、输入哈希、维度、dtype 和 normalize 策略绑定，解决“同名模型变了却无法解释结果”的问题。

### 2. 运行时对象 shape/type/字段

`EmbeddingRecord.vector` 的运行时 shape 是 `list[float]` 或后端边界上的一维数值数组，长度等于 `dimension`。关键字段：embedding/chunk/source version IDs、embedding profile、input hash、dimension、dtype、normalized、vector。

必须同时成立：`len(vector) == dimension`；元素全为有限数；profile 声明维度与记录一致；`input_sha256` 对应实际送入模型的文本，包括 query/document prompt，而不是原始 chunk 的想象值。

以 batch adapter 为例，模型内部常见 shape 是 `(batch_size, dimension)`，但跨 port 的每条 `EmbeddingRecord` 仍是一条 chunk 的一维向量。不要把 batch 维混进领域 dimension。

### 3. 最小可运行代码与逐行关键点

运行 [lab03 embedding](../../labs/README.md) 的 deterministic adapter 和可选真实 Sentence Transformers adapter。阅读顺序：profile 解析 -> document/query 编码入口 -> batch shape 校验 -> finite/normalize 检查 -> `EmbeddingRecord` ID -> index writer。

官方 Sentence Transformers 文档区分 `encode_query` 与 `encode_document`，因为非对称检索模型可能使用不同 prompt/task。课程 adapter 必须显式体现这种差异，不能假定通用 `encode()` 永远等价，资料见 [官方核对表](../references.md)。

### 4. 调用链与中间状态

```text
Chunk.text
 -> apply document encoding profile/prompt
 -> input_sha256
 -> model batch tensor (batch, dimension)
 -> per-row finite/shape/normalization validation
 -> EmbeddingRecord[]

RetrievalQuery.normalized_text
 -> apply query encoding profile/prompt
 -> query vector (dimension,)
 -> verify against IndexManifest
 -> vector search adapter
```

调试时打印 identity、shape、norm 和少量经过允许的数值摘要，不把完整向量写入日志或 TraceEvent。

### 5. 可复现失败：模型 revision 或维度漂移

让 adapter 产生 1024 维向量并尝试写入 dimension=512 的索引。正确结果是 `EMBEDDING_DIMENSION_MISMATCH`，原索引不写入，新建 index build；错误结果包括静默截断、补零、drop active collection 后现场重建，或仍沿用旧 profile identity。

另一个隐蔽故障是文档用带 passage prompt 的编码，query 却误用 document prompt。shape 完全正确，但 Recall@k 下降；它必须由评测发现，而不是 schema 测试。

### 6. 指标与冻结条件

工程指标：batch latency、items/sec、dimension、norm 分布、non-finite count、failure count、缓存命中、模型加载时间。质量指标：Recall@k、MRR、nDCG 和按 query 类型切片的退化。

模型对比必须固定 chunk IDs、dataset version、索引类型参数、retrieval/rerank profile 和 metric profile。更换 embedding profile 必须产生新 embedding ID 和 index ID。

### 7. 参数/方案取舍与边界

| 决策 | 收益 | 代价/边界 |
|---|---|---|
| 小型本地 bi-encoder | CPU 友好、无密钥、低延迟 | 领域/多语言质量可能不足 |
| 更大模型 | 可能提升语义召回 | 内存、延迟、吞吐和部署复杂度增加 |
| normalize + inner product | 规范化后可表达 cosine 排序 | query/document 都必须一致规范化 |
| float16/int8 | 降低存储或提高吞吐 | 可能损失召回；必须独立 profile 和消融 |
| 云端 embedding | 运维简单、可能质量高 | 隐私、费用、限流、网络和供应商 revision 风险 |

“中文就选某个中文模型”不是充分决策。要用目标语料、query 类型、硬件和延迟预算评测，并固定模型 revision。

### 8. 学员任务、验收命令与参考答案

任务：在不改数据和检索算法的前提下，对比 deterministic baseline 与一个真实本地 embedding profile；记录 shape、norm、索引大小、Recall@5、MRR 和 p95。

验收：运行 lab03 命令和 `pytest -k embedding`；预期两个 profile 产生不同 embedding/index ID，维度校验通过，报告列出失败 case 而不是只写平均分。

参考答案要点：真实模型不必在所有 query 上胜出；词面精确 ID、缩写和编号可能由稀疏检索更好。若质量变化但 profile/config hash 相同，实验不可审计；若 dimension 变化却复用 index，属于阻断错误。

## 概念闭环 2：`IndexManifest` 是查询可重复性的边界

### 1. 一句话定义与具体问题

`IndexManifest` 是一次不可变索引构建的清单，冻结 corpus、chunk/embedding/index profile、维度、metric、可过滤字段、覆盖率、校验和与发布状态，解决查询“到底读了哪批向量”的追溯问题。

### 2. 运行时对象 shape/type/字段

重点字段：`index_id`、`index_build_id`、`corpus_version`、chunk/embedding profiles、dimension、metric、filterable fields、source version IDs、expected/indexed/failed counts、coverage、content checksum、state。

不变量：manifest 不可变；coverage 等于 indexed/expected；后端 schema 与 dimension/metric 一致；只有 `state=ready` 才能绑定读 alias；partial 索引默认不得发布。

### 3. 最小可运行代码与阅读点

运行 lab03 的 index build。阅读 staging 写入、逐项 `ItemResult`、manifest checksum、smoke retrieval、ready 转换和 alias compare-and-swap。确认“向量生成成功”和“索引写入成功”是两个不同状态。

### 4. 调用链与中间状态

```text
IndexBuildCommand(index_build_id, chunk_ids, profiles)
 -> validate active source versions and profile compatibility
 -> create staging backend index
 -> embed/write each chunk with item result
 -> verify count, dimension, metric, checksum, smoke search
 -> publish immutable IndexManifest(state=ready)
 -> compare-and-swap alias(expected_active_index_id -> new index_id)
```

查询对象保存实际 `index_id`，不能只保存会漂移的 `course_active` alias。

### 5. 可复现失败：部分写入仍切 alias

注入 100 个 chunk 中 3 个写失败。正确结果是 partial manifest、coverage=0.97、逐项失败 ID 可重试，默认 alias 不切换。错误实现会只打印警告后把不完整索引标为 ready，导致评测和线上查询悄悄漏文档。

### 6. 指标与判断

观察 expected/indexed/failed count、coverage、build duration、write error codes、checksum、smoke retrieval 和 alias conflict count。修复有效必须证明失败项补写后 coverage 恢复且 alias 只切一次；不能只看最终服务能返回结果。

### 7. 方案取舍

不可变索引会增加存储占用，但换来原子发布、可重复评测、快速回滚和历史 Citation 可验证。原地更新适合低风险临时原型，不符合本课程综合项目的审计要求。

alias 是“当前推荐快照”的可变指针，不是对象身份。所有报告和 Answer 必须保存精确 index ID。

### 8. 学员任务与参考答案

任务：阅读 alias CAS 测试，增加两个 build 同时基于同一 expected active ID 发布的并发场景。预期只有一个成功，另一个返回 `ACTIVE_INDEX_CHANGED`，两个 ready index 都保留供审查。

参考答案要点：失败方不能自动覆盖赢家；它应重新读取 active manifest，再由人或编排规则决定比较、放弃或重新发布。删除失败方索引会破坏审计和潜在回滚。

## 概念闭环 3：索引类型是质量、延迟、内存和构建成本的联合决策

### 1. 一句话定义与问题

向量索引通过不同数据结构在精确性、搜索时间、内存、训练和构建时间之间取舍；工程选型要用 exact Flat 作为真值近似基线，再比较近似索引。

### 2. 运行时对象与参数

Flat 关键参数是 dimension 与 metric；IVF 常见参数包括 `nlist` 和查询时 `nprobe`；HNSW 常见参数包括图连接度和搜索深度。参数必须进入不可变 index/retrieval profile，不能只存在调用现场。

FAISS 官方说明 Flat 能提供 exact 结果，IVF/HNSW 等索引用近似换速度/内存。具体能力以 [官方核对表](../references.md) 的链接为准。

### 3. 最小可运行代码与阅读点

运行 lab03 index benchmark。先建立 Flat baseline，再在同一向量集合和 query 集上运行可用的 IVF/HNSW profile；阅读构建阶段与查询阶段参数分别落在哪里。

### 4. 调用链和中间状态

固定 embedding records -> build index per profile -> run warmup -> repeat timed queries -> compare retrieved chunk IDs with Flat -> aggregate recall/latency/memory -> save profile-bound report。

### 5. 可复现失败

把 IVF `nprobe` 设得过低，观察 p95 下降但 Recall@10 明显退化；或用未 normalize 向量比较 cosine/IP，观察排序异常。修复必须改变 profile 并重建或重新查询，不允许在报告里覆盖旧参数。

### 6. 指标

至少记录 Recall@k 相对 Flat、query p50/p95、QPS、index size、peak memory、build/train time 和增量更新代价。小数据只测一次的毫秒数不可靠，必须 warmup、多次运行并说明机器信息。

### 7. 取舍边界

| 场景 | 候选起点 | 必须验证 |
|---|---|---|
| 小语料、查询不多、需要 exact | Flat | 内存是否可接受 |
| 数据增大、允许少量召回损失 | IVF/HNSW | Recall-latency 曲线和构建成本 |
| 生产元数据过滤/多租户 | Milvus/Qdrant 等 adapter | filter schema、隔离、备份、运维和成本 |
| 教学离线基线 | 本地确定性/FAISS adapter | 无网络可运行、结果可解释 |

### 8. 学员任务与参考答案

任务：在至少三组参数上画 Recall@10-p95 曲线，选择一个不低于自定召回门槛的最低延迟 profile，并说明数据规模变化后是否仍成立。

参考答案要点：不接受“某索引更快”这种单点结论。正确答案应包含 Flat 参照、运行重复次数、硬件、数据量、profile、误差/方差和适用范围。若所有参数差异很小，可能数据集过小，结论应是“当前证据不足以引入近似复杂度”。

## 章末小结

- Embedding 质量、shape 和索引兼容是不同层面的验证。
- dimension、normalize、metric、模型 revision 或 chunk profile 变化都要求新索引身份。
- exact Flat 是比较近似索引召回的基线，不是所有生产场景的默认答案。
- alias 负责发布，index ID 负责审计；历史对象不能只引用 alias。

下一步：进入 [L04](L04_retrieval_and_reranking.md)，把稀疏、稠密、过滤、改写、融合、精排和上下文准入拆成可独立评测的阶段。
