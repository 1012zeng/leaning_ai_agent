# 阶段 2：Prompt 工程（学习资料）

> 对应任务：MUJI-5（任务 2.1 ~ 2.5）｜ 时长：约 1-2 周

## 一、学习目标
- 掌握 Prompt 的构成要素与类型（零样本/少样本/角色扮演）
- 掌握进阶技巧：思维链 CoT、自洽性、思维树 ToT、结构化输出
- 了解提示词注入与防范（Agent 安全的第一道防线）
- 沉淀一份自己的 Prompt 模板库

## 二、核心知识
1. **Prompt 构成**：指令（做什么）+ 上下文（背景信息）+ 输入数据 + 输出格式要求
2. **少样本学习（Few-shot）**：给 2-3 个示例再提问，模型模仿示例格式与风格
3. **思维链（CoT）**：让模型"逐步思考"，复杂推理任务准确率显著提升
4. **结构化输出**：指定 JSON Schema 或"只输出 JSON"，配合 API 的 response_format 更稳
5. **提示词注入**：用户输入中藏指令劫持模型——防护：输入过滤、输出审查、指令优先级声明、工具权限隔离

## 三、2026 最新资料
- OpenAI Prompt 工程指南：https://platform.openai.com/docs/guides/prompt-engineering
- 提示词工程指南（中文）：https://www.promptingguide.ai/zh
- Anthropic Prompt 工程文档：https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering
- 吴恩达 Prompt Engineering 课程（B站中文）：BV1s24y1F7eq
- awesome-agentic-ai-zh（Track A 起点是 prompt engineering）：https://github.com/WenyuChiou/awesome-agentic-ai-zh

## 四、动手实验
- 为同一任务设计 5 个不同 Prompt，记录输出差异
- CoT 挑战：让模型解数学应用题，对比"直接答"vs"逐步思考"
- JSON 稳定输出实验：10 次尝试 ≥8 次成功
- 注入攻防实验：构造恶意 Prompt 并设计防护，测试是否被绕过

## 五、避坑
1. Prompt 不是越长越好——冗余信息会稀释指令权重
2. 少样本示例要与目标任务同分布，否则起反作用
3. 温度设置：事实性任务用低温度（0-0.3），创意任务用高温度
4. 系统性沉淀模板，别每次从零写

## 六、验收标准
- [ ] 个人 Prompt 模板库（≥5 个）已传 GitHub
- [ ] 能讲清 CoT、few-shot、注入防护的原理（对 AI 复述挑错）
