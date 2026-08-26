# 阶段 1：大模型基础（学习资料）

> 对应任务：MUJI-4 阶段1（任务 1.1 ~ 1.6）
> 时长：约 3 周（全天投入）；业余学习按 2-3 倍放宽
> 资料时效：2026 年 8 月更新

---

## 一、本阶段学习目标

完成本阶段后，你应能做到：
1. 用自己的话解释"大模型为什么能回答问题"（AI 演变、预训练+微调范式）
2. 说出国内外主流大模型的名称、厂商和各自特点
3. 用 Python 调用大模型 API（含流式输出、Token 统计），参数含义清楚
4. 讲清 Transformer 的核心思想和"模型如何生成一个 token"
5. 知道大模型的能力边界：幻觉、上下文限制、知识时效

---

## 二、核心知识讲解

### 模块 1：认识 AI 与大模型

**AI 发展的三个阶段（简化版）：**
- **AI 1.0（专家系统时代）**：人工编写规则，机器按规则执行。"如果-那么"式逻辑，能力有限
- **AI 2.0（机器学习/深度学习时代）**：数据驱动，机器从样本中自己"学会"规律，不再靠人写规则
- **大模型时代（LLM）**：在 AI 2.0 基础上，模型参数规模达到数十亿~数万亿，通过"预训练 + 微调 + 对齐"获得通识能力，能理解上下文、生成文本、甚至跨模态

**核心概念：**
- **大语言模型（LLM）**：在海量文本上训练的超大规模神经网络，核心能力是预测"下一个 token"
- **预训练（Pre-training）**：模型从互联网规模的通用数据中无监督学习，吸收世界知识
- **微调（Fine-tuning）**：针对特定任务/领域用标注数据进一步训练
- **对齐（Alignment，RLHF/DPO）**：让模型输出符合人类偏好、安全、有用
- **AGI（通用人工智能）**：大模型向 AGI 迈进是当前行业共识，但 AGI 目前仍是目标而非现实

**为什么大模型"能回答问题"？（一句话版）**
模型在预训练时"读过"海量文本，学会了语言的统计规律和知识模式；回答时它做的本质是"在给定上文的情况下，生成概率最高的下一个词"，逐词生成直到结束。

### 模块 2：2026 年主流大模型全景

**国外闭源：**
| 模型 | 厂商 | 特点 |
|---|---|---|
| GPT-5 系列 | OpenAI | 综合能力标杆之一，推理+多模态 |
| Claude 系列（Sonnet/Opus） | Anthropic | 长上下文、代码与 Agent 能力强、安全对齐严格 |
| Gemini | Google | 多模态原生、与 Google 生态集成 |

**国内闭源（重点，API 便宜好用）：**
| 模型 | 厂商 | 特点 |
|---|---|---|
| DeepSeek | 深度求索 | 推理能力强、价格极低、开源也有；国内学习首选之一 |
| 通义千问 Qwen | 阿里云 | 国产综合最强梯队，百炼平台好用 |
| Kimi | 月之暗面 | 长文本处理见长 |
| 豆包 | 字节跳动 | 应用生态广、免费额度大 |
| 文心一言 | 百度 | 中文场景成熟 |
| 讯飞星火 | 科大讯飞 | 语音技术背景 |

**开源模型（可本地部署）：**
- **Qwen（通义千问开源版）**：中文场景首选开源系列
- **DeepSeek-R1 / V3**：推理模型标杆，论文公开
- **Llama**：Meta 开源系列，英文生态最大
- **ChatGLM / GLM**：清华智谱开源系列
- **InternLM**：上海 AI Lab 书生系列

> 建议：学习阶段以 **DeepSeek + 通义千问（百炼）** 为主，API 便宜、文档中文、国内直连；进阶阶段再对比 Claude/OpenAI。

### 模块 3：Transformer 与生成原理

**为什么需要 Transformer？** 在它之前的 RNN/LSTM 逐词处理，难以并行且长距离信息容易丢失。Transformer 用**注意力机制**让每个词能同时"看到"句子中所有词，并行计算、捕捉长距离依赖。

**核心组成（入门版）：**
- **Tokenization（分词）**：把文本切成 token（词/子词/字符），模型按 token 处理。中文一个汉字可能=1-2 个 token
- **Embedding（嵌入）**：把 token 转成高维向量，语义相近的词向量距离更近
- **Self-Attention（自注意力）**：对每个词，计算它与句子中所有词的相关性权重，加权融合信息
- **Multi-Head Attention（多头注意力）**：多组注意力并行，每组关注不同维度的关系
- **位置编码（Positional Encoding）**：给每个 token 加上位置信息，让模型知道顺序（Transformer 本身无顺序概念）
- **Encoder-Decoder / Decoder-only**：GPT 系列是 Decoder-only，逐个生成 token；BERT 是 Encoder-only，做理解任务

**生成过程（一句话）：** 输入 prompt → 逐 token 预测下一个词的概率分布 → 采样/贪心选择 → 拼到输入末尾 → 继续，直到输出结束符或达到 max_tokens。

**本文件夹配套（学 1.4 前必读）：** `线性代数速成_Transformer预备.md` —— Transformer 所需的全部线性代数（向量/点积/矩阵乘法/softmax/张量），含手算例子、numpy 代码和练习题（约 3~5 小时）。

**推荐可视化资源（必看）：**
- 图解 Transformer（中文）：zhuanlan.zhihu.com/p/347904940
- 3Blue1Brown 神经网络系列（B站有中文字幕）
- 李宏毅"自注意力机制和 Transformer 详解"（B站 BV1v3411r78R）
- transformers.run 教程（概念+代码结合）

### 模块 4：Token 与上下文窗口

- **Token 计费**：输入+输出都按 token 计费；1 个汉字≈1-2 token，1 个英文单词≈1.3 token
- **上下文窗口**：一次对话能塞进的最大 token 数（如 Claude Sonnet 为 200K，DeepSeek 为 64K-128K）
- **上下文管理**：超出窗口会截断，长对话需要做历史摘要或丢弃旧消息——这是 Agent 开发的重要课题（阶段 5 会深入）
- **实用工具**：OpenAI Tokenizer（platform.openai.com/tokenizer）可直观感受

### 模块 5：API 调用实战（本阶段动手核心）

**基本流程：** 注册平台 → 申请 API Key → 安装 SDK/用 requests → 发送请求 → 处理响应

**必会参数：**
- `model`：模型名称
- `temperature`：随机性（0=稳定，1=发散；结构化任务用 0-0.3）
- `top_p`：核采样，与 temperature 二选一调节
- `max_tokens`：最大生成长度
- `stream`：是否流式输出

**调用要点：**
- 流式输出（SSE）实现打字机效果——Web 应用必备
- 错误处理：限流（429）、超时、无效 Key，需要重试与降级
- API Key 管理：不要写死在代码/前端，用环境变量或服务端存储
- 消息格式：`system`（系统设定）/ `user` / `assistant` 三角色消息数组

**动手实验（对应任务 1.3）：**
1. 注册 DeepSeek 开放平台（platform.deepseek.com）和阿里云百炼（bailian.console.aliyun.com）
2. 用 Python 写第一个对话调用，打印 token 用量
3. 改为流式输出
4. 对比 temperature=0 和 temperature=1 的输出差异
5. 实现一个简单的重试机制

---

## 三、2026 年最新学习资料清单

### 官方文档（权威，第一优先级）
- DeepSeek API 文档：https://api-docs.deepseek.com/
- 阿里云百炼文档：https://bailian.console.aliyun.com/
- OpenAI 文档：https://platform.openai.com/docs
- Anthropic 文档（Claude）：https://docs.anthropic.com/
- HuggingFace 文档：https://huggingface.co/docs

### 系统课程（按推荐度排序）
1. **ai-engineering-from-scratch（10.7k Star 开源课程，2026 热门）**：20 阶段 435 节约 320 小时，从数学基础到生产部署全覆盖，每节要求动手实现并产出可复用成果（Prompt/Skill/Agent/MCP Server）。可用 `/find-your-level` 定位自己水平
   → https://developer.aliyun.com/article/1737275（中文介绍）
2. **awesome-agentic-ai-zh（240+ 精选资源中文学习地图）**：概念分层演进（prompt→context→harness→loop→graph），Track A 8-10 周 / Track B 16-22 周双主线
   → https://github.com/WenyuChiou/awesome-agentic-ai-zh
3. **华为云学堂"大模型应用开发学习路径"**：8 阶段 48 门课 3 实验 8 认证，阶段 01 就是大模型世界
   → https://bbs.huaweicloud.com/blogs/481390
4. **李沐《动手学深度学习》（免费在线，中文）**：https://courses.d2l.ai/zh-v2/（本阶段选学前 10 章即可，不用全学）
5. **DataCamp《AI 学习路线图 2026》**：https://www.datacamp.com/zh/blog/ai-roadmap
6. **吴恩达大模型系列课程（B站有中文版）**：LLM 入门、Prompt Engineering、Agent 系列

### 书籍
- 《动手做 AI AGENT：零基础玩转智能体》（2026 年 2 月出版）：从大模型认知、Token 原理到提示词工程、RAG 微调、MCP/A2A 协议，适合零基础系统阅读
- 《大规模语言模型：从理论到实践》：https://intro-llm.github.io/
- 《神经网络与深度学习》（邱锡鹏，免费）：https://nndl.github.io/

### 视频教程（B站）
- 鱼皮保姆级 AI 指南视频：BV1i9Z8YhEja（AI 概念快速扫盲）
- 黑马 Python+AI 大模型零基础到项目实战：BV1h1VbzHER2
- 马士兵 AI 大模型全套教程：BV128cUe6EU2
- 李宏毅机器学习/Transformer：https://speech.ee.ntu.edu.tw/~hylee/ml/2023-spring.php

### 高质量文章
- 2026 年智能体（Agent）怎么学？从入门到实战的全景避坑指南：https://developer.aliyun.com/article/1707471
- 从模型、Agent 到 MCP：AI 工程学习路线梳理（含 10.7k Star 项目介绍）：https://developer.aliyun.com/article/1737275
- 图解 Transformer：https://zhuanlan.zhihu.com/p/347904940
- LLM 大模型入门指南：https://zhuanlan.zhihu.com/p/722000336
- 大模型基础（Datawhale）：https://github.com/datawhalechina/so-large-lm

### 社区与信息源
- X/Twitter：关注 @deepseek_ai、@AnthropicAI、@OpenAI 等
- 知乎 AI 话题、HuggingFace 社区
- 编程导航 AI 导航：https://ai.codefather.cn/

---

## 四、动手实验清单（与任务对应）

| 任务 | 实验 | 验收 |
|---|---|---|
| 1.1 | 写 200 字笔记：大模型为什么能回答问题 | 笔记可复述 |
| 1.2 | 试用 ≥3 家网页版大模型，对比输出 | 每家有 1 句评价 |
| 1.3 | API 调用脚本：对话+流式+token 统计+重试 | 脚本跑通并传 GitHub |
| 1.4 | 画 Transformer 结构图；录 3 分钟讲解"生成 token 的过程" | 能讲清即可 |
| 1.5（选修） | 跑通《动手学深度学习》第 3 章线性回归代码 | 代码可运行 |
| 1.6 | 阶段验收：向 AI 复述本阶段知识，让它挑错 | 无重大错误 |

---

## 五、常见误区与避坑

1. **不要死磕数学证明**：理解"注意力是什么、为什么有效"即可，推导留给专业方向（文件 B 原话：应用开发更重工程能力）
2. **不要一开始就啃论文**：先用 API 做出东西，再回头补原理
3. **API 选国产起步**：DeepSeek/通义便宜、中文文档、国内直连，别一上来就纠结 OpenAI 注册
4. **Key 安全**：Key 泄露会被盗刷——环境变量管理，不要发到 GitHub 公开仓库
5. **Token 意识**：从一开始就养成看 token 用量的习惯，Agent 开发中这是成本命脉
6. **动手 > 收藏**：收藏 100 个教程不如跑通 1 个脚本

---

## 六、本阶段验收标准（总）

- [x] API 项目已上传 GitHub（README 完整）
- [x] 能向 AI 完整复述本阶段知识且无重大错误
- [x] 完成 MUJI-4 中任务 1.1 ~ 1.6 打卡

完成后把 MUJI-4 状态改为 done，即可进入阶段 2（Prompt 工程）。
