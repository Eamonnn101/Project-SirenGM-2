---
name: ingest_draft_system
stage: ingest.draft
---

# Ingest Draft · Xianxia genre instructions

These are genre-level instructions the agent follows during the **draft**
step of `playbooks/ingest.md`. For each entity discovered during extract,
consolidate mentions into a single schema-valid page under
`packs/<pack>/<kind>/<slug>.md`. Schemas live in
`genre_packs/xianxia/schemas/<kind>.schema.md`.

## 输入

- `entity_slug`, `entity_kind`, 多条 `mentions`（每条含 `chunk_id`、`evidence`、字段片段）。
- 对应的 entity schema（来自 `genre_packs/xianxia/schemas/<entity_kind>.schema.md`）。

## 输出

严格符合对应 schema 的 frontmatter + markdown body。**不要**引入原文中未出现的身份设定或事件。对于有冲突的 mention（例如两个 chunk 给出不同的 `cultivation_stage`），保留较晚 chunk 的值并把**矛盾点**追加到 user pack 的 `contradictions/ambiguous_points.md`。

## 修仙题材约束

- 人物 body 覆盖：外貌（一两笔白描）、性格、核心动机、与主角的关系起点、能力、不可违反的人物定数。
- 门派 body 覆盖：立宗根基 / 核心功法、内部分层、重要盟约或宿敌、禁令、近期动向。
- 地点 body 覆盖：格局、常驻 NPC 类型、环境线索、常见风险、进入条件。
- **不要**在页面中写"玩家会……"这类 meta 叙述；entity 页面是世界本身的描述，不涉及玩家路径。
- Body 中出现的跨实体引用使用 `[[slug]]` 格式，便于后续 cross-linking。

## 反例

- 给凡人或低境界 NPC 赋予高境界能力。
- 在 body 中引入原文从未提及的宗门分支或门人。
- 写"如果玩家 X 则 Y"——这是 arc/event 页的职责。
