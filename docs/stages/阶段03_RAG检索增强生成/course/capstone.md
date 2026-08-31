# 阶段综合项目：可审计的内部知识库 RAG

## 项目背景

为一个内部知识库构建文本 RAG：文档存在版本更新、重复段落、冲突事实、跨段答案、元数据权限、无答案问题和 Prompt Injection 内容。系统必须离线跑通检索主链；真实生成可使用本地模型或获批云端 adapter；所有事实性回答提供可校验引用。

语料与真值唯一来源是 `../evals/`，实验实现唯一来源是 `../labs/`。不要复制一份数据或框架示例另起项目；在批准的 ports、DTO 和 profiles 上完成产品化组合。

## 用户故事与不可协商约束

| 用户故事 | 可判定验收 |
|---|---|
| 员工查询最新政策 | 只从授权 tenant/current source version 检索，回答带精确引用 |
| 问题表达模糊 | 系统保留 original query，必要时改写/澄清，并可复盘 |
| 知识库没有答案 | 明确拒答，不用模型参数知识强答 |
| 文档包含恶意指令 | 作为数据处理，不改变 system policy，不泄露 secret/执行工具 |
| 数据管理员更新文档 | 构建新不可变索引，验证后 alias CAS 发布，历史 Answer 仍可验证 |
| 值班工程师处理退化 | 能按 trace 定位 stage，执行有界重试、fallback 或索引回滚 |

不可协商：无硬编码密钥；供应商对象不穿过 port；事实/派生/观测数据分离；失败不靠日志字符串分支；fixture 不作为质量结论；测试 split 不用于调参。

## 最低功能范围

1. Ingestion：Markdown 与至少一种额外文本格式；内容版本、空文档、重复导入、删除/恢复。
2. Chunking：至少两种 profile；结构感知、token/byte 限制、确定性 ID 与 span 校验。
3. Indexing：可替换 embedding adapter；不可变 manifest；维度/metric 校验；staging/ready/alias。
4. Retrieval：稀疏、稠密、混合；结构化 metadata filter；至少一种 query transform。
5. Ranking/context：RRF、可选 reranker、低置信度准入、去重和 token budget。
6. Generation：结构化 Answer/Claim/Citation；精确 source version/span；拒答；注入样例。
7. Evaluation：固定 manifest、retrieval/answer/citation/latency/cost 指标和 failure slices。
8. Reliability：幂等、timeout、有限重试、可见 fallback、partial index 不发布、alias rollback。
9. Observability：完整 TraceEvent 链、结构化 problem、低基数指标、隐私扫描。

## 推荐模块与依赖

```text
ingestion -> indexing -> retrieval -> rerank -> context -> generation -> evaluation
     config profiles inject downward; observability reads stage events by ID
```

依赖只能向右；evaluation 驱动被测 pipeline 但不能修改其 profile；observability 不被领域模块反向 import。HTTP、CLI、FAISS、Milvus、LangChain、LlamaIndex 或模型 SDK 都是 adapter。

## 里程碑与阶段证据

| 里程碑 | 主要工作 | 通过证据 |
|---|---|---|
| M1 契约基线 | 对象 schema、ID、errors、profiles、fixture adapter | schema/round-trip/golden/failure tests |
| M2 离线主链 | ingestion 到 refusal/citation | G1 对象链、ready manifest、trace |
| M3 指标优化 | chunk/embedding/retrieval/rerank/context 消融 | G2 固定对照报告和失败 case |
| M4 质量与安全 | 真实 generator/judge 或双人盲审、injection/no-answer | G3 报告、引用校验、安全测试 |
| M5 生产恢复 | 配置、门禁、幂等、partial failure、rollback | G4 测试、演练记录、运行手册 |

每个里程碑先提交失败测试/基线，再改实现，最后记录取舍。禁止最后一天补一份无法对应代码版本的“评估报告”。

## 必做实验

| 编号 | 唯一变量 | 最少观察 | 失败问题 |
|---|---|---|---|
| EXP-01 | chunk profile | token 分布、Recall@5、MRR、引用 span | 断义/噪声/oversize |
| EXP-02 | embedding/index profile | Recall@10、p95、内存、构建时间 | dimension/metric 漂移 |
| EXP-03 | sparse/dense/hybrid | per-channel Recall、MRR、空命中 | 精确词与语义互补 |
| EXP-04 | candidate depth/reranker | MRR/nDCG、p95、fallback | rerank 退化/超时 |
| EXP-05 | context budget | token utilization、faithfulness、citation completeness | 超预算/噪声 |
| EXP-06 | refusal threshold | answerable/unanswerable、拒答 precision/recall | 无证据强答 |

每个实验保存 dataset/index/profiles/metric/judge/commit identities、假设、对照、结果、失败切片、局限和采用/拒绝结论。

## 故障演练

至少注入并恢复以下六类中的四类，且覆盖三个不同 stage：

1. 空文档或非法 UTF-8 被隔离，正常 batch 项继续。
2. Embedding 维度改变，旧索引拒绝写，新索引重建。
3. 1000 chunks 中部分写失败，partial manifest 不切 alias。
4. 合法 filter 无匹配与非法 filter 分别产生空结果/422 语义。
5. Reranker timeout 产生批准的 degraded fallback 或明确 504。
6. Context 超预算不静默截断；引用 span/版本漂移阻断发布。
7. Generation timeout 重试不产生第二个 Answer。
8. 新索引质量回归，alias 回滚后业务 canary 和历史 Citation 都通过。

演练记录采用“症状 -> 假设 -> 观测 -> 根因 -> 修复 -> 回归 -> 预防”格式，不只贴异常截图。

## 验收命令与预期结果

环境前提和准确命令以 `../labs/README.md` 为权威源。最低验收序列：

```powershell
cd docs/stages/阶段03_RAG检索增强生成/labs
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m ruff check .
```

随后按 README 运行离线端到端、评测、trace、failure 和质量模式。预期：所有阻断测试零退出；离线流程无需密钥；质量模式拒绝 fixture；输出报告包含完整 identities；失败演练产生契约规定的 problem/status；无 secret/PII 泄漏。

阈值：G2/G3/G4 按课程入口执行。若客观环境无法运行真实模型，项目可以完成工程回归但不能声称 G3/阶段结业通过，应明确记录缺失证据。

## 提交物清单

- README：干净环境、配置、命令、预期输出、常见错误、清理/重建。
- 架构图与至少 4 个 ADR：后端抽象、profile/version、引用、评测/追踪、恢复可任选。
- 测试报告：环境、版本、正常/边界/错误/恢复、通过/失败/跳过和未覆盖风险。
- 评测报告：固定 identities、消融、切片、失败 case、延迟/成本和结论。
- Trace 样例：正常、retry、fallback、failed 各一条，已脱敏。
- 运行手册：索引构建失败、质量回归、模型不可用、引用故障和回滚。
- 一次故障复盘：真实定位过程，不美化成预先知道答案。
- 简历表述：问题、规模/约束、个人决策、指标证据和取舍，禁止虚构线上规模。

## 项目评分（100 分）

| 维度 | 分值 | 满分证据 |
|---|---:|---|
| 正确性与契约 | 18 | 对象/ID/profile/error 不变量，引用与拒答正确 |
| 检索与上下文质量 | 15 | 分层消融、G2 证据、失败切片 |
| 生成与安全 | 12 | grounded claims、Citation、injection/no-answer 测试 |
| 评测可信度 | 15 | 真值独立、版本冻结、metric/judge 分母与局限 |
| 测试与恢复 | 15 | 正常/边界/错误/恢复、幂等、partial、rollback |
| 架构与可维护性 | 10 | ports/adapters、配置、依赖方向、ADR |
| 可观测与成本 | 8 | trace 完整、低基数指标、隐私、成本口径 |
| 文档与交付 | 7 | 干净环境、运行手册、复盘、可接手 |

项目通过：总分至少 75，且正确性、评测可信度、测试与恢复三项各至少 60%。以下任一项直接不通过：硬编码/泄漏密钥；fixture 冒充质量；伪造运行结果；事实性回答无可校验引用；测试集泄漏用于调参；partial index 默认发布；无法从 README 在干净环境启动。

## 项目答辩量表（20 分钟，40 分）

| 环节 | 分值 | 评审观察 |
|---|---:|---|
| 3 分钟问题与边界 | 5 | 目标用户、为什么 RAG、非目标和风险 |
| 5 分钟对象链演示 | 10 | 一条 query 从 SourceDocument 到 Citation，展示 shape/IDs/trace |
| 4 分钟指标与取舍 | 8 | 一次未达预期消融、失败 case、最终决策 |
| 4 分钟故障定位 | 8 | 现场给症状，提出假设并用中间对象定位 |
| 2 分钟生产恢复 | 4 | timeout/partial/rollback 的状态与副作用 |
| 2 分钟追问表达 | 5 | 回答准确、承认未知、用项目证据而非背术语 |

答辩通过：至少 28/40，且对象链、故障定位均不得低于该项 60%。只演示 UI/最终答案、不展示中间对象和测试，答辩不通过。

## 参考解题路径

先做可解释离线 baseline，再建固定 EvalCase；按 ingestion/indexing/retrieval/rerank/context/generation 顺序增加一层一测；每次只改变一个 profile；最后加异步、缓存、真实模型等 adapter。遇到质量问题先找首个异常对象，遇到可靠性问题先定义副作用和幂等身份。

下一步：创建项目验收清单，先完成 M1 的契约与失败测试，再写主链实现。
