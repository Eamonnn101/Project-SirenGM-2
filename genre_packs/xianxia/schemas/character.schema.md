---
name: character_schema
entity: character
---

# Character Frontmatter Schema

User-pack 内 `characters/<slug>.md` 的 frontmatter 必须满足以下字段。**ingest 的 draft 阶段在生成人物页时应严格产出这些字段**；缺失字段会被 `lint-pack` 标为问题。

## 必填

- `slug` (string, snake_case): 唯一标识。
- `name` (string): 中文显示名。
- `role` (string): 自由标签，如 `protagonist`、`master`、`rival`、`heroine`、`ally`、`antagonist`、`mentor`、`informant`。

## 可选但推荐

- `aliases` (list[string]): 别名 / 绰号 / 过去的称呼。
- `sect` (string): 所属门派的 slug。空则表示散修 / 凡人。
- `cultivation_stage` (string): 按通用阶梯命名（"气感期三层"等）。凡人可写 "凡人"。
- `status` (enum): `alive` (默认) / `injured` / `unconscious` / `dead` / `missing` / `unknown`。与 `PlayerState.status` 对齐。
- `location` (string): 常驻地点的 slug（非必填，仅用于起始场景匹配）。

## Body

Body 是 GM 使用的参考文字，应覆盖：外貌（一两笔白描）、性格、动机、与主角的关系起点、能力、不可违反的人物定数。

## 反例（ingest 不应生成）

- 数值字段（如 hp / atk）——本 genre 拒绝数值化。
- emoji 表情。
- 未在 user pack 其他实体中出现的跨门派人名（会造成断链，lint 会报错）。
