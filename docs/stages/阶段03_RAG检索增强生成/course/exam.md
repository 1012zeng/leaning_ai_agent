# RAG 阶段出师试卷与评分标准

## 考试规则

总分 100：闭卷笔试 50 分（90 分钟）+ 实操 40 分（60 分钟）+ 口述复盘 10 分（10 分钟）。允许实操查仓库文档和官方资料，不允许复制现成答案或使用测试集调参。答案必须引用对象字段、指标或项目证据。

通过：总分至少 75；笔试、实操各至少 60%；实操中的对象追踪和故障定位各至少 60%。硬编码/泄漏密钥、伪造结果、fixture 冒充质量、无证据强答或破坏历史数据，直接不通过。

## A 卷：笔试（50 分）

### 1. 系统边界（5 分）

题目：用不超过 120 字解释“RAG 不等于向量数据库”，并分别给出一个应使用 RAG、应使用 SQL/确定性代码、应先考虑长上下文的场景。

参考答案：RAG 是获取外部证据并据此生成的系统，向量库只是可选检索 adapter。私有政策问答适合 RAG；库存/金额计算应走数据库与业务规则；少量稳定文档可先比较完整上下文。评分：定义 2，三个边界各 1。

### 2. 对象分类（5 分）

题目：将“原始 URI、人工 relevance grade、Chunk.text、rerank final score、Answer、trace latency、LLM judge 分数”归入事实 F、派生 D、观测 O，并解释一个混用风险。

参考答案：原始 URI/人工 grade 是 F；Chunk、final score、Answer、judge score 是 D；latency 是 O。将 final score 写回 source metadata 会污染来源事实且无法重算；将 judge 写入 ground truth 会数据泄漏。分类 3.5，风险 1.5。

### 3. 身份与版本（5 分）

题目：同一文件路径内容更新、parser profile 更新、只更新 chunk profile、删除后恢复时，哪些 IDs 应变化或复用？

参考答案：内容更新保留 source document ID，改变 source version/state 及后续派生链；parser profile 更新保留 source version，从 ParsedDocument 起重建；只改 chunk profile 复用 ParsedDocument，从 Chunk 起重建；删除/恢复复用内容版本，追加新 state ID，按契约决定派生链复用和新 manifest。每场景 1，理由 1。

### 4. 分块实验（5 分）

题目：设计固定/结构感知/父子分块对比，列出唯一变量、冻结项、至少 4 个指标和两个可能相反的结果。

参考答案：唯一变量 chunk profile；冻结 bytes/parser、embedding/index/retrieval/rerank、dataset/labels、metric profile、代码版本。指标含 token 分布、Recall@5、MRR、引用完整、索引大小/延迟。小块可能召回升但上下文断裂；大/父块可能完整度升但噪声/成本升。设计 3，权衡 2。

### 5. 分数语义（5 分）

题目：为什么不能直接相加 BM25 score、cosine similarity 和 L2 distance？给出两个合规方案。

参考答案：标度、分布和高/低优方向不同。可保留通道 rank 用 RRF；或在固定 profile 下校准后加权。Candidate 保存 score kind/semantics，融合属于 rerank profile。原因 2，方案 2，对象边界 1。

### 6. 过滤与改写（5 分）

题目：用户问“只查 2026 生效的财务政策”，query rewrite 删除“2026”。说明对象应保存什么、怎样防止误召回、怎样评测。

参考答案：保留 original/normalized text 与 rewrite steps；把授权且可校验的时效条件放结构化 filter，字段在 manifest 白名单；漂移时回退；用时效冲突切片比较 Recall/错误版本引用/latency。对象 2，修复 2，指标 1。

### 7. 引用与拒答（5 分）

题目：模型给出正确事实，但 ContextBundle 没有证据。系统应返回什么？为什么“答案正确”仍不能发布？

参考答案：`insufficient_evidence`，无伪造 citations。系统承诺是基于冻结证据，不是模型记忆；发布会破坏可追溯和安全边界。若有 claim，Citation 必须验证 hit/context、chunk/source version、quote/span/hash。结果 2，理由 1，校验链 2。

### 8. 指标诊断（5 分）

题目：Recall@5 高、MRR 低、Context Recall 低、Faithfulness 低分别优先检查什么？

参考答案：Recall 高 MRR 低先看融合/rerank；Context Recall 低看 eligible、去重、预算；Faithfulness 低看 generator、噪声、claims/citations；不能先换 embedding。每层 1，诊断顺序 1。

### 9. 评测可信度（5 分）

题目：指出以下报告的五个缺口：“新方案 RAGAS 0.86，旧方案 0.82，所以上线。共 10 题，失败的 judge 请求已按 0 分处理。”

参考答案可包括：无 dataset/system/index/metric/judge/profile/commit 身份；样本小无切片/不确定性；未说明具体 metric；judge 失败不应当 0；无检索/引用/延迟/成本/安全指标；test 是否用于调参未知；无回退/门禁。任五项各 1。

### 10. 恢复工程（5 分）

题目：索引 1000 个 chunks 时 17 个写失败，生成请求超时状态未知。分别说明发布、重试和幂等行为。

参考答案：index manifest partial、coverage 0.983、默认不切 alias，仅用相同 build/key 重试失败项，验证 ready 后 CAS；generation 复用 answer ID/idempotency key，先查询旧结果，不换 key 重发。索引 3，生成 2。

## B 卷：实操（40 分）

### 11. 读代码追对象（12 分）

在 lab01 从 CLI 追踪一个 answerable case。提交调用链、每阶段输入输出类型、关键 IDs/shape、一个不变量和对应测试；从 Citation 反查 SourceDocument 精确版本。

评分：调用链 3，对象/shape 3，ID 反查 3，不变量/测试 2，表达 1。漏掉 source version 或只画框架 chain，最高 6 分。

### 12. 故障定位（12 分）

给定“相关 chunk 在 dense Candidate rank 2，但最终 ContextBundle 不含它”。按假设顺序定位，不允许先修改代码。

参考路径：查 sparse/dense Candidate evidence -> RankedHit candidate IDs/final rank/eligible/decision codes -> rerank profile/timeout/fallback -> Context selected/dropped/warnings/token budget。提交首个异常对象、根因、最小修复和回归。假设 2，证据 4，根因 2，修复 2，回归 2。

### 13. 修改与测试（8 分）

为 `CHUNK_EXCEEDS_REMAINING_BUDGET` 增加一个边界用例，确保 context 跳过整块、记录 warning、不静默截断，Citation 不会引用该块。

评分：失败先复现 2，正确断言 3，修复边界 2，既有回归 1。仅让测试通过但改变原 Chunk，最高 3 分。

### 14. 设计实验（8 分）

在同一 dev set 比较 dense baseline 与 hybrid+rerank。提交假设、profiles、冻结条件、Recall@5/MRR/p95/成本、至少两个失败 case 和采用/拒绝结论。

评分：控制变量 2，指标/身份 2，case 分析 2，取舍/局限 2。使用 test 调参或只报平均分，最高 3 分。

## C 卷：口述复盘（10 分）

用 5 分钟讲一次真实问题：症状、错误假设、观察、根因、修复、验证、预防。随后回答两个追问：“如果流量扩大十倍，哪个结论先失效？”“如果不能使用 LLM judge，如何维持质量证据？”

评分：技术准确 3，定位深度 3，表达结构 2，项目证据/诚实边界 2。没有真实证据只背标准答案，最高 4 分。

## 阅卷等级

| 等级 | 分数 | 能力判断 |
|---|---:|---|
| 未通过 | <75 或关键项失败 | 不能独立交付；按最低分域安排补强和重测 |
| 合格 | 75-84 | 能在明确契约和评测下独立完成文本 RAG 主线 |
| 良好 | 85-92 | 能定位跨阶段问题，做可信消融并处理主要恢复场景 |
| 优秀 | 93-100 | 能清楚辩护边界/风险，对不确定性诚实，证据可供他人复现 |

考试通过不自动等于阶段结业；还必须完成综合项目、答辩和干净环境验收。

下一步：先独立作答 A 卷，再运行实操；评分前不要阅读参考答案段落。
