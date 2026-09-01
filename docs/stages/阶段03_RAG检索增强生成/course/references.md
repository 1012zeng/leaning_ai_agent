# 官方资料核对表

> 核对日期：2026-08-31。版本、API 和产品能力变化较快；实现前再次打开对应官方页，不从本表推断未写明的兼容性。
> 术语定义见 [RAG 术语与常用库解释](glossary.md)，本课程与参考课程的章节映射见 [all-in-rag 路线对照表](all-in-rag-mapping.md)。

## 原理与标准

| 主题 | 一手资料 | 本课程采用的结论 |
|---|---|---|
| RAG | [Lewis et al., 2020](https://arxiv.org/abs/2005.11401) | 检索到的外部证据参与生成；课程进一步要求把证据固化成可校验引用链 |
| RRF | [Cormack, Clarke, Buettcher, SIGIR 2009](https://research.google/pubs/reciprocal-rank-fusion-outperforms-condorcet-and-individual-rank-learning-methods/) | 按排名而非不可比的原始分数融合多路结果；参数必须进入 rerank profile |
| HTTP 错误 | [RFC 9457 Problem Details](https://datatracker.ietf.org/doc/html/rfc9457) | HTTP 状态表达协议结果，稳定 `code` 表达业务语义；problem 不是暴露堆栈的调试通道 |
| Trace 传播 | [W3C Trace Context](https://www.w3.org/TR/trace-context/) | trace ID 为 32 位小写十六进制，parent/span ID 为 16 位，不能混用 |
| 可观测模型 | [OpenTelemetry Trace API](https://opentelemetry.io/docs/specs/otel/trace/api/) | span 表示一次操作并形成父子树；属性必须低基数且不泄漏正文或密钥 |

## 框架、模型与检索后端

| 主题 | 官方资料 | 选型边界 |
|---|---|---|
| LangChain | [Vector store integrations](https://docs.langchain.com/oss/python/integrations/vectorstores)、[Retrievers](https://docs.langchain.com/oss/python/integrations/retrievers/index) | `Document`、Retriever 和 VectorStore 是 adapter 对象；不得穿过本课程领域 port |
| Sentence Transformers | [Semantic Search](https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html)、[Usage](https://www.sbert.net/docs/sentence_transformer/usage/usage.html) | 非对称检索优先区分 query/document 编码入口；模型 revision、维度、normalize 和 prompt 都进入 embedding profile |
| FAISS | [项目与文档入口](https://github.com/facebookresearch/faiss)、[索引选型指南](https://github.com/facebookresearch/faiss/wiki/Guidelines-to-choose-an-index)、[索引列表](https://github.com/facebookresearch/faiss/wiki/Faiss-indexes) | Flat 用作精确基线；IVF/HNSW 用实验比较召回、延迟、内存和构建代价，不能凭数据规模一句话选型 |
| Milvus | [Filtered Search](https://milvus.io/docs/filtered-search.md)、[Hybrid Search](https://milvus.io/docs/multi-vector-search.md) | 元数据过滤缩小候选范围；混合检索可融合多路结果。供应商表达式只存在 adapter 内 |
| Qdrant | [Hybrid Search](https://qdrant.tech/documentation/search/text-search/hybrid-search/)、[Filtering](https://qdrant.tech/documentation/search/filtering/) | dense/sparse 可组合；过滤字段需要索引与显式 schema，不能把全文匹配和业务过滤混为一谈 |
| Ragas | [Available metrics](https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/)、[0.3 到 0.4 迁移](https://docs.ragas.io/en/stable/howtos/migrations/migrate_from_v03_to_v04/) | 指标名称和 API 会演进；课程固定 metric profile，不把旧示例 import 当作稳定接口。LLM judge 结果必须标注 judge profile |

## 对标资产

`datawhalechina/all-in-rag` 用于继承章节递进、真实代码与项目素材；课程不照搬其临时 `Document.metadata` 语义、随机 chunk ID、无引用字符串答案或无版本评测结果。逐章证据与差距见 [需求基线](../planning/01_requirements_and_benchmark.md)。

下一步：每次修改涉及外部库行为时，在 PR 中写明重新核对的官方页面、日期和影响，不只更新链接。
