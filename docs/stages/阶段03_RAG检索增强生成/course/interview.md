# RAG 工程面试题：20 题、追问与评分点

## 使用方式

一次只回答一题，先用 2-3 分钟给结论、机制、取舍和项目证据，再接受追问。每题 5 分：准确性 2、深度 1、表达 1、项目证据 1。参考答案是最低覆盖，不是背诵稿。

## 概念与范式（1-5）

### 1. RAG 是什么，为什么不等于向量数据库？

参考答案：RAG 先取得外部证据，再让生成器基于证据回答；向量库只是检索 adapter，也可以用 BM25、数据库或图检索。可靠系统还需要版本、上下文、引用、拒答和评测。

追问：不用向量库，能否构成 RAG？什么场景 SQL 比 RAG 更合适？

评分点：说清 retrieval + grounded generation 2；指出 adapter 边界 1；给 SQL/长上下文/微调取舍 1；引用自己项目对象链 1。

### 2. Naive、Advanced、Modular RAG 的区别是什么？

参考答案：Naive 是单次摄入/索引/检索/生成基线；Advanced 在检索前后加入分块、改写、混合、Rerank、压缩/引用等优化；Modular 强调可替换 ports、路由和组合。分类是架构语言，不是质量等级。

追问：你的系统加了 Rerank 就一定是 Advanced 且更好吗？

评分点：三者机制 2；不把标签当性能结论 1；用指标/成本说明是否采用 1；项目消融证据 1。

### 3. 长上下文模型出现后，为什么还可能需要 RAG？

参考答案：长上下文不自动解决来源选择、权限、更新、引用、成本、上下文噪声和评测；但数据小且可全部放入时，应把长上下文作为对照而不是默认构建复杂检索。

追问：如何公平比较 long-context baseline 与 RAG？

评分点：至少四个工程因素 2；承认不需要 RAG 的边界 1；给固定数据/质量/延迟/成本实验 1；项目证据 1。

### 4. 为什么课程先手写最小实现，再接 LangChain/LlamaIndex？

参考答案：手写主链暴露对象 shape、调用链、失败语义和指标；框架作为 adapter 提高接入效率。供应商 `Document/Hit` 不穿过领域 port，升级或切换只改 adapter。

追问：什么时候直接用框架是合理的？怎样避免维护“两套逻辑”？

评分点：ports/adapters 2；唯一领域逻辑与契约测试 1；交付速度/锁定权衡 1；指出项目 adapter 测试 1。

### 5. 为什么每个参数都要进入 profile identity？

参考答案：派生对象和结果只有绑定算法、模型 revision、阈值、Prompt 与 config hash 才可复现、比较、缓存和回滚。语义变化而 identity 不变会污染实验和历史审计。

追问：密钥和 API endpoint 是否也应进入公开 config hash？

评分点：可复现/审计 2；说明 version/hash 和派生 ID 关系 1；区分 secret/deployment config 1；项目 golden test 1。

## 数据工程（6-8）

### 6. `SourceDocument`、`ParsedDocument`、`Chunk` 为什么要分开？

参考答案：它们分别表达来源/生命周期事实、固定 parser profile 的解析、固定 chunk profile 的检索视图；分开才能处理内容版本、parser 升级、chunk 消融、删除恢复和历史引用。

追问：只改 chunk size 时哪些对象/ID 复用，哪些重建？

评分点：三对象语义 2；事实/派生分类 1；从 Chunk 起重建后续链 1；项目 ID 追踪证据 1。

### 7. 如何选择 chunk size 和策略？

参考答案：没有通用最佳值。根据文档结构、问题跨度、模型 token 限制和评测任务比较固定/递归/结构/父子等 profile；同时看 Recall/MRR、引用完整、token/成本、oversize 和失败 case。

追问：为什么“块越小召回越准”不总成立？

评分点：拒绝绝对答案 1；控制变量实验 2；断义/噪声/对象数量权衡 1；项目消融 1。

### 8. 如何处理重复文档、内容更新和删除后恢复？

参考答案：逻辑来源 ID 与内容版本/状态分离；同来源同 bytes/profile 可 unchanged；新 bytes 产生新 version；tombstone/restore 追加状态事实；不同来源同 bytes 可共享 blob 但保留追溯链。

追问：为什么不能先过滤 active 再选最新状态？

评分点：生命周期规则 2；解释旧 active 会被错误复活 1；幂等/outcome codes 1；项目恢复测试 1。

## 检索优化（9-13）

### 9. Dense 与 sparse 检索各自擅长什么，为什么混合？

参考答案：dense 擅长语义/同义表达，sparse 擅长精确词、编号和罕见 token；混合保留互补候选。是否提升要按 query slice 测，不是必然。

追问：为什么不能直接相加两路 raw score？

评分点：互补性 2；score kind/semantics 不可比 1；RRF/校准方案 1；per-channel 项目证据 1。

### 10. RRF 与 cross-encoder Rerank 有什么不同？

参考答案：RRF 用多个排名位置融合，无需原始分数校准；cross-encoder 联合读取 query/candidate 文本做更贵的语义精排。常见流程是先召回/RRF，再对有限候选精排。

追问：Reranker 超时如何降级？候选深度怎样选？

评分点：机制 2；candidate depth/质量/延迟权衡 1；profile fallback/degraded 语义 1；项目 MRR/p95 证据 1。

### 11. 元数据过滤与查询改写有什么本质区别？

参考答案：过滤是调用者/权限声明的硬约束，决定合法搜索空间；改写是派生表达，影响相关性。保留 original text 和 rewrite steps，filter 按 manifest schema 校验。

追问：LLM 从问题中提取的“租户”能否直接作为权限 filter？

评分点：事实/派生/权限边界 2；可信 token claim 1；invalid/empty 语义 1；项目 filter 测试 1。

### 12. 如何选择 FAISS Flat、IVF、HNSW 或服务型向量库？

参考答案：先用 Flat 建 exact 基线，再按数据量、Recall-latency、内存、构建/更新、filter、多租户、备份运维和成本选择。产品名不能替代基准。

追问：数据 10 万条时你会直接选哪个？

评分点：拒绝仅按规模拍板 1；至少四个决策维度 2；基准/门槛 1；项目 benchmark 1。

### 13. Context assembly 为什么要单独成 stage？

参考答案：它在 token budget 下处理准入、去重、父子提升、冲突、顺序和引用锚点；与 retrieval/rerank 分开才能观察证据在哪里丢失，并禁止静默截断。

追问：一个 chunk 超过剩余预算怎么办？

评分点：stage 责任 2；整块跳过/warning 或显式派生压缩 1；指标/取舍 1；项目 budget 实验 1。

## 生成集成（14-16）

### 14. 怎样证明一个 Answer 是 grounded 的？

参考答案：每个事实 claim 有 Citation；Citation 指向本次 ContextBundle 的 RankedHit、冻结 Chunk/source version 和精确 quote span/hash；validator 通过后原子发布。

追问：引用 URL 正确但 quote 不支持 claim，算通过吗？

评分点：完整校验链 2；correctness vs completeness 1；装饰引用不通过 1；项目 span 测试 1。

### 15. 如何设计拒答？

参考答案：空 context、低置信度或引用无法验证时返回 `insufficient_evidence`；用 answerable/unanswerable 数据共同调阈值，观察拒答 precision/recall，而不是只追求低幻觉。

追问：模型知道答案但上下文没有证据怎么办？

评分点：明确拒答结果 2；阈值与两类样例 1；模型记忆非系统证据 1；项目 no-answer 证据 1。

### 16. RAG 如何防 Prompt Injection？

参考答案：检索文档是不可信数据；通过角色/结构分隔、来源授权、最小权限、无工具默认、输出/引用校验、敏感信息检测和安全评测防护。关键词黑名单只能辅助。

追问：怎样在不删除整个恶意文档的情况下保留其中正常事实？

评分点：数据/指令边界 2；最小权限 1；utility + attack success 双指标 1；项目注入样例 1。

## 工程交付（17-18）

### 17. 你会如何建立 RAG 离线评测集和门禁？

参考答案：版本化 corpus/eval cases/ground truth/retrieval labels；train/dev/test 分离；冻结 system/index/metric/judge profiles；分层指标和 failure slices；deterministic 回归加真实 judge/人工抽检；关键切片阻断。

追问：LLM judge 超时或版本变化如何处理？

评分点：数据所有权/版本 2；judge profile/失败不当 0 分 1；门禁/waiver 1；项目报告 1。

### 18. 怎样把一个 RAG 索引安全发布到生产？

参考答案：staging 写入，逐项结果；验证 count/dimension/metric/checksum/smoke/质量；ready manifest；用 expected active ID 做 alias CAS；保留旧索引和回滚窗口；业务 canary。

追问：partial coverage 99.5% 能否发布？

评分点：发布状态机 2；默认不发布、例外需批准阈值/风险 1；CAS/回滚 1；项目演练 1。

## 故障定位（19-20）

### 19. “答案错了”你如何系统定位？

参考答案：从最早中间状态向后：Source/Parsed/Chunk -> manifest -> Candidate per channel -> RankedHit/eligible -> Context warnings/budget -> Answer claims/Citations；每步对照 labels/trace，先提出假设再改 profile。

追问：Recall 高但 Faithfulness 低，先改什么？

评分点：顺序/对象 2；区分检索、context、generation 1；避免盲目换 embedding/prompt 1；真实复盘 1。

### 20. 超时重试怎样避免重复副作用？

参考答案：只有 retryable 且操作幂等才自动重试；复用 request/build/query/answer/run ID 和 idempotency key；未知结果先查询；批任务只重试 failed items；每次 attempt 有关联 span；fallback 显式 degraded。

追问：相同 idempotency key 但 payload 不同怎么办？索引回滚是否删除新索引？

评分点：幂等 identity/payload hash 2；409 conflict 1；alias 回滚且保留历史 1；项目重复请求测试 1。

## 总体反馈模板

面试结束按四维反馈：

| 维度 | 观察 |
|---|---|
| 准确性 | 对象、指标、错误与边界是否正确；有无把框架/产品名当原理 |
| 深度 | 能否解释调用链、不变量、失败模式、取舍和不确定性 |
| 表达 | 是否先结论后证据，术语一致，能在追问中修正 |
| 项目证据 | 是否给出可复现命令、指标、case、trace、测试或复盘，而非“我们做过” |

下一步：随机抽一题，录制 3 分钟回答；回听时删掉没有对象、指标或项目证据支撑的句子。
