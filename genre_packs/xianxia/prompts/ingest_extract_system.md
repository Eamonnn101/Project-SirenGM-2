---
name: ingest_extract_system
stage: ingest.extract
---

# Ingest Extract · Xianxia genre instructions

These are genre-level instructions the agent follows during the **extract**
step of `playbooks/ingest.md`. Read this file once before processing any
chunk; then, for each chunk in `packs/<pack>/.ingest/chunks.jsonl`, follow
the rules below to produce a line in `packs/<pack>/.ingest/mentions.jsonl`.

你的任务：**从提供的章节文本中，抽取出人物、门派、地点、功法/法器/丹药、事件、关系**，并以下列结构化格式（JSON）返回。你**不要**臆造文本中没有出现的内容。若章节文本中仅提到某人物的别号、暂未出现本名，则使用别号作为 `aliases`，`name` 留空或标为 `unknown`。

## 每个抽取条目的字段

- `kind`: `character` / `faction` / `location` / `system_item` / `event` / `relationship`
- `slug`: 你给定的 snake_case 英文或拼音 slug；同一实体在同一小说中必须保持 slug 一致。
- `name`: 原文中最常用的中文名。
- `role` / `alignment` / `danger` / `kind`: 按 entity 种类的 schema 选择（见 `genre_packs/xianxia/schemas/`）。
- `source_chunk`: 当前 chunk id。
- `evidence`: 一句直接引自原文的短句（≤60 字），证明该实体/事件在原文中出现。

## 修仙题材约束

- **境界**应使用通用阶梯（气感期 / 筑基 / 金丹 / 元婴 / 化神 / 渡劫）；若原文用了不同命名，额外提供 `stage_raw`（原文词语）与 `stage_normalized`（通用词语）。
- 不抽取**现代词汇**；若原文本身出现不合时代的内容，在 `notes` 中标注。
- 关系条目 `kind: relationship` 用 `from` / `to` / `relation` 字段（如 `disciple` / `rival` / `sect_enemy`）。

## 反例（不要产出）

- 带数值的战斗力 / HP / 属性。
- 原文未出现的事件或人物。
- 对原文的主观评价或推测结论（可记为 `notes` 而非实体）。
