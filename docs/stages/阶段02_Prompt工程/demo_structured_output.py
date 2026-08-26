"""
demo_structured_output.py  ——  模块 4：三种结构化输出方式 + 容错解析 + Pydantic 校验
运行前：pip install openai pydantic   并设置环境变量 DEEPSEEK_API_KEY
运行方式：python demo_structured_output.py
预期：方式 1 可能混入废话；方式 2 纯 JSON；方式 3 从不干净输出中恢复结构化数据。
"""
import json
import os
import re

from openai import OpenAI
from pydantic import BaseModel, ValidationError
from typing import List

client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

USER_INPUT = "张伟，28 岁，是一名后端工程师，擅长 Python 和 Go。"


def extract(system, user, response_format=None):
    kwargs = dict(
        model="deepseek-chat",
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0,
    )
    if response_format:
        kwargs["response_format"] = response_format
    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content


# 方式 1：自然语言要求（不稳定）
print("=== 方式 1：自然语言要求 ===")
out1 = extract("从句子中提取姓名、年龄、职业、技能，输出 JSON。", USER_INPUT)
print("原始输出:", out1)

# 方式 2：JSON Mode
print("\n=== 方式 2：JSON Mode ===")
out2 = extract(
    "从句子中提取姓名、年龄、职业、技能（数组）。输出 JSON，字段：name, age, job, skills。",
    USER_INPUT,
    response_format={"type": "json_object"},
)
print("原始输出:", out2)
print("解析:", json.loads(out2))

# 方式 3：容错解析（生产常用）
def parse_json_robust(text: str) -> dict:
    """从模型输出中尽力提取 JSON，兼容 ```json 包裹、前后废话"""
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if m:
        text = m.group(1)
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        text = m.group(0)
    return json.loads(text)


print("\n=== 方式 3：容错解析 ===")
parsed = parse_json_robust(out1)
print("从方式 1 输出解析:", parsed)

# Pydantic 校验
class Person(BaseModel):
    name: str
    age: int
    job: str
    skills: List[str]


print("\n=== Pydantic 校验 ===")
try:
    person = Person(**parsed)
    print("校验通过:", person.model_dump())
except (json.JSONDecodeError, ValidationError) as e:
    print("解析/校验失败，需要重试:", e)
