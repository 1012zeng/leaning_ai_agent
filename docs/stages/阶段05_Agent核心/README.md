# 阶段 5：Agent 核心（学习资料）★ 核心阶段

> 对应任务：MUJI-8（任务 5.1 ~ 5.9）｜ 时长：约 5-7 周

## 一、学习目标
- 理解 Agent 本质：LLM + 规划 + 工具 + 记忆 + 执行 的闭环
- 手写最小 ReAct Agent（不依赖框架），吃透 Thought→Action→Observation 循环
- 掌握 LangGraph 工作流（节点/边/状态/条件分支/checkpoint）
- 掌握 Function Calling、记忆系统、MCP 协议、LangSmith 观测

## 二、核心知识
1. **Agent 与 LLM 应用的区别**：LLM 应用是一次性问答/生成；Agent 是自主决策的多步循环——能调用工具、能自我修正、能规划
2. **四大架构模式**：ReAct（推理-行动循环）、Plan-and-Execute（先规划再执行）、Reflection（自我反思迭代）、Multi-Agent（多智能体协作）
3. **Agent 四大核心组件（2026 共识框架）**：
   - 感知层（多模态输入）
   - 大脑/规划层（任务拆解、子目标）
   - 记忆层（短期=上下文窗口；长期=向量数据库 RAG）
   - 工具层（API/代码执行/浏览器/文件系统）
4. **吴恩达四大 Agentic Workflow 模式**：Reflection、Tool Use、Planning、Multi-agent Collaboration——本阶段的纲领
5. **Function Calling**：模型输出结构化工具调用 JSON→程序执行→结果回填→模型继续。工具定义越精确，调用越准
6. **MCP（Model Context Protocol）**：工具接入的开放标准协议（2025 起成为行业标准），让 Agent 统一接入外部工具。本阶段至少会调用现成 Server + 写一个简单 Server
7. **LangGraph**：状态机式 Agent 编排框架（2025.10 v1.0 GA），生产级选择——精确状态控制、条件分支、长时运行、完整审计
8. **观测**：LangSmith 记录每一步（prompt/tool call/中间结果），是调试 Agent 的必备工具

## 三、最新资料
- Anthropic《Building Effective Agents》：https://www.anthropic.com/research/building-effective-agents（Agent 设计圣经）
- Anthropic《Building with Claude》文档：https://docs.anthropic.com/en/docs/build-with-claude
- LangGraph 官方文档：https://langchain-ai.github.io/langgraph/
- MCP 官方文档：https://modelcontextprotocol.io/
- ai-agents-from-zero（2026 系统指南，含实战项目+面试题）：https://github.com/XingJi-love/ai-agents-from-zero
- awesome-agentic-ai-zh（harness→loop→graph 分层）：https://github.com/WenyuChiou/awesome-agentic-ai-zh
- 2025 AI Agent 智能体全套教程（B站）：BV18hWtzuErE

## 四、动手实验（按顺序）
1. 手写最小 ReAct Agent：查天气/计算器工具
2. Function Calling 三工具 Agent（天气+计算器+翻译）
3. LangChain Agent：NL2SQL 查询助手
4. LangGraph 重构 + 可视化执行步骤
5. 长期记忆 Demo（重启后仍记得关键信息）
6. MCP：调用现成 Server → 写一个简单 Server
7. 自动调研 Agent（阶段验收项目）：主题→联网→多步整理→带引用报告

## 五、避坑
1. **先手写再框架**：用纯 Python 实现 ReAct 再学 LangGraph，否则全是"魔法感"
2. 工具调用失败是常态：工具要有清晰错误返回，Agent 才能自我修正
3. 无限循环风险：LangGraph 里设最大步数/超时
4. 成本失控：每步都在花钱——日志里记录 token 消耗
5. 权限最小化：Agent 能执行真实操作，危险工具（删文件/付费 API）要隔离

## 六、验收标准
- [ ] 手写 ReAct Agent 代码已上传
- [ ] 自动调研 Agent 完成验收（3 步以上工具链、可追踪日志、带引用报告）
