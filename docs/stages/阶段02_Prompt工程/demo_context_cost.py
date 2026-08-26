"""
demo_context_cost.py  ——  模块 6：Token 计算、成本估算、上下文裁剪
运行前：pip install openai tiktoken   并设置环境变量 DEEPSEEK_API_KEY
运行方式：python demo_context_cost.py
预期：看到 system 占比、预估 vs 实际成本对比，以及 trim_messages 裁剪前后差异。
"""
import os

import tiktoken
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

# DeepSeek 用 cl100k_base 分词器近似
enc = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(enc.encode(text))


# 价格（2026 年 8 月参考，单位：元 / 1M tokens）
PRICE = {
    "deepseek-chat": {"input": 1.0, "output": 2.0},
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    p = PRICE[model]
    return input_tokens / 1e6 * p["input"] + output_tokens / 1e6 * p["output"]


# 模拟一段多轮对话
messages = [
    {"role": "system", "content": "你是客服助手，回答简洁。" * 50},
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "你好！有什么可以帮您？"},
    {"role": "user", "content": "我想退货"},
    {"role": "assistant", "content": "请提供订单号。"},
    {"role": "user", "content": "订单号是 YP123456，买的是蓝牙耳机，上周到的，有杂音"},
]

total_input = sum(count_tokens(m["content"]) for m in messages)
print(f"输入 token: {total_input}")
print(f"system 占比: {count_tokens(messages[0]['content']) / total_input:.0%}")
print(f"预估成本（假设输出 100 token）: {estimate_cost('deepseek-chat', total_input, 100):.6f} 元")

# 实际调用看真实用量
resp = client.chat.completions.create(
    model="deepseek-chat", messages=messages, max_tokens=100
)
print(f"\n实际用量: prompt_tokens={resp.usage.prompt_tokens}, "
      f"completion_tokens={resp.usage.completion_tokens}, "
      f"总计={resp.usage.total_tokens}")
print(f"实际成本 ≈ {estimate_cost('deepseek-chat', resp.usage.prompt_tokens, resp.usage.completion_tokens):.6f} 元")


# 上下文裁剪函数（学员练习的标准答案参考）
def trim_messages(messages: list, max_tokens: int = 3000) -> list:
    """从最早的非 system 消息开始丢弃，直到总 token ≤ max_tokens"""
    msgs = list(messages)  # 不修改原列表
    while sum(count_tokens(m["content"]) for m in msgs) > max_tokens:
        # 找到最早的非 system 消息并丢弃
        for i, m in enumerate(msgs):
            if m["role"] != "system":
                msgs.pop(i)
                break
        else:
            break  # 只剩 system 了
    return msgs


# 造一个超长对话测试裁剪
long_messages = [{"role": "system", "content": "你是助手。"}]
for i in range(20):
    long_messages.append({"role": "user", "content": f"用户消息 {i}" * 50})
    long_messages.append({"role": "assistant", "content": f"助手回复 {i}" * 50})

before = sum(count_tokens(m["content"]) for m in long_messages)
trimmed = trim_messages(long_messages, max_tokens=2000)
after = sum(count_tokens(m["content"]) for m in trimmed)
print(f"\n=== trim_messages 裁剪 ===")
print(f"裁剪前: {before} token, {len(long_messages)} 条消息")
print(f"裁剪后: {after} token, {len(trimmed)} 条消息")
