# E01-E04：RAG 生产化工程扩展

这四个模块把“本机实验能跑”提升为“变更可追溯、回归可判定、失败可恢复、成本和权限有边界”。它们不是另一个框架教程，也是 G4 的必需输入。

## E01：配置、profile、版本与发布身份

### 1. 一句话定义与问题

`ProfileRef(profile_id, profile_version, config_hash)` 把算法、模型 revision、阈值、模板和参数冻结成不可变身份，解决硬编码参数导致的实验不可复现和线上配置漂移。

### 2. 运行时对象

parser、chunk、embedding、index、retrieval、rerank、context、generator、metric 和 judge 各有独立 profile。派生对象保存精确 profile identity；结果报告再保存 dataset/index/commit identity。改变分隔符、tokenizer、模型 revision、RRF 常数、阈值或 prompt，都要得到新 version 或 config hash。

配置值属于 profile，密钥属于运行时 secret provider。二者不能写进同一 YAML/JSON，也不能进入 hash 前的可公开 artifact。

### 3. 最小可运行代码与阅读点

运行 labs 的 profile schema/golden tests。阅读配置加载、canonical serialization、hash、环境覆盖白名单和 adapter 注入；确认领域模块不直接读环境变量。

### 4. 调用链

versioned config -> schema validation -> canonical hash -> dependency injection -> stage command -> derived object/profile refs -> trace attributes/result manifest。发布只切 profile/index alias，历史对象不改。

### 5. 可复现失败

修改 `top_k` 但忘记改变 config hash，两个不同系统被记成同一 profile；回归报告不可比较，测试应阻断。另一个失败是使用 `latest` 模型 tag，供应商更新后结果漂移却 identity 不变。

### 6. 指标与验证

profile validation failure、unknown field、secret scan、config hash mismatch、artifact identity completeness 和 rollback success。修复后同一配置两次 hash 相同，任何语义参数变化 hash 不同。

### 7. 取舍

严格不可变配置增加发布步骤，但使审计、缓存、消融和回滚可行。环境变量只适合密钥、端点等部署差异；质量参数应进入版本化 profile。

### 8. 学员任务与参考答案

任务：把一个硬编码 rerank threshold 移到 profile schema，补默认值、范围验证、hash golden test 和旧 profile 回归。参考答案要点：阈值归属 rerank profile；变化产生新 RankedHit identity；不得通过环境变量静默覆盖评测系统。

## E02：可观测性、日志、隐私与成本

### 1. 一句话定义与问题

生产可观测性用 trace、结构化日志和低基数指标回答“哪次请求、哪个阶段、为什么失败、花了多少”，同时避免把原文、向量、Prompt、密钥和个人信息复制到监控系统。

### 2. 运行时对象

TraceEvent 负责因果和阶段 refs；日志负责离散业务/错误事件；metrics 负责聚合趋势；usage/cost artifact 保存 token 和版本化价格口径。请求 ID、trace ID 和领域对象 ID 用于联接，但不参与领域对象身份。

### 3. 最小可运行代码与阅读点

运行 trace completeness、structured logging 和 secret/PII scan 测试。阅读 telemetry sink 故障时的本地缓冲与丢弃计数，确认观测失败不反向中断领域主链。

### 4. 调用链

request -> root span -> stage spans/events -> structured problems -> numeric metrics -> sampled export；results 通过 IDs 指向受控 artifact store，监控面不保存语料正文。

### 5. 可复现失败

在 prompt 中放 canary secret，验证日志/trace/artifact 展示面均不泄漏。让 telemetry sink 超时，主请求仍按业务结果完成并增加 dropped telemetry 指标。

### 6. 指标与告警

stage p50/p95/p99、QPS、error/retry/fallback、empty retrieval、abstain、citation failure、token/cost、queue depth、trace completeness 和 dropped telemetry。告警必须带影响、problem code、trace 查询入口和运行手册动作。

### 7. 取舍

全量 trace 便于调试但成本高；生产可按正常请求采样、失败/降级全采样。高基数对象 ID 适合 trace/log，不适合 metrics label。成本估算必须记录 provider/model revision 和价格表版本，不能把一次估值当账单事实。

### 8. 学员任务与参考答案

任务：为 `CITATION_SPAN_MISMATCH` 设计一个可行动告警。参考答案应包含错误率/最小样本窗口、受影响 generator profile、trace 入口、回滚/禁用发布动作和无正文泄漏；只写“错误率高请检查”不合格。

## E03：离线评测门禁、缓存与持续回归

### 1. 一句话定义与问题

评测门禁把已批准的质量、延迟、成本、安全和契约阈值放进 CI/发布流程，防止“单测通过但 RAG 行为退化”的变更进入 alias。

### 2. 运行时对象

门禁输入包括 dataset manifest、system/index/metric/judge profiles、commit SHA 和 baseline report；输出逐项 pass/fail/waiver。cache key 必须包含直接输入 IDs、profile identity 和 code/data version，不能只用 query 文本。

### 3. 最小可运行代码与阅读点

运行 deterministic contract suite、retrieval regression 和质量模式的 profile guard。阅读 baseline 选择、阈值方向、失败 case denominator、waiver 到期、报告签名和 cache invalidation。

### 4. 调用链

PR/发布候选 -> build immutable artifacts -> contract/security tests -> deterministic eval -> optional real-model quality eval -> compare approved baseline -> gate report -> human review -> CAS alias publish。

### 5. 可复现失败

新 profile 因 cache key 不含 config hash 命中旧答案，指标“完全不变”。测试应修改任一 profile 后断言 cache miss。另一个失败是 evaluator 超时被算 0 分，门禁错误归咎系统；应单独阻断评估基础设施或按批准策略重试。

### 6. 门禁指标

最低包含 schema/contracts、Recall/MRR/nDCG、faithfulness、citation correctness/completeness、answerable/unanswerable、p95、成本、安全用例和失败切片。阈值同时定义最大允许回归、最小样本和失败处理。

### 7. 取舍

全套真实模型评测慢且贵，可用确定性 suite 做每次提交回归，真实质量评测在合并/发布候选运行；但 fixture 永远不能替代质量门禁。waiver 只能有责任人、理由、风险、到期和补救任务，不能永久跳过。

### 8. 学员任务与参考答案

任务：为“总体 Recall 不降但 no-answer 强答率上升”写门禁。参考答案：整体指标和安全/拒答切片同时设阈值；任一关键切片阻断；报告列出 case IDs、profiles 与回退建议。不能用平均分抵消关键风险。

## E04：故障注入、幂等、重试、降级与回滚

### 1. 一句话定义与问题

恢复工程为每种失败定义可重试性、幂等身份、有限重试、可见降级和不可变回滚，解决超时后重复写、部分索引发布和“降级成功冒充正常”的问题。

### 2. 运行时对象

写操作保存 idempotency key + normalized payload hash；同 key 同 payload 返回第一次结果，同 key 不同 payload 返回 `IDEMPOTENCY_CONFLICT`。重试复用 request/build/query/answer/run IDs；每次尝试有新 span。fallback 产生 degraded 状态；回滚切 alias，不改历史对象。

### 3. 最小可运行代码与阅读点

运行 timeout、partial write、duplicate request、rerank fallback、index alias conflict 和 rollback tests。阅读重试白名单、exponential backoff+jitter、`Retry-After`、unknown outcome 查询和副作用断言。

### 4. 调用链

request -> validate idempotency record -> execute -> timeout/partial result -> query prior outcome -> retry only failed items when retryable -> fallback if profile allows -> persist degraded trace -> rollback via expected-active CAS when required。

### 5. 可复现失败

generation 请求超时后换新 answer ID 重发，会出现两个可发布答案；正确行为是复用 answer ID/key，先查询前次结果。索引 17/1000 写失败时默认不切 alias，补失败项后重新验证。

### 6. 指标与恢复证据

retry count/attempt latency、idempotency conflict、duplicate side effects、partial coverage、fallback rate、rollback latency、old/new alias IDs 和 post-rollback smoke/quality checks。恢复完成不仅是命令成功，还要验证业务查询和历史引用。

### 7. 取舍

只有 `retryable=true` 且操作幂等才自动重试；输入/业务校验失败不重试。fallback 牺牲某些质量换可用性，必须预先审批适用 query 和阈值。回滚保留新旧索引直至审计窗口结束，不能用删除代替回滚。

### 8. 学员任务与参考答案

任务：注入 rerank timeout 与 telemetry sink timeout 的组合故障。预期 rerank 按 profile 降级，主链完成或明确拒答；telemetry 失败不阻断主链；重复请求无重复 Answer；trace/本地缓冲保留足够证据。参考答案应区分两个故障所有者和恢复策略，不能用一个大 `try/except` 吞掉。

## 生产决策清单

在声称“可生产”前逐项回答：

| 决策域 | 必须有的证据 |
|---|---|
| 数据与版本 | 内容身份、tombstone/restore、重建、保留期、删除与审计策略 |
| 权限 | tenant 从可信 token claim 获取，ingest/index/query/generate/evaluate scope 分离 |
| 并发与异步 | ingestion/index/evaluation 作业状态、队列背压、取消、超时和幂等 |
| 发布与回滚 | staging/validate/ready、alias CAS、旧索引保留、smoke 与质量复核 |
| 可靠性 | 每个外部依赖的超时、有限重试、fallback、熔断和问题码 |
| 安全 | prompt injection、来源授权、日志脱敏、secret scan、最小工具权限 |
| 可观测 | stage trace、低基数 metrics、可行动告警、运行手册 |
| 成本 | embedding/LLM/存储/检索成本，预算、限流、cache key 和价格版本 |
| 质量 | 版本化评测集、门禁、失败切片、人工抽检和线上反馈回流 |

## G4 工程化闸门

通过要求：全链路由版本化 profile 驱动；每次运行可由 IDs/trace 复盘；contract、security、quality regression 和恢复测试通过；至少演练一次 index alias 回滚和一次超时幂等重试；干净环境按 README 启动；无硬编码密钥。

G4 报告应附：命令与零退出码、测试范围、版本身份、门禁结果、故障注入记录、回滚前后 IDs、未覆盖风险和责任人。

下一步：把 E01-E04 应用到 [综合项目](../capstone.md)，不要只提交功能截图。
