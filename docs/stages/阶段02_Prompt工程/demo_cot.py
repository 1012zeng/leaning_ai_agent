"""
demo_cot.py  ——  模块 3：直接答 vs 思维链 CoT vs Self-Consistency
运行前：pip install openai   并设置环境变量 DEEPSEEK_API_KEY
运行方式：python demo_cot.py
预期：直接答易在优惠叠加上出错；CoT 分步计算正确率提升；Self-Consistency 用投票兜底。
"""
import os
from collections import Counter
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

QUESTION = """
商店促销：满 200 减 30，满 500 减 80，优惠可叠加。
小明买了 3 件 A 商品（每件 120 元）和 2 件 B 商品（每件 95 元），他应付多少？
"""


def chat(system, user, temperature=0):
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=temperature,
    )
    return resp.choices[0].message.content


print("=== 1. 直接答 ===")
print(chat("你是一个数学助手。", QUESTION))

print("\n=== 2. 思维链 CoT ===")
print(chat(
    "你是一个数学助手。请逐步推理，写出每一步计算，最后给出答案。",
    QUESTION,
))

print("\n=== 3. Self-Consistency（5 次采样，取多数）===")
answers = []
for i in range(5):
    out = chat(
        "你是一个数学助手。请逐步推理，最后用「最终答案：X元」格式给出答案。",
        QUESTION,
        temperature=0.7,
    )
    for line in out.split("\n"):
        if "最终答案" in line:
            answers.append(line.strip())
            break
    print(f"  第{i+1}次: {answers[-1] if answers else '未提取到'}")

print("\n各次答案:", answers)
print("多数投票:", Counter(answers).most_common(1))
