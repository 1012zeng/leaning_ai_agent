# L06：离线评测、失败切片与可观测性

## 本章目标与活动

本章把“感觉回答不错”改造成可复现评测：人工真值和运行评分分离，检索/上下文/生成分层计量，失败样例能沿 trace 回到首个异常对象。

| 活动 | 任务 | 证据 |
|---|---|---|
| 读代码 | 追踪 dataset loader -> pipeline -> per-case metrics -> aggregate | manifest、case、metric profile 和分母处理图 |
| 改代码 | 增加一个 failure slice 或非 LLM metric | schema、单元测试、基线报告差异 |
| 设计实验 | 朴素、混合、混合+rerank 三系统消融 | 同一评测集上的分层指标/延迟/成本 |
| 解释结果 | 深挖至少 3 个失败 case | trace、对象引用、根因、修复与回归 |

## 概念闭环 1：`EvalCase` 和 manifest 冻结“拿什么判断好坏”

### 1. 一句话定义与具体问题

`EvalCase` 是版本化评测集中的不可变题例，包含 query、人工 ground truth、检索相关性标签、参考引用和 tags；manifest 冻结语料与文件校验和，解决实现输出反过来定义“正确答案”的数据泄漏。

### 2. 运行时对象 shape/type/字段

EvalCase 关键字段：case/dataset IDs、dataset version、stable case key、train/dev/test split、query、ground truth、retrieval labels、reference citations 和 tags。运行评分、模型 judge 输出、耗时和 trace 不属于 EvalCase。

不变量：test split 不用于调参；labels 固定 source version/chunk；relevance grade 0..3；required claim 有 reference citation，除非真值规定应拒答；任何标注变化发布新 dataset version 和 manifest checksum。

物理文件按所有权拆分为 corpus、eval cases、ground truth、retrieval labels 和 answer labels，布局见 [数据契约 §9](../../planning/03_code_and_data_contracts.md#9-语料真值标注与轨迹文件)。

### 3. 最小可运行代码与阅读点

运行 [evals 校验入口](../../evals/README.md) 和 [lab06](../../labs/README.md)。先读 manifest loader 和 schema，再读 join 规则、stale label 检查、split guard、case runner 与 aggregate denominator。

### 4. 调用链和中间状态

```text
manifest.json -> verify file checksums/counts/schema
 -> assemble EvalCase from facts/labels
 -> reject incompatible corpus/chunk profile/index
 -> run fixed system profile per case
 -> save Answer/object refs + metric results
 -> aggregate by overall and failure tags
```

调参只用 train/dev；test 只在方案冻结后运行。反复查看 test 再改参数等同泄漏。

### 5. 可复现失败：标注与索引版本漂移

修改 chunk profile 后沿用旧 retrieval labels。正确行为是 `EVALUATION_LABEL_STALE` 并停止受影响 case；错误实现按相似文本猜测迁移或把无匹配当 0 分，导致评估无法解释。

另一个错误是用模型自动生成的答案未经规则/人工确认直接写入 ground truth。模型输出是派生数据，不是领域事实。

### 6. 指标与数据质量

记录 schema/checksum、case count、split/tag 分布、answerable/unanswerable 分布、label coverage、annotation agreement 和 stale label count。评测集小而覆盖失败类型，比大量同质简单题更有诊断价值。

### 7. 方案取舍

人工双审成本高但适合关键真值；规则可校验的结构事实可自动生成候选再人工确认；LLM 适合辅助生成候选或 judge，但其 profile、偏差和失败必须记录，不能成为无来源真值。

### 8. 学员任务、验收与参考答案

任务：新增一个“无答案 + 干扰文档”和一个“时效冲突”题例，补齐 expected abstain、不可接受主张、source version 和 tags。验收 evals 完整性检查通过，现有 case checksum/版本策略符合规范。

参考答案要点：无答案题不能只把 reference answer 写成空字符串；必须明确 allow/expect abstain 和不可接受主张。时效冲突必须冻结旧/新 source version，并能判断引用了哪一版。

## 概念闭环 2：指标要先回答“哪个阶段失败”

### 1. 一句话定义与具体问题

分层指标把召回、排序、上下文、生成、引用和运行成本分开，解决端到端分数下降时不知道该改哪一层的问题。

### 2. 运行时输入/输出与口径

| 层 | 指标 | 最低所需字段 | 解释 |
|---|---|---|---|
| 检索 | Hit@k/Recall@k | query、top-k chunk IDs、相关 labels | 是否找回至少/全部相关证据 |
| 排序 | MRR/nDCG@k | ordered hits、relevance grade | 首个相关项是否靠前、分级相关性排序质量 |
| 上下文 | precision/recall、token utilization | selected hits、labels、token budget | 进 prompt 的证据是否相关且覆盖充分 |
| 生成 | faithfulness、response relevancy、correctness | question、answer、context、reference | 是否基于上下文、是否回答问题、是否符合真值 |
| 引用 | correctness/completeness | claims、citations、reference spans | 引用是否支持 claim、事实 claim 是否覆盖 |
| 运行 | p50/p95、error/fallback、token/cost | TraceEvent、usage、price profile | 是否满足服务与预算约束 |

Hit@k 是至少一条相关证据是否出现；Recall@k 是已找回相关项占全部相关项比例；MRR 关注首个相关项排名；nDCG 支持 0..3 分级相关性。它们不能互相替代。

Ragas 等工具只作为 metric adapter；课程 metric profile 固定准确名称、输入字段、judge 和阈值。API 名称随版本变化时更新 adapter，不改变课程语义，见 [官方核对表](../references.md)。

### 3. 最小可运行代码与阅读点

运行 lab06 非 LLM retrieval metrics，再运行 fixture 契约模式和真实模型质量模式。阅读每个 metric 的输入字段、失败处理、per-case result 和 aggregate denominator；确认 evaluator 失败没有静默当 0。

### 4. 调用链和中间状态

per case: expected labels + Candidate/RankedHit/Context/Answer/Citation refs -> deterministic retrieval/citation metrics -> optional real judge metrics -> status/problem -> aggregate only evaluated cases and report failed count。

### 5. 可复现失败：平均分掩盖关键切片

总体 Recall@5 上升，但“编号查询”和“无答案”切片显著退化。只汇报平均值会发布回归。正确报告按 tags、难度、answerability 和失败类型切片，并列出样本数。

LLM judge 超时若被记为 0 分会混淆系统质量和评估器可用性；正确结果是 case metric failure/partial success，聚合显式报告分母。

### 6. 指标阈值与不确定性

阈值必须在固定数据/系统/metric/judge profiles 下审批。小样本报告原始 case 表和 bootstrap/重复运行的不确定性，不能把 0.01 波动解释为确定提升。LLM judge 至少抽样人工复核；同一系统多次运行观察方差。

### 7. 方案取舍

确定性检索指标便宜、稳定但不覆盖答案语义；LLM judge 能评估 faithfulness/relevancy，却有成本、偏差和版本漂移；人工评审可信但慢。生产门禁通常组合确定性指标、真实 judge 和人工抽样，而不是只用一个总分。

### 8. 学员任务、验收与参考答案

任务：比较 keyword-only、dense-only、hybrid+rerank 三个 profile，至少按 exact-term、semantic、filter、no-answer 四个 slice 报告 Recall@5、MRR、faithfulness、citation completeness、p95 和成本。

验收：lab06 契约模式和 `pytest -k evaluation` 通过；质量模式拒绝 fixture generator/judge；报告列出 total/evaluated/failed cases 和 profiles。

参考答案要点：hybrid+rerank 的预期是提高混合 query 分布的前排质量，不保证每个切片都胜出。若检索提升而 faithfulness 下降，检查 ContextBundle 噪声、预算和 generator；若引用完整但 correctness 低，可能引用真实却不支持 claim。

## 概念闭环 3：`TraceEvent` 回答一次运行发生了什么

### 1. 一句话定义与具体问题

`TraceEvent` 是 append-only 的阶段观测事件，只通过对象 ID 串起 input/output、状态、耗时、重试和降级，解决错误日志无法重建一次 pipeline 的问题。

### 2. 运行时对象 shape/type/字段

关键字段：event ID、32 hex trace ID、16 hex span/parent span ID、sequence、stage、event type、occurred at、status、input/output refs、numeric metrics、low-cardinality attributes 和可选 ProblemDetails。

同 trace sequence 唯一；completed/failed 对应 started span；error 必须有 problem；metrics 不含原文、prompt、向量、密钥或个人信息。TraceEvent 是观测数据，不参与 Chunk/Answer 身份。

### 3. 最小可运行代码与阅读点

运行 lab06 正常、retry、fallback 和 failed case，使用 trace viewer/JSONL。阅读 span 创建、parent 传播、event sink failure 缓冲、字段白名单和日志脱敏测试。

### 4. 调用链和中间状态

root evaluation/query span -> each stage started -> completed/failed; retry 创建新 attempt span 并关联原逻辑 stage；fallback 写 degraded event；evaluation 通过对象 refs 联接 per-case 产物，不复制领域正文。

### 5. 可复现失败：trace 断链或泄密

故意让 retry 使用新 trace ID，或把 parent span 填成 trace ID。trace 树无法还原因果，格式校验应失败。让 adapter 把完整 prompt/API key 写入 attributes，隐私测试必须阻断。

### 6. 指标

stage p50/p95、error/retry/fallback count、candidate/hit/context counts、token/cost、trace completeness、orphan span count、dropped telemetry 和敏感字段扫描。可观测 sink 失败不得阻塞主链，但必须有本地缓冲/丢弃计数。

### 7. 取舍

记录完整正文调试方便但泄密、高基数、昂贵且难保留；只记 ID/计数/哈希需要额外对象存储联接，却更安全可控。采样可降成本，但失败、降级和评测运行通常应提高采样率并有明确保留策略。

### 8. 学员任务与参考答案

任务：给 rerank timeout fallback 增加 trace 断言，验证 started -> fallback/degraded -> completed 的因果关系，同时确保 attributes 不含候选正文。

参考答案要点：fallback 是可见的降级成功，不是正常 success 也不是必然 failed；trace 应保留原 query/candidate/output refs、fallback profile 和 problem code，但不保存敏感输入。

## 指标驱动诊断决策树

| 症状 | 先看 | 常见根因 | 不要先做 |
|---|---|---|---|
| Recall 低 | Chunk/labels/Candidate per channel | 分块、embedding、query、filter、index | 调 prompt |
| Recall 高、MRR 低 | Candidate -> RankedHit | 融合、reranker、tie、截断 | 增大 context |
| MRR 高、context recall 低 | ContextBundle warnings/budget | 准入、去重、预算 | 换 embedding |
| context 好、faithfulness 低 | Answer claims/Citations/generator | prompt、模型、注入、validator | 增大 top_k |
| 质量好、p95/成本超限 | stage trace/usage | 候选深度、rerank、budget、模型 | 降低质量门槛且不评测 |
| 无答案题强答 | eligible/context/outcome | 阈值、拒答、模型绕过证据 | 把无答案题删掉 |

## G3 评估闸门

使用固定 dataset/system/metric profiles 和真实本地或云端生成模型。Faithfulness 不低于 0.80；judge 必须是独立真实模型或双人盲审；至少完成三个失败实验，覆盖检索、上下文和生成中的三个不同环节。fixture profile 必须被质量模式拒绝。

通过报告还要包含引用正确/完整、answer relevancy、answerable/unanswerable 切片、p95、成本、failed evaluator count、commit SHA 和至少三个 case 的完整根因分析。单一总分达标不够。

## 章末小结

- 真值、模型输出和运行观测各有所有者，不能互相回写。
- 指标先定位阶段，再用于调参；平均分必须配切片和样本数。
- evaluator 失败和被测系统失败要分开记录。
- trace 连接对象 ID 和因果，不复制内容；可观察不等于泄露全部数据。

下一步：完成 [工程扩展 E01-E04](../extensions/engineering.md)，把本地实验升级为配置可追溯、可回归、可恢复的交付。
