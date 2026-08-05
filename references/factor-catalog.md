# 因子清单 · Futures CTA Alpha Factor Catalog

商品期货因子库，对标股票侧 `skill-factor-alpha191-alpha101`。每个因子给出：
**代号 · 因子族 · 计算式 · 数据接口(Pandadata) · 方向假设(预期 IC 符号) · 备注**。

## 通用约定

- **计算标的**：各品种主力**连续（后复权）合约**日线，由 `scripts/build_continuous.py` 构建
  （见 [[continuous-contract]]）。截面类因子在**同一交易日跨品种**计算。
- **符号**：`P_t` 连续后复权收盘；`Pn`/`Pf` 近月/次月合约结算价，`Dn`/`Df` 到期天数；
  `OI_t` 持仓量；`r_t = ln(P_t/P_{t-1})`；`HV_L` = L 日 `r` 的年化标准差。
- **方向假设**：`IC+` = 因子值越大、未来收益越高（多高空低）；`IC−` = 反向。
  方向假设是**先验**，最终以 `skill-ic-analysis` 实测为准（见 SKILL.md 质量标准）。
- **防泄漏**：所有因子在 `t` 日仅用 `≤ t` 的数据；未来收益在下游对齐 `t+1` 开盘。
- **标准化**：原始因子值输出后，下游按需截面 winsorize + zscore（本库产出原始值，不做择时）。

---

> ⚠️ **实测校准（2018–2026, 30 品种, 见 [[l3-evidence-ic]]）**：动量族先验多被推翻——
> **中国商品是反转市**。`tsmom_63`/`ema_xover`/`breakout` 实测为**反转**（IC@T20 −7%/−5.5%/−2.4%，
> t 达 −11），只有 `tsmom_252_21`（12-1 长动量）保持弱正。方向列已加"实测"。

## A. 时序动量 Time-Series Momentum（★★★先验，实测多为反转）

| 代号 | 计算式 | 数据接口 | 先验→实测 | 备注 |
|---|---|---|---|---|
| `tsmom_252` | `P_t / P_{t-252} − 1` | `get_future_daily` | IC+ → ~0 | 经典 12 月动量；实测无效 |
| `tsmom_252_21` | `P_{t-21} / P_{t-252} − 1` | `get_future_daily` | IC+ → **IC+ ✅** | 12−1 长动量；实测 t=+3.1 保留 |
| `tsmom_63` | `P_t / P_{t-63} − 1` | `get_future_daily` | IC+ → **IC− ❗** | 3 月动量；实测**强反转** t=−11，反向用 |
| `breakout_55` | `clip((P_t − mid)/(0.5·(HH_55−LL_55)), −1, 1)`，`mid=(HH_55+LL_55)/2` | `get_future_daily` | IC+ → **IC−** | 唐奇安突破；实测反转 |
| `ema_xover_20_100` | `(EMA_20 − EMA_100) / (HV_20 · P_t)` | `get_future_daily` | IC+ → **IC−** | 快慢均线；实测反转 t=−9.4 |

## B. 截面动量 Cross-Sectional Momentum（同 A，实测同向反转）

| 代号 | 计算式 | 数据接口 | 先验→实测 | 备注 |
|---|---|---|---|---|
| `xsmom_252_21` | 跨品种对 `P_{t-21}/P_{t-252}−1` 排序 | `get_future_daily` | IC+ → **IC+ ✅** | 12-1 截面；实测 t=+3.1 保留 |
| `xsmom_63` | 跨品种对 `P_t/P_{t-63}−1` 排序 | `get_future_daily` | IC+ → **IC− ❗** | 3 月截面；实测强反转 t=−11 |

> ⚠️ **实测校准（2023–2026, 30 品种, 新浪单合约近/次月, 见 [[l3-evidence-ic]]）**：
> **中国商品 carry 与全球相反！** `carry_ann` 实测 IC@T20 = **−4.1%(t=−5.1)**，
> `ts_slope`(=−carry) 实测 **IC+ (t=+5.1)**——即 **contango 品种跑赢、backwardation 跑输**，
> 与全球"做多 backwardation"正相反。且 `ts_slope` 是全库**净 Sharpe 最高(+0.59)、回撤最小(−14%)**的
> 可交易因子。方向列已按实测覆盖。(carry 为新浪单合约 proxy，待 Pandadata 精确数据复核。)

## C. Carry / 展期收益 Carry & Roll（★★★先验，实测方向与全球相反）

| 代号 | 计算式 | 数据接口 | 先验→实测 | 备注 |
|---|---|---|---|---|
| `carry_ann` | `(Pn/Pf − 1) · 365/(Df − Dn)` | `get_future_term_structure` | IC+ → **IC− ❗** | 中国 backwardation 反而跑输；t=−5.1 |
| `roll_return_63` | 63 日累计 `(连续收益 − 单合约价格收益)` | `build_continuous.py` 展期日志 | IC+ → 待测 | 实现展期收益（Pandadata 未接，未测） |
| `basis_mom_20` | `basis_t − basis_{t−20}`，`basis=(现货−Pn)/现货` | `get_future_basis` | IC+ → 待测 | 需现货价，新浪无，**未测** |
| `vol_scaled_carry` | `carry_ann / HV_20` | 同 `carry_ann` | IC+ → **IC− ❗** | 同 carry 反向；t=−8.2 |

## D. 期限结构 Term Structure（实测：contango 跑赢，最佳可交易因子）

| 代号 | 计算式 | 数据接口 | 先验→实测 | 备注 |
|---|---|---|---|---|
| `ts_slope` | `ln(Pf/Pn) / (Df − Dn)` | `get_future_term_structure` | IC− → **IC+ ✅⭐** | contango 跑赢；净 Sharpe +0.59、回撤仅 −14%，全库最佳 |
| `ts_curvature` | `(P3 − 2·P2 + P1)` 三点曲率 | `get_future_term_structure` | 探索 → 待测 | 需三点期限结构（Pandadata），**未测** |

## E. 持仓/情绪 Positioning（COT 类，方向需实测）

| 代号 | 计算式 | 数据接口 | 方向 | 备注 |
|---|---|---|---|---|
| `oi_price_confirm_20` | `sign(P_t−P_{t−20}) · ln(OI_t/OI_{t−20})` | `get_future_daily` | IC+ | 趋势+增仓确认 |
| `broker_net_chg_5` | `Δ(前 N 席位净多头, 5 日) / OI_t` | `get_broker_netmarg_change` / `get_future_netcap_change` | IC+ | 跟主力增净多（先验，需实测） |
| `ls_ratio_z` | 散户多空比的 60 日 z-score | `get_future_ls_ratio` | **IC−** | 多空比过高=拥挤多头，反向 |
| `virtual_ratio_chg` | `Δ虚实盘比(20 日)` | `get_future_virtual_ratio` | 探索 | 交割博弈，先验不定 |

## F. 库存/仓单/现货 Inventory & Spot（IC−，供给压力）

| 代号 | 计算式 | 数据接口 | 方向 | 备注 |
|---|---|---|---|---|
| `inventory_mom_20` | `ln(库存_t / 库存_{t−20})` | `get_future_inventory` | **IC−** | 累库→过剩→偏空 |
| `receipt_mom_20` | `ln(仓单_t / 仓单_{t−20})` | `get_future_warehouse_receipt` | **IC−** | 仓单增→交割压力→偏空 |
| `spot_profit_z` | 现货/加工利润的 60 日 z-score | `get_future_spot_profit` | **IC−** | 高利润→增产→均值回归偏空 |

## G. 波动率/反转 Volatility & Reversal

| 代号 | 计算式 | 数据接口 | 方向 | 备注 |
|---|---|---|---|---|
| `lowvol` | `− HV_20` | `get_future_daily` | IC+ → **IC+ ✅最强** | 低波动跑赢；实测 t=+5.7，全库最强信号 |
| `st_reversal_5` | `− (P_t/P_{t−5} − 1)` | `get_future_daily` | IC+ → **IC+ ✅** | 短期反转；实测 t=+3.3 |

---

## 因子族与先验强度小结

| 因子族 | 先验强度 | deepview 是否触及 |
|---|---|---|
| A 时序动量 | ★★★（CTA 基石） | ❌ 完全没有 |
| C Carry/展期 | ★★★（商品最稳健） | 只做基差**研判**，不算因子值 |
| F 库存/仓单 | ★★ | 只做库存**叙事** |
| B 截面动量 | ★★ | ❌ |
| D 期限结构 | ★★（与 C 互补） | 只研判 |
| G 波动率/反转 | ★★ | ❌ |
| E 持仓/情绪 | ★（方向需实测） | 只做席位**博弈叙事** |

> 与 `skill-futures-deepview-analyst` 的边界：deepview 用相同数据源产出**人读研判报告**；
> 本库产出 **date×variety×factor 的结构化因子面板**，下游对接 `factor-evaluate`/`ic-analysis`/
> `backtest`。同数据、不同产物、不同下游。详见 SKILL.md「与 deepview-analyst 的分工」。
