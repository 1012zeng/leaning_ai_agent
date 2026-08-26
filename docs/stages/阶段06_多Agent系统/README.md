# 阶段 6：多 Agent 系统（学习资料）

> 对应任务：MUJI-9（任务 6.1 ~ 6.5）｜ 时长：约 3-5 周

## 一、学习目标
- 理解多 Agent 协作模式与通信机制
- 研读 MetaGPT（模拟软件公司 SOP 流程）与 AutoGen（微软对话式协作）
- 用 LangGraph 实现多角色协作系统（Supervisor / Team 模式）

## 二、核心知识
1. **为什么需要多 Agent**：单 Agent 上下文和角色会互相干扰；多 Agent 让"专家各司其职"——如软件公司：产品经理 Agent + 架构师 Agent + 程序员 Agent + 测试 Agent
2. **协作模式**：
   - 群聊模式（AutoGen）：Agent 之间对话协商
   - Supervisor 模式（LangGraph）：中央调度者分派任务给子 Agent
   - 流水线模式：角色串行接力（调研→撰稿→校对）
   - 竞速模式：多 Agent 各做各的，取最优
3. **关键设计**：角色边界清晰、通信协议明确、任务分配机制、错误传播与重试
4. **2026 现状**：LangGraph 与 CrewAI 为两大主导框架（Agentic Programming Roadmap 结论）；AutoGen 并入 Semantic Kernel 生态；MetaGPT 适合研读思想、生产用框架为主

## 三、最新资料
- MetaGPT：https://github.com/geekan/MetaGPT
- AutoGen：https://microsoft.github.io/autogen/
- LangGraph 多 Agent 教程（Supervisor/Team）：https://langchain-ai.github.io/langgraph/concepts/multi_agent/
- CrewAI：https://docs.crewai.com/
- Datawhale 多智能体入门教程：https://github.com/datawhalechina/hugging-multi-agent
- Agentic Programming: A Roadmap：https://machinelearningmastery.com/agentic-programming-a-roadmap/

## 四、动手实验
1. 设计 3 角色协作方案并画协作图
2. 跑通 MetaGPT 示例，写 SOP 设计分析
3. AutoGen 双 Agent（编程者+评审者）
4. LangGraph 三角色（调研员+撰稿员+校对员）产出一篇文章

## 五、避坑
1. 多 Agent ≠ 更强：上下文成本成倍增长，简单任务别用
2. 角色 Prompt 要清晰，否则 Agent 之间"客套话"刷屏
3. 先定义终止条件（何时算完成），否则无限讨论
4. 一次加一个 Agent，逐步调试，别上来就 5 个

## 六、验收标准
- [ ] LangGraph 三角色协作系统产出文章并上传 GitHub
- [ ] 多 Agent vs 单 Agent 收益与坑总结笔记
