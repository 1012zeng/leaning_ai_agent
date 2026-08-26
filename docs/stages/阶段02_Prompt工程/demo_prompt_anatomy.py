"""
demo_prompt_anatomy.py  ——  模块 1：感受 system prompt 的作用
运行前：pip install openai   并设置环境变量 DEEPSEEK_API_KEY（或换成 OPENAI_API_KEY + 改 base_url）
运行方式：python demo_prompt_anatomy.py
预期：实验 1 输出通用定义；实验 2 强制出现类比且只有一句话。
"""
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)


def chat(system: str, user: str) -> str:
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0,
    )
    return resp.choices[0].message.content


print("=== 实验 1：无 system ===")
print(chat("", "用一句话解释什么是 Token"))

print("\n=== 实验 2：有 system（角色 + 输出约束）===")
print(chat(
    "你是一名资深 AI 讲师，擅长用生活中的类比解释技术概念。回答限 1 句话，且必须包含一个类比。",
    "用一句话解释什么是 Token",
))

print("\n=== 实验 3：system 给输出格式 ===")
print(chat(
    "你是 JSON 生成器。只输出 JSON，不要任何解释。字段：term（术语）, definition（一句话定义）。",
    "解释什么是 Token",
))
