# 数据版本与变更流程

## 不可变发布

`datasets/<dataset_id>/<version>/` 一旦进入 PR 审查即视为发布候选。合并后不得原地修改；任何 query、split、source metadata、正文、真值、标签或 chunk profile 变化都创建新 SemVer 目录并重算 manifest。

| 变化 | 版本级别 | 处理 |
|---|---|---|
| 修正文档说明，不改变数据字节 | patch | 只改 `evals/` 文档，不重发数据集。 |
| 修正文案、证据 span、标签或新增兼容题例 | minor | 复制到新目录，保留 case key，重新编译并复核受影响题例。 |
| 改变标注含义、split 纪律、必填字段或 ID 算法 | major | 并行保留旧 major，提供迁移说明，禁止覆盖旧目录。 |
| 改变 chunk profile | minor 或 major | 生成全新 chunk catalog；旧标签不得按相似文本猜测迁移。 |

## 变更步骤

1. 在新版本目录修改源文档或 `authoring/cases.jsonl`，记录变更理由和受影响 case keys。
2. 运行 `python tools/compile_dataset.py --dataset <目录>` 生成发布 JSONL 与 manifest。
3. 运行 `python validate_dataset.py --dataset <目录>`；任何 stale label、孤立 claim、坏 span、哈希或分布错误都阻断发布。
4. 对受影响题例执行来源复核，确认必要主张逐条有证据、不可接受主张仍能捕获目标错误。
5. 在 PR 中列出新增、删除、语义变化和 split 变化；test 题被看过或用于调参时必须重建 test split。

## 标注状态

本数据集使用合成语料和逐条来源规则审查，provenance 明确写为 `agent_assisted_manual_curation`，不冒充双人盲审或 LLM 自动生成真值。生产门禁若要求人工双审，应在不覆盖本版本的前提下发布新版本并记录匿名 reviewer ID。
