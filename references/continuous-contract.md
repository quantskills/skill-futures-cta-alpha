# Continuous Contract — 连续合约与展期收益

时序因子（动量/波动/反转）必须在**连续价格序列**上算，不能在单个到期合约上算
（会在换月处断裂）。本库自带 `scripts/build_continuous.py` 做后复权连续合约。
这块 deepview-analyst 没有——它只看单日期限结构快照，不构建连续序列。

## 换月规则（roll）

- **触发**：当次主力合约的成交量/持仓量被下一合约超过，且持续 `confirm_days`（默认 2 日），
  在**下一交易日**换到新主力。主力映射用 `get_future_dominant`。
- **不在到期周换**：避免流动性枯竭与交割干扰；以成交/持仓为准而非纯到期日。
- **换月日**记入展期日志 `roll_log`：`date, variety, old_symbol, new_symbol, old_close, new_close`。

## 后复权拼接（back-adjustment）

在换月日用**比例因子**衔接，保证收益连续、无跳空：

```
factor = old_close_on_roll / new_close_on_roll
调整：换月日之前的所有历史价 × factor（滚动累乘），使拼接点收益 = 真实持仓收益
```

- 采用**比例后复权**（乘法），非加法，避免长序列出现负价。
- 连续价仅用于**收益/动量类**因子；**价差/carry/期限结构**因子仍用原始合约价（`Pn/Pf`），不用连续价。

## 展期收益 Roll Return

```
roll_return_t = 连续序列日收益_t − 当日在持合约的价格收益_t
```

- 换月日两者之差即该次展期收益；非换月日为 0。
- `roll_return_63` = 过去 63 日 `roll_return` 累计，是 `carry_ann` 的**实现版**，二者应同号可对账。
- back-wardation（近>远）品种长期为正展期收益，是商品 CTA carry 因子的经济来源。

## 防泄漏

- 换月决策只用 `≤t` 的成交/持仓，`confirm_days` 确认后**次日**生效——不允许用换月当日之后的信息。
- 后复权因子在 `t` 日只累乘 `≤t` 的换月事件；回测时严禁用全样本一次性复权（会引入未来）。
  本库产出**逐日可复现**的连续价，`validate_factors.py` 抽查换月点收益连续性。

## 未来拆分

`build_continuous.py` 逻辑独立、可复用，未来可拆为独立基础设施 skill
`skill-futures-continuous-contract`，供本库与期货回测协议共用。当前先内置。
