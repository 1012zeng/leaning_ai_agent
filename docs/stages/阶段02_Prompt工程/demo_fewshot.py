"""
demo_fewshot.py  ——  模块 2：零样本 vs 少样本对比
运行前：pip install openai   并设置环境变量 DEEPSEEK_API_KEY
运行方式：python demo_fewshot.py
预期：少样本在格式一致性上更稳，尤其是要求固定格式时优势明显。
"""
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

REVIEW = "手机屏幕很清晰，但电池一天要充三次，系统偶尔卡顿。"


def chat(messages, temperature=0):
    resp = client.chat.completions.create(
        model="deepseek-chat", messages=messages, temperature=temperature
    )
    return resp.choices[0].message.content


# 零样本：只说任务，不给例子
print("=== 零样本 ===")
print(chat([
    {"role": "system", "content": "对评论做情感分类，只输出 正面/负面/中立"},
    {"role": "user", "content": REVIEW},
]))

# 少样本：给 3 个范例
print("\n=== 少样本 ===")
print(chat([
    {"role": "system", "content": "对评论做情感分类，只输出 正面/负面/中立。"},
    {"role": "user", "content": "快递很快，包装完好！"},
    {"role": "assistant", "content": "正面"},
    {"role": "user", "content": "等了一周才到，箱子都压扁了"},
    {"role": "assistant", "content": "负面"},
    {"role": "user", "content": "东西一般，没什么特别的"},
    {"role": "assistant", "content": "中立"},
    {"role": "user", "content": REVIEW},
]))

# 少样本：固定 JSON 格式（优势更明显）
print("\n=== 少样本（固定 JSON 格式）===")
print(chat([
    {"role": "system", "content": "从评论中提取信息，输出 JSON，字段：sentiment(正面/负面/中立), product(产品名)"},
    {"role": "user", "content": "快递很快，包装完好！"},
    {"role": "assistant", "content": '{"sentiment": "正面", "product": "未知"}'},
    {"role": "user", "content": "手机屏幕很清晰，但电池一天要充三次"},
    {"role": "assistant", "content": '{"sentiment": "中立", "product": "手机"}'},
    {"role": "user", "content": REVIEW},
]))
