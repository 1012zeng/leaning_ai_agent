"""
demo_evaluation.py  ——  模块 8：Prompt 评测集 + 自动评分 + LLM-as-Judge
运行前：pip install openai   并设置环境变量 DEEPSEEK_API_KEY
运行方式：python demo_evaluation.py
预期：V2 在"褒贬参半"的 case 上优于 V1，评测分数量化差异。
"""
import json
import os

from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

# 评测集：情感分类任务（含边界 case）
EVAL_SET = [
    {"input": "快递很快，包装完好！", "expected": "正面"},
    {"input": "等了一周才到，箱子都压扁了", "expected": "负面"},
    {"input": "东西一般，没什么特别的", "expected": "中立"},
    {"input": "手机屏幕很清晰，但电池一天要充三次", "expected": "中立"},
    {"input": "再也不买了，质量太差", "expected": "负面"},
    {"input": "性价比超高，会回购", "expected": "正面"},
    {"input": "说不上好也说不上坏", "expected": "中立"},
    {"input": "客服态度差，但商品本身还行", "expected": "中立"},
]

PROMPT_V1 = "对评论做情感分类，只输出 正面/负面/中立。"
PROMPT_V2 = """对评论做情感分类。
规则：
- 整体满意 → 正面
- 整体不满 → 负面
- 褒贬参半或无明显情感 → 中立
只输出一个词：正面、负面 或 中立。"""


def run_prompt(system, user):
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0,
    )
    return resp.choices[0].message.content.strip()


def evaluate(system, eval_set):
    correct = 0
    results = []
    for item in eval_set:
        out = run_prompt(system, item["input"])
        ok = out == item["expected"]
        correct += ok
        results.append({"input": item["input"], "output": out, "expected": item["expected"], "ok": ok})
    return correct / len(eval_set), results


print("=== Prompt V1 评测 ===")
acc1, r1 = evaluate(PROMPT_V1, EVAL_SET)
print(f"准确率: {acc1:.0%}")
for r in r1:
    mark = "✓" if r["ok"] else "✗"
    print(f"  {mark} 输入={r['input']!r} 输出={r['output']!r} 期望={r['expected']!r}")

print("\n=== Prompt V2 评测 ===")
acc2, r2 = evaluate(PROMPT_V2, EVAL_SET)
print(f"准确率: {acc2:.0%}")
for r in r2:
    mark = "✓" if r["ok"] else "✗"
    print(f"  {mark} 输入={r['input']!r} 输出={r['output']!r} 期望={r['expected']!r}")

print(f"\n结论: V2 vs V1 准确率 {acc2:.0%} vs {acc1:.0%}")


# LLM-as-Judge：用强模型当裁判
JUDGE_PROMPT = """你是一名评测裁判。给定【任务描述】【输入】【输出】【期望】，判断输出是否满足任务要求。
输出 JSON：{"score": 0-10整数, "reason": "简短理由", "pass": true/false}"""


def llm_judge(task, input_text, output, expected):
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": JUDGE_PROMPT},
            {"role": "user", "content": f"【任务】{task}\n【输入】{input_text}\n【输出】{output}\n【期望】{expected}"},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)


print("\n=== LLM-as-Judge：抽查 V2 的结果 ===")
for r in r2[:3]:
    judge = llm_judge("情感分类", r["input"], r["output"], r["expected"])
    print(f"  输入={r['input']!r} 评分={judge['score']} 理由={judge['reason']}")
