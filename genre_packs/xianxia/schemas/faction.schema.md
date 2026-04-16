---
name: faction_schema
entity: faction
---

# Faction Frontmatter Schema

User-pack 内 `factions/<slug>.md` 的 frontmatter 字段。

## 必填

- `slug` (string, snake_case)
- `name` (string): 中文名。
- `alignment` (string): `orthodox` / `demonic` / `neutral` / `independent` / 其他自定义标签。

## 可选

- `seat` (string): 总坛所在地点的 slug。
- `leaders` (list[string]): 高层人物的 slug 列表。

## Body

覆盖：立宗根基 / 核心功法、内部分层、重要盟约或宿敌、禁令、近期动向。不写具体人物履历（那在 character 页）。
