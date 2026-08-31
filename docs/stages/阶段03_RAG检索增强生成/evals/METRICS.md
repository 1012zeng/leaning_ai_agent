# 分层指标与失败归因

机器口径见 `metrics/metric_contract.json`，运行结果形状见 `schemas/evaluation_run.schema.json`。同名指标只有在 dataset、system、metric、judge 与 pricing profiles 完全相同时才能比较。

## 检索与排序

设正相关集合 `R={chunk | relevance_grade >= 1}`，系统前 `k` 个去重 chunk 为 `P_k`：

- `Hit@k = 1[P_k ∩ R 非空]`。
- `Recall@k = |P_k ∩ R| / |R|`；`|R|=0` 时为 `not_applicable`，不是 0 或 1。
- `MRR@k` 是首个正相关 chunk 排名的倒数；前 k 个无正相关时为 0。
- `nDCG@k = DCG/IDCG`，gain 为 `2^grade-1`，折损为 `log2(rank+1)`；`IDCG=0` 时不适用。

Hit 只证明“至少一个”，Recall 才衡量“找全”；MRR 只看第一个正例，nDCG 才使用 0..3 分级顺序，不能互相替代。grade 0 是经审查的困难负例，不进入 `R`。

## 上下文、答案与引用

`context_recall` 按必要 claim key 计算，而不是按字符相似度。检索已找到证据但 context 未覆盖必要 claim，首个失败阶段是 `context`。

`citation_coverage` 的分母是回答中的事实性 claim，分子是至少有一个通过 source version、chunk span 与 quote hash 校验的 claim。没有事实 claim 时为不适用；拒答不能自动得 1 分。

`faithfulness` 判断事实 claim 是否被选中上下文支持；`answer_relevance` 判断响应是否处理了用户问题。一个答案可以相关但不忠实，也可以忠实地复述无关上下文。模型 judge 必须固定 profile，并报告 evaluator error；fixture judge 只做契约回归，不能充当质量证据。

## 延迟与成本

- 延迟按一次逻辑 case 的 root span 统计，重试包含在同一次耗时内；p50/p95 使用 nearest-rank `ceil(p*n)`。
- 成本必须携带 usage、币种和不可变 pricing profile。缺价格或 usage 时写 `status=unknown, amount=null`，不能写 0。
- evaluator 超时与被测系统失败分开计数；聚合必须报告 total、evaluated、system error、evaluator error 和 not applicable。

## 首个失败阶段

| 条件 | 归因 |
|---|---|
| top-k 不含任何支撑必要主张的 chunk | `retrieval` |
| 候选含支撑 chunk，但过滤、去重、预算或版本选择让 context 丢失必要主张 | `context` |
| context 足够，但答案漏主张、强答、引用失效、采纳注入或响应模式错误 | `generation` |
| 系统产物完整，metric/judge 自身失败 | `evaluator` |

一次 case 只记录最早可证实的失败阶段，后续症状作为附属 notes，防止同一根因重复计数。

## 三基线预期

`metrics/baseline_expectations.json` 记录待验证的序位假设：关键词基线偏强于精确词、数字与日期；稠密基线偏强于语义改写；混合 + rerank 预期在混合分布的 MRR/nDCG 更好，但延迟与成本最高。无答案和 Prompt Injection 不声明检索赢家，因为它们主要验证上下文信任与生成行为。任何实测反转都保留并用 case 证据解释，不能修改真值迎合预期。
