---
name: arc_schema
entity: arc
---

# Arc Frontmatter Schema

## 必填

- `slug` (string)
- `name` (string)
- `status` (enum): `opening` / `active` / `suspended` / `closed`
- `summary` (string): 一段话概括本 arc 的目标与冲突。

## 可选

- `driving_entities` (list[string]): 本 arc 的主要驱动角色 slug。

## Body

覆盖：节奏（回合数区间）、关键节点、成功/失败出口、与其他 arc 的衔接。
