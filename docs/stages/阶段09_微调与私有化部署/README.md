# 阶段 9：微调与私有化部署（学习资料 · 选修）

> 对应任务：MUJI-12（任务 9.1 ~ 9.9）｜ 时长：约 15 周（选修，可跳过或后置）

## 一、学习目标
- 深入理解 Transformer（能动手实现迷你版本）
- 掌握开源模型本地部署（Ollama / vLLM）
- 掌握 LoRA/QLoRA 参数高效微调（LLaMA-Factory）
- 了解量化（GPTQ/AWQ）、训练数据、模型评估

## 二、核心知识
1. **微调 vs 应用开发**：应用开发调用 API；微调是让模型适配特定业务（风格/领域/格式）。**能用 RAG/Prompt 解决就别微调**——微调成本高、周期长、效果不易预期
2. **LoRA/QLoRA**：冻结原模型，只训练低秩增量矩阵——显存友好（消费级显卡可跑 7B 模型）
3. **量化**：把 FP16 权重压成 4/8bit，体积减小、速度提升、精度小幅损失
4. **部署选型**：Ollama（个人开发最简）、vLLM（生产高并发，PagedAttention 加速）、OpenLLM（BentoML 生态）
5. **多模态（选修）**：图文/语音模型应用，AIGC 方向

## 三、最新资料
- LLaMA-Factory（一键微调框架）：https://github.com/hiyouga/LLaMA-Factory
- Ollama：https://ollama.ai/ ｜ 动手学 Ollama：https://datawhalechina.github.io/handy-ollama/
- vLLM：https://github.com/vllm-project/vllm
- HF PEFT 文档：https://huggingface.co/docs/peft
- 吴恩达量化课程（B站）：BV1kw4m1X7Bi
- DeepSeek-R1 技术报告：https://github.com/deepseek-ai/DeepSeek-R1
- 华为云学习路径阶段 05（微调及评测）：https://bbs.huaweicloud.com/blogs/481390

## 四、动手实验
1. PyTorch 迷你 Transformer（文本分类）
2. Ollama 跑通 2 个模型，对比速度/显存
3. LLaMA-Factory LoRA 微调 Qwen/ChatGLM 完成业务任务（如工单分类/客服话术）
4. 量化微调模型并对比效果
5. （选修）图文/语音 Demo

## 五、避坑
1. 微调前先问：RAG 或 Prompt 能否解决？微调是最后手段
2. 数据质量 > 数据量：几百条高质量数据 > 几万条脏数据
3. 中文任务选 Qwen/ChatGLM 基座，别选英文模型裸跑中文
4. 先量化再部署：消费级显卡跑 7B 需要 Q4 量化
5. 评估微调效果必须量化（任务准确率），别凭感觉

## 六、验收标准
- [ ] LoRA 微调模型完成业务任务且效果可量化
- [ ] 微调模型以 API 部署 + 评估报告 + 技术博客
