# 离线可观测 RAG 实验工程

本项目是 MUJI-19 契约的可运行教学实现。核心路径只依赖 Python 3.11+ 标准库，不需要 API Key、网络、GPU、远程模型或向量数据库。离线 adapter 用于理解对象流转、错误边界和恢复策略，不冒充真实模型质量。

## 一条主命令

在本目录执行：

```bash
python -m rag_lab demo --config configs/offline.json
```

命令会确定性地解析 `data/corpus/`，构建结构感知 chunk、哈希 Embedding 和内存向量索引，执行 BM25 + 向量召回、RRF、规则 Rerank、上下文预算、引用校验与拒答，并把结果写入 `results/latest.json`、trace 写入 `results/trace.jsonl`。同一配置的领域对象 ID、候选次序和答案固定；真实耗时及 trace/event ID 会变化。

查看每一步而不写文件：

```bash
python -m rag_lab demo --config configs/offline.json --stdout
```

## 故障注入

一次运行全部故障实验：

```bash
python -m rag_lab failures --config configs/offline.json --scenario all
```

也可把 `all` 替换为：`empty_document`、`decode_error`、`semantic_break`、`dimension_mismatch`、`duplicate_documents`、`filter_false_negative`、`no_hits`、`rerank_degradation`、`context_overflow`。输出中的 `observed` 必须为 `true`；每项同时给出对象 shape、错误/丢弃原因和恢复动作。

## 开发验证

运行时没有第三方依赖。测试工具单独安装：

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m mypy rag_lab tests
python -m rag_lab benchmark --config configs/offline.json --iterations 30
```

测试不访问外网。benchmark 输出吞吐、p50/p95 和成本占位值，不把机器相关数字写成固定通过门槛。

## 模块与契约边界

| 模块 | 输入 -> 输出 | 主要可观察信息 |
|---|---|---|
| `ingestion` | SourceInput -> SourceDocument / ParsedDocument / Chunk | 字符跨度、section path、隔离原因、重复内容组 |
| `indexing` | Chunk -> EmbeddingRecord / IndexManifest | shape、维度、coverage、checksum |
| `retrieval` | RetrievalQuery -> CandidateSet | 通道、raw score、channel rank、过滤结果 |
| `rerank` | Candidate IDs -> RankedHitSet | RRF 分量、lexical 分量、准入与 fallback |
| `context` | RankedHit IDs -> ContextBundle | token budget、选中项、丢弃 warning |
| `generation` | ContextBundle ID -> Answer / Citation | claim、quote span、拒答原因 |
| `observability` | stage 生命周期 -> TraceEvent | latency、计数、degraded/error、成本占位 |

核心对象是冻结 dataclass；adapter 通过 `Protocol` 注入。任何 LangChain、LlamaIndex、FAISS、Milvus 等可选实现都必须在 adapter 内转换，不能把供应商对象传进领域端口。

## 失败与重试边界

- 无命中和低置信度是成功的空结果，最终必须 `insufficient_evidence`，不是 500。
- 向量维度不匹配拒绝写入；恢复方式是创建匹配维度的新索引，不能原地改 manifest。
- Rerank 超时只有在 profile 允许时降级为 RRF，并记录 `fallback/degraded`。
- 上下文不静默截断 chunk；超预算项被跳过并记录 `CHUNK_EXCEEDS_REMAINING_BUDGET`。
- adapter 重试只接受显式 `retryable=true` 的错误，复用逻辑 ID，并受 `max_attempts` 与 timeout budget 限制。
- trace 和日志只写 ID、哈希、计数和耗时，不写完整 prompt、向量、密钥或异常栈。

## 可选真实 adapter

`EmbeddingPort`、`VectorStorePort`、`RerankerPort` 和 `GeneratorPort` 是替换点。接入真实本地模型或向量库时，保持 MUJI-19 的字段、profile identity、维度校验、引用验证和超时/重试语义不变。fixture 结果只能证明工程链路，不能作为课程 G3 质量闸门证据。
