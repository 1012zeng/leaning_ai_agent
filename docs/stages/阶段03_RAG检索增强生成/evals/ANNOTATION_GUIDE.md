# 标注指南与质量规则

## 标注顺序

1. 先冻结 source bytes、source metadata 和 chunk profile，再写问题；不得从某个系统输出反推答案。
2. 把参考答案拆成原子的必要主张，每条主张绑定一个或多个 source/chunk 证据。
3. 写至少一个不可接受主张，优先覆盖旧版本、近名文档、错误单位、无依据外推或注入指令。
4. 根据证据充分性选择 `answer`、`abstain` 或 `clarify`；无答案不能用空 reference answer 表达。
5. 标注正例和困难负例，最后再决定 category、difficulty、split 与首要诊断阶段。

## 相关性等级

| grade | 含义 | 典型用途 |
|---:|---|---|
| 3 | 直接支撑至少一个必要主张，或直接支撑应拒答的边界 | 答案关键证据、明确的“本文未规定” |
| 2 | 完成答案需要的背景、比较版本或合理解释之一 | 多跳第二证据、版本对照、澄清候选集合 |
| 1 | 主题相关并有上下文价值，但单独不能支撑必要主张 | 相邻步骤、比较背景、未知未来版本的最近现行规则 |
| 0 | 看似相关但不得作为答案依据 | 旧政策、近名城市、语义近邻、Prompt Injection |

grade 0 可以进入标签文件用于审查困难负例，但不进入 Recall/MRR/nDCG 的正相关集合。相同 case/chunk 只允许一条标签。

## 响应模式

- `answer`：证据足以满足全部必要主张；每条主张至少有一个正标签与参考 citation。
- `abstain`：语料缺少答案、明确禁止外推或只有不可信证据；`allow_abstain=true` 且必要主张为空。
- `clarify`：存在多个同等合理解释或缺少指代对象；同样不允许先猜一个答案。

## 难度与切分

easy 是单文档直接事实；medium 包含表格、否定、两个字段或一次过滤；hard 包含跨文档、多版本、多个必要主张、安全边界或有吸引力的困难负例。

train 用于讲解格式，dev 用于调参，test 只在 profile 冻结后运行。看过 test 结果再改参数属于泄漏；需发布新版本和新 test split。

## 诊断阶段

- `retrieval`：题目主要检查精确词、语义改写、metadata filter 或干扰文档是否使证据进入候选集。
- `context`：题目主要检查多跳证据、重复段、版本冲突、预算或去重后是否仍覆盖必要主张。
- `generation`：题目给定足够上下文后检查强答、澄清、引用、忠实度或注入抵抗。

## 审查规则

| 规则 | 阻断条件 |
|---|---|
| `AR-SOURCE-01` | 来源 chunk 不存在，source version 不匹配，或引用的是实现运行输出。 |
| `AR-CLAIM-02` | answer 模式的必要主张没有正标签和参考 citation。 |
| `AR-NEGATIVE-03` | 不可接受主张为空，或 hard negative 与目标错误无关。 |
| `AR-RESPONSE-04` | abstain/clarify 仍含必要主张，或 answer 模式允许无条件拒答。 |
| `AR-SPLIT-05` | test case 被用于参数选择却没有重建 split。 |
| `AR-VERSION-06` | 修改 source/chunk/query/label 后原地覆盖已发布版本。 |
| `AR-SECURITY-07` | 把文档内指令提升为系统指令，或把 untrusted source 当官方事实。 |

当前版本的语料与真值为 agent-assisted 手工策展并经确定性来源规则校验，provenance 如实记录；没有把 LLM judge 输出或未审查的自动生成答案写入事实。需要更高保证时由两名匿名人工 reviewer 独立标注重叠样本、记录一致率和裁决，再发布新版本。
