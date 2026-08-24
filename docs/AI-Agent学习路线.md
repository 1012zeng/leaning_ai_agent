# AI Agent 工程师完整学习路线（基于个人仓库两份学习路线文件整合）

> 本路线以你 GitHub 仓库 `leaning_ai_agent` 中的两份文件为基础整合：
> - **文件 A**《agent工程师的学习路线图.md》——AI Agent 应用开发学习路线（编程导航·鱼皮，7 阶段，以求职就业为导向）
> - **文件 B**《ai应用开发学习路线.md》——AI 大模型应用开发学习路线（编程导航·鱼皮，4 大阶段，从后端工程师视角、内容更深更全）
>
> 两份文件高度重叠的部分（大模型基础、Prompt、RAG、LangChain、Agent）已合并去重；文件 B 独有的"微调/量化/私有化部署/多模态"和文件 A 独有的"多 Agent、求职备战"全部保留。各阶段标注了内容来源，★ = 我补充的整合说明。

---

## 总览：两份文件如何合并成一条路线

| 本路线阶段 | 内容来源 |
|---|---|
| 阶段 1 大模型基础 | 文件B 阶段1（基本信息+原理）+ 文件A 阶段1 |
| 阶段 2 Prompt 工程 | 文件B Prompt（10天）+ 文件A 阶段1 |
| 阶段 3 RAG 检索增强 | 文件B 阶段2（完整 37 天） |
| 阶段 4 LangChain / LlamaIndex | 文件B 阶段3 前半（20 天） |
| 阶段 5 Agent 核心 | 文件A 阶段2+3 + 文件B Agent（20天） |
| 阶段 6 多 Agent 系统 | 文件A 阶段4 + 文件B 多 Agent 部分 |
| 阶段 7 优化、部署与可视化平台 | 文件A 阶段5 + 文件B 可视化开发框架（GPTs/Coze/Dify） |
| 阶段 8 项目实战 | 文件A 阶段6 + 文件B RAG 项目 |
| 阶段 9 微调与私有化部署 | 文件B 阶段4（完整，约 100 天） |
| 阶段 10 求职备战 | 文件A 阶段7 |

★ 两份文件的定位差异：文件 A 目标 = **尽快做出 Agent 应用、找 Agent 开发工作**；文件 B 目标 = **大模型应用全栈（含模型层）**。阶段 9 可视为选修/进阶线——先按 1-8 走，就业后再深入。

---

## 阶段 1：大模型基础（文件B 5+60 天、文件A 10-20 天 → 整合约 20 天）

**学习目标**：理解大模型是什么、怎么工作、能力和边界在哪，会用 API 调用。

**知识点**
- 大模型基本认知（文件B）：AI 演变（AI 1.0/2.0）、大模型与 AGI 关系、主流大模型全景——国外（GPT/Claude/Gemini/Llama/Mistral/Grok）+ 国产（DeepSeek/通义/豆包/Kimi/文心/讯飞/ChatGLM/百川/腾讯元宝）
- 大模型原理（文件B，★ 选学，不必 60 天死磕）：生成式模型与大语言模型、GPT 系列演进（GPT1→4、InstructGPT）、LLaMA 系列、Transformer 架构、NLP 基础（数学基础/机器学习/神经网络）、关键技术（预训练、SFT、RLHF、PPO）
- API 调用（文件A）：OpenAI API + 国产 API、API 参数（temperature/top_p/max_tokens）、流式输出、错误处理、Token 计算

**学习建议**（文件B）：
- 不要死磕数学证明和底层推导，掌握理解模型结构所需的知识即可；大模型应用开发更重工程能力
- 动手：用网页版 ChatGPT/DeepSeek 对话感受输出，申请 API Key 跑通一次调用

**关键资源**（文件B）
- 李沐《动手学深度学习》：courses.d2l.ai/zh-v2/（B站同步）
- 黑马 Python+AI 大模型零基础到项目实战（B站 BV1h1VbzHER2）
- 马士兵 AI 大模型全套教程（B站 BV128cUe6EU2）
- OpenAI API 文档、阿里云百炼（bailian.console.aliyun.com）
- ★ 鱼皮保姆级 AI 指南视频（B站 BV1i9Z8YhEja）

**经典面试题**（文件B）：人工智能发展主要阶段；大模型与 AGI 的关系；国内外主流大模型特点；Transformer 核心机制。

**验收标准**：★ 能讲清"大模型如何生成一个 token"；能用 Python 调通至少 1 家 API（含流式输出）。

---

## 阶段 2：Prompt 工程（文件B 10 天 + 文件A）

**学习目标**：掌握引导大模型输出符合需求的核心技能。

**知识点**（文件B）
- Python 快速入门 + 开发环境搭建（★ 若零基础先补 Python：变量/函数/类/虚拟环境/pip）
- 提示词工程基础：Prompt 构成要素、零样本、少样本（上下文学习）
- 进阶：思维链 CoT、自洽性 Self-Consistency、思维树 ToT
- 提示词攻击与防范：提示词注入、防范措施
- Prompt 与 RAG / Agent / 微调的关系

**学习建议**（文件B）：一定要动手调试优化 Prompt；用 AI 学 AI 效率最高。

**关键资源**（文件B）
- OpenAI 官方 Prompt 工程指南：platform.openai.com/docs/guides/prompt-engineering
- 提示词工程指南（中文）：promptingguide.ai/zh
- 吴恩达 x OpenAI 提示工程教程（B站 BV1s24y1F7eq）

**经典面试题**（文件B）：什么样的 prompt 是好 prompt？如何优化？什么是提示词注入？如何防范？

**验收标准**：★ 能用角色设定+few-shot+结构化输出让模型稳定输出 JSON。

---

## 阶段 3：RAG 检索增强生成（文件B 完整 37 天）

**学习目标**：让大模型访问外部知识库，回答私有领域问题。

**知识点**（文件B）
- RAG 基础（15 天）：LLM 缺陷分析、RAG 三大范式（Naive/Advanced/Modular）、三大部件（检索器/生成器/增强方法）、Naive RAG 全流程（文档加载分块→Embedding 向量化→向量相似度→向量数据库→Prompt 上下文增强）
- 优化（10 天）：索引优化（元数据/摘要/父子/假设性问题索引）、检索前优化（微调 Embedding/混合检索/问题转换）、检索后优化（重排 Rerank/信息压缩/知识融合）、RAG 变体（T-RAG/CRAG/Self-RAG/RAG-Fusion/Rewrite-Retrieve-Read）
- 评估（5 天）：质量指标（上下文相关性/答案忠实度/答案相关性）、能力指标（噪声鲁棒性等）、工具（RAGAS/ARES/Trulens）
- 项目（7 天）：RAGFlow、FastGPT、QAnything、LangChain-Chatchat、GraphRAG 选一个深入

**关键资源**（文件B）
- 一文读懂大模型 RAG（zhuanlan.zhihu.com/p/675509396）
- RAG 优化方案和实践（zhuanlan.zhihu.com/p/703182970）
- HuggingFace RAG 评估教程（huggingface.co/learn/cookbook/zh-CN/rag_evaluation）

**经典面试题**（文件B）：RAG 主要流程？Rerank 怎么做？召回与 query 不匹配如何改进？如何评测幻觉？

**验收标准**：★ 完成"个人知识库问答"项目：50 篇文档可问，答出依据来源。

---

## 阶段 4：LangChain / LlamaIndex（文件B 20 天）

**学习目标**：掌握主流 LLM 应用开发框架，能快速搭出 AI 应用。

**知识点**（文件B）
- LangChain（15 天）：核心组件——Chat models vs LLMs、模型 I/O 封装（Prompt 模板）、数据连接（向量化/向量数据库 Chroma·ES·FAISS·Milvus/文档切割）、Memory 记忆封装、链 Chain（LCEL 表达式、Runnable 协议）
- LlamaIndex（5 天）：是什么、与 LangChain 对比、RAG 联合应用

**学习建议**（文件B）：先跑通几个 Demo（本地知识库问答），不用死磕底层；能独立用 LangChain 接 API、处理数据、搭出可用工具即可，细节边做边补。

**关键资源**（文件B）
- LangChain 官方文档：python.langchain.com / 中文：langchain.asia
- LlamaIndex 官方文档：docs.llamaindex.ai
- B站 LangChain 全套教程 BV1BgfBYoEpQ

**经典面试题**（文件B）：LangChain 是什么？Chain 和 Agent 区别？如何构建文档问答系统？Memory 如何工作？

**验收标准**：★ 用 LangChain 独立搭建一个本地知识库问答 Demo。

---

## 阶段 5：Agent 核心（文件A 阶段2+3 + 文件B Agent 20天 → 整合约 35-50 天）★ 核心阶段

**学习目标**：理解并实现"能自主决策、调用工具、完成多步任务"的 Agent。

**知识点**
- Agent 基础概念（文件A）：什么是 Agent、核心能力（感知/推理/决策/执行）、Agent 与 LLM 的区别、应用场景
- 架构模式（文件A）：ReAct（推理→行动→观察循环）、Plan-and-Execute、Reflection 反思、Multi-Agent
- 工具调用（文件A+B）：Function Calling 原理与实现、工具定义描述、参数解析、执行结果返回、远程 Function Calling、支持 Function Calling 的国产模型
- 记忆系统（文件A）：短期记忆（对话历史）、长期记忆（向量数据库）、记忆检索与更新
- 认知框架（文件B）：ReAct、Plan-and-Execute、Self-Ask、Thinking and Self-Reflection
- 框架实战（文件A）：LangChain Agent、LangGraph（图工作流，推荐复杂应用）、AutoGPT
- Prompt 优化与调试（文件A）：System Prompt 设计、输出格式控制、日志记录、中间步骤可视化、LangSmith

**学习建议**（文件A）：Agent 核心是让 LLM 使用工具——动手实现一个最简单 Agent（天气查询工具），理解工作循环比看理论有效得多；建议先实现一个 ReAct Agent 吃透原理。

**关键资源**（文件A）
- 2025 AI Agent 智能体全套教程（B站 BV18hWtzuErE）
- LangGraph 教程（zhuanlan.zhihu.com/p/1944381324740757196）
- LangChain 中文文档：langchain.asia
- ★ 补充：Anthropic《Building Effective Agents》+ MCP 协议（modelcontextprotocol.io）

**经典面试题**（文件A）：什么是 AI Agent？与 LLM 区别？ReAct 工作原理？工具调用如何实现？记忆系统如何设计？如何优化准确性和性能？

**验收标准**：★ Agent 能连续完成 3 步以上工具调用任务链，出错能自我修正，有步骤日志。

---

## 阶段 6：多 Agent 系统（文件A 15-35 天）

**学习目标**：设计多 Agent 协作系统，完成单人 Agent 难以完成的复杂任务。

**知识点**（文件A）
- 多 Agent 架构：协作模式、通信机制、任务分配协调、角色设计
- MetaGPT（建议学）：模拟软件公司流程，研究源码理解多 Agent 设计思路
- AutoGen（建议学）：微软开源，对话式协作、群聊模式、自定义 Agent
- Agent 编排（必学）：工作流设计、条件分支、循环迭代、错误处理与重试（LangGraph 提供强编排能力）
- ★ 多智能体入门教程（文件B 资源）：datawhalechina/hugging-multi-agent

**经典面试题**（文件A）：如何设计多 Agent 系统？如何协作、通信？如何保证可控性？

**验收标准**：★ 用 LangGraph 搭一个 2-3 角色协作的 Agent 系统（如"调研员+报告撰写员"）。

---

## 阶段 7：优化、部署与可视化平台（文件A 10-30 天 + 文件B 10 天）

**学习目标**：把 Agent 做成生产级、可上线、人人可用的应用。

**知识点**
- 性能优化（文件A）：Prompt 优化、缓存策略、并行执行、流式输出、成本控制
- 安全可控（文件A）：输入过滤、输出审查、权限控制、敏感信息保护、行为约束（★ Agent 会执行真实操作，权限最小化）
- 监控调试（文件A）：LangSmith、日志分析、性能监控、错误追踪
- 部署（文件A）：API 服务部署、Web 应用部署、微信/钉钉集成
- 可视化开发框架/Agent IDE（文件B，10 天）：GPTs + Assistants API、Coze 扣子（人设/插件/工作流/知识库/记忆/发布）、Dify 开源编排平台

**经典面试题**（文件A）：如何优化性能？如何调试？如何保证可控和安全？如何部署？

**关键资源**：LangSmith 文档（docs.smith.langchain.com）、Dify 官方文档（docs.dify.ai/zh-hans）

**验收标准**：★ 阶段 5/6 的 Agent 部署上线公网可访问，有监控和评估记录。

---

## 阶段 8：项目实战（文件A 20-50 天）

**学习目标**：综合运用所学，做出 1-2 个完整、可展示、能写进简历的项目。

**项目方向**（文件A）：智能客服 Agent、代码助手 Agent、数据分析 Agent、内容创作 Agent、个人助理 Agent
**项目要求**（文件A）：完整功能（交互界面+多工具集成+记忆+错误处理+日志监控）、把场景做深做透、收集反馈持续优化、开源或写技术博客

**经典面试题（项目经验）**（文件A）：开发过哪些 Agent 应用？技术难点？如何优化准确性和响应速度？如何评估性能？

**验收标准**：★ 至少 1 个完整项目有在线演示 + 技术博客/README。

---

## 阶段 9：微调与私有化部署（文件B 阶段4，约 100 天，★ 选修/进阶）

**学习目标**：掌握模型层技术——微调、量化、本地部署，能定制专属模型。

**知识点**（文件B）
- Transformer 深入（10 天）：Self-Attention、Encoder/Decoder、Multi-head、Decoding 方法
- 开源模型（20 天）：国外（Llama/Falcon/vLLM/OpenLLM/Ollama/Mistral）+ 国内（ChatGLM/Qwen/DeepSeek/Baichuan/InternLM），本地部署跑通（Ollama 跑 Llama3、vLLM 部署 ChatGLM）
- Fine-Tuning（15 天）：选基座模型、数据收集清洗、HuggingFace Transformers/PyTorch/DeepSpeed
- PEFT 参数高效微调（20 天）：Adapter/Prompt/Prefix Tuning、LoRA（+AdaLoRA/QLoRA/LongLoRA/SLoRA）、P-Tuning V2
- 量化（10 天）：PTQ/QAT、AWQ、GPTQ
- 训练数据（5 天）：数据来源/清洗/影响分析、Pile/ROOTS/RefinedWeb/SlimPajama
- 模型评估（5 天）：评估体系、指标（BLEU/ROUGE/F1）、GLUE/SuperGLUE
- 多模态（20 天）：多模态模型、AIGC、图像生成（DALL-E3/Midjourney/Stable Diffusion/ControlNet）、TTS 语音

**学习建议**（文件B）：先跑通主流模型本地部署，再学微调；中文任务选 ChatGLM3/Qwen，英文选 Llama3；几百条高质量数据即可见效（LLaMA-Factory 一键式 LoRA 微调）。

**经典面试题**（文件B）：微调原理与适用场景？LoRA/QLoRA 原理？PEFT 与全参微调区别？量化如何减少显存？如何选基座模型？

**验收标准**：★ 用 LLaMA-Factory 完成一次 LoRA 微调（如工单分类），并能部署成 API。

---

## 阶段 10：求职备战（文件A）

**学习目标**：简历有项目、面试有底气、拿到 Offer。

**学习建议**（文件A）
1. 简历上必须有完整、可在线访问的 Agent 项目，提前准备演示视频和介绍文档
2. 简历工具：老鱼简历（laoyujianli.com）
3. 刷题：面试鸭（mianshiya.com）AI Agent / LangChain 关键词，重点：Agent 基础概念、架构设计、工具调用、RAG、项目经验
4. 持续关注 OpenAI/Anthropic/国内大厂在 Agent 方向的最新进展

**面试题库**（文件A）：AI 面试题（mianshiya.com/bank/1906189461556076546）、LangChain 面试题（mianshiya.com/bank/1991427331415080961）

---

## 总体时间线 ★

| 阶段 | 内容 | 时间（全天投入） | 累计 |
|---|---|---|---|
| 1 | 大模型基础 | 约 3 周 | 3 周 |
| 2 | Prompt 工程 | 约 1-2 周 | 1 个月 |
| 3 | RAG | 约 5 周 | 2.5 个月 |
| 4 | LangChain/LlamaIndex | 约 3 周 | 3.5 个月 |
| 5 | Agent 核心 | 约 5-7 周 | 5 个月 |
| 6 | 多 Agent | 约 3-5 周 | 6 个月 |
| 7 | 优化部署 + 可视化平台 | 约 3-6 周 | 7 个月 |
| 8 | 项目实战 | 约 4-7 周 | 8 个月 |
| 9 | 微调/私有化（选修） | 约 15 周 | 12 个月 |
| 10 | 求职备战 | 持续 | — |

★ 业余时间（15-20h/周）约 12-14 个月走完全程；若目标只是"快速做 Agent 应用"，阶段 1-8 约 8-9 个月即可，阶段 9 可后置。

## 贯穿全程的习惯（★ 补充）

1. 每个项目 Push 到 GitHub，README 写清"做了什么、怎么跑、效果如何"
2. 用 AI 学 AI：不懂的概念用 Claude 等追问到能讲清楚
3. 框架迭代快（LangChain 等），以官方最新文档为准
4. 对外输出（博客/开源）倒逼输入（文件A 结尾共勉）
5. 看 1 小时教程、动手 4 小时

## 两份文件的原始资源保留

完整的视频教程、书籍、项目、论文清单见你仓库原文件：
- `agent工程师的学习路线图.md`（求职导向资源：编程导航/面试鸭/老鱼简历）
- `ai应用开发学习路线.md`（深度资源：李沐/马士兵/刘知远公开课、LLMs-from-scratch、LLaMA-Factory、DeepSeek-R1 论文、16 篇论文报告等）

合并过程中如某份文件有你想保留但本总结遗漏的细节，指出后我补充。
