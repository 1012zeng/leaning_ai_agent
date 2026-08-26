# 阶段 3：RAG 检索增强生成（学习资料）

> 对应任务：MUJI-6（任务 3.1 ~ 3.8）｜ 时长：约 5 周

## 一、学习目标
- 理解 RAG 三大范式（Naive / Advanced / Modular）与三大部件（检索器/生成器/增强方法）
- 掌握文档处理（分块）、Embedding 向量化、向量数据库（Chroma/FAISS/Milvus）
- 掌握检索优化：混合检索、Rerank、索引优化（元数据/父子/摘要索引）
- 掌握 RAG 评估（RAGAS）与主流开源 RAG 项目

## 二、核心知识
1. **为什么需要 RAG**：LLM 知识有时效性限制（训练数据截止）、私有数据不可见、幻觉
2. **Naive RAG 流程**：文档加载→切分（chunk）→Embedding→向量库索引→query 向量化→相似度检索 TopK→拼进 Prompt→生成
3. **Advanced RAG**：检索前（查询改写/混合检索）+ 检索后（Rerank/信息压缩/知识融合）
4. **Modular RAG**：模块化组合，智能编排（如 GraphRAG 引入知识图谱）
5. **评估指标**：上下文相关性、答案忠实度（faithfulness，防幻觉核心）、答案相关性
6. **2026 趋势**：GraphRAG 落地、Agentic RAG（RAG 与 Agent 结合，检索变成可决策的工具调用）

## 三、最新资料
- 一文读懂大模型 RAG（含高级方法）：https://zhuanlan.zhihu.com/p/675509396
- RAG 优化方案和实践：https://zhuanlan.zhihu.com/p/703182970
- RAGAS 评估库：https://github.com/explodinggradients/ragas
- 开源项目：RAGFlow（github.com/infiniflow/ragflow）、FastGPT（github.com/labring/FastGPT）、LangChain-Chatchat（github.com/chatchat-space/Langchain-Chatchat）、GraphRAG（github.com/microsoft/graphrag）
- 华为云学习路径阶段 03（RAG 知识库）：https://bbs.huaweicloud.com/blogs/481390

## 四、动手实验
- 50 篇文档 → 知识库问答机器人（核心项目）
- 优化实验：混合检索 + Rerank 前后准确率对比
- RAGAS 评估报告

## 五、避坑
1. 分块粒度是效果命脉：太大噪声多、太小上下文破碎，需按文档类型调
2. 检索质量决定生成质量：先查检索 TopK 准不准，再谈生成
3. 中文用中文 Embedding 模型（如 bge-large-zh），效果差距明显
4. 向量库选型：小项目 Chroma 起步，生产考虑 Milvus/Qdrant

## 六、验收标准
- [ ] 50 文档知识库：10 问 ≥8 对且能指出依据
- [ ] RAGAS 评估报告 + 优化前后对比已上传 GitHub
