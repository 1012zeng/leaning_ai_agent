# RAG 术语与常用库解释

> 本课程术语表按 L01–L06 小节组织。每个条目给出**一句话定义、作用、适用边界**，并标注它在哪个 lesson 是主线、哪个是选修/扩展。实现前一手资料见 [官方资料核对表](references.md)。

---

## L01 可观测朴素 RAG：全链对象

| 术语 | 定义 | 作用 | 边界 |
|---|---|---|---|
| RAG（Retrieval-Augmented Generation） | 先从可追溯知识源检索证据，再让生成器基于证据回答的系统模式。 | 解决模型知识过时、无私有数据、回答缺出处的问题。 | 适合知识更新频繁、需出处的场景；不适合确定性计算（应走 SQL/业务代码）或可完整放进上下文的少量文档。 |
| Naive RAG | 文档→切块→嵌入→向量检索→拼接上下文→生成的最简流程。 | 建立对象链直觉、做确定性对照基线。 | 生产命中率和引用质量通常不足，需在此基础上叠加优化。 |
| StageResult[T] | 每个阶段统一返回的结构化信封（success / partial_success / failed），携带 `data`、`item_results`、`problem`。 | 让调用方按稳定状态分支，不解析异常文本。 | 空结果与失败必须区分：合法无命中是 success，不是 failed。 |
| TraceEvent | 只记录 ID / 计数 / 哈希 / 耗时的追加式事件，不复制正文或密钥。 | 用于故障定位和性能归因。 | 高基数或敏感字段不得进 trace；trace 丢失是 telemetry_error，不是系统失败。 |
| 调用链（pipeline） | CLI → ingestion → indexing → retrieval → rerank → context → generation 的可观察对象流。 | 让每一步的输入/输出类型可检查。 | 调试从最早异常中间对象开始，不要直接看最终答案。 |

## L02 解析与分块

| 术语 | 定义 | 作用 | 边界 |
|---|---|---|---|
| SourceDocument | 带版本/租户/来源 URI 的逻辑源快照，由内容 SHA-256 派生稳定 ID。 | 作为整条派生链的根，内容不变则 ID 不变。 | 内容更新保留 source document ID，只改 source version。 |
| ParsedDocument | 在固定 parser profile 下对源字节解码、规范化、结构解析后的产物。 | 携带规范化文本、元素列表、section path、charset 与 replacement 信息。 | 不同 profile 对同一源产生不同 parsed document ID。 |
| Chunk | ParsedDocument 在固定 chunk profile 下产生的、带来源版本与字符跨度的最小检索单元。 | 让长文档可被检索和引用。 | 同一文档换 chunk profile 必须产生新 chunk ID，旧标签不可按"文本差不多"迁移。 |
| 结构感知分块（structural chunking） | 按 Markdown/HTML 标题层级切分，保留 section path。 | 让 chunk 具备可读结构和引用路径。 | 依赖源文档结构质量；结构混乱时退化为段落/固定长度分块。 |
| 固定长度分块 | 按 token/byte 窗口滑动切分，可选 overlap。 | 实现简单、适合 baseline。 | 破坏标题/段落语义，可能切断"条件-结论"关系。 |
| 父子分块（parent-child chunking） | 小块负责精确召回，父块负责完整生成上下文。 | 兼顾检索精度与上下文完整性。 | 对象/索引和去重更复杂；检索命中子块后须通过 `parent_chunk_id` 显式提升。 |
| overlap | 相邻 chunk 之间故意重复的 token 区间。 | 减少跨块信息丢失。 | 按 byte 计算 overlap 而 span 按 code point 解释时，中文会产生引用错位。 |
| CHUNK_TOO_LARGE | 单块超过 profile token/byte 上限时的显式错误。 | 阻止 embedding adapter 静默截断。 | 必须从源头拆分或新建更小 chunk profile，不能忽略。 |
| strict / lenient decode | 遇到非法 UTF-8 字节时严格报错或宽松替换的策略。 | strict 保质量，lenient 保可用性。 | lenient 必须在 `replacement_char_count > 0` 时发 warning，并阻止低质量内容自动发布。 |

## L03 Embedding 与索引

| 术语 | 定义 | 作用 | 边界 |
|---|---|---|---|
| Embedding / 向量嵌入 | 把文本映射为固定维稠密浮点向量，使语义相似度可用距离衡量。 | 支撑稠密检索的核心特征。 | 模型 revision、维度、normalize、prompt 都进 embedding profile；换模型必须产生新 ID。 |
| 确定性 hashing embedding | 用特征哈希把 token 映射到固定维桶，无需模型权重。 | 用于离线契约回归和 CI，结果完全可复现。 | 不代表真实语义质量，不能用于 G3 质量验收。 |
| Sentence Transformers | 基于 Transformer 的句子/文档编码库，支持对称与非对称检索。 | 生产级稠密检索的常用选型。 | 非对称模型须区分 query/document 编码入口；模型 revision 和 prompt 必须版本化。 |
| FAISS | Facebook 的向量相似度搜索库，提供 Flat / IVF / HNSW 等索引。 | Flat 作精确基线，IVF/HNSW 在召回-延迟-内存间权衡。 | 不能凭数据规模一句话选型；须实验比较召回、延迟、内存和构建代价。 |
| Milvus / Qdrant | 托管向量数据库，支持混合检索、元数据过滤、多租户。 | 生产部署的常见后端。 | 供应商表达式只存在于 adapter 内，不得穿过领域 port；过滤字段需显式索引/schema。 |
| 索引优化（index optimization） | 通过量化、图结构、聚类加速向量检索。 | 在可接受召回损失下降低延迟和内存。 | 优化参数进 index profile；须用固定评测集证明召回损失可控。 |
| IndexManifest | 索引构建的不可变清单，含维度、metric、coverage、content_checksum、state。 | 让索引发布可审计、可回滚。 | 只有 `state=ready` 的索引可发布；写失败产生 partial 状态，不得切流量。 |
| EmbeddingRecord | 单个 chunk 在固定 embedding profile 下生成的向量记录，含输入哈希与 profile identity。 | 让向量可追溯到精确 profile 和输入。 | 维度不匹配索引时拒绝写入，恢复方式是新建匹配维度的索引。 |

## L04 检索、重排与上下文

| 术语 | 定义 | 作用 | 边界 |
|---|---|---|---|
| BM25 | 基于词频/逆文档频率的经典稀疏检索算法。 | 对精确词、数字、日期、稀有术语强。 | 对同义改写、跨语言弱；不能直接与 cosine 分数相加。 |
| Dense retrieval | 用 query 向量在向量库中做近邻搜索。 | 对语义改写、措辞变化强。 | 对精确数字、近名实体、否定和版本冲突弱。 |
| Hybrid search | 同时走稀疏和稠密两路候选，再融合。 | 兼顾精确词与语义。 | 融合必须在 rerank 阶段完成，检索阶段不比较跨通道原始分数。 |
| RRF（Reciprocal Rank Fusion） | 按排名倒数融合多路候选：`score = Σ 1/(k + rank)`。 | 避免直接比较不可比的原始分数。 | 参数 `k` 进 rerank profile；须实验校准。 |
| Reranking | 对候选集用更重模型重新打分排序。 | 提升前排质量、分离难负例。 | 增加延迟和成本；超时按 profile 允许时降级为 RRF-only 并记 degraded。 |
| Cross-encoder reranker | 把 query-document 拼接后过 Transformer 打分。 | 比向量检索更精确的相关性判断。 | 成本高、需 batch；不可用时须有 fallback。 |
| BGE-M3 | 支持多语言、多粒度、稀疏+稠密+多向量检索的嵌入模型。 | 混合检索的常用选型。 | 模型 revision 和编码配置进 profile。 |
| 元数据过滤（metadata filter） | 按结构化字段（类别、日期、版本）缩小候选范围。 | 满足业务约束、减少噪声。 | 过滤字段须在 index manifest 白名单；非法字段在检索前失败，合法无匹配返回空结果。 |
| 查询改写（query rewriting） | 对原始查询扩展、分解或重写以提升召回。 | 覆盖同义、多跳、歧义场景。 | 改写失败/删除关键约束时必须回退原 query 并记 degraded。 |
| Text2SQL | 把自然语言查询转为结构化 SQL。 | 适合精确数值/聚合场景。 | 本课程范围外；确定性计算应走数据库而非 RAG。 |
| Candidate | 单通道对单个 chunk 的原始检索观察，含 channel、raw score、rank。 | 作为 rerank 的输入证据。 | 不同 channel 的 raw score 不可直接比较；Candidate 直接携带来源链（source document/version ID）。 |
| RankedHit | 融合/精排后的全局命中，含 final score、eligible、decision codes。 | 决定哪些证据进入上下文。 | 不修改 Candidate 或 Chunk；低于准入阈值的 hit 被标记 LOW_CONFIDENCE。 |
| ContextBundle | 按预算选取合格 hit 后渲染的冻结证据包，含 token budget/count、selected hits、warnings。 | 生成器唯一允许消费的证据来源。 | 超预算 chunk 被跳过并发 `CHUNK_EXCEEDS_REMAINING_BUDGET`，绝不静默截断。 |

## L05 引用、拒答与生成

| 术语 | 定义 | 作用 | 边界 |
|---|---|---|---|
| Grounded generation | 生成器只能基于冻结 ContextBundle 中的证据生成回答。 | 让回答可追溯到具体 chunk 和来源版本。 | 模型记忆中的"正确事实"不得发布，除非 ContextBundle 有证据。 |
| Citation | 回答中事实 claim 与冻结 chunk quote 之间的可校验关系（含 span、quote hash、source locator）。 | 让学员/用户能验证每个事实。 | 没有事实 claim 时 citation 不适用；拒答不能自动得 1 分。 |
| Claim | 回答中的一个事实 span，必须绑定至少一个 citation。 | 最小可验证事实单元。 | 装饰性文本不是 claim；claim 必须由 citation 支持。 |
| 拒答（abstain） | ContextBundle 无足够证据时明确返回 `insufficient_evidence`。 | 避免编造答案。 | 是合法业务结果，不是系统错误；拒答率是观测指标。 |
| 澄清（clarify） | 查询存在多个同等合理解释时请求用户限定。 | 避免强行猜测。 | 不等于系统失败；检索返回多个对象本身是正确的。 |
| Prompt injection | 文档中嵌入恶意指令诱导模型执行非预期操作。 | 安全威胁。 | 检索可能命中注入文档；安全由 context renderer 和 generation 边界决定，不能靠提高召回掩盖。 |
| source locator | citation 中展示的来源定位信息（display name、section path、pages）。 | 让用户能定位原始证据。 | 必须与 frozen chunk 一致，不能引用未进入 context 的 chunk。 |

## L06 离线评测与可观测性

| 术语 | 定义 | 作用 | 边界 |
|---|---|---|---|
| Hit@k | 前 k 个结果中至少有一个正相关 chunk 则为 1，否则为 0。 | 衡量"至少找到一个"。 | 只证明存在，不衡量找全；不能替代 Recall/nDCG。 |
| Recall@k | 前 k 中找到的正相关 chunk 数 / 总正相关 chunk 数。 | 衡量"找全"。 | 正相关集合为空时为 not_applicable，不是 0 或 1。 |
| MRR@k | 首个正相关 chunk 排名的倒数；前 k 无正例为 0。 | 衡量首个正例的位置。 | 只看第一个正例，不反映分级顺序。 |
| nDCG@k | 按分级相关性排序质量的归一化指标（gain=2^grade-1，折损=log2(rank+1)）。 | 使用 0..3 分级顺序。 | IDCG=0 时不适用；grade 0 是审查过的困难负例，不计入正相关集合。 |
| Context recall | 必要 claim key 被至少一个选中 context chunk 支持的比例。 | 定位 context 选择失败。 | 检索已找到证据但 context 丢失必要 claim，首个失败阶段是 context。 |
| Faithfulness | 事实 claim 是否被选中上下文支持。 | 衡量生成是否忠于证据。 | 模型 judge 必须固定 profile；fixture judge 只做契约回归，不能充当质量证据。 |
| Answer relevance | 响应是否处理了用户问题。 | 衡量回答切题性。 | 可相关但不忠实，也可忠实地复述无关上下文。 |
| Response mode accuracy | 回答/拒答/澄清行为是否符合预期响应方式。 | 衡量生成策略正确性。 | 系统无答案对象时为 system_error，不是 0。 |
| Filter violation count | 检索结果中违反查询元数据过滤的 chunk 数。 | 衡量过滤正确性。 | 通过门槛是零。 |
| Unacceptable claim rate | 回答中匹配不可接受主张的 span 比例。 | 衡量安全防护。 | 拒答且无事实 claim 不惩罚。 |
| Ragas | RAG 评测框架，提供 faithfulness / answer relevancy 等指标。 | 常用质量评估工具。 | 指标名称和 API 会演进；须固定 metric profile，不把旧 import 当稳定接口。 |
| LlamaIndex Evaluator | LlamaIndex 提供的 FaithfulnessEvaluator / RelelevancyEvaluator。 | 另一种评估实现。 | 与 Ragas 互斥选择；judge 结果必须标注 judge profile。 |
| 失败归因（failure attribution） | 一次 case 只记录最早可证实的失败阶段。 | 防止同一根因重复计数。 | 顺序：retrieval → context → generation → evaluator。 |
| 切片（slice） | 按 category / difficulty / diagnostic stage / response mode 分组。 | 暴露局部短板。 | 只报平均分无法发现切片级退化。 |

---

## 常用库与工具索引

| 库 / 工具 | 角色 | 本课程位置 | 一手资料 |
|---|---|---|---|
| LangChain | LLM 应用框架（loader / retriever / vector store 抽象） | 仅作 adapter，对象不得穿过领域 port | [Vector store integrations](https://docs.langchain.com/oss/python/integrations/vectorstores)、[Retrievers](https://docs.langchain.com/oss/python/integrations/retrievers/index) |
| LlamaIndex | RAG 框架（索引/查询/评估） | 仅作 adapter；评估示例见 all-in-rag C6 | [Docs](https://docs.llamaindex.ai/) |
| Sentence Transformers | 句子/文档嵌入 | 生产稠密检索选型 | [Semantic Search](https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html) |
| FAISS | 向量相似度搜索库 | Flat 基线 / IVF / HNSW 对比 | [Guidelines](https://github.com/facebookresearch/faiss/wiki/Guidelines-to-choose-an-index)、[Indexes](https://github.com/facebookresearch/faiss/wiki/Faiss-indexes) |
| Milvus | 托管向量数据库 | 混合检索 + 元数据过滤 | [Filtered Search](https://milvus.io/docs/filtered-search.md)、[Hybrid Search](https://milvus.io/docs/multi-vector-search.md) |
| Qdrant | 托管向量数据库 | dense/sparse 组合 + 过滤 | [Hybrid Search](https://qdrant.tech/documentation/search/text-search/hybrid-search/)、[Filtering](https://qdrant.tech/documentation/search/filtering/) |
| BGE-M3 | 多语言多粒度嵌入模型 | 混合检索选型 | [Model](https://huggingface.co/BAAI/bge-m3) |
| Ragas | RAG 评测框架 | 质量评估工具 | [Available metrics](https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/) |
| LangSmith | LLM 可观测与评测平台 | 生产可观测选型（本课程用自研 TraceEvent） | [Docs](https://docs.smith.langchain.com/) |

下一步：对照 [all-in-rag 路线映射](all-in-rag-mapping.md) 看每个术语在参考路线中的位置与差异。
