# 阶段 4：LangChain / LlamaIndex（学习资料）

> 对应任务：MUJI-7（任务 4.1 ~ 4.5）｜ 时长：约 3 周

## 一、学习目标
- 掌握 LangChain 核心组件：Chat models、Prompt 模板、结构化输出、数据连接、Memory
- 掌握 LCEL 表达式与链组合
- 掌握 LlamaIndex 的索引结构与 RAG 应用
- 能独立用 LangChain 搭出可用的 AI 工具

## 二、核心知识
1. **LangChain 组件**：模型 I/O（Chat models vs LLMs、Prompt 模板、输出解析）、数据连接（文档加载/切割/向量化/向量库）、Memory（对话历史）、Chain/Agent
2. **LCEL（LangChain Expression Language）**：用 `|` 管道式组合组件，支持流式、异步、批量——2025 起官方主推写法
3. **LangGraph 关系**：LangChain 提供组件，LangGraph 提供工作流编排（状态机）——阶段 5 重点
4. **LlamaIndex**：以索引为核心的数据框架，擅长文档问答；与 LangChain 可互补
5. **2026 现状**：LangGraph 成为主流复杂应用框架；LangChain 定位为组件库。学习时注意：教程很多是旧 API（如 `LLMChain`、`load_qa_chain` 已弃用），以官方最新文档为准

## 三、最新资料
- LangChain 官方文档（Python）：https://python.langchain.com/docs
- LangChain 中文文档：https://www.langchain.asia/
- LlamaIndex 官方文档：https://docs.llamaindex.ai
- ai-engineering-from-scratch 的 harness/框架章节（含 LangGraph）
- B站 LangChain 全套教程：BV1BgfBYoEpQ

## 四、动手实验
- 用 LangChain 重写阶段 1 的 API 项目（对话+结构化输出）
- LCEL 多链流水线：输入→翻译→摘要
- LangChain 版知识库问答（对比手写 RAG）
- LlamaIndex 文档问答 Demo + 对比笔记

## 五、避坑
1. 教程版本混杂：看到 `LLMChain`/`load_qa_chain` 的老代码，先查官方最新写法
2. 不要贪多学所有链类型——核心是 LCEL + 几个常用组件
3. 向量库接口统一但底层差异大，本地 Chroma 跑通再换 Milvus
4. 中文检索仍建议中文 Embedding 模型

## 六、验收标准
- [ ] 4.3/4.4 两个 Demo 已传 GitHub
- [ ] 写一篇 LangChain vs LlamaIndex 对比笔记
