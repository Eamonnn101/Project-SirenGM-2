---
name: event_schema
entity: event
---

# Event Frontmatter Schema

## 必填

- `slug` (string)
- `name` (string)
- `kind` (enum): `key` (固定回合的锚点) / `triggerable` (条件触发) / `dangerous_divergence` (玩家越界时的保护性事件)

## 可选

- `preconditions` (list[string]): 触发条件的自由标签，例如 `turn<=3`, `at:outer_gate`, `relationship:heroine>=3`, `has_item:spirit_talisman`。

## Body

覆盖：触发条件、叙事走向、必要时向 `session_log.jsonl` 记一条摘要或向 `divergences.jsonl` 追加一条 `DivergenceNote` 的规则。
