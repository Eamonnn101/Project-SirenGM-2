---
name: canon_guardrails
---

# 修仙 · 通用定数（Genre-level）

这些规则对所有修仙 user pack **默认生效**。user pack 可通过自己的 `canon_guardrails.md` **补充更严格的**定数（例如"本作禁止走火入魔"），但**不得削弱**本文件中的通用定数。

GM 在叙事时必须遵守；状态更新器在玩家行为与此冲突时，应拒绝写入结构化状态并向 save 的 `divergences.jsonl` 追加一条 `DivergenceNote`。

## 修为阶梯

- 境界次序遵循 `systems/cultivation.md` 中的阶梯，**不可跳阶**。
- 突破必须伴随明显的**瓶颈、代价或外部条件**（丹药、机缘、秘境灵气、生死关头）。
- 单次回合中不得跨越一个以上的大境界（气感 → 筑基 是一个大境界跨越）。

## 时代与器物

- 不出现现代科技、现实品牌、非古代汉文化背景之外的特有事物。
- 武器以冷兵器、符箓、丹药、法器为主。火铳与之后的火器不允许出现，除非 user pack 明确引入。

## 魔修红线

- 玩家**不可**突然加入魔门。魔宗 / 魔修 / 邪修只能作为敌对或第三方出现。
- 玩家可在极端情境下**暂时**接触魔功，但必须有明确的代价（心魔、气息转浊、被察觉），并向 `divergences.jsonl` 追加一条 `DivergenceNote`。

## 人物与宗门

- 人物的立场、修为、关系在单次对话中不得无根据地大幅变动。
- NPC 不会因一次交谈而背叛己方宗门、门派或亲人。

## 神通与设定

- 复活、时间倒流、跨世界旅行不允许，除非 user pack 的 `canon_guardrails.md` 显式开启此设定。
- 玩家不能凭空获得超越其修为上限的法器（如筑基期持有元婴法器且能正常使用）。

## 写作

- 叙事与 NPC 台词遵循 `style_guide.md`。
- 未出现在 user pack 中的大门派、大家族、大仇人，若剧情需要新势力，应由玩家行动逐步浮现，并通过 patch 的 `hidden_truths_append` 写入 `meta.json::hidden_truths`，同时向 `divergences.jsonl` 追加一条说明（不得直接写 `hidden_truths.md` — 它由 `render_save.py` 重新渲染）。
