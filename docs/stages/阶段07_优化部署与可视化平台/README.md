# 阶段 7：优化、部署与可视化平台（学习资料）

> 对应任务：MUJI-10（任务 7.1 ~ 7.6）｜ 时长：约 3-6 周

## 一、学习目标
- 掌握 Agent 性能与成本优化（缓存/并行/流式/Prompt 瘦身）
- 掌握安全与可控（输入过滤、权限控制、行为约束）
- 掌握 LangSmith 观测与 FastAPI/Docker 部署
- 会用 Coze / Dify 低代码平台快速搭建并发布应用

## 二、核心知识
1. **成本优化**：Prompt 瘦身（系统提示词精简）、结果缓存（相同 query 复用）、并行 vs 串行取舍、模型分级（简单任务用小模型）
2. **质量优化**：评估集回归（每改一次 Prompt 跑一遍）、可观测性先行（看不到就调不了）
3. **安全**：输入过滤（注入防护）、输出审查（敏感信息脱敏）、权限最小化（工具白名单）、行为约束（危险操作需确认）
4. **部署架构**：FastAPI 封装 → Docker 容器化 → 云服务器 → 域名/HTTPS；异步与并发控制（控制 API 调用速率）
5. **低代码平台**：Coze（字节，国内生态好）/ Dify（开源，可自托管）——非程序员也能发布 Agent，也是产品验证利器

## 三、最新资料
- FastAPI 官方教程：https://fastapi.tiangolo.com/zh/
- Docker 入门：https://docs.docker.com/get-started/
- LangSmith：https://docs.smith.langchain.com/
- Dify 文档：https://docs.dify.ai/zh-hans
- Coze 平台：https://www.coze.cn/
- ai-engineering-from-scratch 的生产部署章节

## 四、动手实验
1. 成本/延迟优化前后对比表（对阶段 5 项目）
2. 安全加固：权限白名单 + 输出过滤 + 注入测试
3. LangSmith 接入并查看全链路
4. FastAPI + Docker 部署上线（公网可访问）
5. Dify 或 Coze 搭一个可发布的知识库问答应用

## 五、避坑
1. 别直接暴露 API Key：服务端存储 + 环境变量 + 限流
2. 并发要限流：免费/低价 Key 有速率限制，超限 429 处理要优雅
3. 先监控再优化：没有数据支撑的优化都是拍脑袋
4. Docker 里注意时区、日志持久化、健康检查

## 六、验收标准
- [ ] 部署应用稳定运行一周，部署文档含成本与监控截图
- [ ] 安全测试通过（恶意指令无法执行危险操作）
