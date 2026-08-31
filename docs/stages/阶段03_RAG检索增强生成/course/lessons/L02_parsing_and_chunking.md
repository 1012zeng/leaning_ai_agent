# L02：解析、清洗与结构感知分块

## 本章目标与活动

本章回答两个工程问题：原始来源如何变成稳定的可检索对象；分块参数改变后，如何证明效果变化来自分块而不是别的变量。

| 活动 | 任务 | 证据 |
|---|---|---|
| 读代码 | 追踪 connector、parser、chunker 和 ID 生成 | 三个对象的字段映射与所有者表 |
| 改代码 | 新增一个 Markdown 标题边界或 lenient decode profile | profile 版本、单元测试、旧 profile 回归 |
| 设计实验 | 固定/递归/结构感知/父子分块消融 | Recall@5、MRR、token 分布、oversize 和引用 span 通过率 |
| 解释结果 | 定位“检索到了但答不全” | 证据链和修复理由 |

## 概念闭环 1：来源身份、内容版本与解析结果必须分开

### 1. 一句话定义与问题

`SourceDocument` 表示逻辑来源的一次不可变内容/生命周期快照，`ParsedDocument` 表示固定 parser profile 对某个内容版本的确定性解析；分开它们才能处理内容更新、删除恢复、解析器升级和历史引用。

### 2. 运行时对象 shape/type/字段

| 对象 | 关键字段 | 身份变化规则 | 不变量 |
|---|---|---|---|
| `SourceDocument` | source document/version/state IDs、URI、media type、byte size、content hash、lifecycle state | 同逻辑来源改内容：document ID 不变，version/state ID 变；删除/恢复只追加 state | blob bytes 的长度和 SHA-256 必须匹配；历史快照不可改 |
| `ParsedDocument` | parsed ID、source IDs、parser profile、charset、replacement count、text、elements、warnings | source version 或 parser profile 变化就产生新 parsed ID | element span 落在 text 内；空 text 不创建对象 |

来源 URI、标题和业务 metadata 属于事实；规范化文本、元素和哈希属于派生数据；耗时、重试和异常属于观测数据。把三者混在 `Document.metadata` 会让更新、回滚和评测无法解释。

### 3. 最小可运行代码与逐行阅读点

运行 [lab02 ingestion](../../labs/README.md) 的正常 Markdown、空文件和非法 UTF-8 样例。阅读时逐行确认：bytes 在何处哈希；charset 策略从哪个 profile 注入；换行规范化何时发生；element span 依据规范化前还是后文本；错误如何映射为 item-level `ProblemDetails`。

不要在 lesson 中重写 parser。完整实现和测试只在 `labs/`。

### 4. 调用链和中间状态

```text
connector discovers item
 -> read bytes + verify expected hash
 -> append SourceDocument state snapshot
 -> parser decodes and normalizes text
 -> build Element[] with code-point spans
 -> validate text hash and spans
 -> publish ParsedDocument or quarantine item
```

状态排查：有 SourceDocument 但没有 ParsedDocument，通常是空文档、媒体类型、解码或解析失败；ParsedDocument 存在但结构丢失，则看 element kind、section path 和 page 是否正确。

### 5. 可复现失败：乱码与空文档

严格 UTF-8 profile 遇到非法 bytes 应返回 `DECODE_ERROR` 并隔离；lenient profile 可以产生替换字符，但 `replacement_char_count > 0` 时必须有 warning。0 bytes 或全空白只登记 SourceDocument，返回 `EMPTY_DOCUMENT`，不得产生 ParsedDocument/Chunk。

错误修复不是把 `errors="ignore"` 加上让异常消失；那会静默改变文本和引用 span。修复必须选择显式 charset/profile、保留 warning，并重新验证引用。

### 6. 指标与判断

观察 parse success/quarantine rate、replacement char count、element count、page/section coverage、content hash mismatch 和阶段延迟。修改 parser 后同时检查旧样例回归和新样例恢复；只看成功率会掩盖文本被吞字符。

### 7. 参数和方案取舍

| 方案 | 适用 | 风险 |
|---|---|---|
| 原生 Markdown/HTML parser | 结构规则稳定、依赖少 | 对复杂 PDF/表格覆盖有限 |
| 通用解析库 adapter | 多格式与版面元素 | 系统依赖重、版本变化；必须映射回领域对象 |
| strict decode | 数据质量优先、可重新采集 | 失败率更高但不会静默损坏 |
| lenient decode | 来源不可重取且允许人工复核 | 必须记录 replacement 并阻止低质量内容自动发布 |

### 8. 学员修改任务、验收与答案

任务：给 parser 增加一个“出现替换字符即 quarantine”的 profile，同时保留已有 lenient 行为。验收运行 `pytest -k "decode or parser"`，预期 strict、lenient、新 profile 三组行为各自稳定，profile/config hash 不同。

参考答案要点：策略属于 profile 而不是硬编码 if；同一 bytes 在不同 parser profile 下产生不同 ParsedDocument ID；SourceDocument 的内容版本不变；新策略必须有明确 warning/problem code 和回归测试。

## 概念闭环 2：Chunk 是可重建派生视图，不是随手切出的字符串

### 1. 一句话定义与问题

`Chunk` 是 `ParsedDocument` 在固定 chunk profile 下产生的、带来源版本与字符跨度的最小检索单元，解决长文档不能直接作为检索和上下文单位的问题。

### 2. 运行时对象 shape/type/字段

关键字段：`chunk_id`、`parsed_document_id`、`source_document_id`、`source_version_id`、`chunk_profile`、`ordinal`、`text`、`text_sha256`、`document_char_span`、`token_count`、`section_path`、`page_refs`，父子分块才有 `parent_chunk_id`。

核心不变量：正文应等于 ParsedDocument 对应半开区间；token count 不超 profile 上限；ordinal 从 0 连续；父块和子块必须同 source version；同输入/profile 可重建同一 chunk ID。

### 3. 最小可运行代码与阅读点

运行 lab02 四组分块 profile。读 chunker 的边界选择、overlap、token 计算、标题前缀注入和 ID 编码；随后读 span property test，确认没有用数组下标或随机 UUID 当稳定身份。

### 4. 调用链和中间状态

```text
ParsedDocument.text + elements + chunk profile
 -> choose structural boundaries
 -> enforce token/byte limits
 -> compute [start, end) spans and optional overlap
 -> derive text/hash/token count/section path
 -> validate coverage and ordinal order
 -> publish immutable Chunk[]
```

父子分块中，小块负责精确召回，父块负责完整上下文。检索命中子块后必须通过 `parent_chunk_id` 显式提升，不能把父正文偷偷写回子 Chunk。

### 5. 可复现失败：断义、超长与 overlap 错位

将“适用条件”和“例外条款”放在相邻段，使用过小固定块会把它们拆开；使用过大块会引入多个无关主题。把 overlap 算成 byte offset 而 span 按 code point 解释，会在中文上产生引用错位。单块超过 profile 上限必须 `CHUNK_TOO_LARGE`，不能让 embedding adapter 静默截断。

### 6. 指标与冻结条件

数据指标：chunks/doc、token p50/p95/p99、oversize count、重复字符比例、结构边界命中率、span round-trip 通过率。检索指标：Recall@5、MRR、nDCG；生成指标：引用正确率/完整率、faithfulness 和上下文利用率。

分块对比必须固定 parser profile、embedding/index/retrieval/rerank profile 和 eval labels。chunk profile 改变会产生新 chunk ID，旧 retrieval label 不能按“文本差不多”直接迁移。

### 7. 参数和方案取舍

| 策略 | 优点 | 失败边界 |
|---|---|---|
| 固定长度 | 快、确定、适合 baseline | 破坏标题/段落语义 |
| 递归分隔 | 尊重常见结构、成本低 | 对表格和跨段事实有限 |
| Markdown 结构感知 | section path 和引用友好 | 依赖文档结构质量 |
| 语义分块 | 可能更贴近主题 | 模型/阈值成本高，难复现，必须版本化 |
| 父子分块 | 召回粒度小、生成上下文完整 | 对象/索引和去重更复杂 |

不存在“最佳 chunk size”。短 FAQ、规范手册和跨页表格需要不同 profile；选型依据是固定任务上的质量、延迟、成本与维护复杂度。

### 8. 学员任务、验收与参考答案

任务：对同一语料运行 3 个 chunk profile，每组列出对象数量、token 分布、Recall@5、MRR、引用 span 通过率和索引大小；挑出两个失败题例解释根因。

验收：`pytest -k "chunk or span"` 通过；报告仅改变 chunk profile；每组结果携带新 profile identity 和 index ID；不复用过期 labels。

参考答案要点：小块通常提高定位精度但可能丢上下文并增大对象数；大块可能提高单块信息量但增加噪声和预算压力；结构感知策略只有在源结构可靠时占优。报告必须承认样本量和任务分布限制，不能把一次局部提升推广为通用规律。

## 章末实验：从失败反推分块问题

给定症状“相关文档进入 top 5，但答案漏掉例外条款”：

1. 查 Candidate/RankedHit 是否包含承载例外条款的 chunk。
2. 若没有，检查 label、分块 span 和 retrieval；若有但没进 context，检查准入和预算。
3. 若同一事实被拆成两个块，比较 overlap、结构边界或父子策略。
4. 修复后同时观察 Recall/MRR、引用完整率、token 数与延迟，防止只优化一个题例。

参考结论：不能因为最终答案漏信息就直接加大 chunk。根因也可能是 Rerank 阈值、上下文预算或 citation parser；必须找到首个异常对象。

下一步：进入 [L03](L03_embedding_and_index.md)，理解向量 profile 与不可变索引快照如何把“模型变化”变成可审计重建。
