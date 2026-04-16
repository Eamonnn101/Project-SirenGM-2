---
name: location_schema
entity: location
---

# Location Frontmatter Schema

## 必填

- `slug` (string)
- `name` (string)
- `danger` (enum): `safe` / `guarded` / `hostile` / `deadly`

## 可选

- `region` (string): 大区域名。
- `controlled_by` (string): 掌控势力的 slug。

## Body

覆盖：格局、常驻 NPC 类型、环境线索、常见风险级别、进入条件（若有硬约束）。
